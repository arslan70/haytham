"""System State Management Module.

Provides storage for system state (capabilities, decisions, entities,
constraints) via the JSON-backed SystemStateStore (ADR-027).
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
