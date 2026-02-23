# ADR-027: Replace VectorDB with JSON Store

## Status
**Accepted** - 2026-02-23

**Supersedes:** [ADR-003: System State Evolution](ADR-003-system-state-evolution.md)

## Context

### The Problem

[ADR-003](ADR-003-system-state-evolution.md) introduced LanceDB as a vector database for system state, with the rationale that agents would use **semantic similarity search** to query capabilities, decisions, and entities. The implementation includes:

- `SystemStateDB` (LanceDB wrapper with vector search, ~590 lines)
- `TitanEmbedder` (Amazon Titan embedding calls via Bedrock, ~135 lines)
- `StateReaderAgent` (~485 lines, wraps `SystemStateDB` with semantic search methods)
- `StateWriterAgent` (~570 lines, wraps `SystemStateDB` with typed write methods)
- `supersede.py` and `coverage.py` (~860 lines combined, change impact analysis)

Total: ~2,640 lines of vector DB infrastructure.

### What Actually Happened

An audit of every call site that uses `SystemStateDB` in the workflow reveals that **no consumer uses semantic search**:

| Call Site | Operation | Uses Vector Search? |
|---|---|---|
| `mvp_specification.py:store_capabilities_in_vector_db` | Write capabilities after capability-model stage | No |
| `entry_validators/build_buy.py` | Check capability count for entry validation | No, `get_capabilities()` |
| `state/coverage.py` | Coverage analysis across capabilities and decisions | No, `get_capabilities()` + `get_decisions()` |
| `state/supersede.py` | Change impact from superseded capabilities | No, filtered reads by type |
| `frontend_streamlit/views/artifacts.py` | Display capabilities, decisions, entities | No, `get_*()` calls |
| `frontend_streamlit/views/dashboard.py` | Show artifact counts | No, `len(db.get_*())` |
| `frontend_streamlit/lib/session_utils.py` | Compute artifact counts for session | No, `get_capabilities()` + `get_decisions()` + `get_entities()` |

The methods `find_similar()` and `impact_analysis()` are defined in both `SystemStateDB` and `StateReaderAgent`; `check_duplicate()` is defined in `StateReaderAgent` only. None of these methods are **ever called** by any workflow stage, entry validator, or frontend view. A grep for `find_similar` across `haytham/workflow/` returns zero results. There are also zero tests for any of the vector DB modules.

Every actual consumer performs one of three operations:
1. **Write** an entry by type (capability, decision, entity)
2. **Read all** entries of a given type, filtered by `superseded_by == ""`
3. **Look up** a single entry by ID

These are dictionary/list operations, not vector similarity operations.

### The Cost of Keeping It

1. **Embedding API calls on every write.** Each `add_entry()` calls `TitanEmbedder.embed()`, which makes a network round-trip to AWS Bedrock (`amazon.titan-embed-text-v2:0`). The `supersede_entry()` method makes **3 embedding calls** (delete old, re-add old with superseded flag, add new) due to LanceDB's lack of in-place update support. These embeddings are never queried by similarity.

2. **Runtime dependency on a critical path.** `lancedb>=0.26.1` and `pyarrow>=22.0.0` are behind an optional `vectordb` extra, but any workflow that reaches the capability-model stage requires them. This makes them a de facto runtime dependency for the core pipeline, not a true optional.

3. **Fragile update pattern.** `supersede_entry()` uses a delete-then-re-add dance with a `PENDING` placeholder because LanceDB doesn't support in-place updates. This is 3 separate operations (any of which could fail mid-sequence) to do what should be a dictionary update.

4. **Complexity without consumers.** ~2,640 lines of infrastructure for what is functionally a typed dictionary persisted to disk.

## Decision

Replace `SystemStateDB` (LanceDB) with a JSON-file-backed store. Keep the `SystemStateEntry` Pydantic model and `IDGenerator` unchanged.

### Alternatives Considered

