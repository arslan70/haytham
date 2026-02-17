# Pre-Merge Fixes for PR #3

Issues found during code review of `here-we-go` branch. Each item is self-contained and can be tackled independently.

Status key: `[ ]` = open, `[x]` = done

---

## Critical

### C1. Split `session_manager.py` (1,119 lines, limit ~500)

- **File**: `haytham/session/session_manager.py`
- **Problem**: At 1,119 lines this is the largest file in the codebase, over 2x the CLAUDE.md limit. It handles session CRUD, checkpoint saving, workflow state delegation, MVP spec handling, feedback queries, and phase tracking.
- **Context**: ADR-024 already extracted `formatting.py` and `workflow_runs.py` from it, but didn't go far enough.
- **Fix**: Extract at least two more modules:
  - `mvp_handling.py` (lines ~602-693): MVP spec save/load/query methods
  - Collapse the ~240 lines of pure delegation methods (lines ~702-941) that just forward to `_run_tracker`. Either expose the tracker via a property or inline the delegation more concisely.
- **Validation**: `uv run pytest tests/test_session_manager.py -v` must still pass. Run `wc -l` on the result, target <500 lines.

### C2. Split 6 files exceeding 500 lines

Each file below needs splitting. The suggested splits are starting points, not prescriptions.

| File | Lines | Suggested split |
|------|-------|-----------------|
| `haytham/agents/tools/recommendation.py` | 687 | `recommendation_tools.py` (@tool functions) + `recommendation_scoring.py` (verdict/dimension logic) |
| `haytham/agents/tools/pdf_report.py` | 646 | `pdf_styles.py` (brand colors, style defs) + `pdf_markdown.py` (markdown-to-flowable parsing) + `pdf_report.py` (public API) |
| `haytham/agents/utils/langfuse_tracer.py` | 600 | `langfuse_config.py` (pricing tables, cost calc) + `langfuse_tracer.py` (tracer class) |
| `haytham/agents/utils/performance_monitor.py` | 566 | `performance_metrics.py` (dataclasses, collection) + `performance_reporter.py` (report generation, recommendations) |
| `haytham/agents/output_utils.py` | 561 | `output_extraction.py` (extract_*, scan_*) + `output_formatters.py` (_format_* functions) |
| `haytham/config.py` | 511 | `config/base.py` (enums, TimeoutConfig) + `config/tools.py` (ToolProfile, resolvers) + `config/agents.py` (AgentConfig, AGENT_CONFIGS) |

- **Validation per file**: Run `uv run ruff check haytham/` and `uv run pytest tests/ -v -m "not integration" -x` after each split. Grep for imports of the old module to update callers.

### C3. Fix TOCTOU race conditions in session file operations

- **File**: `haytham/session/session_manager.py`
- **Problem**: Two places use check-then-act patterns (`if path.exists(): shutil.rmtree(path)`) which can race if another process deletes the path between the check and the delete.
- **Locations**:
  - Line ~157: `create_session()` calls `shutil.rmtree(self.session_dir)` after an `.exists()` guard
  - Line ~223: `clear_workflow_stages()` iterates stage dirs with `.exists()` then `shutil.rmtree()`
- **Fix**: Replace check-then-act with try/except:
  ```python
  # Before (racy)
  if self.session_dir.exists():
      shutil.rmtree(self.session_dir)

  # After (safe)
  try:
      shutil.rmtree(self.session_dir)
  except FileNotFoundError:
      pass  # Already deleted
  ```
  Apply the same pattern to the lock file `.unlink()` call nearby.
- **Validation**: `uv run pytest tests/test_session_manager.py -v`

---

## High

### H1. Remove or un-deprecate `logging_utils.py`

- **File**: `haytham/agents/utils/logging_utils.py` (475 lines)
- **Problem**: This is a brand new file in this PR, yet its module docstring says `DEPRECATED: This module is deprecated in favor of OpenTelemetry-based observability.` CLAUDE.md says "When deprecating code, delete it rather than leaving dead implementations behind."
- **Fix**: Check if anything imports from this module. If yes, remove the deprecation notice. If no, delete the file entirely.
- **How to check**: `uv run ruff check haytham/ --select F401` and `grep -r "from haytham.agents.utils.logging_utils" haytham/`
- **Validation**: `uv run pytest tests/ -v -m "not integration" -x`

### H2. Deduplicate workflow aliases to single source of truth

