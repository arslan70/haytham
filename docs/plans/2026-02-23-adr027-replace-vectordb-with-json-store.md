# ADR-027 Implementation Plan: Replace VectorDB with JSON Store

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace LanceDB-backed `SystemStateDB` with a JSON-file-backed `SystemStateStore`, eliminating ~2,640 lines of unused vector search infrastructure and the `lancedb`/`pyarrow` dependencies.

**Architecture:** New `SystemStateStore` class in `haytham/state/store.py` backed by a single JSON file (`session/system_state.json`). Entries stored as a `dict[str, dict]` keyed by ID. Preserves `SystemStateEntry` Pydantic model and `IDGenerator`. All call sites swap import from `SystemStateDB` to `SystemStateStore` with identical method signatures.

**Tech Stack:** Python stdlib `json` + existing `pydantic`. No new dependencies.

---

## Task 1: Create `SystemStateStore` with tests (core write path)

**Files:**
- Create: `haytham/state/store.py`
- Create: `tests/test_system_state_store.py`

**Step 1: Write failing tests for write operations**

```python
# tests/test_system_state_store.py
"""Tests for JSON-backed SystemStateStore."""

import json
from pathlib import Path

import pytest

from haytham.state.schema import IDGenerator, SystemStateEntry, create_capability, create_decision
from haytham.state.store import DuplicateEntryError, SystemStateStore


@pytest.fixture
def store_path(tmp_path):
    return tmp_path / "system_state.json"


@pytest.fixture
def store(store_path):
    return SystemStateStore(store_path)


class TestAddEntry:
    def test_add_entry_generates_id(self, store):
        entry = create_capability(
            name="User Auth",
            description="Users can log in",
            subtype="functional",
            source_stage="capability-model",
        )
        entry_id = store.add_entry(entry)
        assert entry_id == "CAP-F-001"

    def test_add_entry_persists_to_disk(self, store, store_path):
        entry = create_capability(
            name="User Auth",
            description="Users can log in",
            subtype="functional",
        )
        store.add_entry(entry)
        assert store_path.exists()
        data = json.loads(store_path.read_text())
        assert "CAP-F-001" in data

    def test_add_entry_duplicate_raises(self, store):
        entry = create_capability(
            name="User Auth",
            description="Users can log in",
            subtype="functional",
        )
        store.add_entry(entry)
        entry2 = create_capability(
            name="User Auth",
            description="Same name again",
            subtype="functional",
        )
        with pytest.raises(DuplicateEntryError):
            store.add_entry(entry2)

    def test_add_entry_with_preset_id(self, store):
        entry = create_capability(
            name="Custom",
            description="Preset ID",
            subtype="functional",
        )
        entry.id = "CAP-F-099"
        entry_id = store.add_entry(entry)
        assert entry_id == "CAP-F-099"

    def test_sequential_ids(self, store):
        e1 = create_capability(name="A", description="a", subtype="functional")
        e2 = create_capability(name="B", description="b", subtype="functional")
        id1 = store.add_entry(e1)
        id2 = store.add_entry(e2)
        assert id1 == "CAP-F-001"
        assert id2 == "CAP-F-002"


class TestSupersedeEntry:
    def test_supersede_entry(self, store):
        old = create_capability(name="Auth v1", description="v1", subtype="functional")
        old_id = store.add_entry(old)

        new = create_capability(name="Auth v2", description="v2", subtype="functional")
        new_id = store.supersede_entry(old_id, new)

        assert new_id == "CAP-F-002"
        old_record = store.get_by_id(old_id)
        assert old_record["superseded_by"] == new_id
        new_record = store.get_by_id(new_id)
        assert new_record["supersedes"] == old_id

    def test_supersede_nonexistent_raises(self, store):
        new = create_capability(name="X", description="x", subtype="functional")
        with pytest.raises(ValueError, match="not found"):
            store.supersede_entry("CAP-F-999", new)


class TestDeleteEntry:
    def test_delete_existing(self, store):
        entry = create_capability(name="X", description="x", subtype="functional")
        entry_id = store.add_entry(entry)
        assert store.delete_entry(entry_id) is True
        assert store.get_by_id(entry_id) is None

    def test_delete_nonexistent(self, store):
        assert store.delete_entry("NOPE-001") is False
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_system_state_store.py -v`
Expected: FAIL (ModuleNotFoundError for `haytham.state.store`)

