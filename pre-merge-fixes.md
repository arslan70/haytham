# Pre-Merge Fixes for PR #3

Findings from code review, ordered by severity. Each item is self-contained with file paths, line numbers, and fix guidance.

---

## CRITICAL (Block Merge)

### C1. 10 test files silently not discovered by pytest

**File:** `pyproject.toml:112`

**Problem:** `python_files = ["test_*.py"]` does not match 10 test files using `*_tests.py` naming. These ~3,700 lines of tests are never executed by `pytest tests/`.

**Affected files:**
- `tests/architecture_diff_tests.py`
- `tests/backlog_cli_tests.py`
- `tests/pipeline_state_tests.py`
- `tests/orchestration_tests.py`
- `tests/design_evolution_tests.py`
- `tests/implementation_execution_tests.py`
- `tests/mvp_spec_parser_tests.py`
- `tests/stack_selection_tests.py`
- `tests/story_interpretation_tests.py`
- `tests/task_generation_tests.py`

**Fix:** Either rename them to `test_*.py`, or change pyproject.toml to:
```toml
python_files = ["test_*.py", "*_tests.py"]
```

**Verify:** `uv run pytest tests/ --collect-only | grep "tests collected"` should show a higher count after the fix.

---

### C2. Thread-safety race in `_context_store` during parallel agent execution

**File:** `haytham/agents/tools/context_retrieval.py:13`
**Called from:** `haytham/workflow/agent_runner.py:129-136`

**Problem:** `run_agent()` calls `set_context_store(context)` which writes to a module-level global dict. When `run_parallel_agents` runs multiple agents concurrently with `use_context_tools=True`, all threads share the same global store. Thread A's context gets overwritten by Thread B's. The `clear_context_store()` in the `finally` block clears it for all threads.

```python
# context_retrieval.py line 13
_context_store: dict[str, str] = {}
```

**Fix:** Replace the module-level dict with `threading.local()`:
```python
import threading
_thread_local = threading.local()

def set_context_store(context: dict[str, str]) -> None:
    _thread_local.context_store = context

def get_context_store() -> dict[str, str]:
    return getattr(_thread_local, "context_store", {})

def clear_context_store() -> None:
    _thread_local.context_store = {}
```

**Verify:** Grep for all callers of `set_context_store`, `get_context_store`, `clear_context_store` and confirm they work with the new API.

---

### C3. Workflow alias inconsistency in `WorkflowRunTracker`

**File:** `haytham/session/workflow_runs.py`

**Problem:** `_update_workflow_run_status` (line 146), `complete_workflow_run` (line 338), and `fail_workflow_run` (line 374) do direct string comparison on `workflow_type`. But `is_workflow_complete` (line 214) and `get_workflow_feedback_state` (line 107-114) use `self.WORKFLOW_ALIASES` for lookup. If a workflow run is recorded under a legacy name (e.g., "discovery") but operations use "idea-validation", updates silently fail.

```python
# Line 146 -- direct comparison, ignores aliases
if run.get("workflow_type") == workflow_type:
```

**Fix:** In each of the three methods, normalize the workflow_type using the alias mapping before comparison, matching the pattern used in `is_workflow_complete`:
```python
canonical = self.WORKFLOW_ALIASES.get(workflow_type, workflow_type)
# Then compare: run.get("workflow_type") in {workflow_type, canonical}
# Or normalize both sides
```

Apply to:
- `_update_workflow_run_status` (line 146)
- `complete_workflow_run` (line 338)
- `fail_workflow_run` (line 374)

**Verify:** Unit tests in `test_session_manager.py` for workflow locking with legacy aliases.

---

## HIGH (Should Fix Before Merge)

### H1. Privacy: User startup idea logged in plaintext

**Files and lines:**
- `haytham/workflow/burr_workflow.py:151` -- `logger.info(f"System Goal: {system_goal[:50]}...")`
- `haytham/workflow/workflow_builder.py:193` -- `logger.info(f"System Goal: {system_goal[:50]}...")`
- `haytham/agents/utils/web_search.py:342-350` -- `query[:100]` logged in `extra` dict

**Problem:** CLAUDE.md says: "Never log: User's startup idea text." These lines log the user's startup idea at INFO level.

