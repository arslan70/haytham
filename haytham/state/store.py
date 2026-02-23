"""JSON-backed store for system state entries.

Replaces the LanceDB-backed SystemStateDB (ADR-027). Every caller performed
dict/list operations; no consumer ever used semantic search. This store
provides the same read/write API over a single JSON file.
"""

import json
import logging
from pathlib import Path

from .schema import IDGenerator, SystemStateEntry

logger = logging.getLogger("haytham")

# Nullable fields stored as "" internally, normalized to None on output
_NULLABLE_FIELDS = (
    "supersedes",
    "superseded_by",
    "subtype",
    "rationale",
    "source_stage",
)


class DuplicateEntryError(Exception):
    """Raised when adding an entry with the same name+type as an existing one.

    To update an existing entry, use supersede_entry() instead.
    """


class SystemStateStore:
    """JSON-file-backed store for system state entries.

    Entries are held in memory as ``dict[str, dict]`` keyed by entry ID
    and persisted to a single JSON file on every write.
    """

    def __init__(self, store_path: str | Path) -> None:
        self._path = Path(store_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._id_gen = IDGenerator()
        self._entries: dict[str, dict] = {}
        self._load()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _load(self) -> None:
        """Load entries from disk and sync ID counters."""
        if self._path.exists():
            try:
                with open(self._path) as fh:
                    self._entries = json.load(fh)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Corrupt JSON in system state file {self._path}: {exc}") from exc
            self._sync_id_counters()
            logger.info(
                "SystemStateStore loaded %d entries from %s",
                len(self._entries),
                self._path,
            )
        else:
            self._entries = {}
            logger.info("SystemStateStore created (empty) at %s", self._path)

    def _persist(self) -> None:
        """Write entries to disk atomically via rename."""
        tmp = self._path.with_suffix(".tmp")
        with open(tmp, "w") as fh:
            json.dump(self._entries, fh, indent=2, default=str)
        tmp.replace(self._path)

    def _sync_id_counters(self) -> None:
        """Parse existing IDs and resume counters from the highest number."""
        prefix_max: dict[str, int] = {}
        for entry_id in self._entries:
            if "-" not in entry_id:
                continue
            parts = entry_id.rsplit("-", 1)
            if len(parts) == 2 and parts[1].isdigit():
                prefix = parts[0] + "-"
                num = int(parts[1])
                prefix_max[prefix] = max(prefix_max.get(prefix, 0), num)

        for prefix, max_num in prefix_max.items():
            self._id_gen.set_counter(prefix, max_num + 1)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _entry_to_record(self, entry: SystemStateEntry) -> dict:
        """Convert a Pydantic model to the internal dict representation."""
        return {
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
            "metadata": entry.metadata,
        }

    def _normalize_output(self, record: dict) -> dict:
        """Return a copy with empty-string nullable fields converted to None."""
        out = dict(record)
        for field in _NULLABLE_FIELDS:
            if out.get(field) == "":
                out[field] = None
        return out

    # ------------------------------------------------------------------
    # Write operations
    # ------------------------------------------------------------------

    def add_entry(self, entry: SystemStateEntry) -> str:
        """Add a new entry. Generates an ID if ``entry.id`` is empty.

        Raises:
            DuplicateEntryError: if a non-superseded entry with the same
                name + type already exists.
        """
        existing = self.find_by_name(entry.name, entry_type=entry.type)
        if existing:
            raise DuplicateEntryError(
                f"Entry with name '{entry.name}' and type '{entry.type}' "
                f"already exists (id={existing['id']}). "
                f"Use supersede_entry() to update instead."
            )

        if not entry.id:
            entry.id = self._id_gen.next_id(entry.type, entry.subtype)

        self._entries[entry.id] = self._entry_to_record(entry)
        self._persist()
        logger.info("Added entry: %s", entry.id)
        return entry.id

    def supersede_entry(self, old_id: str, new_entry: SystemStateEntry) -> str:
        """Mark *old_id* as superseded and add *new_entry* as its replacement.

        Raises:
            ValueError: if *old_id* does not exist.
        """
        if old_id not in self._entries:
            raise ValueError(f"Entry {old_id} not found")

        # Generate ID for the new entry
        if not new_entry.id:
            new_entry.id = self._id_gen.next_id(new_entry.type, new_entry.subtype)
        new_entry.supersedes = old_id

        # Update old entry in-place
        self._entries[old_id]["superseded_by"] = new_entry.id

        # Store new entry
        self._entries[new_entry.id] = self._entry_to_record(new_entry)
        self._persist()
        logger.info("Superseded %s with %s", old_id, new_entry.id)
        return new_entry.id

    def delete_entry(self, entry_id: str) -> bool:
        """Remove an entry by ID. Returns True if found, False otherwise."""
        if entry_id not in self._entries:
            return False
        del self._entries[entry_id]
        self._persist()
        logger.info("Deleted entry: %s", entry_id)
        return True

    # ------------------------------------------------------------------
    # Read operations
    # ------------------------------------------------------------------

    def get_by_id(self, entry_id: str) -> dict | None:
        """Return a single entry by ID, or None."""
        record = self._entries.get(entry_id)
        if record is None:
            return None
        return self._normalize_output(record)

    def find_by_name(self, name: str, entry_type: str | None = None) -> dict | None:
        """Find a non-superseded entry by exact name (and optional type)."""
        for record in self._entries.values():
            if record["name"] != name:
                continue
            if record.get("superseded_by", "") not in ("", None):
                continue
            if entry_type and record["type"] != entry_type:
                continue
            return self._normalize_output(record)
        return None

    def get_current_state(
        self,
        entry_type: str | None = None,
        subtype: str | None = None,
        include_superseded: bool = False,
    ) -> list[dict]:
        """Return entries, optionally filtered by type/subtype.

        By default only non-superseded entries are returned. Pass
        ``include_superseded=True`` to include superseded entries as well.
        """
        results = []
        for record in self._entries.values():
            if not include_superseded and record.get("superseded_by", "") not in ("", None):
                continue
            if entry_type and record["type"] != entry_type:
                continue
            if subtype and record.get("subtype") != subtype:
                continue
            results.append(self._normalize_output(record))
        return results

    def get_capabilities(
        self, subtype: str | None = None, include_superseded: bool = False
    ) -> list[dict]:
        """Return capabilities, optionally filtered by subtype."""
        return self.get_current_state(
            entry_type="capability", subtype=subtype, include_superseded=include_superseded
        )

    def get_decisions(self, include_superseded: bool = False) -> list[dict]:
        """Return decisions."""
        return self.get_current_state(entry_type="decision", include_superseded=include_superseded)

    def get_entities(self, include_superseded: bool = False) -> list[dict]:
        """Return entities."""
        return self.get_current_state(entry_type="entity", include_superseded=include_superseded)

    def get_history(self, entry_id: str) -> list[dict]:
        """Follow the supersedes chain from *entry_id* back to the oldest."""
        history = []
        current = self.get_by_id(entry_id)
        while current:
            history.append(current)
            supersedes_id = current.get("supersedes")
            current = self.get_by_id(supersedes_id) if supersedes_id else None
        return history

    def count(self, entry_type: str | None = None) -> int:
        """Count non-superseded entries, optionally filtered by type."""
        return len(self.get_current_state(entry_type=entry_type))
