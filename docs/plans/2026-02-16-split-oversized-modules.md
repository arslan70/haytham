# Split Oversized Modules Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Split 5 oversized modules into focused, debuggable units per ADR-024.

**Architecture:** Extract code along responsibility boundaries (agent execution, context building, formatting, workflow state, entry validation). Each new module maps to one debugging scenario. No behavioral changes.

**Tech Stack:** Python, Burr `GraphBuilder`, existing test suite for regression.

**Reference:** `docs/adr/ADR-024-split-oversized-modules.md`

**Verification command (run after every commit):**
```bash
uv run ruff check haytham/ --fix && uv run ruff format haytham/ && uv run pytest tests/ -v -m "not integration" -x
```

---

### Task 1: Delete `checkpoint/` directory

**Files:**
- Delete: `haytham/checkpoint/checkpoint_manager.py`
- Delete: `haytham/checkpoint/__init__.py`
- Delete: `haytham/checkpoint/README.md`

**Step 1: Verify zero importers**

Run: `uv run python -c "import ast, pathlib; files = pathlib.Path('haytham').rglob('*.py'); [print(f) for f in files if 'checkpoint' in f.read_text() and 'checkpoint_manager' not in str(f) and '__pycache__' not in str(f)]"`

Expected: Only files with docstring references (session_manager.py, test files), no actual imports.

**Step 2: Delete the directory**

```bash
rm -rf haytham/checkpoint/
```

**Step 3: Run tests**

```bash
uv run ruff check haytham/ --fix && uv run ruff format haytham/ && uv run pytest tests/ -v -m "not integration" -x
```

Expected: All tests pass. Nothing imported from checkpoint/.

**Step 4: Commit**

```bash
git add -A haytham/checkpoint/
git commit -m "chore: delete legacy checkpoint/ directory (ADR-024 step 1)

Zero production importers. __init__.py explicitly marked deprecated.
SessionManager is the complete replacement. Resolves Task 17 (formatting dedup)."
```

---

### Task 2: Extract `workflow/agent_runner.py` from `burr_actions.py`

**Files:**
- Create: `haytham/workflow/agent_runner.py`
- Modify: `haytham/workflow/burr_actions.py` (remove moved functions, keep re-exports temporarily)
- Modify: `haytham/workflow/stage_executor.py:305,328,376,401` (change lazy imports to module-level from agent_runner)
- Modify: `haytham/workflow/stages/idea_validation.py:285` (update import)
- Modify: `haytham/workflow/stages/mvp_specification.py:36` (update import)
- Modify: `haytham/feedback/feedback_agent.py` (update import of `_extract_agent_output`)

**Step 1: Create `agent_runner.py`**

Move these functions from `burr_actions.py` (lines 32-527) to a new `haytham/workflow/agent_runner.py`:
- `_is_token_limit_error()` (lines 32-56)
- `_get_user_friendly_error()` (lines 59-77)
- `run_agent()` (lines 296-406)
- `run_parallel_agents()` (lines 409-480, including nested `run_single`)
- `_extract_agent_output()` (lines 483-491)
- `save_stage_output()` (lines 494-527)

Copy the required imports for these functions (logging, concurrent.futures, typing, strands Agent, etc.). Do NOT copy context_builder or @action imports.

**Step 2: Add backward-compatible re-exports in `burr_actions.py`**

At the top of `burr_actions.py`, after removing the function bodies, add:

```python
# Re-exports for backward compatibility during migration
from .agent_runner import (
    _extract_agent_output,
    _get_user_friendly_error,
    _is_token_limit_error,
    run_agent,
    run_parallel_agents,
    save_stage_output,
)
```

**Step 3: Run tests (re-exports ensure nothing breaks yet)**

```bash
uv run ruff check haytham/ --fix && uv run ruff format haytham/ && uv run pytest tests/ -v -m "not integration" -x
```

Expected: All tests pass.

**Step 4: Update `stage_executor.py` lazy imports to module-level**

Replace the 4 lazy imports at lines 305, 328, 376, 401 with a single module-level import:

```python
from .agent_runner import (
    _extract_agent_output,
    run_agent,
    run_parallel_agents,
    save_stage_output,
)
```

