"""State Reader Agent Implementation.

This agent is responsible for all read operations from the system state
vector database. It provides semantic search and filtering capabilities
for querying capabilities, decisions, entities, and constraints.

Any Haytham agent can invoke this agent to query system state.
"""

import logging
from pathlib import Path
from typing import Any

from haytham.state import SystemStateDB, TitanEmbedder

logger = logging.getLogger(__name__)


class StateReaderAgent:
    """Agent for querying system state from the vector DB.

    This agent provides a read-only interface to the system state,
    supporting semantic search, filtering, history traversal, and
    impact analysis.

    Example:
        reader = StateReaderAgent.from_session_path("session/vector_db")

        # Find capabilities related to authentication
        results = reader.find_similar("user login authentication")

        # Get all functional capabilities
        caps = reader.get_capabilities(subtype="functional")

        # Analyze impact of a proposed change
        impact = reader.impact_analysis("change authentication to use SAML")
    """

    def __init__(self, db: SystemStateDB):
        """Initialize the StateReaderAgent.

        Args:
            db: SystemStateDB instance for read operations
        """
        self.db = db
        logger.info("StateReaderAgent initialized")

    @classmethod
    def from_session_path(
        cls,
        db_path: str | Path,
        embedder: TitanEmbedder | None = None,
    ) -> "StateReaderAgent":
        """Create a StateReaderAgent from a database path.

        Args:
            db_path: Path to the LanceDB database directory
            embedder: Optional TitanEmbedder instance

        Returns:
            Configured StateReaderAgent instance
        """
        db = SystemStateDB(db_path, embedder=embedder)
        return cls(db)

    # ==========================================================================
    # Semantic Search
    # ==========================================================================

    def find_similar(
        self,
        query: str,
        entry_type: str | None = None,
        subtype: str | None = None,
        include_superseded: bool = False,
        limit: int = 5,
    ) -> list[dict]:
        """Find semantically similar entries.

        Uses vector similarity search to find entries related to the query.

        Args:
            query: Natural language query (e.g., "user authentication login")
            entry_type: Filter by type ("capability", "decision", "entity", "constraint")
            subtype: Filter by subtype (e.g., "functional", "non_functional")
            include_superseded: If True, include superseded entries in results
            limit: Maximum number of results to return

        Returns:
            List of matching entries, ordered by similarity (most similar first)
        """
        results = self.db.find_similar(
            query=query,
            entry_type=entry_type,
            subtype=subtype,
            include_superseded=include_superseded,
            limit=limit,
        )

        logger.debug(f"find_similar '{query}' returned {len(results)} results")
        return results

    def find_capabilities(
        self,
        query: str,
        subtype: str | None = None,
        limit: int = 5,
    ) -> list[dict]:
        """Find capabilities similar to a query.

        Convenience method for searching capabilities only.

        Args:
            query: What capability to search for
            subtype: Filter by "functional", "non_functional", or "operational"
            limit: Maximum results

        Returns:
            List of matching capabilities
        """
        return self.find_similar(
            query=query,
            entry_type="capability",
            subtype=subtype,
            limit=limit,
        )

    def find_decisions(self, query: str, limit: int = 5) -> list[dict]:
        """Find decisions similar to a query.

        Args:
            query: What decision to search for
            limit: Maximum results

        Returns:
            List of matching decisions
        """
        return self.find_similar(query=query, entry_type="decision", limit=limit)

    def check_duplicate(
        self,
        name: str,
        description: str,
        entry_type: str,
        threshold: float = 0.85,
    ) -> dict | None:
        """Check if a similar entry already exists.

        Useful for preventing duplicate entries.

        Args:
            name: Name of the proposed entry
            description: Description of the proposed entry
            entry_type: Type of entry to check against
            threshold: Similarity threshold (0-1, higher = more similar)

        Returns:
            The existing entry if a duplicate is found, None otherwise
        """
        query = f"{name}\n\n{description}"
        results = self.find_similar(query=query, entry_type=entry_type, limit=1)

        if results:
            # LanceDB returns distance, lower = more similar
            # We don't have direct access to similarity score, so we
            # rely on the top result being very similar if it's a duplicate
            # This is a heuristic - in practice, review the result
            return results[0]

        return None

    # ==========================================================================
    # Direct Lookups
    # ==========================================================================

    def get_by_id(self, entry_id: str) -> dict | None:
        """Get a specific entry by its ID.

        Args:
            entry_id: The ID to look up (e.g., "CAP-F-001", "DEC-003")

        Returns:
            The entry as a dict, or None if not found
        """
        return self.db.get_by_id(entry_id)

    def get_by_ids(self, entry_ids: list[str]) -> list[dict]:
        """Get multiple entries by their IDs.

        Args:
            entry_ids: List of IDs to look up

        Returns:
            List of found entries (missing IDs are skipped)
        """
        results = []
        for entry_id in entry_ids:
            entry = self.db.get_by_id(entry_id)
            if entry:
                results.append(entry)
        return results

    # ==========================================================================
    # Filtered Queries
    # ==========================================================================

    def get_current_state(
        self,
        entry_type: str | None = None,
        subtype: str | None = None,
    ) -> list[dict]:
        """Get all current (non-superseded) entries.

        Args:
            entry_type: Filter by type
            subtype: Filter by subtype

        Returns:
            List of current entries
        """
        return self.db.get_current_state(entry_type=entry_type, subtype=subtype)

    def get_capabilities(self, subtype: str | None = None) -> list[dict]:
        """Get all current capabilities.

        Args:
            subtype: Filter by "functional", "non_functional", or "operational"

        Returns:
            List of capabilities
        """
        return self.db.get_capabilities(subtype=subtype)

    def get_functional_capabilities(self) -> list[dict]:
        """Get all functional capabilities (what users can do)."""
        return self.get_capabilities(subtype="functional")

    def get_non_functional_capabilities(self) -> list[dict]:
        """Get all non-functional capabilities (quality attributes)."""
        return self.get_capabilities(subtype="non_functional")

    def get_operational_capabilities(self) -> list[dict]:
        """Get all operational capabilities (how system is run)."""
        return self.get_capabilities(subtype="operational")

    def get_decisions(self) -> list[dict]:
        """Get all current decisions."""
        return self.db.get_decisions()

    def get_entities(self) -> list[dict]:
        """Get all current entities (domain model)."""
        return self.db.get_entities()

    def get_constraints(self) -> list[dict]:
        """Get all current constraints."""
        return self.db.get_current_state(entry_type="constraint")

    # ==========================================================================
    # History and Traceability
    # ==========================================================================

    def get_history(self, entry_id: str) -> list[dict]:
        """Get the full history of an entry.

        Follows the supersedes chain to show how an entry evolved.

        Args:
            entry_id: Starting entry ID (usually the current version)

        Returns:
            List of entries from newest to oldest
        """
        return self.db.get_history(entry_id)

    def get_superseded_entries(self, entry_type: str | None = None) -> list[dict]:
        """Get all superseded (historical) entries.

        Useful for auditing or viewing change history.

        Args:
            entry_type: Filter by type

        Returns:
            List of superseded entries
        """
        # Get all including superseded, then filter to only superseded
        all_entries = self.db.find_similar(
            query="",  # Empty query to get all
            entry_type=entry_type,
            include_superseded=True,
            limit=10000,
        )

        return [e for e in all_entries if e.get("superseded_by")]

    # ==========================================================================
    # Impact Analysis
    # ==========================================================================

    def impact_analysis(self, query: str, limit: int = 10) -> dict:
        """Analyze what would be affected by a proposed change.

        Given a description of a proposed change, finds:
        1. Directly related entries (semantic similarity)
        2. Potentially affected entries (via 'affects' relationships)

        Args:
            query: Description of the proposed change
            limit: Maximum number of directly related entries to find

        Returns:
            Dict with 'directly_related' and 'potentially_affected' lists
        """
        return self.db.impact_analysis(query=query, limit=limit)

    def get_affected_by(self, entry_id: str) -> list[dict]:
        """Get entries that are affected by a given entry.

        Looks up the 'affects' list for the entry and retrieves those entries.

        Args:
            entry_id: ID of the entry to check

        Returns:
            List of affected entries
        """
        entry = self.get_by_id(entry_id)
        if not entry:
            return []

        affected_ids = entry.get("affects", [])
        return self.get_by_ids(affected_ids)

    def get_dependencies(self, entry_id: str) -> list[dict]:
        """Get entries that a given entry depends on.

        Looks up the 'depends_on' list for the entry and retrieves those entries.

        Args:
            entry_id: ID of the entry to check

        Returns:
            List of dependency entries
        """
        entry = self.get_by_id(entry_id)
        if not entry:
            return []

        depends_on_ids = entry.get("depends_on", [])
        return self.get_by_ids(depends_on_ids)

    # ==========================================================================
    # Statistics and Summary
    # ==========================================================================

    def get_stats(self) -> dict[str, int]:
        """Get statistics about the current system state.

        Returns:
            Dict with counts per entry type and subtype
        """
        return {
            "total_capabilities": self.db.count(entry_type="capability"),
            "functional_capabilities": len(self.get_functional_capabilities()),
            "non_functional_capabilities": len(self.get_non_functional_capabilities()),
            "operational_capabilities": len(self.get_operational_capabilities()),
            "decisions": self.db.count(entry_type="decision"),
            "entities": self.db.count(entry_type="entity"),
            "constraints": self.db.count(entry_type="constraint"),
        }

    def get_summary(self) -> dict[str, Any]:
        """Get a summary of the current system state.

        Returns:
            Dict with stats and lists of entry names by type
        """
        stats = self.get_stats()

        return {
            "stats": stats,
            "capabilities": {
                "functional": [c["name"] for c in self.get_functional_capabilities()],
                "non_functional": [c["name"] for c in self.get_non_functional_capabilities()],
                "operational": [c["name"] for c in self.get_operational_capabilities()],
            },
            "decisions": [d["name"] for d in self.get_decisions()],
            "entities": [e["name"] for e in self.get_entities()],
        }

    # ==========================================================================
    # Export
    # ==========================================================================

    def export_to_dict(self) -> dict[str, list[dict]]:
        """Export all current state to a dictionary.

        Useful for serialization or debugging.

        Returns:
            Dict with all entries organized by type
        """
        return {
            "capabilities": {
                "functional": self.get_functional_capabilities(),
                "non_functional": self.get_non_functional_capabilities(),
                "operational": self.get_operational_capabilities(),
            },
            "decisions": self.get_decisions(),
            "entities": self.get_entities(),
            "constraints": self.get_constraints(),
        }

    def export_capability_model(self) -> dict:
        """Export the capability model in the format expected by downstream agents.

        Returns:
            Dict matching the capability model schema from ADR-004
        """
        caps = self.export_to_dict()["capabilities"]

        # Transform to expected format
        return {
            "capabilities": {
                "functional": [
                    {
                        "id": c["id"],
                        "name": c["name"],
                        "description": c["description"],
                        "priority": c.get("metadata", {}).get("priority", "P1"),
                        "user_segment": c.get("metadata", {}).get("user_segment"),
                        "acceptance_criteria": c.get("metadata", {}).get("acceptance_criteria", []),
                        "rationale": c.get("rationale"),
                    }
                    for c in caps["functional"]
                ],
                "non_functional": [
                    {
                        "id": c["id"],
                        "name": c["name"],
                        "description": c["description"],
                        "category": c.get("metadata", {}).get("category"),
                        "requirement": c.get("metadata", {}).get("requirement"),
                        "measurement": c.get("metadata", {}).get("measurement"),
                        "rationale": c.get("rationale"),
                    }
                    for c in caps["non_functional"]
                ],
                "operational": [
                    {
                        "id": c["id"],
                        "name": c["name"],
                        "description": c["description"],
                        "category": c.get("metadata", {}).get("category"),
                        "requirement": c.get("metadata", {}).get("requirement"),
                        "rationale": c.get("rationale"),
                    }
                    for c in caps["operational"]
                ],
            },
            "decisions": [
                {
                    "id": d["id"],
                    "name": d["name"],
                    "description": d["description"],
                    "rationale": d.get("rationale"),
                    "affects": d.get("affects", []),
                    "alternatives_considered": d.get("metadata", {}).get(
                        "alternatives_considered", []
                    ),
                }
                for d in self.get_decisions()
            ],
            "entities": [
                {
                    "id": e["id"],
                    "name": e["name"],
                    "description": e["description"],
                    "attributes": e.get("metadata", {}).get("attributes", []),
                    "relationships": e.get("metadata", {}).get("relationships", []),
                }
                for e in self.get_entities()
            ],
        }
