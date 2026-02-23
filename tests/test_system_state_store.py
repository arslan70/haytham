"""Tests for SystemStateStore (ADR-027).

Covers write-path operations: add, supersede, delete.
"""

import json

import pytest

# Import from submodules directly to avoid __init__.py pulling in lancedb
# (will be cleaned up when __init__.py is updated in a later task)
from haytham.state.schema import (
    SystemStateEntry,
    create_capability,
    create_decision,
    create_entity,
)
from haytham.state.store import DuplicateEntryError, SystemStateStore

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_cap(name: str = "Auth", subtype: str = "functional") -> SystemStateEntry:
    return create_capability(
        name=name,
        description=f"Description for {name}",
        subtype=subtype,
        source_stage="capability-model",
    )


def _make_decision(name: str = "Use PostgreSQL") -> SystemStateEntry:
    return create_decision(
        name=name,
        description=f"Description for {name}",
        rationale=f"Rationale for {name}",
        source_stage="architecture-decisions",
    )


def _store(tmp_path) -> SystemStateStore:
    return SystemStateStore(tmp_path / "system_state.json")


# ---------------------------------------------------------------------------
# TestAddEntry
# ---------------------------------------------------------------------------


class TestAddEntry:
    """add_entry generates IDs, persists, rejects duplicates."""

    def test_generates_id_when_empty(self, tmp_path):
        store = _store(tmp_path)
        entry = _make_cap()
        assert entry.id == ""
        returned_id = store.add_entry(entry)
        assert returned_id == "CAP-F-001"

    def test_persists_to_disk(self, tmp_path):
        path = tmp_path / "system_state.json"
        store = SystemStateStore(path)
        store.add_entry(_make_cap())
        assert path.exists()
        data = json.loads(path.read_text())
        assert "CAP-F-001" in data

    def test_duplicate_name_type_raises(self, tmp_path):
        store = _store(tmp_path)
        store.add_entry(_make_cap("Auth"))
        with pytest.raises(DuplicateEntryError, match="Auth"):
            store.add_entry(_make_cap("Auth"))

    def test_same_name_different_type_allowed(self, tmp_path):
        store = _store(tmp_path)
        store.add_entry(_make_cap("Logging"))
        dec = _make_decision("Logging")
        dec_id = store.add_entry(dec)
        assert dec_id == "DEC-001"

    def test_preset_id_preserved(self, tmp_path):
        store = _store(tmp_path)
        entry = _make_cap()
        entry.id = "CUSTOM-ID-999"
        returned_id = store.add_entry(entry)
        assert returned_id == "CUSTOM-ID-999"
        assert store.get_by_id("CUSTOM-ID-999") is not None

    def test_sequential_ids(self, tmp_path):
        store = _store(tmp_path)
        id1 = store.add_entry(_make_cap("A"))
        id2 = store.add_entry(_make_cap("B"))
        id3 = store.add_entry(_make_cap("C"))
        assert id1 == "CAP-F-001"
        assert id2 == "CAP-F-002"
        assert id3 == "CAP-F-003"

    def test_sequential_ids_across_subtypes(self, tmp_path):
        store = _store(tmp_path)
        f_id = store.add_entry(_make_cap("Func", subtype="functional"))
        nf_id = store.add_entry(_make_cap("NonFunc", subtype="non_functional"))
        assert f_id == "CAP-F-001"
        assert nf_id == "CAP-NF-001"

    def test_counters_resume_on_reload(self, tmp_path):
        """After reopening the store, IDs continue from the highest existing."""
        path = tmp_path / "system_state.json"
        store = SystemStateStore(path)
        store.add_entry(_make_cap("A"))
        store.add_entry(_make_cap("B"))

        store2 = SystemStateStore(path)
        id3 = store2.add_entry(_make_cap("C"))
        assert id3 == "CAP-F-003"

    def test_nullable_fields_normalized(self, tmp_path):
        store = _store(tmp_path)
        store.add_entry(_make_cap())
        record = store.get_by_id("CAP-F-001")
        assert record is not None
        assert record["supersedes"] is None
        assert record["superseded_by"] is None
        assert record["rationale"] is None

    def test_creates_parent_dirs(self, tmp_path):
        deep_path = tmp_path / "a" / "b" / "c" / "state.json"
        store = SystemStateStore(deep_path)
        store.add_entry(_make_cap())
        assert deep_path.exists()


# ---------------------------------------------------------------------------
# TestSupersedeEntry
# ---------------------------------------------------------------------------