Remove all 4 `from .burr_actions import` blocks inside function bodies. Remove the `# Lazy: circular dep` comments.

**Step 5: Update other importers to use `agent_runner` directly**

- `haytham/workflow/stages/idea_validation.py:285` - change `from haytham.workflow.burr_actions import run_agent, save_stage_output` to `from haytham.workflow.agent_runner import run_agent, save_stage_output`
- `haytham/workflow/stages/mvp_specification.py:36` - same pattern
- `haytham/feedback/feedback_agent.py` - change `from .burr_actions import _extract_agent_output` to `from haytham.workflow.agent_runner import _extract_agent_output`

**Step 6: Remove re-exports from `burr_actions.py`**

Delete the re-export block added in Step 2.

**Step 7: Run tests**

```bash
uv run ruff check haytham/ --fix && uv run ruff format haytham/ && uv run pytest tests/ -v -m "not integration" -x
```

Expected: All tests pass. No lazy imports remain in stage_executor.py.

**Step 8: Verify no circular imports**

```bash
uv run python -c "from haytham.workflow.agent_runner import run_agent; print('OK')"
uv run python -c "from haytham.workflow.stage_executor import execute_stage; print('OK')"
uv run python -c "from haytham.workflow.burr_actions import idea_analysis; print('OK')"
```

Expected: All print "OK" with no ImportError.

**Step 9: Commit**

```bash
git add haytham/workflow/agent_runner.py haytham/workflow/burr_actions.py haytham/workflow/stage_executor.py haytham/workflow/stages/idea_validation.py haytham/workflow/stages/mvp_specification.py haytham/feedback/feedback_agent.py
git commit -m "refactor: extract agent_runner.py, break circular dependency (ADR-024 step 2)

Move run_agent, run_parallel_agents, save_stage_output, _extract_agent_output
to workflow/agent_runner.py. Eliminates lazy imports in stage_executor.py."
```

---

### Task 3: Extract `workflow/context_builder.py` from `burr_actions.py`

**Files:**
- Create: `haytham/workflow/context_builder.py`
- Modify: `haytham/workflow/burr_actions.py` (remove moved functions)
- Modify: `haytham/workflow/stages/mvp_scope_swarm.py:39` (update import)
- Modify: `haytham/workflow/stages/mvp_specification.py:180` (update import)

**Step 1: Create `context_builder.py`**

Move these functions from `burr_actions.py` (lines 85-293) to a new `haytham/workflow/context_builder.py`:
- `_TLDR_PATTERN` compiled regex (line 80)
- `_extract_tldr()` (lines 85-108)
- `_extract_first_paragraph()` (lines 111-126)
- `_render_risk_assessment_context()` (lines 129-148)
- `render_validation_summary_from_json()` (lines 151-171, PUBLIC)
- `_render_validation_summary_context()` (lines 174-176)
- `_render_build_buy_context()` (lines 179-189)
- `_render_story_generation_context()` (lines 192-206)
- `_JSON_CONTEXT_RENDERERS` dict (lines 209-214)
- `_try_render_json_context()` (lines 217-229)
- `_build_context_summary()` (lines 232-293)

These are all pure functions. Only stdlib imports (json, re, logging).

**Step 2: Update `burr_actions.py` to import from `context_builder`**

`burr_actions.py` itself may call `_build_context_summary` from within the @action functions (via `stage_executor` -> `StageExecutionConfig`). Check whether `burr_actions.py` still needs any of these functions. If not, no re-export needed.

If `stage_executor.py` or stage configs reference `_build_context_summary`, update those imports to point to `context_builder`.

**Step 3: Update external importers**

- `haytham/workflow/stages/mvp_scope_swarm.py:39` - change `from haytham.workflow.burr_actions import render_validation_summary_from_json` to `from haytham.workflow.context_builder import render_validation_summary_from_json`
- `haytham/workflow/stages/mvp_specification.py:180` - same

**Step 4: Run tests**

```bash
uv run ruff check haytham/ --fix && uv run ruff format haytham/ && uv run pytest tests/ -v -m "not integration" -x
```

