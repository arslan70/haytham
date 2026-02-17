# ADR-024: Split Oversized Modules

## Status
**Accepted** -- 2026-02-16

## Context

After completing Tasks 1-8 of the pre-merge cleanup (PR #3), six files have multiple responsibilities tangled together:

| File | Lines | Core Problem |
|------|------:|-------------|
| `session/session_manager.py` | 1,575 | God object: 47 methods spanning 9 responsibilities |
| `workflow/workflow_factories.py` | 946 | 5 copy-paste factory functions with ~80% identical boilerplate |
| `workflow/entry_conditions.py` | 895 | 5 validators in one file, no way to find the right one from a traceback |
| `checkpoint/checkpoint_manager.py` | 867 | Dead code (zero production importers, explicitly deprecated) |
| `workflow/burr_actions.py` | 848 | Circular dependency with `stage_executor.py`, mixes 3 concerns |
| `backlog/cli.py` | 828 | Self-contained, well-organized. Not worth splitting |

### Design Principles

Line count is not the goal. The splits are driven by:

1. **Extensibility:** When adding a new workflow or stage, which files do you touch? Fewer is better.
2. **Debuggability:** When something breaks, does the module name in the traceback tell you what went wrong?

### Interactions with Other Tasks

- **Task 17** (deduplicate formatting): Resolved by deleting `checkpoint_manager.py`. No second copy to deduplicate.
- **Task 10** (dispatch dicts): Independent. Can be done before or after.
- **Task 6** (circular dep): Resolved by extracting `agent_runner.py`.

## Decisions

### 1. Delete `checkpoint/` directory

**Verdict: LEGACY. Delete, do not split.**

Evidence:
- Zero production importers. No Python file imports `CheckpointManager`.
- `checkpoint/__init__.py` explicitly says: "Deprecated - use SessionManager."
- The `projects/{id}/sessions/{id}/` directory structure it writes to does not exist.
- `SessionManager` provides all equivalent functionality with the newer `session/{slug}/` model.
- No test file exists for it.
- Two docstrings elsewhere confirm it was replaced: `session_manager.py` line 4 and `test_change_request_handler.py` line 3.

Per CLAUDE.md deprecation policy: "When deprecating code, delete it."

### 2. Extract `workflow/agent_runner.py` from `burr_actions.py`

**Problem:** Circular dependency. `burr_actions.py` imports `execute_stage` from `stage_executor.py`. `stage_executor.py` lazy-imports `run_agent`, `run_parallel_agents`, `save_stage_output`, `_extract_agent_output` from `burr_actions.py`.

**Move to `agent_runner.py`:**
- `run_agent()`
- `run_parallel_agents()`
- `save_stage_output()`
- `_extract_agent_output()`
- `_is_token_limit_error()`
- `_get_user_friendly_error()`

**Import graph after split:**
```
stage_executor.py ──imports──> agent_runner.py
burr_actions.py   ──imports──> agent_runner.py  (if needed for shared helpers)
workflow_factories.py ──imports──> burr_actions.py (stage @action functions only)
```

No more lazy imports. No circular dependency.

**Debug value:** Agent call fails -> traceback says `agent_runner.py`.

### 3. Extract `workflow/context_builder.py` from `burr_actions.py`

**Move to `context_builder.py`:**
- `_build_context_summary()`, `_extract_tldr()`, `_extract_first_paragraph()`
- All `_render_*_context()` functions and `_JSON_CONTEXT_RENDERERS` dict
- `render_validation_summary_from_json()` (public, imported by `mvp_scope_swarm.py` and `mvp_specification.py`)
- `_try_render_json_context()`
- `_TLDR_PATTERN` compiled regex

All pure functions. Zero state dependencies. Zero circular dependency risk.

**What stays in `burr_actions.py`:**
- 13 `@action` stage functions (thin wrappers calling `execute_stage`)
- 2 human-in-the-loop actions (`await_user_approval`, `await_user_choice`)

**Debug value:** Stage gets garbage context -> traceback says `context_builder.py`.

### 4. Refactor `workflow_factories.py` with `GraphBuilder` + data specs

**Problem:** 5 factory functions with ~80% identical boilerplate (~120 lines each). Adding a new workflow means copying and tweaking.

**Approach:** Use Burr's `GraphBuilder` to separate graph topology from application setup.

**Create `workflow/workflow_specs.py`** with workflow definitions as data:
```python
@dataclass
class WorkflowSpec:
    workflow_type: WorkflowType
    actions: dict[str, Callable]      # action_name -> @action function
    transitions: list[tuple]           # Burr transition tuples
    entrypoint: str
    state_keys: list[str]             # Keys to initialize in state
    tracking_project: str
    stages: list[str]                 # For progress hook ordering
```

Five spec constants: `IDEA_VALIDATION_SPEC`, `MVP_SPECIFICATION_SPEC`, etc.

**Create `workflow/workflow_builder.py`** with one shared `build_workflow()` function that:
1. Validates entry conditions
2. Generates app_id
3. Builds graph from spec's actions + transitions via `GraphBuilder`
4. Sets up initial state from spec's state_keys
5. Wires hooks, tracker, identifiers
6. Returns Burr Application

**What stays in `workflow_factories.py`:**
- `create_workflow_for_type()` dispatch
- `get_terminal_stage()`
- `WORKFLOW_TERMINAL_STAGES`

**Extensibility value:** New workflow = define a `WorkflowSpec`, register it. No copy-paste.

### 5. Split `session_manager.py` into focused modules

`SessionManager` has 47 methods across 9 responsibility groups. Three extractions:

**`session/formatting.py` (pure functions):**
- `format_checkpoint()` (was `_format_checkpoint`)
- `format_agent_output()` (was `_format_agent_output`)
- `format_user_feedback()` (was `_format_user_feedback`)
- `create_manifest()` (was `_create_manifest`)
- `update_manifest()` (was `_update_manifest`)
- `parse_manifest()` (was `_parse_manifest`)

Module-level functions, not private methods. Explicit parameters, not `self`. Testable in isolation.

**`session/workflow_runs.py` (workflow state machine):**
Extract as `WorkflowRunTracker` class taking `session_dir: Path`:
- `start_workflow_run()`, `complete_workflow_run()`, `fail_workflow_run()`
- `record_workflow_complete()`, `is_workflow_complete()`, `get_workflow_status()`, `get_current_workflow()`
- `lock_workflow()`, `is_workflow_locked()`, `get_workflow_feedback_state()`

`SessionManager` holds a `WorkflowRunTracker` instance and delegates.

**What stays in `SessionManager`:**
- Session lifecycle (create, load, has_active, clear)
- System goal delegation to ProjectStateManager
- Stage I/O (save_checkpoint, save_agent_output, save_user_feedback, get_stage_outputs, load_stage_output) calling `formatting.py`
- MVP spec management, preferences, backlog markers, phase management (small, domain-specific)

**Debug value:** "Workflow won't restart" -> `workflow_runs.py`. "Output file looks wrong" -> `formatting.py`. "Session won't load" -> `session_manager.py`.

### 6. Split `entry_conditions.py` into `workflow/entry_validators/` package

Note: `workflow/validators/` is already taken by ADR-022 post-validators (claim_origin, concept_health, etc.). Entry condition validators go in a separate package.

```
workflow/entry_validators/
    __init__.py              # Re-exports dispatch functions + _VALIDATORS dict
    base.py                  # WorkflowEntryValidator, EntryConditionResult, SessionStateAdapter
    idea_validation.py       # IdeaValidationEntryValidator
    mvp_specification.py     # MVPSpecificationEntryValidator
    build_buy.py             # BuildBuyAnalysisEntryValidator
    architecture.py          # ArchitectureDecisionsEntryValidator
    story_generation.py      # StoryGenerationEntryValidator
```

Update the one production importer (`workflow_factories.py`) to import from `workflow.entry_validators`.

**Extensibility value:** New workflow validator = new file in `validators/`, register in `_VALIDATORS`.

### 7. Skip `backlog/cli.py`

Self-contained, well-organized internally, 2 importers, part of the generated system output. Not worth the churn.

## Execution Order

Each step is independently commitable and testable. No step depends on a later step.

1. **Delete `checkpoint/`** (zero risk, resolves Task 17)
2. **Extract `agent_runner.py`** (fixes circular dep, highest structural value)
3. **Extract `context_builder.py`** (clean, pure functions)
4. **Extract `session/formatting.py`** (pure functions, enables testing)
5. **Extract `session/workflow_runs.py`** (separates state machine from god object)
6. **Refactor `workflow_factories.py`** with specs + builder (biggest refactor, benefits from clean imports)
7. **Split `entry_conditions.py`** into `entry_validators/` (self-contained)

**Before every commit:** `uv run ruff check haytham/ --fix && uv run ruff format haytham/ && uv run pytest tests/ -v -m "not integration" -x`

## Import Boundary Rules After Split

- `workflow/agent_runner.py` imports from `agents/` (factory) and `session/` (save output). Does NOT import from `burr_actions.py` or `stage_executor.py`.
- `workflow/context_builder.py` is pure. Imports only stdlib.
- `workflow/burr_actions.py` imports from `stage_executor.py` only. Stage actions call `execute_stage()`.
- `workflow/stage_executor.py` imports from `agent_runner.py` (not `burr_actions.py`). No more lazy imports.
- `session/formatting.py` is pure. No imports from `session_manager.py`.
- `session/workflow_runs.py` imports from `workflow/stage_registry.py` for `WorkflowType`. Does NOT import `SessionManager`.

## Consequences

**Positive:**
- Circular dependency between `burr_actions` and `stage_executor` eliminated
- Each module name maps to one debugging scenario
- Adding a new workflow touches: one spec in `workflow_specs.py`, one validator in `validators/`, one set of stage configs. No copy-paste
- Task 17 (formatting dedup) resolved as a side effect of deleting `checkpoint/`
- ~870 lines of dead code removed

**Negative:**
- More files to navigate (mitigated by clear naming and one-concept-per-file)
- Import path changes for 6 files that import from `burr_actions.py`
- `entry_conditions.py` import path changes for `workflow_factories.py`

**Not changing:**
- No behavioral changes. All existing functionality preserved
- No new dependencies
- `backlog/cli.py` stays as-is
