"""System State Management Module.

Provides vector database storage for system state (capabilities,
decisions, entities, constraints) with semantic search capabilities.

Example usage:
    from haytham.state import SystemStateDB, create_capability

    # Initialize database
    db = SystemStateDB("session/vector_db")

    # Create a capability
    cap = create_capability(
        name="User Authentication",
        description="Users can create accounts, login, logout, and reset passwords",
        subtype="functional",
        source_stage="capability-model",
        rationale="Core functionality required for user management",
    )

    # Add to database
    cap_id = db.add_entry(cap)

    # Query capabilities
    results = db.find_similar("authentication login")
    current_caps = db.get_capabilities(subtype="functional")
"""

from .embedder import TitanEmbedder, get_embedder
from .schema import (
    CAPABILITY_SUBTYPES,
    CapabilitySubtype,
    EntryType,
    IDGenerator,
    SystemStateEntry,
    create_capability,
    create_constraint,
    create_decision,
    create_entity,
)
from .vector_db import DuplicateEntryError, SystemStateDB

__all__ = [
    # Main classes
    "SystemStateDB",
    "SystemStateEntry",
    "TitanEmbedder",
    "IDGenerator",
    # Exceptions
    "DuplicateEntryError",
    # Factory functions
    "create_capability",
    "create_decision",
    "create_entity",
    "create_constraint",
    # Helpers
    "get_embedder",
    # Types and constants
    "EntryType",
    "CapabilitySubtype",
    "CAPABILITY_SUBTYPES",
]