Expected: All tests pass.

**Step 5: Commit**

```bash
git add haytham/workflow/context_builder.py haytham/workflow/burr_actions.py haytham/workflow/stages/mvp_scope_swarm.py haytham/workflow/stages/mvp_specification.py
git commit -m "refactor: extract context_builder.py from burr_actions (ADR-024 step 3)

Pure functions for context summarization, TL;DR extraction, JSON renderers.
burr_actions.py now contains only @action stage wrappers."
```

---

### Task 4: Extract `session/formatting.py` from `session_manager.py`

**Files:**
- Create: `haytham/session/formatting.py`
- Modify: `haytham/session/session_manager.py:1184-1575` (replace methods with calls to formatting.py)
- Test: `tests/test_session_manager.py` (existing tests cover save_checkpoint, save_agent_output)

**Step 1: Create `formatting.py` with extracted functions**

Move from `SessionManager` (private methods become module-level functions):
- `_format_checkpoint()` (lines 1384-1480) -> `format_checkpoint(**kwargs) -> str`
- `_format_agent_output()` (lines 1483-1535) -> `format_agent_output(**kwargs) -> str`
- `_format_user_feedback()` (lines 1538-1575) -> `format_user_feedback(**kwargs) -> str`
- `_create_manifest()` (lines 1184-1226) -> `create_manifest(**kwargs) -> str`
- `_update_manifest()` (lines 1228-1305) -> `update_manifest(manifest_path, **kwargs) -> None`
- `_parse_manifest()` (lines 1307-1381) -> `parse_manifest(content) -> dict`

Each function takes explicit parameters instead of `self`. For example:

```python
def format_checkpoint(
    stage_slug: str,
    stage_name: str,
    status: str,
    started: str | None,
    completed: str | None,
    duration: float | None,
    retry_count: int,
    execution_mode: str,
    agents: list[dict],
    errors: list[str],
) -> str:
    """Format checkpoint.md content."""
    ...
```

**Step 2: Update `SessionManager` methods to delegate**

Replace method bodies with calls to `formatting.py` functions. For example:

```python
from .formatting import format_checkpoint, format_agent_output, ...

def _format_checkpoint(self, **kwargs) -> str:
    return format_checkpoint(**kwargs)
```

Or, better: update callers within SessionManager to call `formatting.format_checkpoint()` directly and remove the private methods entirely.

**Step 3: Run tests**

```bash
uv run ruff check haytham/ --fix && uv run ruff format haytham/ && uv run pytest tests/ -v -m "not integration" -x
```

Expected: All tests pass (test_session_manager.py tests save_checkpoint which calls the formatting).

**Step 4: Commit**

```bash
git add haytham/session/formatting.py haytham/session/session_manager.py
git commit -m "refactor: extract session/formatting.py from SessionManager (ADR-024 step 4)

Pure functions for checkpoint, agent output, feedback, and manifest formatting.
Testable in isolation, no self/state dependencies."
```

---

### Task 5: Extract `session/workflow_runs.py` from `session_manager.py`

**Files:**
- Create: `haytham/session/workflow_runs.py`
- Modify: `haytham/session/session_manager.py` (delegate to WorkflowRunTracker)
- Modify: `haytham/session/__init__.py` (optionally re-export WorkflowRunTracker)

**Step 1: Create `WorkflowRunTracker` class**

Move from `SessionManager` to a new class `WorkflowRunTracker(session_dir: Path)`:
- `lock_workflow()` (line 737)
- `is_workflow_locked()` (line 761)
- `get_workflow_feedback_state()` (line 776)
- `_update_workflow_run_status()` (line 825)
- `record_workflow_complete()` (line 951)
- `is_workflow_complete()` (line 994)
- `get_workflow_status()` (line 1020)
- `get_current_workflow()` (line 1050)
- `start_workflow_run()` (line 1070)
- `complete_workflow_run()` (line 1111)
- `fail_workflow_run()` (line 1147)

Also move `WORKFLOW_ALIASES` class variable (the dict mapping workflow names to lookup keys).

The class takes `session_dir: Path` in `__init__` and operates on `session_manifest.md` and `.lock` files in that directory.

