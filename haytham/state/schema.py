"""System State Schema.

Defines the data models for entries stored in the vector database.
"""

from datetime import datetime
from itertools import count
from typing import Any, Literal

from pydantic import BaseModel, Field

# Valid entry types
EntryType = Literal["capability", "decision", "entity", "constraint"]

# Valid capability subtypes
CapabilitySubtype = Literal["functional", "non_functional", "operational"]

# Capability subtype descriptions
CAPABILITY_SUBTYPES = {
    "functional": "What the system does for users",
    "non_functional": "Quality attributes (performance, security, etc.)",
    "operational": "How the system is run (deployment, monitoring, etc.)",
}


class SystemStateEntry(BaseModel):
    """Base schema for all entries in the vector database.

    This is a flexible schema that supports capabilities, decisions,
    entities, and constraints with type-specific metadata.
    """

    # Identity
    id: str = Field(default="", description="Unique identifier (e.g., CAP-F-001, DEC-003)")
    type: EntryType = Field(..., description="Entry type")

    # Content (embedded for semantic search)
    name: str = Field(..., description="Short name/title")
    description: str = Field(..., description="Detailed description")

    # Classification
    subtype: str | None = Field(None, description="Type-specific classification")
    tags: list[str] = Field(default_factory=list)

    # Relationships
    affects: list[str] = Field(
        default_factory=list, description="IDs of related entries affected by this"
    )
    depends_on: list[str] = Field(default_factory=list, description="IDs of dependencies")

    # Temporal (for traceability)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    supersedes: str | None = Field(None, description="ID of entry this replaces")
    superseded_by: str | None = Field(None, description="ID of entry that replaced this")

    # Provenance
    source_stage: str | None = Field(None, description="Workflow stage that created this")
    rationale: str | None = Field(None, description="Why this exists or was decided")

    # Flexible metadata
    metadata: dict[str, Any] = Field(default_factory=dict)

    def get_text_for_embedding(self) -> str:
        """Get the text content to be embedded for semantic search."""
        parts = [self.name, self.description]
        if self.rationale:
            parts.append(f"Rationale: {self.rationale}")
        return "\n\n".join(parts)


class IDGenerator:
    """Thread-safe ID generator with type-based prefixes.

    Generates sequential IDs like CAP-F-001, DEC-002, etc.
    """

    PREFIXES = {
        ("capability", "functional"): "CAP-F-",
        ("capability", "non_functional"): "CAP-NF-",
        ("capability", "operational"): "CAP-OP-",
        ("capability", None): "CAP-",
        ("decision", None): "DEC-",
        ("entity", None): "ENT-",
        ("constraint", None): "CON-",
    }

    def __init__(self):
        self._counters: dict[str, count] = {}

    def _get_prefix(self, entry_type: str, subtype: str | None = None) -> str:
        """Get the prefix for a given type and subtype."""
        # Try specific key first
        key = (entry_type, subtype)
        if key in self.PREFIXES:
            return self.PREFIXES[key]

        # Fall back to type-only key
        key = (entry_type, None)
        if key in self.PREFIXES:
            return self.PREFIXES[key]

        # Default fallback
        return f"{entry_type.upper()}-"

    def next_id(self, entry_type: str, subtype: str | None = None) -> str:
        """Generate the next ID for a given type and subtype."""
        prefix = self._get_prefix(entry_type, subtype)

        if prefix not in self._counters:
            self._counters[prefix] = count(1)

        return f"{prefix}{next(self._counters[prefix]):03d}"

    def set_counter(self, prefix: str, value: int) -> None:
        """Set the counter for a prefix (useful when loading existing data)."""
        self._counters[prefix] = count(value)


# Convenience factory functions
def create_capability(
    name: str,
    description: str,
    subtype: CapabilitySubtype,
    source_stage: str | None = None,
    rationale: str | None = None,
    tags: list[str] | None = None,
    affects: list[str] | None = None,
    depends_on: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
) -> SystemStateEntry:
    """Create a capability entry."""
    return SystemStateEntry(
        type="capability",
        subtype=subtype,
        name=name,
        description=description,
        source_stage=source_stage,
        rationale=rationale,
        tags=tags or [],
        affects=affects or [],
        depends_on=depends_on or [],
        metadata=metadata or {},
    )


def create_decision(
    name: str,
    description: str,
    rationale: str,
    source_stage: str | None = None,
    affects: list[str] | None = None,
    alternatives_considered: list[str] | None = None,
    serves_capabilities: list[str] | None = None,
) -> SystemStateEntry:
    """Create a decision entry.

    Args:
        name: Short name/title for the decision
        description: Detailed description of the decision
        rationale: Why this decision was made
        source_stage: Workflow stage that created this
        affects: IDs of related entries affected by this decision
        alternatives_considered: List of alternatives that were considered
        serves_capabilities: List of capability IDs (CAP-*) that this decision serves.
            Required for Workflow 2 to track which capabilities are covered by decisions.
            See ADR-005 for the capability-to-decision traceability model.
    """
    return SystemStateEntry(
        type="decision",
        name=name,
        description=description,
        rationale=rationale,
        source_stage=source_stage,
        affects=affects or [],
        metadata={
            "alternatives_considered": alternatives_considered or [],
            "serves_capabilities": serves_capabilities or [],
        },
    )


def create_entity(
    name: str,
    description: str,
    attributes: list[str] | None = None,
    relationships: list[str] | None = None,
    source_stage: str | None = None,
) -> SystemStateEntry:
    """Create an entity entry."""
    return SystemStateEntry(
        type="entity",
        name=name,
        description=description,
        source_stage=source_stage,
        metadata={
            "attributes": attributes or [],
            "relationships": relationships or [],
        },
    )


def create_constraint(
    name: str,
    description: str,
    constraint_type: str,
    source_stage: str | None = None,
    rationale: str | None = None,
    affects: list[str] | None = None,
) -> SystemStateEntry:
    """Create a constraint entry."""
    return SystemStateEntry(
        type="constraint",
        subtype=constraint_type,
        name=name,
        description=description,
        rationale=rationale,
        source_stage=source_stage,
        affects=affects or [],
    )