- **File**: `haytham/session/workflow_runs.py` (lines ~27-35, `WORKFLOW_ALIASES` dict)
- **Problem**: Workflow type aliases (e.g. mapping legacy names to canonical `WorkflowType` values) are defined in `WorkflowRunTracker` but the same mapping logic also exists in `SessionManager`. This violates DRY.
- **Fix**: Move `WORKFLOW_ALIASES` to `haytham/workflow/stage_registry.py` (where `WorkflowType` is defined). Import it in both `workflow_runs.py` and `session_manager.py`.
- **Validation**: `uv run pytest tests/test_session_manager.py tests/test_pipeline_state.py -v`

### H3. Mark `bedrock_config.py` as internal

- **File**: `haytham/agents/utils/bedrock_config.py`
- **Problem**: This module is an implementation detail of `model_provider.py` (the public API), but it's exposed as a public module. Other code could accidentally import from it directly.
- **Fix**: Rename to `_bedrock_config.py`. Update the one import in `model_provider.py`.
- **Validation**: `grep -r "from.*bedrock_config" haytham/` to find all imports, then `uv run pytest tests/ -v -m "not integration" -x`

---

## Medium

### M1. Extract magic numbers in validators to named constants

- **Files**:
  - `haytham/workflow/entry_validators/mvp_specification.py` (lines ~114, ~156)
  - `haytham/workflow/entry_validators/story_generation.py` (line ~82)
- **Problem**: `len(text.strip()) >= 100` and `len(text.strip()) < 100` appear as bare magic numbers.
- **Fix**: Define `MIN_STAGE_OUTPUT_LENGTH = 100` in `entry_validators/base.py` and import in each validator.
- **Validation**: `uv run pytest tests/ -k "entry" -v`

### M2. Extract shared directory-creation helper

- **Files**: `logging_utils.py`, `performance_monitor.py`, `phase_logger.py`
- **Problem**: The pattern `try: path.mkdir(parents=True, exist_ok=True) except Exception ...` is duplicated 3+ times.
- **Fix**: Create a small helper (e.g. in `haytham/agents/utils/__init__.py` or a new `file_helpers.py`):
  ```python
  def ensure_dir(path: Path, context: str = "directory") -> bool:
      try:
          path.mkdir(parents=True, exist_ok=True)
          return True
      except OSError as e:
          logger.error("Failed to create %s %s: %s", context, path, e)
          return False
  ```
- **Validation**: `uv run ruff check haytham/ && uv run pytest tests/ -v -m "not integration" -x`

### M3. Deduplicate search result formatting

- **Files**: `haytham/agents/utils/brave_search.py`, `haytham/agents/utils/duckduckgo_search.py`, `haytham/agents/utils/web_search.py`
- **Problem**: All three format search results into markdown with nearly identical header/footer patterns.
- **Fix**: Add a `format_search_results(results, query, source)` function in `web_search.py` (the orchestrator) and call it from each provider.
- **Validation**: `uv run pytest tests/test_web_search_domains.py -v`

### M4. Reduce complexity in two functions

- **`haytham/agents/tools/pdf_report.py:302`** - `_markdown_to_flowables()` (C901 complexity: 12, limit: 10)
  - Fix: Extract each markdown element type (heading, list, code block, table) into its own handler function.
- **`haytham/agents/utils/performance_monitor.py:472`** - `_generate_recommendations()` (C901 complexity: 11, limit: 10)
  - Fix: Use a list of rule functions instead of a long if/elif chain.
- **Validation**: `uv run ruff check haytham/ --select C901`

---

## Low

### L1. Add concurrency tests for session file operations

- **File**: `tests/test_session_manager.py`
- **Problem**: No tests exercise concurrent access to session files (two processes creating/clearing sessions simultaneously).
- **Fix**: Add tests using `concurrent.futures.ThreadPoolExecutor` that call `create_session()`, `clear_workflow_stages()`, and `save_checkpoint()` from multiple threads. Verify no `FileNotFoundError` or corrupted state.
- **Validation**: The new tests themselves.

### L2. Use registry for status key construction

- **File**: `haytham/workflow/burr_workflow.py` (line ~170)
- **Problem**: Constructs status keys with `f"{stage}_status"` instead of using `registry.get_by_slug(stage).status_key`. Works today but fragile if naming conventions change.
- **Fix**: Replace the f-string with a registry lookup. This is a one-line change.
- **Validation**: `uv run pytest tests/ -k "workflow" -v`

### L3. Simplify boolean assertions in tests

- **Files**: Various test files (9 instances)
- **Problem**: `assert x is True` / `assert x is False` instead of `assert x` / `assert not x`.
- **Fix**: Find and replace. `grep -rn "assert .* is True\|assert .* is False" tests/`
- **Validation**: `uv run pytest tests/ -v -m "not integration" -x`