**Step 2: Update `SessionManager` to delegate**

```python
from .workflow_runs import WorkflowRunTracker

class SessionManager:
    def __init__(self, base_dir="."):
        ...
        self._run_tracker = WorkflowRunTracker(self.session_dir)

    def lock_workflow(self, workflow_type):
        return self._run_tracker.lock_workflow(workflow_type)

    # ... etc for all delegated methods
```

Keep the delegation methods on SessionManager for backward compatibility (all external callers use `session_manager.is_workflow_complete()` etc.).

**Step 3: Run tests**

```bash
uv run ruff check haytham/ --fix && uv run ruff format haytham/ && uv run pytest tests/ -v -m "not integration" -x
```

Expected: All tests pass.

**Step 4: Commit**

```bash
git add haytham/session/workflow_runs.py haytham/session/session_manager.py haytham/session/__init__.py
git commit -m "refactor: extract session/workflow_runs.py from SessionManager (ADR-024 step 5)

WorkflowRunTracker encapsulates workflow state machine: start/complete/fail runs,
locking, status queries. SessionManager delegates to it."
```

---

### Task 6: Refactor `workflow_factories.py` with specs + builder

**Files:**
- Create: `haytham/workflow/workflow_specs.py`
- Create: `haytham/workflow/workflow_builder.py`
- Modify: `haytham/workflow/workflow_factories.py` (replace 5 factory functions with spec references)
- Test: existing tests that call `create_workflow_for_type()`

**Step 1: Create `WorkflowSpec` dataclass in `workflow_specs.py`**

```python
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from haytham.workflow.stage_registry import WorkflowType


@dataclass
class WorkflowSpec:
    """Declarative workflow definition."""
    workflow_type: WorkflowType
    actions: dict[str, Callable]
    transitions: list[tuple]
    entrypoint: str
    state_keys: list[str]
    tracking_project: str
    stages: list[str]
    # Extra state values beyond empty-string defaults (e.g., archetype, concept_anchor)
    extra_state_factory: Callable[[Any], dict[str, Any]] | None = None
```

Then define each workflow spec as a constant. Import @action functions from `burr_actions.py`.

**Step 2: Create `build_workflow()` in `workflow_builder.py`**

One shared function that:
1. Validates entry conditions
2. Generates app_id
3. Creates `WorkflowProgressHook` (move class here from `workflow_factories.py`)
4. Loads anchor from disk (move `_load_anchor_from_disk` here)
5. Builds `GraphBuilder` with spec's actions + transitions
6. Sets up initial state (all state_keys default to "", merge extra_state)
7. Wires hooks, tracker, identifiers
8. Returns Burr Application

**Step 3: Replace factory functions in `workflow_factories.py`**

Each `create_*_workflow()` becomes a thin wrapper that looks up the spec and calls `build_workflow()`. Or, `create_workflow_for_type()` does this directly from the spec registry.

Keep `create_workflow_for_type()`, `get_terminal_stage()`, `WORKFLOW_TERMINAL_STAGES` in `workflow_factories.py`.

**Step 4: Run tests**

```bash
uv run ruff check haytham/ --fix && uv run ruff format haytham/ && uv run pytest tests/ -v -m "not integration" -x
```

Expected: All tests pass. Workflow creation behavior unchanged.

**Step 5: Verify workflow creation still works end-to-end**

```bash
uv run python -c "
from haytham.workflow.workflow_factories import create_workflow_for_type
from haytham.workflow.stage_registry import WorkflowType
# Smoke test: can we import and reference the dispatch?
print(create_workflow_for_type)
print('OK')
"
```

**Step 6: Commit**

```bash
git add haytham/workflow/workflow_specs.py haytham/workflow/workflow_builder.py haytham/workflow/workflow_factories.py
git commit -m "refactor: extract workflow specs + builder from factories (ADR-024 step 6)

Workflow definitions are now data (WorkflowSpec). Shared build_workflow() handles
the common setup. Adding a new workflow = define a spec, no copy-paste."
```

---

### Task 7: Split `entry_conditions.py` into `workflow/entry_validators/`