**SQLite.** Gives indexed lookups, concurrent access safety, and a migration path to FTS5 (full-text search). However, with 10-50 entries per session, indexing provides no measurable benefit over a linear scan, and SQLite adds query-building complexity for what are simple list/dict operations. If entry counts grow significantly, SQLite can be substituted behind the same `SystemStateStore` API without changing callers. Not worth the complexity now.

**Strip embeddings but keep LanceDB.** Remove `TitanEmbedder` and store entries without vectors, keeping LanceDB for its metadata filtering. This eliminates Bedrock calls but retains the `lancedb`/`pyarrow` dependency, the lack-of-in-place-update problem in `supersede_entry()`, and ~590 lines of wrapper code, all for a store that is functionally a typed dictionary. The dependency cost isn't justified.

**In-memory Pydantic store with file persistence.** This is effectively what the proposed JSON store is: Pydantic models serialized to a JSON file, loaded into a dict on read. Naming it explicitly: the "JSON store" is this pattern.

### What Changes

| Component | Before | After |
|---|---|---|
| Storage backend | LanceDB (`session/vector_db/`) | JSON file (`session/system_state.json`) |
| Embedding on write | Amazon Titan via Bedrock (per entry) | None |
| Dependencies | `lancedb`, `pyarrow` | None (stdlib `json` + existing `pydantic`) |
| `SystemStateDB` | Vector DB wrapper (~590 lines) | JSON store (~150 lines est.) |
| `TitanEmbedder` | Bedrock embedding client | Removed |
| `StateReaderAgent` | Thin wrapper (~485 lines) with unused semantic search | Removed. New store API covers all methods callers actually use |
| `StateWriterAgent` | Thin wrapper (~570 lines) for typed writes | Removed. Callers use store directly |
| `supersede.py`, `coverage.py` | Import and instantiate `SystemStateDB` | Updated to use `SystemStateStore` (logic unchanged) |
| Call sites | Import `SystemStateDB` | Import `SystemStateStore` (same method signatures) |

### What Stays the Same

- `SystemStateEntry` Pydantic model (schema.py)
- `IDGenerator` and ID conventions (CAP-F-001, DEC-001, etc.)
- `supersede.py` and `coverage.py` logic (updated to use new store, but analysis logic unchanged)
- All call site method signatures (`get_capabilities()`, `get_decisions()`, `add_entry()`, etc.)
- The `supersedes`/`superseded_by` temporal chain for traceability

### New Store API

The replacement `SystemStateStore` exposes the same interface that consumers actually use:

```python
class SystemStateStore:
    """JSON-backed store for system state entries."""

    def __init__(self, store_path: Path): ...

    # Write
    def add_entry(self, entry: SystemStateEntry) -> str: ...
    def supersede_entry(self, old_id: str, new_entry: SystemStateEntry) -> str: ...
    def delete_entry(self, entry_id: str) -> bool: ...

    # Read
    def get_by_id(self, entry_id: str) -> dict | None: ...
    def find_by_name(self, name: str, entry_type: str | None = None) -> dict | None: ...
    def get_current_state(self, entry_type: str | None = None, subtype: str | None = None) -> list[dict]: ...
    def get_capabilities(self, subtype: str | None = None) -> list[dict]: ...
    def get_decisions(self) -> list[dict]: ...
    def get_entities(self) -> list[dict]: ...
    def get_history(self, entry_id: str) -> list[dict]: ...
    def count(self, entry_type: str | None = None) -> int: ...
```

Methods that are defined but never called (`find_similar`, `impact_analysis`, `check_duplicate`) are not carried forward.

### Migration

Existing `session/vector_db/` directories can be migrated by reading all entries via the current `SystemStateDB.get_current_state()` and writing them to `system_state.json`. This is a one-time operation. Since sessions are ephemeral (regenerated per idea), migration may not be necessary in practice.

## Consequences

### Positive