**Step 3: Write `SystemStateStore` implementation**

```python
# haytham/state/store.py
"""JSON-backed store for system state entries.

Replaces LanceDB-backed SystemStateDB per ADR-027. All consumers use
simple dict/list operations (add, get-by-type, get-by-id, supersede),
none use vector similarity search.
"""

import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .schema import IDGenerator, SystemStateEntry

logger = logging.getLogger("haytham")


class DuplicateEntryError(Exception):
    """Raised when attempting to add an entry that already exists."""

    pass


class SystemStateStore:
    """JSON-file-backed store for system state entries."""

    def __init__(self, store_path: str | Path):
        self.store_path = Path(store_path)
        self.id_generator = IDGenerator()
        self._entries: dict[str, dict[str, Any]] = {}
        self._load()

    def _load(self) -> None:
        """Load entries from disk and sync ID counters."""
        if self.store_path.exists():
            data = json.loads(self.store_path.read_text())
            self._entries = data
            self._sync_id_counters()

    def _save(self) -> None:
        """Persist entries to disk."""
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        self.store_path.write_text(json.dumps(self._entries, indent=2, default=str))

    def _sync_id_counters(self) -> None:
        """Sync ID generator counters from existing entries."""
        prefix_max: dict[str, int] = {}
        for entry_id in self._entries:
            # Extract prefix and number: "CAP-F-001" -> ("CAP-F-", 1)
            parts = entry_id.rsplit("-", 1)
            if len(parts) == 2:
                prefix = parts[0] + "-"
                try:
                    num = int(parts[1])
                    prefix_max[prefix] = max(prefix_max.get(prefix, 0), num)
                except ValueError:
                    pass
        for prefix, max_num in prefix_max.items():
            self.id_generator.set_counter(prefix, max_num + 1)

    def _entry_to_dict(self, entry: SystemStateEntry) -> dict[str, Any]:
        """Convert a Pydantic entry to a storable dict."""
        d = entry.model_dump(mode="json")
        # Normalize None to empty string for supersedes/superseded_by
        # to match the convention used by downstream consumers
        if d.get("superseded_by") is None:
            d["superseded_by"] = ""
        if d.get("supersedes") is None:
            d["supersedes"] = ""
        return d

    def _normalize_output(self, record: dict[str, Any]) -> dict[str, Any]:
        """Normalize a stored record for output (match SystemStateDB format)."""
        result = dict(record)
        # Convert empty strings to None for nullable fields
        for field in ["supersedes", "superseded_by", "subtype", "rationale", "source_stage"]:
            if result.get(field) == "":
                result[field] = None
        # Parse created_at back to datetime if it's a string
        if "created_at" in result and isinstance(result["created_at"], str):
            try:
                result["created_at"] = datetime.fromisoformat(result["created_at"])
            except (ValueError, TypeError):
                pass
        return result

    # ── Write ──────────────────────────────────────────────────────────

    def add_entry(self, entry: SystemStateEntry) -> str:
        """Add a new entry. Raises DuplicateEntryError if name+type exists."""
        existing = self.find_by_name(name=entry.name, entry_type=entry.type)
        if existing:
            raise DuplicateEntryError(
                f"Entry with name '{entry.name}' and type '{entry.type}' already exists "
                f"(id={existing['id']}). Use supersede_entry() to update instead."
            )

        if not entry.id:
            entry.id = self.id_generator.next_id(entry.type, entry.subtype)

        self._entries[entry.id] = self._entry_to_dict(entry)
        self._save()
        logger.info(f"Added entry: {entry.id}")
        return entry.id

    def supersede_entry(self, old_id: str, new_entry: SystemStateEntry) -> str:
        """Create a new version and mark the old one as superseded."""
        if old_id not in self._entries:
            raise ValueError(f"Entry {old_id} not found")

        # Generate ID for new entry
        if not new_entry.id:
            new_entry.id = self.id_generator.next_id(new_entry.type, new_entry.subtype)
        new_entry.supersedes = old_id

        # Mark old as superseded (in-place, no delete-re-add dance)
        self._entries[old_id]["superseded_by"] = new_entry.id

        # Add new entry
        self._entries[new_entry.id] = self._entry_to_dict(new_entry)

        self._save()
        logger.info(f"Superseded {old_id} with {new_entry.id}")
        return new_entry.id

    def delete_entry(self, entry_id: str) -> bool:
        """Delete an entry by ID. Returns True if deleted."""
        if entry_id in self._entries:
            del self._entries[entry_id]
            self._save()
            logger.info(f"Deleted entry: {entry_id}")
            return True
        return False

    # ── Read ───────────────────────────────────────────────────────────

    def get_by_id(self, entry_id: str) -> dict | None:
        """Get a specific entry by ID."""
        record = self._entries.get(entry_id)
        return self._normalize_output(record) if record else None

    def find_by_name(
        self, name: str, entry_type: str | None = None
    ) -> dict | None:
        """Find a non-superseded entry by exact name match."""
        for record in self._entries.values():
            if record.get("superseded_by") not in ("", None):
                continue
            if record["name"] == name:
                if entry_type is None or record["type"] == entry_type:
                    return self._normalize_output(record)
        return None

    def get_current_state(
        self, entry_type: str | None = None, subtype: str | None = None
    ) -> list[dict]:
        """Get all current (non-superseded) entries."""
        results = []
        for record in self._entries.values():
            if record.get("superseded_by") not in ("", None):
                continue
            if entry_type and record["type"] != entry_type:
                continue
            if subtype and record.get("subtype") != subtype:
                continue
            results.append(self._normalize_output(record))
        return results

    def get_capabilities(self, subtype: str | None = None) -> list[dict]:
        """Get all current capabilities."""
        return self.get_current_state(entry_type="capability", subtype=subtype)

    def get_decisions(self) -> list[dict]:
        """Get all current decisions."""
        return self.get_current_state(entry_type="decision")

    def get_entities(self) -> list[dict]:
        """Get all current entities."""
        return self.get_current_state(entry_type="entity")

    def get_history(self, entry_id: str) -> list[dict]:
        """Get full history by following the supersedes chain."""
        history = []
        current = self.get_by_id(entry_id)
        while current:
            history.append(current)
            supersedes_id = current.get("supersedes")
            current = self.get_by_id(supersedes_id) if supersedes_id else None
        return history

    def count(self, entry_type: str | None = None) -> int:
        """Count current (non-superseded) entries."""
        return len(self.get_current_state(entry_type=entry_type))
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_system_state_store.py -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add haytham/state/store.py tests/test_system_state_store.py
git commit -m "feat(state): add JSON-backed SystemStateStore (ADR-027)"
```

