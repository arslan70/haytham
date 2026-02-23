"""System State Management Module.

Provides storage for system state (capabilities, decisions, entities,
constraints). The JSON-backed SystemStateStore (ADR-027) is the primary
store. Legacy vector DB classes are re-exported when lancedb is installed.
"""

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
from .store import DuplicateEntryError, SystemStateStore

__all__ = [
    # Primary store (ADR-027)
    "SystemStateStore",
    "SystemStateEntry",
    "IDGenerator",
    # Exceptions
    "DuplicateEntryError",
    # Factory functions
    "create_capability",
    "create_decision",
    "create_entity",
    "create_constraint",
    # Types and constants
    "EntryType",
    "CapabilitySubtype",
    "CAPABILITY_SUBTYPES",
]

# Legacy vector DB support (requires optional lancedb dependency)
try:
    from .embedder import TitanEmbedder, get_embedder
    from .vector_db import SystemStateDB

    # Keep old DuplicateEntryError import path working
    __all__ += ["SystemStateDB", "TitanEmbedder", "get_embedder"]
except ImportError:
    pass