- **Removes ~2,640 lines** of infrastructure code that wraps unused vector search capabilities
- **Eliminates embedding API calls** that add latency and cost on every write with no downstream consumer
- **Removes `lancedb` and `pyarrow`** from the critical path, making the core pipeline dependency-free for state storage
- **Simplifies `supersede_entry()`** from a 3-step delete-re-add-re-add dance to an in-place dictionary update
- **Faster writes** (file I/O vs network round-trip to Bedrock)
- **Testable without AWS credentials** (JSON read/write vs Bedrock embedding calls)
- **Consistent with session persistence pattern.** Every other stage output is already stored as files in `session/{stage-slug}/`. The vector DB was the sole exception

### Negative

- **No semantic search capability.** The current pipeline has no consumer for semantic search, but this may reflect that the consumers haven't been built yet rather than that they'll never be needed. SENTIENCE-milestone agents that cross-reference capabilities could want similarity search. Mitigation: `SystemStateEntry` and `get_text_for_embedding()` are preserved, so the data model is ready for embeddings. Re-adding semantic search would require: a vector index dependency (LanceDB, FAISS, or similar), embedding integration in `add_entry()`, a `find_similar()` method on the store, and testing similarity quality. This is a focused task (a few hundred lines + one new dependency) but more than just re-adding `embedder.py`.
- **Linear scan for lookups.** `get_by_id()` becomes O(n) instead of indexed. With typical system state sizes (10-50 entries), this is negligible. If entry counts grow significantly, a SQLite backend can be substituted without API changes.

### Neutral

- **ADR-003 is superseded**, but its core insight remains valid: system state should be structured and queryable, not buried in Markdown documents. This ADR changes the storage backend, not the data model.
- **Concurrency.** Sessions are currently single-user, single-process. The workflow writes state, then the frontend reads it after completion. There is no concurrent read-write scenario today, so JSON file I/O is safe without locking. If parallel stage execution or live UI reloading is introduced, this assumption should be revisited (atomic write-via-rename would be cheap insurance).
- **`StateReaderAgent` and `StateWriterAgent` are removed**, not preserved as thin wrappers. Every method that callers actually use (`get_capabilities()`, `add_entry()`, etc.) is on the new `SystemStateStore` directly. Keeping two wrapper classes for a store that is already a simple API would add indirection with no value.

## Implementation Checklist

### Files to Delete

- `haytham/state/vector_db.py` (SystemStateDB, ~590 lines)
- `haytham/state/embedder.py` (TitanEmbedder, ~135 lines)
- `haytham/agents/state_reader/` (StateReaderAgent, ~485 lines)
- `haytham/agents/state_writer/` (StateWriterAgent, ~570 lines)

### Files to Create

- `haytham/state/store.py` (SystemStateStore, ~150 lines est.)

### Files to Modify

1. `haytham/state/__init__.py` - update barrel exports (remove `SystemStateDB`, `TitanEmbedder`; add `SystemStateStore`)
2. `haytham/workflow/stages/mvp_specification.py` - change import, remove `StateWriterAgent` usage, use `SystemStateStore` directly
3. `haytham/workflow/entry_validators/build_buy.py` - change import from `SystemStateDB` to `SystemStateStore`
4. `haytham/state/coverage.py` - change import from `SystemStateDB` to `SystemStateStore`
5. `haytham/state/supersede.py` - change import in 3 functions from `SystemStateDB` to `SystemStateStore`
6. `haytham/frontend_streamlit/views/artifacts.py` - change import from `SystemStateDB` to `SystemStateStore`
7. `haytham/frontend_streamlit/views/dashboard.py` - change import from `SystemStateDB` to `SystemStateStore`
8. `haytham/frontend_streamlit/lib/session_utils.py` - change import from `SystemStateDB` to `SystemStateStore`
9. `pyproject.toml` - remove `vectordb` optional extra (and from `full` composite extra)

## References

- [ADR-003: System State Evolution](ADR-003-system-state-evolution.md) (superseded by this ADR)
- [ADR-026: Simplified Validation Pipeline](ADR-026-simplified-validation-pipeline.md) (precedent for removing unused complexity)
- [CLAUDE.md: Stay Lean principle](../../CLAUDE.md) ("Minimum viable implementation. No gold-plating.")