---

## Task 2: Add read-path tests

**Files:**
- Modify: `tests/test_system_state_store.py`

**Step 1: Write failing tests for read operations**

Add these test classes to `tests/test_system_state_store.py`:

```python
class TestGetById:
    def test_get_existing(self, store):
        entry = create_capability(name="X", description="x", subtype="functional")
        entry_id = store.add_entry(entry)
        result = store.get_by_id(entry_id)
        assert result is not None
        assert result["name"] == "X"
        assert result["id"] == entry_id

    def test_get_nonexistent(self, store):
        assert store.get_by_id("NOPE-001") is None

    def test_output_normalizes_empty_strings(self, store):
        """Nullable fields stored as '' should be returned as None."""
        entry = create_capability(name="X", description="x", subtype="functional")
        store.add_entry(entry)
        result = store.get_by_id("CAP-F-001")
        assert result["supersedes"] is None
        assert result["superseded_by"] is None


class TestFindByName:
    def test_find_existing(self, store):
        entry = create_capability(name="Auth", description="login", subtype="functional")
        store.add_entry(entry)
        result = store.find_by_name("Auth")
        assert result is not None
        assert result["name"] == "Auth"

    def test_find_nonexistent(self, store):
        assert store.find_by_name("Nope") is None

    def test_find_skips_superseded(self, store):
        old = create_capability(name="Auth", description="v1", subtype="functional")
        old_id = store.add_entry(old)
        new = create_capability(name="Auth v2", description="v2", subtype="functional")
        store.supersede_entry(old_id, new)
        assert store.find_by_name("Auth") is None

    def test_find_with_type_filter(self, store):
        cap = create_capability(name="Auth", description="cap", subtype="functional")
        dec = create_decision(name="Auth", description="dec", rationale="r")
        store.add_entry(cap)
        store.add_entry(dec)
        result = store.find_by_name("Auth", entry_type="decision")
        assert result["type"] == "decision"


class TestGetCurrentState:
    def test_filters_superseded(self, store):
        old = create_capability(name="A", description="a", subtype="functional")
        old_id = store.add_entry(old)
        new = create_capability(name="B", description="b", subtype="functional")
        store.supersede_entry(old_id, new)
        current = store.get_current_state()
        assert len(current) == 1
        assert current[0]["name"] == "B"

    def test_filter_by_type(self, store):
        cap = create_capability(name="C", description="c", subtype="functional")
        dec = create_decision(name="D", description="d", rationale="r")
        store.add_entry(cap)
        store.add_entry(dec)
        caps = store.get_current_state(entry_type="capability")
        assert len(caps) == 1
        assert caps[0]["type"] == "capability"

    def test_filter_by_subtype(self, store):
        f = create_capability(name="F", description="f", subtype="functional")
        nf = create_capability(name="NF", description="nf", subtype="non_functional")
        store.add_entry(f)
        store.add_entry(nf)
        functional = store.get_current_state(entry_type="capability", subtype="functional")
        assert len(functional) == 1
        assert functional[0]["name"] == "F"


class TestConvenienceReaders:
    def test_get_capabilities(self, store):
        cap = create_capability(name="C", description="c", subtype="functional")
        dec = create_decision(name="D", description="d", rationale="r")
        store.add_entry(cap)
        store.add_entry(dec)
        assert len(store.get_capabilities()) == 1
        assert len(store.get_decisions()) == 1

    def test_get_capabilities_with_subtype(self, store):
        f = create_capability(name="F", description="f", subtype="functional")
        nf = create_capability(name="NF", description="nf", subtype="non_functional")
        store.add_entry(f)
        store.add_entry(nf)
        assert len(store.get_capabilities(subtype="functional")) == 1

    def test_count(self, store):
        cap = create_capability(name="C", description="c", subtype="functional")
        dec = create_decision(name="D", description="d", rationale="r")
        store.add_entry(cap)
        store.add_entry(dec)
        assert store.count() == 2
        assert store.count(entry_type="capability") == 1


class TestGetHistory:
    def test_history_chain(self, store):
        v1 = create_capability(name="Auth v1", description="v1", subtype="functional")
        v1_id = store.add_entry(v1)
        v2 = create_capability(name="Auth v2", description="v2", subtype="functional")
        v2_id = store.supersede_entry(v1_id, v2)
        v3 = create_capability(name="Auth v3", description="v3", subtype="functional")
        v3_id = store.supersede_entry(v2_id, v3)

        history = store.get_history(v3_id)
        assert len(history) == 3
        assert history[0]["id"] == v3_id
        assert history[1]["id"] == v2_id
        assert history[2]["id"] == v1_id


class TestPersistence:
    def test_reload_from_disk(self, store_path):
        store1 = SystemStateStore(store_path)
        entry = create_capability(name="Persist", description="test", subtype="functional")
        store1.add_entry(entry)

        store2 = SystemStateStore(store_path)
        assert store2.get_by_id("CAP-F-001") is not None
        assert store2.get_by_id("CAP-F-001")["name"] == "Persist"

    def test_id_counters_restored(self, store_path):
        store1 = SystemStateStore(store_path)
        store1.add_entry(create_capability(name="A", description="a", subtype="functional"))
        store1.add_entry(create_capability(name="B", description="b", subtype="functional"))

        store2 = SystemStateStore(store_path)
        entry = create_capability(name="C", description="c", subtype="functional")
        entry_id = store2.add_entry(entry)
        assert entry_id == "CAP-F-003"


class TestEmptyStore:
    def test_empty_store_reads(self, store):
        assert store.get_capabilities() == []
        assert store.get_decisions() == []
        assert store.get_entities() == []
        assert store.count() == 0
        assert store.get_by_id("X") is None
        assert store.find_by_name("X") is None
        assert store.get_history("X") == []
```