**Fix:**
- For `burr_workflow.py` and `workflow_builder.py`: Change to `logger.info("Starting workflow execution")` or `logger.debug("System goal provided, length=%d", len(system_goal))`.
- For `web_search.py`: Remove `query[:100]` from the `extra` dict in the logger call. Log only the search count and provider name.

---

### H2. Falsy-value bugs in `formatting.py`

**File:** `haytham/session/formatting.py`

**Problem:** `duration=0.0`, `input_tokens=0`, `output_tokens=0` are legitimate values that render as `"-"` due to truthiness checks.

**Line 48:**
```python
duration_str = f"{duration:.1f}s" if duration else "-"
```
`0.0` is falsy, so instant-completion stages show `"-"` instead of `"0.0s"`.

**Lines 49-51:**
```python
model_str = model if model else "-"
input_tokens_str = str(input_tokens) if input_tokens else "-"
output_tokens_str = str(output_tokens) if output_tokens else "-"
```
Token count of `0` shows `"-"` instead of `"0"`.

**Same pattern at line 175** for `format_checkpoint`.

**Fix:** Change all truthiness checks to `is not None`:
```python
duration_str = f"{duration:.1f}s" if duration is not None else "-"
input_tokens_str = str(input_tokens) if input_tokens is not None else "-"
output_tokens_str = str(output_tokens) if output_tokens is not None else "-"
```

---

### H3. `validation_warnings` state key collision across stages

**File:** `haytham/workflow/stage_executor.py:202`

**Problem:** Every stage with post-validators writes to the same `validation_warnings` state key. Later stages overwrite earlier warnings.

```python
extra_state_updates["validation_warnings"] = validation_warnings
```

**Fix:** Namespace the key per stage:
```python
extra_state_updates[f"{self.stage.slug}_validation_warnings"] = validation_warnings
```

**Verify:** Grep for any reads of `validation_warnings` from Burr state and update them to use the namespaced key. Check `burr_actions.py` `writes` lists.

---

### H4. Bare `except Exception` blocks (~15 instances)

**Problem:** CLAUDE.md says: "Never use bare `except Exception:` that silently swallows errors. Always catch specific exceptions."

**Instances to fix (prioritized by risk):**

| # | File | Line | Expected Exceptions | Risk |
|---|------|------|---------------------|------|
| 1 | `workflow/stage_executor.py` | 193 | `TypeError`, `KeyError`, `json.JSONDecodeError`, `ValueError` | Post-validator bugs invisible |
| 2 | `workflow/stage_executor.py` | 215 | `AttributeError`, `pydantic.ValidationError` | Markdown render failures hidden |
| 3 | `workflow/stage_executor.py` | 390 | `TypeError`, `RuntimeError`, `ValueError` | Custom agent errors swallowed + raw msg in output |
| 4 | `workflow/burr_workflow.py` | 237 | Consider re-raising unexpected types | Top-level catch-all |
| 5 | `workflow/workflow_builder.py` | 61 | `json.JSONDecodeError`, `OSError`, `KeyError` | Anchor loading |
| 6 | `workflow/workflow_builder.py` | 90, 111 | `TypeError`, `AttributeError` | Callbacks |
| 7 | `workflow/workflow_builder.py` | 201 | `OSError`, `json.JSONDecodeError` | Tracking |
| 8 | `workflow/agent_runner.py` | 305, 316 | `OSError`, `PermissionError` | File save failures silenced |
| 9 | `workflow/entry_validators/base.py` | 94 | `json.JSONDecodeError`, `OSError` | Concept anchor loading |
| 10 | `workflow/entry_validators/base.py` | 213 | `ImportError`, `TypeError`, `ValueError` | Phase verification |
| 11 | `workflow/entry_validators/__init__.py` | 97 | `ValueError`, `OSError`, `json.JSONDecodeError` | Availability check |
| 12 | `workflow/entry_validators/build_buy.py` | 99 | `OSError`, `json.JSONDecodeError`, `KeyError` | Capabilities loading |

**Fix pattern:** Replace each `except Exception as e:` with the specific exception types listed in the "Expected Exceptions" column.

---

### H5. `.claude/` and `.serena/` not in `.gitignore`

**File:** `.gitignore`