**Files:**
- Create: `haytham/workflow/entry_validators/__init__.py`
- Create: `haytham/workflow/entry_validators/base.py`
- Create: `haytham/workflow/entry_validators/idea_validation.py`
- Create: `haytham/workflow/entry_validators/mvp_specification.py`
- Create: `haytham/workflow/entry_validators/build_buy.py`
- Create: `haytham/workflow/entry_validators/architecture.py`
- Create: `haytham/workflow/entry_validators/story_generation.py`
- Modify: `haytham/workflow/workflow_factories.py` (update import from entry_conditions)
- Delete or keep: `haytham/workflow/entry_conditions.py` (thin re-export shim or delete)

**Step 1: Create the package with `base.py`**

Move to `base.py`:
- `SessionStateAdapter` (lines 37-109)
- `EntryConditionResult` (lines 117-135)
- `WorkflowEntryValidator` (lines 143-274)

**Step 2: Create one file per validator**

- `idea_validation.py`: `IdeaValidationEntryValidator` (lines 282-316)
- `mvp_specification.py`: `MVPSpecificationEntryValidator` (lines 324-491)
- `build_buy.py`: `BuildBuyAnalysisEntryValidator` (lines 499-597)
- `architecture.py`: `ArchitectureDecisionsEntryValidator` (lines 605-678)
- `story_generation.py`: `StoryGenerationEntryValidator` (lines 686-772)

Each file imports the base class from `.base`.

**Step 3: Create `__init__.py` with dispatch functions and re-exports**

Move to `__init__.py`:
- `_VALIDATORS` dict (updated to import from submodules)
- `get_entry_validator()` (lines 788-806)
- `validate_workflow_entry()` (lines 809-832)
- `get_available_workflows()` (lines 840-861)
- `get_next_available_workflow()` (lines 864-895)

Re-export the key public symbols.

**Step 4: Update the one production importer**

`haytham/workflow/workflow_factories.py:26`:
```python
# Before:
from haytham.workflow.entry_conditions import validate_workflow_entry
# After:
from haytham.workflow.entry_validators import validate_workflow_entry
```

**Step 5: Decide on `entry_conditions.py`**

Option A: Delete it entirely (only 1 production importer to update).
Option B: Keep as thin re-export shim for any external/test callers.

Recommend Option A (delete) since there is exactly one importer.

**Step 6: Run tests**

```bash
uv run ruff check haytham/ --fix && uv run ruff format haytham/ && uv run pytest tests/ -v -m "not integration" -x
```

Expected: All tests pass.

**Step 7: Commit**

```bash
git add haytham/workflow/entry_validators/ haytham/workflow/workflow_factories.py
git rm haytham/workflow/entry_conditions.py  # if deleting
git commit -m "refactor: split entry_conditions into entry_validators/ package (ADR-024 step 7)

One file per workflow validator. Adding a new validator = new file + register in _VALIDATORS."
```

---

## Post-Implementation Checklist

After all 7 tasks:

1. Run full test suite: `uv run pytest tests/ -v -m "not integration"`
2. Run lint: `uv run ruff check haytham/ && uv run ruff format --check haytham/`
3. Verify no circular imports:
   ```bash
   uv run python -c "from haytham.workflow.agent_runner import run_agent; print('agent_runner OK')"
   uv run python -c "from haytham.workflow.context_builder import render_validation_summary_from_json; print('context_builder OK')"
   uv run python -c "from haytham.workflow.stage_executor import execute_stage; print('stage_executor OK')"
   uv run python -c "from haytham.workflow.burr_actions import idea_analysis; print('burr_actions OK')"
   uv run python -c "from haytham.workflow.entry_validators import validate_workflow_entry; print('entry_validators OK')"
   uv run python -c "from haytham.session.formatting import format_checkpoint; print('formatting OK')"
   uv run python -c "from haytham.session.workflow_runs import WorkflowRunTracker; print('workflow_runs OK')"
   ```
4. Verify no lazy imports remain: `grep -rn "# Lazy" haytham/workflow/` should return nothing
5. Update `CLAUDE.md` key files section to reference new modules