**Step 2: Run tests**

Run: `uv run pytest tests/test_system_state_store.py -v`
Expected: All PASS (implementation from Task 1 should handle these)

**Step 3: Commit**

```bash
git add tests/test_system_state_store.py
git commit -m "test(state): add comprehensive read-path tests for SystemStateStore"
```

---

## Task 3: Update `haytham/state/__init__.py` barrel exports

**Files:**
- Modify: `haytham/state/__init__.py`

**Step 1: Replace the file contents**

The old `__init__.py` imports from `vector_db` and `embedder`. Replace with imports from `store`:

```python
"""System State Management Module.

Provides JSON-backed storage for system state (capabilities,
decisions, entities, constraints).

Example usage:
    from haytham.state import SystemStateStore, create_capability

    store = SystemStateStore("session/system_state.json")
    cap = create_capability(
        name="User Authentication",
        description="Users can create accounts, login, logout, and reset passwords",
        subtype="functional",
        source_stage="capability-model",
        rationale="Core functionality required for user management",
    )
    cap_id = store.add_entry(cap)
    current_caps = store.get_capabilities(subtype="functional")
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
    # Main classes
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
```

**Step 2: Run tests**

Run: `uv run pytest tests/test_system_state_store.py -v`
Expected: All PASS

**Step 3: Commit**