**Problem:** Both directories are currently untracked (`git status` shows `?? .claude/` and `?? .serena/`). `.claude/` contains machine-specific paths (`/Users/amehboob/Desktop/haytham`) and local permission overrides.

**Fix:** Add to `.gitignore`:
```
# Claude Code (machine-local)
.claude/

# Serena IDE plugin (cache and memories are local)
.serena/cache/
.serena/memories/
```

---

## MEDIUM (Nice to Fix)

### M1. Imports inside function bodies without circular dependency justification

**Problem:** CLAUDE.md says: "Module-level imports only. No import inside function bodies unless avoiding a genuine circular dependency (document the reason in a comment)."

**Instances to fix:**

| File | Lines | Import | Action |
|------|-------|--------|--------|
| `agents/output_utils.py` | 99, 296 | `from pydantic import BaseModel` | Move to module-level (pydantic is a core dep) |
| `agents/output_utils.py` | 102-113 | `from haytham.workflow.stage_output import StageOutput` | Add comment explaining circular dep, or move to module-level |
| `session/session_manager.py` | 981, 1001, 1027, 1048, 1101, 1131 | 6 imports from `formatting.py` | Move all to module-level (no circular dep exists) |
| `workflow/burr_workflow.py` | 135 | `from .stage_registry import WorkflowType` | Move to module-level |
| `workflow/agent_runner.py` | 114, 119, 279 | Various workflow/agent imports | Add comments explaining circular dep reason (this file was extracted to break cycles) |
| `agents/utils/model_provider.py` | 128, 186 | `bedrock_config` imports | Add comment or move to module-level |

---

### M2. Hardcoded stage lists bypass StageRegistry

**Problem:** Three files maintain hardcoded stage lists instead of deriving them from the registry or specs. When stages change, these go stale.

| File | Lines | What's Hardcoded |
|------|-------|------------------|
| `workflow/burr_workflow.py` | 174-178 | Failure detection checks only 4 stages |
| `workflow/context_builder.py` | 199-207 | Context key list with display names |
| `workflow/workflow_factories.py` | 158-164 | `WORKFLOW_TERMINAL_STAGES` dict |

**Fix for `workflow_factories.py`:** Compute from specs:
```python
WORKFLOW_TERMINAL_STAGES = {wt: spec.stages[-1] for wt, spec in WORKFLOW_SPECS.items()}
```

**Fix for others:** Derive from `StageRegistry` or `WorkflowSpec` data.

---

### M3. Module-level `_scorecard` has no thread locking

**File:** `haytham/agents/tools/recommendation.py:166-172`

**Problem:** Unlike `web_search.py` which uses `threading.Lock` to protect its counter, the scorecard accumulator dict has no synchronization. The `@tool` functions mutate `_scorecard` directly.

**Fix:** Add a `threading.Lock` and acquire it in `record_knockout`, `record_dimension_score`, `record_counter_signal`, `clear_scorecard`, and `get_scorecard`.

---

### M4. No `conftest.py` in test suite

**File:** `tests/` (missing file)

**Problem:** 50 test files with no shared fixtures. The `_mock_reportlab()` boilerplate is duplicated across 5+ files. `temp_dir` and `session_manager` fixtures are redefined independently in multiple files.

**Fix:** Create `tests/conftest.py` with:
1. Shared `_mock_reportlab` autouse fixture
2. Shared `tmp_path`-based session directory fixture
3. Shared `session_manager` fixture

---

### M5. Dead code

| File | Lines | What | Action |
|------|-------|------|--------|
| `workflow/burr_workflow.py` | ~270-320 | `run_single_stage` | Delete (never called) |
| `workflow/burr_workflow.py` | ~330+ | `run_workflow_async` | Delete (never imported) |
| `workflow/agent_runner.py` | 273-281 | `_extract_agent_output` | Delete backward-compat wrapper, update callers to import from `output_utils` |
| `workflow/entry_validators/*.py` | Various | `if TYPE_CHECKING: pass` | Remove unused `TYPE_CHECKING` imports from 5 files: `idea_validation.py`, `mvp_specification.py`, `build_buy.py`, `architecture.py`, `story_generation.py` |
| `session/session_manager.py` | 77 | `self.archive_dir` | Delete unused attribute |
| `session/session_manager.py` | 538-557 | `archive_session()` | Delete deprecated method (or add `warnings.warn()`) |