class TestSupersedeEntry:
    """supersede_entry links old and new entries."""

    def test_supersede_basic(self, tmp_path):
        store = _store(tmp_path)
        old_id = store.add_entry(_make_cap("Auth"))
        new_entry = _make_cap("Auth v2")
        new_id = store.supersede_entry(old_id, new_entry)

        old = store.get_by_id(old_id)
        new = store.get_by_id(new_id)

        assert old is not None
        assert old["superseded_by"] == new_id
        assert new is not None
        assert new["supersedes"] == old_id

    def test_superseded_excluded_from_current(self, tmp_path):
        store = _store(tmp_path)
        old_id = store.add_entry(_make_cap("Auth"))
        store.supersede_entry(old_id, _make_cap("Auth v2"))

        current = store.get_current_state()
        ids = [e["id"] for e in current]
        assert old_id not in ids

    def test_supersede_nonexistent_raises(self, tmp_path):
        store = _store(tmp_path)
        with pytest.raises(ValueError, match="not found"):
            store.supersede_entry("NOPE-001", _make_cap("New"))

    def test_history_chain(self, tmp_path):
        store = _store(tmp_path)
        id1 = store.add_entry(_make_cap("Auth"))
        id2 = store.supersede_entry(id1, _make_cap("Auth v2"))
        id3 = store.supersede_entry(id2, _make_cap("Auth v3"))

        history = store.get_history(id3)
        assert len(history) == 3
        assert history[0]["id"] == id3
        assert history[1]["id"] == id2
        assert history[2]["id"] == id1

    def test_supersede_persists(self, tmp_path):
        """Supersede relationships survive a reload."""
        path = tmp_path / "system_state.json"
        store = SystemStateStore(path)
        old_id = store.add_entry(_make_cap("Auth"))
        new_id = store.supersede_entry(old_id, _make_cap("Auth v2"))

        store2 = SystemStateStore(path)
        old = store2.get_by_id(old_id)
        assert old is not None
        assert old["superseded_by"] == new_id


# ---------------------------------------------------------------------------
# TestDeleteEntry
# ---------------------------------------------------------------------------


class TestDeleteEntry:
    """delete_entry removes entries by ID."""

    def test_delete_existing(self, tmp_path):
        store = _store(tmp_path)
        entry_id = store.add_entry(_make_cap())
        assert store.delete_entry(entry_id) is True
        assert store.get_by_id(entry_id) is None

    def test_delete_nonexistent(self, tmp_path):
        store = _store(tmp_path)
        assert store.delete_entry("NOPE-001") is False

    def test_delete_persists(self, tmp_path):
        path = tmp_path / "system_state.json"
        store = SystemStateStore(path)
        entry_id = store.add_entry(_make_cap())
        store.delete_entry(entry_id)

        store2 = SystemStateStore(path)
        assert store2.get_by_id(entry_id) is None


# ---------------------------------------------------------------------------
# TestReadOperations (basic coverage of read helpers)
# ---------------------------------------------------------------------------


class TestReadOperations:
    """Quick smoke tests for convenience readers and count."""

    def test_get_capabilities(self, tmp_path):
        store = _store(tmp_path)
        store.add_entry(_make_cap("A"))
        store.add_entry(_make_decision("D"))
        caps = store.get_capabilities()
        assert len(caps) == 1
        assert caps[0]["name"] == "A"

    def test_get_capabilities_filtered_by_subtype(self, tmp_path):
        store = _store(tmp_path)
        store.add_entry(_make_cap("A", subtype="functional"))
        store.add_entry(_make_cap("B", subtype="non_functional"))
        assert len(store.get_capabilities(subtype="functional")) == 1

    def test_get_decisions(self, tmp_path):
        store = _store(tmp_path)
        store.add_entry(_make_decision("D1"))
        store.add_entry(_make_cap("C1"))
        decs = store.get_decisions()
        assert len(decs) == 1

    def test_get_entities(self, tmp_path):
        store = _store(tmp_path)
        ent = create_entity(name="User", description="A user")
        store.add_entry(ent)
        assert len(store.get_entities()) == 1

    def test_count(self, tmp_path):
        store = _store(tmp_path)
        store.add_entry(_make_cap("A"))
        store.add_entry(_make_cap("B"))
        store.add_entry(_make_decision("D"))
        assert store.count() == 3
        assert store.count(entry_type="capability") == 2
        assert store.count(entry_type="decision") == 1

    def test_find_by_name(self, tmp_path):
        store = _store(tmp_path)
        store.add_entry(_make_cap("Auth"))
        result = store.find_by_name("Auth")
        assert result is not None
        assert result["name"] == "Auth"

    def test_find_by_name_with_type(self, tmp_path):
        store = _store(tmp_path)
        store.add_entry(_make_cap("Logging"))
        store.add_entry(_make_decision("Logging"))
        result = store.find_by_name("Logging", entry_type="decision")
        assert result is not None
        assert result["type"] == "decision"

    def test_find_by_name_excludes_superseded(self, tmp_path):
        store = _store(tmp_path)
        old_id = store.add_entry(_make_cap("Auth"))
        store.supersede_entry(old_id, _make_cap("Auth v2"))
        result = store.find_by_name("Auth")
        assert result is None

    def test_empty_store_reads(self, tmp_path):
        store = _store(tmp_path)
        assert store.get_by_id("NOPE") is None
        assert store.find_by_name("NOPE") is None
        assert store.get_current_state() == []
        assert store.get_capabilities() == []
        assert store.get_decisions() == []
        assert store.get_entities() == []
        assert store.get_history("NOPE") == []
        assert store.count() == 0