```bash
git add haytham/state/__init__.py
git commit -m "refactor(state): update barrel exports to use SystemStateStore"
```

---

## Task 4: Update `store_capabilities_in_vector_db` in `mvp_specification.py`

**Files:**
- Modify: `haytham/workflow/stages/mvp_specification.py` (lines 290-367)

**What changes:**
- Remove `StateWriterAgent` import and usage
- Replace `SystemStateDB` + `get_embedder` with `SystemStateStore`
- Use `create_capability` + `store.add_entry()` directly (StateWriterAgent's convenience methods just built metadata dicts and called `db.add_entry()`)
- Change db path from `session_dir / "vector_db"` to `session_dir / "system_state.json"`

**Step 1: Replace the function body**

Replace `store_capabilities_in_vector_db` (lines 290-367) with:

```python
def store_capabilities_in_vector_db(session_manager: Any, output: str) -> None:
    """Store capability model output in the system state store.

    Parses the JSON capability model output and stores each capability.
    Per ADR-004: System State Implementation, ADR-027: JSON Store.
    """
    if session_manager is None:
        logger.warning("No session manager - skipping state storage")
        return

    try:
        json_str = extract_json_from_output(output)
        capability_data = json.loads(json_str)
    except json.JSONDecodeError as e:
        logger.warning(f"Could not parse capability model JSON: {e}")
        logger.info("Capabilities will not be stored in system state")
        return

    try:
        from haytham.state import DuplicateEntryError, SystemStateStore, create_capability

        store_path = session_manager.session_dir / "system_state.json"
        store = SystemStateStore(store_path)

        stored_ids = []
        skipped_count = 0

        for cap in capability_data.get("capabilities", {}).get("functional", []):
            try:
                entry = create_capability(
                    name=cap.get("name", ""),
                    description=cap.get("description", ""),
                    subtype="functional",
                    source_stage="capability-model",
                    rationale=cap.get("rationale"),
                    metadata={
                        k: v
                        for k, v in {
                            "priority": "P1",
                            "acceptance_criteria": cap.get("acceptance_criteria"),
                            "user_segment": capability_data.get("summary", {}).get(
                                "primary_user_segment"
                            ),
                        }.items()
                        if v is not None
                    },
                )
                cap_id = store.add_entry(entry)
                stored_ids.append(cap_id)
                logger.info(f"Stored functional capability: {cap_id}")
            except DuplicateEntryError:
                logger.info(f"Skipping existing capability: {cap.get('name', '')}")
                skipped_count += 1

        for cap in capability_data.get("capabilities", {}).get("non_functional", []):
            try:
                entry = create_capability(
                    name=cap.get("name", ""),
                    description=cap.get("description", ""),
                    subtype="non_functional",
                    source_stage="capability-model",
                    rationale=cap.get("rationale"),
                    metadata={
                        k: v
                        for k, v in {
                            "category": cap.get("category", "performance"),
                            "requirement": cap.get("requirement", ""),
                            "measurement": cap.get("measurement"),
                        }.items()
                        if v is not None
                    },
                )
                cap_id = store.add_entry(entry)
                stored_ids.append(cap_id)
                logger.info(f"Stored non-functional capability: {cap_id}")
            except DuplicateEntryError:
                logger.info(f"Skipping existing capability: {cap.get('name', '')}")
                skipped_count += 1

        logger.info(f"Stored {len(stored_ids)} capabilities in state store: {stored_ids}")
        if skipped_count > 0:
            logger.info(f"Skipped {skipped_count} existing capabilities (idempotent)")

    except (OSError, KeyError, TypeError, ValueError, RuntimeError) as e:
        logger.error(f"Failed to store capabilities in state store: {e}", exc_info=True)
```

Note: The function name `store_capabilities_in_vector_db` is kept unchanged because it's referenced by `configs.py` and renaming would require updating the import + reference there. The docstring and internal comments are updated to reflect the new store.

**Step 2: Remove now-unused imports**

If the file has any top-level imports of `StateWriterAgent`, `SystemStateDB`, `get_embedder`, or `TitanEmbedder`, remove them. (Currently these are inside the function body as lazy imports, so only the function body changes.)

**Step 3: Run tests**

Run: `uv run pytest tests/ -v -m "not integration" -x`
Expected: All PASS

**Step 4: Commit**

```bash
git add haytham/workflow/stages/mvp_specification.py
git commit -m "refactor(mvp-spec): use SystemStateStore instead of VectorDB + StateWriterAgent"
```

---

## Task 5: Update `build_buy.py` entry validator

**Files:**
- Modify: `haytham/workflow/entry_validators/build_buy.py` (method `_check_functional_capabilities`, lines 69-96)

**Step 1: Replace `_check_functional_capabilities`**

```python
def _check_functional_capabilities(self) -> int:
    """Check that at least 1 functional capability exists."""
    try:
        from haytham.state.store import SystemStateStore

        store_path = self.session_manager.session_dir / "system_state.json"
        if not store_path.exists():
            self.errors.append("System state file not found")
            return 0

        store = SystemStateStore(store_path)
        capabilities = store.get_capabilities()

        functional_caps = [c for c in capabilities if c.get("subtype") == "functional"]

        if not functional_caps:
            self.errors.append("No functional capabilities found in system state")
            return 0

        return len(functional_caps)

    except ImportError:
        self.warnings.append("State store module not available - skipping capability check")
        return 0
    except (OSError, KeyError, TypeError, AttributeError) as e:
        self.errors.append(f"Failed to load capabilities: {e!s}")
        return 0
```

**Step 2: Run tests**

Run: `uv run pytest tests/test_entry_validators.py -v`
Expected: PASS

**Step 3: Commit**

```bash
git add haytham/workflow/entry_validators/build_buy.py
git commit -m "refactor(entry-validators): use SystemStateStore in build-buy validator"
```

---

## Task 6: Update `coverage.py`

**Files:**
- Modify: `haytham/state/coverage.py` (function `get_capability_coverage`, lines 122-261)

**Step 1: Update import and initialization in `get_capability_coverage`**

Replace these lines (around lines 143-153):

```python
    # Old:
    from haytham.state.vector_db import SystemStateDB

    db_path = session_manager.session_dir / "vector_db"
    if not db_path.exists():
        logger.warning("VectorDB not found, returning empty coverage report")
        return CoverageReport()

    db = SystemStateDB(str(db_path))

    capabilities = db.get_capabilities()
    decisions = db.get_decisions()
```

With:

```python
    from haytham.state.store import SystemStateStore

    store_path = session_manager.session_dir / "system_state.json"
    if not store_path.exists():
        logger.warning("System state not found, returning empty coverage report")
        return CoverageReport()

    store = SystemStateStore(store_path)

    capabilities = store.get_capabilities()
    decisions = store.get_decisions()
```

No other changes needed in the function; the rest operates on `list[dict]` returned by both APIs.

**Step 2: Run tests**

Run: `uv run pytest tests/ -v -m "not integration" -x`
Expected: PASS

**Step 3: Commit**

```bash
git add haytham/state/coverage.py
git commit -m "refactor(coverage): use SystemStateStore instead of SystemStateDB"
```

---

## Task 7: Update `supersede.py` (3 functions)

**Files:**
- Modify: `haytham/state/supersede.py` (3 functions use `SystemStateDB`)

**Step 1: Update `find_superseded_capabilities` (lines 100-130)**

Replace the `SystemStateDB` import and initialization block:

```python
    # Old:
    from haytham.state.vector_db import SystemStateDB
    db_path = session_manager.session_dir / "vector_db"
    if not db_path.exists():
        return []
    db = SystemStateDB(str(db_path))
    capabilities = db.get_capabilities()
```

With:

```python
    from haytham.state.store import SystemStateStore
    store_path = session_manager.session_dir / "system_state.json"
    if not store_path.exists():
        return []
    store = SystemStateStore(store_path)
    capabilities = store.get_capabilities()
```

**Step 2: Update `find_affected_decisions` (lines 194-241)**

Same pattern - replace the `SystemStateDB` block:

```python
    # Old:
    from haytham.state.vector_db import SystemStateDB
    db_path = session_manager.session_dir / "vector_db"
    if not db_path.exists():
        return []
    db = SystemStateDB(str(db_path))
    decisions = db.get_decisions()
```

With:

```python
    from haytham.state.store import SystemStateStore
    store_path = session_manager.session_dir / "system_state.json"
    if not store_path.exists():
        return []
    store = SystemStateStore(store_path)
    decisions = store.get_decisions()
```

**Step 3: Update `find_affected_entities` (lines 244-291)**

Same pattern:

```python
    # Old:
    from haytham.state.vector_db import SystemStateDB
    db_path = session_manager.session_dir / "vector_db"
    if not db_path.exists():
        return []
    db = SystemStateDB(str(db_path))
    entities = db.get_entities()
```

With:

```python
    from haytham.state.store import SystemStateStore
    store_path = session_manager.session_dir / "system_state.json"
    if not store_path.exists():
        return []
    store = SystemStateStore(store_path)
    entities = store.get_entities()
```

**Step 4: Run tests**

Run: `uv run pytest tests/ -v -m "not integration" -x`
Expected: PASS

**Step 5: Commit**

```bash
git add haytham/state/supersede.py
git commit -m "refactor(supersede): use SystemStateStore instead of SystemStateDB"
```

---

## Task 8: Update frontend files

**Files:**
- Modify: `frontend_streamlit/views/artifacts.py` (3 functions)
- Modify: `frontend_streamlit/views/dashboard.py` (1 function)

**Step 1: Update `artifacts.py`**

Three functions (`load_capabilities`, `load_decisions`, `load_entities`) all follow the same pattern. In each, replace:

```python
        from haytham.state.vector_db import SystemStateDB

        db_path = SESSION_DIR / "vector_db"
        if db_path.exists():
            db = SystemStateDB(str(db_path))
```

With:

```python
        from haytham.state.store import SystemStateStore

        store_path = SESSION_DIR / "system_state.json"
        if store_path.exists():
            store = SystemStateStore(store_path)
```

And update the method calls from `db.get_capabilities()` to `store.get_capabilities()` (etc.).

**Step 2: Update `dashboard.py`**

In `load_artifact_counts`, same replacement:

```python
        from haytham.state.store import SystemStateStore

        store_path = SESSION_DIR / "system_state.json"
        if store_path.exists():
            store = SystemStateStore(store_path)
            return {
                "capabilities": len(store.get_capabilities()),
                "decisions": len(store.get_decisions()),
                "entities": len(store.get_entities()),
            }
```

**Step 3: Run lint**

Run: `uv run ruff check frontend_streamlit/ --fix && uv run ruff format frontend_streamlit/`
Expected: Clean

**Step 4: Commit**

```bash
git add frontend_streamlit/views/artifacts.py frontend_streamlit/views/dashboard.py
git commit -m "refactor(frontend): use SystemStateStore instead of SystemStateDB"
```

---

## Task 9: Remove `vectordb` dependency from `pyproject.toml`

**Files:**
- Modify: `pyproject.toml`

**Step 1: Remove the `vectordb` extra and update `full`**

In `[project.optional-dependencies]`, delete the line:

```
vectordb = ["lancedb>=0.26.1", "pyarrow>=22.0.0"]
```

And change `full` from:

```
full = ["haytham[observability,vectordb,providers]"]
```

To:

```
full = ["haytham[observability,providers]"]
```

**Step 2: Run dependency sync**

Run: `uv sync`
Expected: Success (lancedb and pyarrow no longer installed)

**Step 3: Commit**

```bash
git add pyproject.toml
git commit -m "chore(deps): remove lancedb and pyarrow optional dependencies (ADR-027)"
```

---

## Task 10: Delete old vector DB infrastructure

**Files:**
- Delete: `haytham/state/vector_db.py`
- Delete: `haytham/state/embedder.py`
- Delete: `haytham/agents/state_reader/` (entire directory)
- Delete: `haytham/agents/state_writer/` (entire directory)

**Step 1: Delete files**

```bash
rm haytham/state/vector_db.py
rm haytham/state/embedder.py
rm -rf haytham/agents/state_reader/
rm -rf haytham/agents/state_writer/
```

**Step 2: Verify no remaining references**

Run: `uv run ruff check haytham/ && grep -r "SystemStateDB\|StateReaderAgent\|StateWriterAgent\|TitanEmbedder\|vector_db\|get_embedder" haytham/ --include="*.py"`

Expected: No matches (other than possibly the function name `store_capabilities_in_vector_db` which is an internal name, not a reference to the old code).

**Step 3: Run full test suite**

Run: `uv run ruff check haytham/ --fix && uv run ruff format haytham/ && uv run pytest tests/ -v -m "not integration" -x`
Expected: All PASS, no lint errors

**Step 4: Commit**

```bash
git add -A
git commit -m "refactor(state): delete vector DB infrastructure (~2,640 lines removed, ADR-027)"
```

---

## Task 11: Update ADR status and CLAUDE.md

**Files:**
- Modify: `docs/adr/ADR-027-replace-vectordb-with-json-store.md` (status line)
- Modify: `docs/adr/ADR-003-system-state-evolution.md` (status line)
- Modify: `docs/adr/index.md` (status column for ADR-003 and ADR-027)
- Modify: `CLAUDE.md` (remove VectorDB references, update key files)

**Step 1: Update ADR-027 status**

Change `**Proposed** - 2026-02-23` to `**Accepted** - 2026-02-23`.

**Step 2: Update ADR-003 status**

Add a superseded notice at the top of ADR-003, and update its status to `**Superseded** by [ADR-027](ADR-027-replace-vectordb-with-json-store.md)`.

**Step 3: Update ADR index**

Change ADR-003 status from `Accepted (superseded when ADR-027 is accepted)` to `Superseded by ADR-027`.
Change ADR-027 status from `Proposed` to `Accepted`.

**Step 4: Update CLAUDE.md**

- In "Key Patterns" section, remove the `StateReaderAgent`/`StateWriterAgent` references
- Remove or update any mentions of `vector_db`, `TitanEmbedder`, `get_embedder`
- Add `haytham/state/store.py` to key files where `vector_db.py` was referenced
- Update "Adding a New Agent" section if it references state agents
- The `DuplicateEntryError` import path in any documented examples changes from `haytham.state.vector_db` to `haytham.state.store` (though it's also re-exported from `haytham.state`)

**Step 5: Commit**

```bash
git add docs/adr/ADR-027-replace-vectordb-with-json-store.md docs/adr/ADR-003-system-state-evolution.md docs/adr/index.md CLAUDE.md
git commit -m "docs: accept ADR-027, supersede ADR-003, update CLAUDE.md references"
```

---

## Task 12: Optionally rename `store_capabilities_in_vector_db`

**Files:**
- Modify: `haytham/workflow/stages/mvp_specification.py`
- Modify: `haytham/workflow/stages/configs.py`

This is optional cleanup. The function name `store_capabilities_in_vector_db` is now misleading since it stores to JSON. Rename to `store_capabilities_in_state`:

**Step 1: Rename in `mvp_specification.py`**

Rename the function from `store_capabilities_in_vector_db` to `store_capabilities_in_state`.

**Step 2: Update import in `configs.py`**

Change import from `store_capabilities_in_vector_db` to `store_capabilities_in_state` and update the `additional_save=` reference.

**Step 3: Run full test suite**

Run: `uv run ruff check haytham/ --fix && uv run ruff format haytham/ && uv run pytest tests/ -v -m "not integration" -x`
Expected: All PASS

**Step 4: Commit**

```bash
git add haytham/workflow/stages/mvp_specification.py haytham/workflow/stages/configs.py
git commit -m "refactor: rename store_capabilities_in_vector_db to store_capabilities_in_state"
```

---

## Task 13: Final verification

**Step 1: Run full pre-commit checks**

```bash
uv run ruff check haytham/ --fix && uv run ruff format haytham/ && uv run pytest tests/ -v -m "not integration" -x
```

Expected: All PASS, no lint errors.

**Step 2: Verify no remaining vector DB references**

```bash
grep -r "lancedb\|pyarrow\|TitanEmbedder\|get_embedder\|StateReaderAgent\|StateWriterAgent\|SystemStateDB" haytham/ --include="*.py"
```

Expected: No matches.

**Step 3: Verify deleted files are gone**

```bash
ls haytham/state/vector_db.py haytham/state/embedder.py haytham/agents/state_reader/ haytham/agents/state_writer/ 2>&1
```

Expected: All "No such file or directory".

**Step 4: Count lines removed**

```bash
git diff --stat main
```

Expected: Net reduction of ~2,500+ lines.
