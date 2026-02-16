"""State Writer Agent Implementation.

This agent is responsible for all write operations to the system state
vector database. It provides a controlled interface for creating and
updating capabilities, decisions, entities, and constraints.

Only Haytham orchestration agents (e.g., capability_model, architecture_agent)
should invoke this agent directly.
"""

import logging
from pathlib import Path
from typing import Any

from haytham.state import (
    SystemStateDB,
    SystemStateEntry,
    TitanEmbedder,
    create_capability,
    create_constraint,
    create_decision,
    create_entity,
)

logger = logging.getLogger(__name__)


class StateWriterAgent:
    """Agent responsible for all writes to the system state vector DB.

    This agent provides a controlled interface for creating and updating
    system state entries. It ensures consistent ID generation, embedding
    creation, and temporal tracking.

    Example:
        writer = StateWriterAgent.from_session_path("session/vector_db")

        # Create a functional capability
        cap_id = writer.create_capability(
            name="User Authentication",
            description="Users can login, logout, and manage their accounts",
            subtype="functional",
            source_stage="capability-model",
            rationale="Core user management functionality",
        )

        # Create a decision
        dec_id = writer.create_decision(
            name="OAuth 2.0 for Authentication",
            description="Use OAuth 2.0 with Google and GitHub providers",
            rationale="Industry standard, reduces password management burden",
            source_stage="capability-model",
            affects=[cap_id],
        )
    """

    def __init__(self, db: SystemStateDB):
        """Initialize the StateWriterAgent.

        Args:
            db: SystemStateDB instance for storage operations
        """
        self.db = db
        logger.info("StateWriterAgent initialized")

    @classmethod
    def from_session_path(
        cls,
        db_path: str | Path,
        embedder: TitanEmbedder | None = None,
    ) -> "StateWriterAgent":
        """Create a StateWriterAgent from a database path.

        Args:
            db_path: Path to the LanceDB database directory
            embedder: Optional TitanEmbedder instance

        Returns:
            Configured StateWriterAgent instance
        """
        db = SystemStateDB(db_path, embedder=embedder)
        return cls(db)

    # ==========================================================================
    # Capability Operations
    # ==========================================================================

    def create_capability(
        self,
        name: str,
        description: str,
        subtype: str,
        source_stage: str,
        rationale: str | None = None,
        tags: list[str] | None = None,
        affects: list[str] | None = None,
        depends_on: list[str] | None = None,
        priority: str | None = None,
        acceptance_criteria: list[str] | None = None,
        user_segment: str | None = None,
        category: str | None = None,
        requirement: str | None = None,
        measurement: str | None = None,
    ) -> str:
        """Create a new capability entry.

        Args:
            name: Short name for the capability
            description: Detailed description of what this capability enables
            subtype: One of "functional", "non_functional", "operational"
            source_stage: Workflow stage that created this (e.g., "capability-model")
            rationale: Why this capability is needed
            tags: Classification tags (e.g., ["P0", "auth"])
            affects: IDs of other entries this capability affects
            depends_on: IDs of entries this capability depends on
            priority: Priority level (P0, P1, P2)
            acceptance_criteria: List of acceptance criteria (functional)
            user_segment: Who benefits from this capability (functional)
            category: Category for non-functional/operational capabilities
            requirement: Measurable requirement (non-functional/operational)
            measurement: How to verify the requirement is met

        Returns:
            The generated capability ID (e.g., "CAP-F-001")
        """
        # Build metadata based on subtype
        metadata: dict[str, Any] = {}

        if priority:
            metadata["priority"] = priority
        if acceptance_criteria:
            metadata["acceptance_criteria"] = acceptance_criteria
        if user_segment:
            metadata["user_segment"] = user_segment
        if category:
            metadata["category"] = category
        if requirement:
            metadata["requirement"] = requirement
        if measurement:
            metadata["measurement"] = measurement

        entry = create_capability(
            name=name,
            description=description,
            subtype=subtype,
            source_stage=source_stage,
            rationale=rationale,
            tags=tags,
            affects=affects,
            depends_on=depends_on,
            metadata=metadata,
        )

        cap_id = self.db.add_entry(entry)
        logger.info(f"Created capability: {cap_id} - {name}")
        return cap_id

    def create_functional_capability(
        self,
        name: str,
        description: str,
        source_stage: str,
        rationale: str | None = None,
        priority: str = "P1",
        acceptance_criteria: list[str] | None = None,
        user_segment: str | None = None,
        affects: list[str] | None = None,
        depends_on: list[str] | None = None,
    ) -> str:
        """Create a functional capability (what users can do).

        Convenience method for creating functional capabilities with
        appropriate metadata fields.
        """
        return self.create_capability(
            name=name,
            description=description,
            subtype="functional",
            source_stage=source_stage,
            rationale=rationale,
            tags=[priority] if priority else None,
            affects=affects,
            depends_on=depends_on,
            priority=priority,
            acceptance_criteria=acceptance_criteria,
            user_segment=user_segment,
        )

    def create_non_functional_capability(
        self,
        name: str,
        description: str,
        category: str,
        requirement: str,
        source_stage: str,
        rationale: str | None = None,
        measurement: str | None = None,
        affects: list[str] | None = None,
    ) -> str:
        """Create a non-functional capability (quality attribute).

        Args:
            category: One of "performance", "security", "reliability",
                     "compliance", "usability"
        """
        return self.create_capability(
            name=name,
            description=description,
            subtype="non_functional",
            source_stage=source_stage,
            rationale=rationale,
            tags=[category] if category else None,
            affects=affects,
            category=category,
            requirement=requirement,
            measurement=measurement,
        )

    def create_operational_capability(
        self,
        name: str,
        description: str,
        category: str,
        requirement: str,
        source_stage: str,
        rationale: str | None = None,
        affects: list[str] | None = None,
    ) -> str:
        """Create an operational capability (how system is run).

        Args:
            category: One of "observability", "deployment", "scaling",
                     "disaster_recovery", "maintenance"
        """
        return self.create_capability(
            name=name,
            description=description,
            subtype="operational",
            source_stage=source_stage,
            rationale=rationale,
            tags=[category] if category else None,
            affects=affects,
            category=category,
            requirement=requirement,
        )

    # ==========================================================================
    # Decision Operations
    # ==========================================================================

    def create_decision(
        self,
        name: str,
        description: str,
        rationale: str,
        source_stage: str,
        affects: list[str] | None = None,
        alternatives_considered: list[str] | None = None,
        tags: list[str] | None = None,
    ) -> str:
        """Create a new decision entry.

        Args:
            name: Short title for the decision
            description: What was decided
            rationale: Why this decision was made
            source_stage: Workflow stage that made this decision
            affects: IDs of capabilities/entities affected by this decision
            alternatives_considered: Other options that were considered
            tags: Classification tags

        Returns:
            The generated decision ID (e.g., "DEC-001")
        """
        entry = create_decision(
            name=name,
            description=description,
            rationale=rationale,
            source_stage=source_stage,
            affects=affects,
            alternatives_considered=alternatives_considered,
        )

        if tags:
            entry.tags = tags

        dec_id = self.db.add_entry(entry)
        logger.info(f"Created decision: {dec_id} - {name}")
        return dec_id

    # ==========================================================================
    # Entity Operations
    # ==========================================================================

    def create_entity(
        self,
        name: str,
        description: str,
        source_stage: str,
        attributes: list[str] | None = None,
        relationships: list[str] | None = None,
        tags: list[str] | None = None,
    ) -> str:
        """Create a new entity entry (domain model).

        Args:
            name: Entity name (e.g., "User", "Note")
            description: What this entity represents
            source_stage: Workflow stage that defined this entity
            attributes: List of attributes (e.g., ["id: UUID", "name: String"])
            relationships: List of relationships (e.g., ["has_many: Note"])
            tags: Classification tags

        Returns:
            The generated entity ID (e.g., "ENT-001")
        """
        entry = create_entity(
            name=name,
            description=description,
            source_stage=source_stage,
            attributes=attributes,
            relationships=relationships,
        )

        if tags:
            entry.tags = tags

        ent_id = self.db.add_entry(entry)
        logger.info(f"Created entity: {ent_id} - {name}")
        return ent_id

    # ==========================================================================
    # Constraint Operations
    # ==========================================================================

    def create_constraint(
        self,
        name: str,
        description: str,
        constraint_type: str,
        source_stage: str,
        rationale: str | None = None,
        affects: list[str] | None = None,
        tags: list[str] | None = None,
    ) -> str:
        """Create a new constraint entry.

        Args:
            name: Short name for the constraint
            description: What the constraint requires
            constraint_type: Type of constraint (e.g., "technical", "business", "regulatory")
            source_stage: Workflow stage that identified this constraint
            rationale: Why this constraint exists
            affects: IDs of entries affected by this constraint
            tags: Classification tags

        Returns:
            The generated constraint ID (e.g., "CON-001")
        """
        entry = create_constraint(
            name=name,
            description=description,
            constraint_type=constraint_type,
            source_stage=source_stage,
            rationale=rationale,
            affects=affects,
        )

        if tags:
            entry.tags = tags

        con_id = self.db.add_entry(entry)
        logger.info(f"Created constraint: {con_id} - {name}")
        return con_id

    # ==========================================================================
    # Update Operations
    # ==========================================================================

    def supersede_entry(
        self,
        old_id: str,
        name: str,
        description: str,
        rationale: str | None = None,
        **kwargs,
    ) -> str:
        """Create a new version of an entry, marking the old one as superseded.

        This is used when a capability, decision, or other entry needs to be
        updated. The old entry is preserved for history, with a link to the
        new version.

        Args:
            old_id: ID of the entry to supersede
            name: New name (can be same as old)
            description: New description
            rationale: Why this change was made
            **kwargs: Additional fields to update

        Returns:
            The ID of the new entry
        """
        # Get the old entry to preserve its type and other fields
        old_entry = self.db.get_by_id(old_id)
        if not old_entry:
            raise ValueError(f"Entry {old_id} not found")

        # Create new entry based on old one
        new_entry = SystemStateEntry(
            id="",  # Will be generated
            type=old_entry["type"],
            subtype=old_entry.get("subtype"),
            name=name,
            description=description,
            tags=kwargs.get("tags", old_entry.get("tags", [])),
            affects=kwargs.get("affects", old_entry.get("affects", [])),
            depends_on=kwargs.get("depends_on", old_entry.get("depends_on", [])),
            source_stage=kwargs.get("source_stage", old_entry.get("source_stage")),
            rationale=rationale,
            metadata=kwargs.get("metadata", old_entry.get("metadata", {})),
        )

        new_id = self.db.supersede_entry(old_id, new_entry)
        logger.info(f"Superseded {old_id} with {new_id}")
        return new_id

    def update_affects(self, entry_id: str, affects: list[str]) -> str:
        """Update the 'affects' relationships of an entry.

        This supersedes the entry with updated affects list.

        Args:
            entry_id: ID of the entry to update
            affects: New list of affected entry IDs

        Returns:
            The ID of the new entry
        """
        entry = self.db.get_by_id(entry_id)
        if not entry:
            raise ValueError(f"Entry {entry_id} not found")

        return self.supersede_entry(
            old_id=entry_id,
            name=entry["name"],
            description=entry["description"],
            rationale="Updated affects relationships",
            affects=affects,
        )

    # ==========================================================================
    # Bulk Operations
    # ==========================================================================

    def create_capabilities_from_dict(
        self,
        capabilities_data: dict,
        source_stage: str,
    ) -> dict[str, list[str]]:
        """Create multiple capabilities from a structured dictionary.

        This is useful when parsing capability model output from an agent.

        Args:
            capabilities_data: Dict with keys "functional", "non_functional", "operational"
                              Each value is a list of capability dicts
            source_stage: Workflow stage creating these capabilities

        Returns:
            Dict mapping subtype to list of created IDs
        """
        created_ids: dict[str, list[str]] = {
            "functional": [],
            "non_functional": [],
            "operational": [],
        }

        for subtype in ["functional", "non_functional", "operational"]:
            caps = capabilities_data.get(subtype, [])
            for cap in caps:
                if subtype == "functional":
                    cap_id = self.create_functional_capability(
                        name=cap.get("name", ""),
                        description=cap.get("description", ""),
                        source_stage=source_stage,
                        rationale=cap.get("rationale"),
                        priority=cap.get("priority", "P1"),
                        acceptance_criteria=cap.get("acceptance_criteria"),
                        user_segment=cap.get("user_segment"),
                    )
                elif subtype == "non_functional":
                    cap_id = self.create_non_functional_capability(
                        name=cap.get("name", ""),
                        description=cap.get("description", ""),
                        category=cap.get("category", ""),
                        requirement=cap.get("requirement", ""),
                        source_stage=source_stage,
                        rationale=cap.get("rationale"),
                        measurement=cap.get("measurement"),
                    )
                else:  # operational
                    cap_id = self.create_operational_capability(
                        name=cap.get("name", ""),
                        description=cap.get("description", ""),
                        category=cap.get("category", ""),
                        requirement=cap.get("requirement", ""),
                        source_stage=source_stage,
                        rationale=cap.get("rationale"),
                    )

                created_ids[subtype].append(cap_id)

        return created_ids

    def create_decisions_from_list(
        self,
        decisions_data: list[dict],
        source_stage: str,
    ) -> list[str]:
        """Create multiple decisions from a list of dicts.

        Args:
            decisions_data: List of decision dicts
            source_stage: Workflow stage creating these decisions

        Returns:
            List of created decision IDs
        """
        created_ids = []

        for dec in decisions_data:
            dec_id = self.create_decision(
                name=dec.get("name", ""),
                description=dec.get("description", ""),
                rationale=dec.get("rationale", ""),
                source_stage=source_stage,
                affects=dec.get("affects"),
                alternatives_considered=dec.get("alternatives_considered"),
            )
            created_ids.append(dec_id)

        return created_ids

    def create_entities_from_list(
        self,
        entities_data: list[dict],
        source_stage: str,
    ) -> list[str]:
        """Create multiple entities from a list of dicts.

        Args:
            entities_data: List of entity dicts
            source_stage: Workflow stage creating these entities

        Returns:
            List of created entity IDs
        """
        created_ids = []

        for ent in entities_data:
            ent_id = self.create_entity(
                name=ent.get("name", ""),
                description=ent.get("description", ""),
                source_stage=source_stage,
                attributes=ent.get("attributes"),
                relationships=ent.get("relationships"),
            )
            created_ids.append(ent_id)

        return created_ids