---

### M6. Inconsistent `session_manager` in Burr action `reads` declarations

**File:** `haytham/workflow/burr_actions.py`

**Problem:** Some actions declare `"session_manager"` in their `reads` list, others don't. But `StageExecutor.execute()` always reads it from state. This is an inconsistency that could cause issues if Burr ever enforces read declarations.

**Actions missing `"session_manager"` in reads:** Lines 44, 61, 69, 84, 264, 283.

**Fix:** Add `"session_manager"` to the `reads` list of every action that calls `execute_stage`.

---

## LOW (Cleanup / Tech Debt)

### L1. Docstring says `KeyError` but raises `ValueError`

**File:** `haytham/workflow/stage_registry.py:546-559`

`get_workflow_for_stage` docstring says `Raises: KeyError` but `get_by_slug` raises `ValueError`.

---

### L2. Inconsistent timezone in `save_final_output`

**File:** `haytham/session/session_manager.py:568`

Uses `datetime.now()` (local time) while everywhere else uses `datetime.now(UTC)`.

---

### L3. `streaming` parameter silently dropped for non-Bedrock providers

**File:** `haytham/agents/utils/model_provider.py:197-279`

`_create_anthropic`, `_create_openai`, and `_create_ollama` accept `streaming` but never pass it to their model constructors.

---

### L4. `int()` on env var with no error handling

**File:** `haytham/agents/utils/web_search.py:47,51`

```python
int(os.getenv("WEB_SEARCH_SESSION_LIMIT", "20"))
```

Will crash with `ValueError` if env var is set to non-integer.

**Fix:** Wrap in try/except with fallback to default.

---

### L5. Section header detection threshold inconsistent

**File:** `haytham/agents/tools/content_extraction.py`

The colon-based header detection heuristic uses `len(line) < 50` in two places and `len(line) < 60` in another. Should be consistent and extracted to a shared helper.

---

### L6. `get_terminal_stage` returns empty string on unknown type

**File:** `haytham/workflow/workflow_factories.py:176`

Returning `""` is a silent failure. Should raise `ValueError` for unknown workflow types.

---

### L7. `is_final_stage` checks global last stage, not per-workflow

**File:** `haytham/workflow/stage_registry.py:504-509`

Returns `False` for `validation_summary` (which IS the last stage of idea-validation). `is_last_stage_of_workflow` at line 585 is the correct method. Consider deprecating `is_final_stage` or fixing its semantics.

---

### L8. Regex compiled inside method body

**File:** `haytham/workflow/entry_validators/mvp_specification.py:167`

```python
match = re.search(r"RECOMMENDATION:\s*(GO|NO-GO|PIVOT)", summary_upper)
```

Per CLAUDE.md: "Compile regex patterns at module level."

---

### L9. `_build_context_summary` has underscore prefix but is imported externally

**File:** `haytham/workflow/context_builder.py`

Imported by `agent_runner.py` despite the `_` prefix indicating module-private. Rename to `build_context_summary` (no underscore).

---

### L10. Makefile inconsistencies

- `pytest` and `ruff` invoked without `uv run` prefix (CLAUDE.md says to use `uv run`)
- `lint` target missing `--fix` flag
- Missing `.PHONY` entries for 7 targets: `burr`, `test-unit`, `test-e2e`, `clear-from-preview`, `stages-list`, `view-stage`, `stages`

---

### L11. Silent `json.JSONDecodeError` handling in `workflow_runs.py`

**File:** `haytham/session/workflow_runs.py` (lines 152, 221, 251, 272, 294, 348, 383)

Corrupted `workflow_runs.json` causes all queries to return "not_started" silently. Add `logger.warning` in each `except json.JSONDecodeError` block.

---

### L12. `_clear_workflow_runs` silently swallows JSON errors

**File:** `haytham/session/session_manager.py:243`

```python
except json.JSONDecodeError:
    pass
```

Add `logger.warning("Corrupted workflow_runs.json, skipping clear")`.

---

### L13. Duplicate telemetry import pattern

**Files:** `burr_workflow.py:115-126` and `stage_executor.py:124-132`

Same try/except ImportError pattern duplicated. Extract to a shared helper in `haytham/telemetry.py`.
