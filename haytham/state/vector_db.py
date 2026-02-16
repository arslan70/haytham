"""Vector Database for System State.

Uses LanceDB for storing and querying system state entries
with semantic search capabilities.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

import lancedb
import pyarrow as pa

from .embedder import TitanEmbedder, get_embedder
from .schema import IDGenerator, SystemStateEntry

logger = logging.getLogger(__name__)


class DuplicateEntryError(Exception):
    """Raised when attempting to add an entry that already exists.

    This error indicates that an entry with the same name and type
    already exists in the database. To update an existing entry,
    use the supersede_entry() method instead.
    """

    pass


# LanceDB table schema
# Note: LanceDB infers schema from first insert, but we define it
# explicitly for documentation and type safety
ENTRIES_SCHEMA = pa.schema(
    [
        # Vector (for similarity search) - Titan produces 1024 dimensions
        pa.field("vector", pa.list_(pa.float32(), 1024)),
        # Identity
        pa.field("id", pa.string()),
        pa.field("type", pa.string()),
        pa.field("subtype", pa.string()),
        # Content
        pa.field("name", pa.string()),
        pa.field("description", pa.string()),
        # Classification
        pa.field("tags", pa.list_(pa.string())),
        # Relationships (stored as lists)
        pa.field("affects", pa.list_(pa.string())),
        pa.field("depends_on", pa.list_(pa.string())),
        # Temporal
        pa.field("created_at", pa.string()),  # ISO format string
        pa.field("supersedes", pa.string()),
        pa.field("superseded_by", pa.string()),
        # Provenance
        pa.field("source_stage", pa.string()),
        pa.field("rationale", pa.string()),
        # Flexible metadata (JSON string)
        pa.field("metadata_json", pa.string()),
    ]
)


class SystemStateDB:
    """Vector database for system state management.

    Provides methods for storing and querying system state entries
    (capabilities, decisions, entities, constraints) with semantic
    search and temporal filtering.
    """

    TABLE_NAME = "system_state"

    def __init__(
        self,
        db_path: str | Path,
        embedder: TitanEmbedder | None = None,
    ):
        """Initialize the system state database.

        Args:
            db_path: Path to the LanceDB database directory
            embedder: TitanEmbedder instance. If None, uses the cached singleton.
        """
        self.db_path = Path(db_path)
        self.db_path.mkdir(parents=True, exist_ok=True)

        self.db = lancedb.connect(str(self.db_path))
        self.embedder = embedder or get_embedder()
        self.id_generator = IDGenerator()

        self._ensure_table()
        self._sync_id_counters()

        logger.info(f"SystemStateDB initialized at {self.db_path}")

    def _ensure_table(self) -> None:
        """Create table if it doesn't exist."""
        if self.TABLE_NAME not in self.db.table_names():
            logger.info(f"Creating table {self.TABLE_NAME}")
            # Create with empty data - schema will be set on first insert
            self._table = None
        else:
            self._table = self.db.open_table(self.TABLE_NAME)
            logger.info(f"Opened existing table {self.TABLE_NAME}")

    def _sync_id_counters(self) -> None:
        """Sync ID counters with existing data."""
        if self._table is None:
            return

        try:
            # Get all existing IDs to find max per prefix
            results = self._table.search().limit(10000).to_list()

            prefix_max: dict[str, int] = {}
            for row in results:
                entry_id = row.get("id", "")
                if "-" in entry_id:
                    # Extract prefix and number (e.g., "CAP-F-001" -> "CAP-F-", 1)
                    parts = entry_id.rsplit("-", 1)
                    if len(parts) == 2 and parts[1].isdigit():
                        prefix = parts[0] + "-"
                        num = int(parts[1])
                        prefix_max[prefix] = max(prefix_max.get(prefix, 0), num)

            # Set counters to start after max
            for prefix, max_num in prefix_max.items():
                self.id_generator.set_counter(prefix, max_num + 1)
                logger.debug(f"Set counter for {prefix} to {max_num + 1}")

        except Exception as e:
            logger.warning(f"Failed to sync ID counters: {e}")

    @property
    def table(self):
        """Get the LanceDB table, creating if needed."""
        if self._table is None:
            if self.TABLE_NAME in self.db.table_names():
                self._table = self.db.open_table(self.TABLE_NAME)
        return self._table

    def _entry_to_record(self, entry: SystemStateEntry, vector: list[float]) -> dict[str, Any]:
        """Convert a SystemStateEntry to a LanceDB record."""
        return {
            "vector": vector,
            "id": entry.id,
            "type": entry.type,
            "subtype": entry.subtype or "",
            "name": entry.name,
            "description": entry.description,
            "tags": entry.tags,
            "affects": entry.affects,
            "depends_on": entry.depends_on,
            "created_at": entry.created_at.isoformat(),
            "supersedes": entry.supersedes or "",
            "superseded_by": entry.superseded_by or "",
            "source_stage": entry.source_stage or "",
            "rationale": entry.rationale or "",
            "metadata_json": json.dumps(entry.metadata),
        }

    def _record_to_dict(self, record: dict) -> dict[str, Any]:
        """Convert a LanceDB record to a clean dictionary."""
        result = dict(record)

        # Remove vector from output (large, not needed for display)
        result.pop("vector", None)
        result.pop("_distance", None)  # LanceDB adds this for search results

        # Parse metadata JSON
        if "metadata_json" in result:
            try:
                result["metadata"] = json.loads(result["metadata_json"])
            except (json.JSONDecodeError, TypeError):
                result["metadata"] = {}
            del result["metadata_json"]

        # Convert empty strings to None for nullable fields
        for field in [
            "supersedes",
            "superseded_by",
            "subtype",
            "rationale",
            "source_stage",
        ]:
            if result.get(field) == "":
                result[field] = None

        # Parse created_at back to datetime
        if "created_at" in result and result["created_at"]:
            try:
                result["created_at"] = datetime.fromisoformat(result["created_at"])
            except (ValueError, TypeError):
                pass

        return result

    # ==========================================================================
    # Write Operations
    # ==========================================================================

    def find_by_name(
        self,
        name: str,
        entry_type: str | None = None,
        include_superseded: bool = False,
    ) -> dict | None:
        """Find an entry by exact name match.

        Args:
            name: The exact name to search for
            entry_type: Optional type filter (capability, decision, etc.)
            include_superseded: If True, include superseded entries

        Returns:
            The entry as a dict, or None if not found
        """
        if self._table is None:
            return None

        try:
            # Build filter - escape single quotes in name
            escaped_name = name.replace("'", "''")
            filters = [f"name = '{escaped_name}'"]

            if not include_superseded:
                filters.append("superseded_by = ''")
            if entry_type:
                filters.append(f"type = '{entry_type}'")

            where_clause = " AND ".join(filters)
            results = self._table.search().where(where_clause).limit(1).to_list()

            if results:
                return self._record_to_dict(results[0])
            return None
        except Exception as e:
            logger.error(f"Failed to find entry by name '{name}': {e}")
            return None

    def add_entry(self, entry: SystemStateEntry) -> str:
        """Add a new entry to the database.

        This method checks for duplicates by name+type before inserting.
        To update an existing entry, use supersede_entry() instead.

        Args:
            entry: The entry to add. If id is empty, one will be generated.

        Returns:
            The ID of the added entry.

        Raises:
            DuplicateEntryError: If an entry with the same name+type already exists
        """
        # Check for duplicate by name + type (only for non-superseded entries)
        existing = self.find_by_name(
            name=entry.name,
            entry_type=entry.type,
            include_superseded=False,
        )

        if existing:
            raise DuplicateEntryError(
                f"Entry with name '{entry.name}' and type '{entry.type}' already exists "
                f"(id={existing['id']}). Use supersede_entry() to update instead."
            )

        return self._add_entry_unchecked(entry)

    def _add_entry_unchecked(self, entry: SystemStateEntry) -> str:
        """Internal method to add entry without duplicate checking.

        Used by add_entry (after validation) and supersede_entry.

        Args:
            entry: The entry to add. If id is empty, one will be generated.

        Returns:
            The ID of the added entry.
        """
        # Generate ID if not provided
        if not entry.id:
            entry.id = self.id_generator.next_id(entry.type, entry.subtype)

        # Generate embedding
        text_to_embed = entry.get_text_for_embedding()
        vector = self.embedder.embed(text_to_embed)

        # Create record
        record = self._entry_to_record(entry, vector)

        # Add to table (create table if first entry)
        if self._table is None:
            self._table = self.db.create_table(self.TABLE_NAME, [record])
            logger.info(f"Created table with first entry: {entry.id}")
        else:
            self._table.add([record])
            logger.info(f"Added entry: {entry.id}")

        return entry.id

    def supersede_entry(self, old_id: str, new_entry: SystemStateEntry) -> str:
        """Create a new version of an entry and mark the old one as superseded.

        This method bypasses the duplicate check because it's specifically
        designed to create a new version with the same name.

        Args:
            old_id: ID of the entry to supersede
            new_entry: The new entry (supersedes field will be set automatically)

        Returns:
            The ID of the new entry

        Raises:
            ValueError: If old_id is not found
        """
        # Get old entry first
        old_entry = self.get_by_id(old_id)
        if not old_entry:
            raise ValueError(f"Entry {old_id} not found")

        # Mark old entry as superseded FIRST (before adding new)
        # This prevents the duplicate check from failing
        # LanceDB doesn't support in-place updates well, so we use a workaround:
        # Delete old, re-add with superseded_by set to a placeholder, then update

        # Delete old entry
        self._table.delete(f"id = '{old_id}'")

        # Re-add with superseded_by set (placeholder - will update after new entry created)
        old_entry_obj = SystemStateEntry(
            id=old_id,
            type=old_entry["type"],
            subtype=old_entry.get("subtype"),
            name=old_entry["name"],
            description=old_entry["description"],
            tags=old_entry.get("tags", []),
            affects=old_entry.get("affects", []),
            depends_on=old_entry.get("depends_on", []),
            created_at=old_entry.get("created_at", datetime.utcnow()),
            supersedes=old_entry.get("supersedes"),
            superseded_by="PENDING",  # Temporary placeholder
            source_stage=old_entry.get("source_stage"),
            rationale=old_entry.get("rationale"),
            metadata=old_entry.get("metadata", {}),
        )

        # Re-embed and add old entry (now marked as superseded)
        text_to_embed = old_entry_obj.get_text_for_embedding()
        vector = self.embedder.embed(text_to_embed)
        record = self._entry_to_record(old_entry_obj, vector)
        self._table.add([record])

        # Now add new entry (without duplicate check since old is superseded)
        new_entry.supersedes = old_id
        new_id = self._add_entry_unchecked(new_entry)

        # Update old entry with correct superseded_by
        self._table.delete(f"id = '{old_id}'")
        old_entry_obj.superseded_by = new_id
        text_to_embed = old_entry_obj.get_text_for_embedding()
        vector = self.embedder.embed(text_to_embed)
        record = self._entry_to_record(old_entry_obj, vector)
        self._table.add([record])

        logger.info(f"Superseded {old_id} with {new_id}")
        return new_id

    def delete_entry(self, entry_id: str) -> bool:
        """Delete an entry by ID.

        Args:
            entry_id: ID of the entry to delete

        Returns:
            True if deleted, False if not found
        """
        if self._table is None:
            return False

        try:
            self._table.delete(f"id = '{entry_id}'")
            logger.info(f"Deleted entry: {entry_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete {entry_id}: {e}")
            return False

    # ==========================================================================
    # Read Operations
    # ==========================================================================

    def get_by_id(self, entry_id: str) -> dict | None:
        """Get a specific entry by ID.

        Args:
            entry_id: The ID to look up

        Returns:
            The entry as a dict, or None if not found
        """
        if self._table is None:
            return None

        try:
            results = self._table.search().where(f"id = '{entry_id}'").limit(1).to_list()
            if results:
                return self._record_to_dict(results[0])
            return None
        except Exception as e:
            logger.error(f"Failed to get entry {entry_id}: {e}")
            return None

    def find_similar(
        self,
        query: str,
        entry_type: str | None = None,
        subtype: str | None = None,
        include_superseded: bool = False,
        limit: int = 5,
    ) -> list[dict]:
        """Find semantically similar entries.

        Args:
            query: Text to search for
            entry_type: Filter by entry type (capability, decision, etc.)
            subtype: Filter by subtype (functional, non_functional, etc.)
            include_superseded: If True, include superseded entries
            limit: Maximum number of results

        Returns:
            List of matching entries, ordered by similarity
        """
        if self._table is None:
            return []

        # Generate query embedding
        vector = self.embedder.embed(query)

        # Build filter
        filters = []
        if not include_superseded:
            filters.append("superseded_by = ''")
        if entry_type:
            filters.append(f"type = '{entry_type}'")
        if subtype:
            filters.append(f"subtype = '{subtype}'")

        where_clause = " AND ".join(filters) if filters else None

        try:
            search = self._table.search(vector).limit(limit)
            if where_clause:
                search = search.where(where_clause)

            results = search.to_list()
            return [self._record_to_dict(r) for r in results]
        except Exception as e:
            logger.error(f"Similarity search failed: {e}")
            return []

    def get_current_state(
        self,
        entry_type: str | None = None,
        subtype: str | None = None,
    ) -> list[dict]:
        """Get all current (non-superseded) entries.

        Args:
            entry_type: Filter by entry type
            subtype: Filter by subtype

        Returns:
            List of current entries
        """
        if self._table is None:
            return []

        filters = ["superseded_by = ''"]
        if entry_type:
            filters.append(f"type = '{entry_type}'")
        if subtype:
            filters.append(f"subtype = '{subtype}'")

        where_clause = " AND ".join(filters)

        try:
            results = self._table.search().where(where_clause).limit(10000).to_list()
            return [self._record_to_dict(r) for r in results]
        except Exception as e:
            logger.error(f"Failed to get current state: {e}")
            return []

    def get_capabilities(self, subtype: str | None = None) -> list[dict]:
        """Get all current capabilities.

        Args:
            subtype: Filter by capability subtype (functional, non_functional, operational)

        Returns:
            List of current capabilities
        """
        return self.get_current_state(entry_type="capability", subtype=subtype)

    def get_decisions(self) -> list[dict]:
        """Get all current decisions."""
        return self.get_current_state(entry_type="decision")

    def get_entities(self) -> list[dict]:
        """Get all current entities."""
        return self.get_current_state(entry_type="entity")

    def get_history(self, entry_id: str) -> list[dict]:
        """Get full history of an entry by following supersedes chain.

        Args:
            entry_id: Starting entry ID

        Returns:
            List of entries from newest to oldest
        """
        history = []
        current = self.get_by_id(entry_id)

        while current:
            history.append(current)
            supersedes_id = current.get("supersedes")
            current = self.get_by_id(supersedes_id) if supersedes_id else None

        return history

    def impact_analysis(self, query: str, limit: int = 10) -> dict:
        """Find what would be affected by a proposed change.

        Args:
            query: Description of the proposed change
            limit: Maximum number of related entries to find

        Returns:
            Dict with 'directly_related' and 'potentially_affected' entries
        """
        related = self.find_similar(query, limit=limit)

        affected_ids = set()
        for entry in related:
            affected_ids.update(entry.get("affects", []))

        # Fetch affected entries
        affected_entries = []
        for aid in affected_ids:
            entry = self.get_by_id(aid)
            if entry:
                affected_entries.append(entry)

        return {
            "directly_related": related,
            "potentially_affected": affected_entries,
        }

    def count(self, entry_type: str | None = None) -> int:
        """Count entries in the database.

        Args:
            entry_type: Filter by entry type, or None for all

        Returns:
            Number of matching entries
        """
        if self._table is None:
            return 0

        try:
            if entry_type:
                results = (
                    self._table.search()
                    .where(f"type = '{entry_type}' AND superseded_by = ''")
                    .limit(100000)
                    .to_list()
                )
            else:
                results = self._table.search().where("superseded_by = ''").limit(100000).to_list()
            return len(results)
        except Exception as e:
            logger.error(f"Failed to count entries: {e}")
            return 0
