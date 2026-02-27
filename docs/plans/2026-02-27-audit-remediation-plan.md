# Audit Remediation Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix the actionable gaps identified in `audit-report.md` (4 critical, 28 warnings, 16 suggestions), prioritized by impact.

**Architecture:** Security fixes first, then workflow integrity (fail-fast transitions, context validation), then documentation drift, then code hygiene, then open-source readiness. Items requiring large refactors or design decisions are deferred with rationale.

**Tech Stack:** Python 3.12, Burr (state machine), Strands SDK, Streamlit, ruff, pytest

---

## Scope Decisions

### In Scope (this plan)

| ID | Summary |
|----|---------|
| CRIT-01 | Fail-fast workflow transitions |
| CRIT-03 | Documentation describes removed architecture |
| WARN-01 | Required context validation before execution |
| WARN-05 | Startup config validation |
| WARN-11 | XSS via unsafe_allow_html |
| WARN-12 | Path traversal in delete_project |
| WARN-13 | LLM I/O logging violates policy |
| WARN-15 | "21 agents" count outdated (actual: 19) |
| WARN-16 | AGENT_FACTORIES referenced (actual: AGENT_CONFIGS) |
| WARN-17 | Referenced files do not exist |
| WARN-18 | Module READMEs describe wrong architecture |
| WARN-19 | Sequential vs parallel inconsistency |
| WARN-20 | Troubleshooting/CONTRIBUTING reference removed stage |
| WARN-21 | Em dashes in plan doc |
| WARN-22 | Web search session limit inconsistency |
| WARN-23 | 4x duplicate extract_text wrappers |
| WARN-28 | Broad except Exception blocks (annotation pass) |
| WARN-31 | Missing .pre-commit-config.yaml |

### Deferred (with rationale)

| ID | Summary | Rationale |
|----|---------|-----------|
| CRIT-02 | SessionManager in Burr state | 12+ action refactor acknowledged in code comment. Requires design decision on DI pattern. Separate PR. |
| CRIT-04 | 16% test coverage | Separate initiative. Too broad for a single plan. |
| WARN-02 | Global context store race condition | No concurrent agent execution today. Fix when parallelism is added. |
| WARN-03 | File-based state no locking | No concurrent access pattern exists. Fix when multi-tenant. |
| WARN-04 | Transient error string matching | Works currently. Fix when AWS SDK provides typed errors. |
| WARN-06 | No end-to-end integration test | Separate test initiative alongside CRIT-04. |
| WARN-07 | Session rmtree on creation | Design decision needed (archive vs timestamp). Separate PR. |
| WARN-08 | Missing JSON context renderers | TL;DR fallback works. Add renderers incrementally per stage. |
| WARN-09 | Hook timing not thread-safe | Each agent gets its own hook instance. Safe today. |
| WARN-10 | Global mutable singletons | Works for single-process. Fix when multi-tenant. |
| WARN-14 | Langfuse full I/O | Disabled by default. Document in .env.example (covered in WARN-22 area). |
| WARN-24 | 83 function-body imports | Massive refactor, circular dep resolution needed. Separate initiative. |
| WARN-25 | 113 functions over 50 lines | Refactor incrementally as modules are touched. |
| WARN-26 | Nesting depth 13 | Refactor when cli.py is next modified. |
| WARN-27 | Placeholder verifier | Design decision on what verification means. Separate PR. |
| WARN-29 | Missing CHANGELOG.md | Frequent changes in progress. Add when release cadence stabilizes. |
| WARN-30 | Missing GitHub issue/PR templates | Not needed yet. Add closer to public release. |
| S-01..S-16 | Suggestions | Nice-to-haves. Defer per "Stay Lean" principle. |

---

## Task 1: Security - XSS Fix (WARN-11)

**Files:**
- Modify: `frontend_streamlit/views/execution.py`
- Test: `tests/test_execution_xss.py`

**Step 1: Write the failing test**

```python
# tests/test_execution_xss.py
"""Tests for XSS prevention in Streamlit execution view."""
import html


def test_html_escape_prevents_xss():
    """Verify html.escape sanitizes XSS payloads."""
    malicious = '<img src=x onerror=alert(1)>'
    escaped = html.escape(malicious)
    assert "<" not in escaped
    assert ">" not in escaped
    assert "&lt;" in escaped


def test_html_escape_preserves_normal_text():
    """Verify html.escape doesn't mangle normal startup ideas."""
    normal = "A gym leaderboard app for CrossFit athletes"
    assert html.escape(normal) == normal
```

**Step 2: Run test to verify it passes**

Run: `uv run pytest tests/test_execution_xss.py -v`
Expected: PASS (these test html.escape behavior)

**Step 3: Add html.escape to execution.py**

In `frontend_streamlit/views/execution.py`, add `import html` at the top, then escape all user-derived strings before HTML embedding:

- Line 111: `html.escape(unrelated_redirect["original_input"])`
- Line 118: `html.escape(unrelated_redirect["message"])`
- Line 144-145: `html.escape(icon)`, `html.escape(title)`, `html.escape(description)`

**Step 4: Verify lint passes**

Run: `uv run ruff check frontend_streamlit/ --fix && uv run ruff format frontend_streamlit/`

**Step 5: Commit**

```
fix(security): escape HTML in Streamlit execution view (WARN-11)
```

---

## Task 2: Security - Path Traversal Fix (WARN-12)

**Files:**
- Modify: `haytham/project/project_manager.py`
- Test: `tests/test_project_manager_security.py`

**Step 1: Write the failing test**

```python
# tests/test_project_manager_security.py
"""Tests for path traversal prevention in ProjectManager."""
import pytest
from pathlib import Path
from unittest.mock import patch
from haytham.project.project_manager import ProjectManager


@pytest.fixture
def pm(tmp_path):
    return ProjectManager(base_dir=tmp_path)


def test_delete_project_rejects_path_traversal(pm):
    """Path traversal in project_id must raise ValueError."""
    with pytest.raises(ValueError, match="Invalid project ID"):
        pm.delete_project("../../etc")


def test_delete_project_rejects_absolute_path(pm):
    """Absolute paths in project_id must raise ValueError."""
    with pytest.raises(ValueError, match="Invalid project ID"):
        pm.delete_project("/etc/passwd")


def test_delete_project_accepts_valid_id(pm, tmp_path):
    """Normal project IDs should work."""
    project_dir = tmp_path / "my_project"
    project_dir.mkdir()
    pm.delete_project("my_project")
    assert not project_dir.exists()
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_project_manager_security.py -v`
Expected: FAIL (path traversal not yet blocked)

**Step 3: Add path validation to delete_project**

In `haytham/project/project_manager.py`, in the `delete_project` method, add validation before the `exists()` check:

```python
def delete_project(self, project_id: str) -> None:
    project_dir = self.base_dir / project_id
    # Prevent path traversal
    if not project_dir.resolve().is_relative_to(self.base_dir.resolve()):
        raise ValueError(f"Invalid project ID: {project_id}")
    if not project_dir.exists():
        raise FileNotFoundError(f"Project not found: {project_id}")
    shutil.rmtree(project_dir)
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_project_manager_security.py -v`
Expected: PASS

**Step 5: Commit**

```
fix(security): prevent path traversal in delete_project (WARN-12)
```

---

## Task 3: Security - Redact LLM I/O Logging (WARN-13)

**Files:**
- Modify: `haytham/agents/utils/logging_utils.py`

**Step 1: Replace full content logging with token-count-only logging**

In `log_llm_input()` (line ~235) and `log_llm_output()` (line ~262), change `content=prompt` and `content=response` to log only metadata:

```python
# In log_llm_input:
entry = LogEntry(
    timestamp=datetime.now().isoformat(),
    session_id=session_id,
    agent_name=self.agent_name,
    interaction_type="llm_input",
    content=f"[REDACTED] {input_tokens} tokens",
    metadata={**(metadata or {}), "estimated_tokens": input_tokens},
)

# In log_llm_output:
entry = LogEntry(
    timestamp=datetime.now().isoformat(),
    session_id=session_id,
    agent_name=self.agent_name,
    interaction_type="llm_output",
    content=f"[REDACTED] {output_tokens} tokens",
    metadata={**(metadata or {}), "estimated_tokens": output_tokens},
)
```

**Step 2: Verify lint passes**

Run: `uv run ruff check haytham/agents/utils/logging_utils.py --fix && uv run ruff format haytham/agents/utils/logging_utils.py`

**Step 3: Commit**

```
fix(security): redact LLM I/O in disk logs (WARN-13)
```

---

## Task 4: Fail-Fast Workflow Transitions (CRIT-01)

**Files:**
- Modify: `haytham/workflow/workflow_specs.py`
- Modify: `haytham/workflow/burr_actions.py`
- Modify: `haytham/workflow/burr_workflow.py`
- Test: `tests/workflow/test_fail_fast_transitions.py`

This is the most impactful fix. Currently, failed stages propagate garbage because transitions are unconditional 2-tuples. We convert to 3-tuples with Burr `Condition` guards and add a terminal `workflow_failed` action.

**Step 1: Write the failing test**

```python
# tests/workflow/test_fail_fast_transitions.py
"""Tests for fail-fast workflow transitions (CRIT-01)."""
import pytest
from haytham.workflow.workflow_specs import (
    IDEA_VALIDATION_SPEC,
    MVP_SPECIFICATION_SPEC,
)


def test_idea_validation_transitions_are_conditional():
    """Every transition must be a 3-tuple with a condition, not unconditional 2-tuple."""
    for t in IDEA_VALIDATION_SPEC.transitions:
        assert len(t) == 3, (
            f"Transition {t[0]} -> {t[1]} is unconditional (2-tuple). "
            "Must include a Condition guard for fail-fast."
        )


def test_mvp_specification_transitions_are_conditional():
    """Every transition must be a 3-tuple with a condition."""
    for t in MVP_SPECIFICATION_SPEC.transitions:
        assert len(t) == 3, (
            f"Transition {t[0]} -> {t[1]} is unconditional (2-tuple). "
            "Must include a Condition guard for fail-fast."
        )


def test_failed_stage_has_terminal_transition():
    """Each stage must have a failure transition to a terminal action."""
    stage_names = {t[0] for t in IDEA_VALIDATION_SPEC.transitions}
    for name in stage_names:
        transitions_from = [t for t in IDEA_VALIDATION_SPEC.transitions if t[0] == name]
        targets = {t[1] for t in transitions_from}
        assert "workflow_failed" in targets, (
            f"Stage '{name}' has no failure transition to 'workflow_failed'"
        )
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/workflow/test_fail_fast_transitions.py -v`
Expected: FAIL (transitions are currently 2-tuples)

**Step 3: Add workflow_failed action to burr_actions.py**

Add a terminal Burr action that halts the workflow:

```python
@action(reads=["current_stage"], writes=["workflow_failed_stage", "workflow_failed_error"])
def workflow_failed(state: State) -> State:
    """Terminal action when a stage fails. Halts the workflow."""
    failed_stage = state.get("current_stage", "unknown")
    error = state.get(f"{failed_stage}_output", "Unknown error")
    logger.error(f"Workflow halted: stage '{failed_stage}' failed")
    return state.update(
        workflow_failed_stage=failed_stage,
        workflow_failed_error=str(error)[:500],
    )
```

**Step 4: Convert transitions to conditional 3-tuples in workflow_specs.py**

Each workflow spec's transitions list changes from:

```python
transitions=[
    ("idea_analysis", "market_context"),
    ("market_context", "research_brief"),
    ("research_brief", "report_synthesis"),
]
```

To:

```python
from burr.core import Condition, default

transitions=[
    ("idea_analysis", "workflow_failed", Condition.when(idea_analysis_status="failed")),
    ("idea_analysis", "market_context", default),
    ("market_context", "workflow_failed", Condition.when(market_context_status="failed")),
    ("market_context", "research_brief", default),
    ("research_brief", "workflow_failed", Condition.when(research_brief_status="failed")),
    ("research_brief", "report_synthesis", default),
]
```

The pattern: for each stage, add a failure transition first (Burr evaluates in order), then the success transition as `default`.

This requires that each stage writes a `{action_name}_status` key to Burr state. Verify that `stage_executor.py` already does this (it writes status via the action's `writes` list).

**Step 5: Wire workflow_failed into burr_workflow.py**

In `_build_workflow_graph()`, add `workflow_failed` to the actions list and ensure it has no outgoing transitions (terminal node).

Update the post-run failure detection in `run_workflow()` to also check for `workflow_failed_stage` in state.

**Step 6: Run tests**

Run: `uv run pytest tests/workflow/test_fail_fast_transitions.py -v`
Expected: PASS

**Step 7: Run full test suite**

Run: `uv run pytest tests/ -v -m "not integration" -x`
Expected: All pass

**Step 8: Commit**

```
feat: fail-fast workflow transitions halt on stage failure (CRIT-01)
```

---

## Task 5: Required Context Validation (WARN-01)

**Files:**
- Modify: `haytham/workflow/stage_executor.py`
- Test: `tests/workflow/test_context_validation.py`

**Step 1: Write the failing test**

```python
# tests/workflow/test_context_validation.py
"""Tests for required context validation before stage execution (WARN-01)."""
import pytest
from unittest.mock import MagicMock
from haytham.workflow.stage_executor import StageExecutor


def test_build_context_raises_on_empty_required_context():
    """If a required_context stage has empty output, raise before LLM call."""
    executor = StageExecutor.__new__(StageExecutor)
    executor.config = MagicMock()
    executor.config.custom_context_builder = None
    executor.registry = MagicMock()

    # Mock a stage that requires "market_context" but it's empty
    executor.stage = MagicMock()
    executor.stage.slug = "report_synthesis"
    executor.stage.required_context = ["market_context"]

    mock_meta = MagicMock()
    mock_meta.state_key = "market_context_output"
    executor.registry.get_by_slug_safe.return_value = mock_meta

    state = MagicMock()
    state.get.side_effect = lambda key, default="": {
        "concept_anchor_str": "",
        "market_context_output": "",  # Empty!
    }.get(key, default)

    with pytest.raises(ValueError, match="required context.*empty"):
        executor._build_context(state, "test goal")
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/workflow/test_context_validation.py -v`
Expected: FAIL (no validation exists)

**Step 3: Add validation in _build_context**

After the loop that collects required context, add:

```python
# Validate required context is non-empty
for slug in self.stage.required_context:
    stage_meta = self.registry.get_by_slug_safe(slug)
    if stage_meta:
        value = state.get(stage_meta.state_key, "")
        if value:
            context[stage_meta.state_key] = value
        else:
            raise ValueError(
                f"Stage '{self.stage.slug}' required context from '{slug}' is empty. "
                f"Upstream stage may have failed."
            )
```

**Step 4: Run tests**

Run: `uv run pytest tests/workflow/test_context_validation.py -v && uv run pytest tests/ -v -m "not integration" -x`

**Step 5: Commit**

```
fix: validate required context is non-empty before stage execution (WARN-01)
```

---

## Task 6: Startup Config Validation (WARN-05)

**Files:**
- Modify: `haytham/config.py`
- Test: `tests/test_config_validation.py`

**Step 1: Write the failing test**

```python
# tests/test_config_validation.py
"""Tests for startup config validation (WARN-05)."""
import pytest
from unittest.mock import patch
from haytham.config import validate_config


def test_validate_config_missing_heavy_model():
    """Missing BEDROCK_HEAVY_MODEL_ID should raise."""
    with patch.dict("os.environ", {}, clear=True):
        with pytest.raises(EnvironmentError, match="BEDROCK_HEAVY_MODEL_ID"):
            validate_config()


def test_validate_config_all_present():
    """All required vars present should not raise."""
    env = {
        "BEDROCK_HEAVY_MODEL_ID": "anthropic.claude-3-5-sonnet",
        "BEDROCK_LIGHT_MODEL_ID": "anthropic.claude-3-haiku",
        "BEDROCK_REASONING_MODEL_ID": "anthropic.claude-3-5-sonnet",
    }
    with patch.dict("os.environ", env, clear=True):
        validate_config()  # Should not raise
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_config_validation.py -v`
Expected: FAIL (validate_config doesn't exist yet)

**Step 3: Add validate_config() to config.py**

```python
_REQUIRED_ENV_VARS = [
    "BEDROCK_HEAVY_MODEL_ID",
    "BEDROCK_LIGHT_MODEL_ID",
    "BEDROCK_REASONING_MODEL_ID",
]


def validate_config() -> None:
    """Validate all required environment variables are set. Call at startup."""
    missing = [var for var in _REQUIRED_ENV_VARS if not os.environ.get(var)]
    if missing:
        raise EnvironmentError(
            f"Missing required environment variables: {', '.join(missing)}. "
            f"Set them in .env or export them."
        )
```

**Step 4: Run tests**

Run: `uv run pytest tests/test_config_validation.py -v`
Expected: PASS

**Step 5: Commit**

```
feat: add startup config validation for required env vars (WARN-05)
```

---

## Task 7: Deduplicate Extract Functions (WARN-23)

**Files:**
- Modify: `haytham/agents/worker_story_generator/story_swarm.py`
- Modify: `haytham/feedback/feedback_agent.py`
- Modify: `haytham/testing/runner.py`
- Modify: `haytham/workflow/verifiers/what_phase_swarm/swarm.py`
- Modify: `haytham/workflow/stages/mvp_specification.py`
- Modify: `haytham/workflow/build_buy/capability_analyzer.py`

Each of these files has a local wrapper that just calls the canonical function from `haytham.agents.output_utils`. Replace all call sites with direct imports.

**Step 1: For each file, replace the local wrapper with a direct import**

Pattern for `extract_text_from_result` wrappers:

1. `story_swarm.py`: Remove `_extract_text()` (lines 45-49). Replace all calls to `_extract_text(result)` with `extract_text_from_result(result)`. Add `from haytham.agents.output_utils import extract_text_from_result` at module level.

2. `feedback_agent.py`: Remove `_extract_text_output()` (lines 422-426). Replace calls with `extract_text_from_result(result)`. Add module-level import.

3. `runner.py`: Remove `_extract_agent_output()` (lines 49-53). Replace calls with `extract_text_from_result(result)`. Add module-level import.

4. `swarm.py` (what_phase_swarm): Remove `_extract_text_from_result()` (lines 187-191). Replace calls with `extract_text_from_result(result)`. Add module-level import.

Pattern for `extract_json_from_text` wrappers:

5. `mvp_specification.py`: Remove `extract_json_from_output()` (lines 278-288). At call sites, replace `extract_json_from_output(text)` with the equivalent using `extract_json_from_text`. Note: the wrapper returns `json.dumps(parsed)` for backward compat, so check callers to see if they need a string or dict.

6. `capability_analyzer.py`: Remove `_extract_json_from_output()` (lines 270-280). Same pattern as above.

**Step 2: Run full test suite**

Run: `uv run pytest tests/ -v -m "not integration" -x`
Expected: All pass

**Step 3: Commit**

```
refactor: deduplicate extract_text/json wrappers to use output_utils (WARN-23)
```

---

## Task 8: Annotate Broad Except Blocks (WARN-28)

**Files:**
- Modify: `haytham/agents/utils/langfuse_tracer.py` (10 blocks)
- Modify: `haytham/agents/utils/context_summarizer.py` (2 blocks)
- Modify: `haytham/agents/tools/brave_search.py` (1 block)
- Modify: `haytham/agents/utils/file_context.py` (1 block)
- Modify: `haytham/telemetry/spans.py` (2 blocks)
- Modify: `haytham/agents/utils/prompt_loader.py` (1 block)

Per project convention, broad `except Exception` blocks must have `# Intentional catch-all:` annotation explaining why.

**Step 1: Add annotations to each block**

For `langfuse_tracer.py` (10 blocks): These are all for Langfuse API calls where the tracer must never crash the main workflow. Annotate each with:
```python
except Exception as e:  # Intentional catch-all: tracer must never crash workflow
```

For `context_summarizer.py` (2 blocks): Summarization failures should fall back gracefully.
```python
except Exception as agent_error:  # Intentional catch-all: summarization failure uses raw output
```

For `brave_search.py` (1 block): Final catch after specific httpx exceptions.
```python
except Exception as e:  # Intentional catch-all: wrap unknown errors as BraveSearchError
```

For `file_context.py` (1 block): Auto-summarization failure falls back to unsummarized.
```python
except Exception as e:  # Intentional catch-all: summarization failure uses raw context
```

For `spans.py` (2 blocks): OTEL span recording must never crash the workflow.
```python
except Exception as e:  # Intentional catch-all: re-raised after recording to OTEL span
```

For `prompt_loader.py` (1 block): Prompt loading failure.
```python
except Exception as e:  # Intentional catch-all: prompt loading failure
```

**Step 2: Run lint**

Run: `uv run ruff check haytham/ --fix && uv run ruff format haytham/`

**Step 3: Commit**

```
chore: annotate broad except blocks per project convention (WARN-28)
```

---

## Task 9: Documentation - Remove Scoring Pipeline (CRIT-03 partial)

**Files:**
- Delete: `docs/architecture/scoring-pipeline.md`
- Modify: `docs/README.md` (remove link)
- Modify: `docs/architecture/overview.md` (remove scorer/narrator/merge, LanceDB)
- Modify: `docs/contributing/architecture-patterns.md` (remove scoring pipeline section, fix parallel/sequential)

**Step 1: Delete scoring-pipeline.md**

Remove `docs/architecture/scoring-pipeline.md` entirely.

**Step 2: Remove link from docs/README.md**

Line 16: Remove the line `**[Scoring Pipeline](architecture/scoring-pipeline.md)** - Validation scoring mechanics (scorer, narrator, merge)`

**Step 3: Update docs/architecture/overview.md**

- Remove LanceDB from mermaid component diagram (lines ~56, ~66)
- Remove "reads/writes context" LanceDB edge
- Line ~75: Remove "Agents read upstream context from LanceDB" prose
- Line ~115: Remove LanceDB table row
- Line ~170: Replace "three-step pipeline (scorer -> narrator -> merge)" with "single report_synthesis agent (see ADR-026)"
- Line ~185: Remove `haytham/phases/` reference

**Step 4: Update docs/contributing/architecture-patterns.md**

- Line ~77: Change "Parallel Execution: Phase 1 runs market_intelligence and competitor_analysis concurrently" to "Sequential Execution: Phase 1 runs market_intelligence then competitor_analysis (JTBD handoff)" (WARN-19)
- Line ~152: Remove reference to `haytham/agents/tools/recommendation.py`
- Lines ~189-193: Remove "Scoring & Validation Pipeline" section referencing `validation_summary_models.py`

**Step 5: Commit**

```
docs: remove scoring-pipeline.md and LanceDB references (CRIT-03)
```

---

## Task 10: Documentation - Update Agents Table and Pipeline Diagram (CRIT-03 partial)

**Files:**
- Modify: `docs/how-it-works.md`
- Modify: `docs/technology.md`

**Step 1: Update docs/how-it-works.md**

- Lines 16-57: Replace old pipeline diagram with current 4-phase diagram matching the stages in `stage_registry.py`
- Lines 146-168: Update agents table. Remove 5 deleted agents (Validation Scorer, Validation Narrator, Validation Summary, and any others that no longer exist). Add current agents from AGENT_CONFIGS (19 agents).

**Step 2: Update docs/technology.md**

- Line 27: Change "21 agents" to "19 agents"
- Line 114: Change "default: 20" to "default: 30" for WEB_SEARCH_SESSION_LIMIT (WARN-22)
- Lines 122-127: Replace LanceDB section with JSON Store section per ADR-027

**Step 3: Commit**

```
docs: update agents table, pipeline diagram, replace LanceDB with JSON Store (CRIT-03)
```

---

## Task 11: Documentation - Fix Agent Count and Stale References (WARN-15, WARN-16, WARN-17, WARN-20)

**Files:**
- Modify: `docs/getting-started.md`
- Modify: `docs/dogfood/haytham-idea-statement.md`
- Modify: `docs/plans/2026-02-20-gtm-strategy.md`
- Modify: `docs/roadmap.md`
- Modify: `docs/adr/ADR-019-system-trait-detection.md`
- Modify: `docs/troubleshooting.md`
- Modify: `CONTRIBUTING.md`

**Step 1: Fix agent counts (WARN-15)**

- `docs/getting-started.md` line 144: "21 agents" -> "19 agents"
- `docs/dogfood/haytham-idea-statement.md` line 25: "21 specialist AI agents" -> "19 specialist AI agents"
- `docs/plans/2026-02-20-gtm-strategy.md` line 5: "21 specialist agents" -> "19 specialist agents"
- `docs/plans/2026-02-20-gtm-strategy.md` line 35: "21 agents" -> "19 agents"

**Step 2: Fix AGENT_FACTORIES -> AGENT_CONFIGS (WARN-16)**

- `docs/roadmap.md` line 97: `AGENT_FACTORIES` -> `AGENT_CONFIGS`
- `docs/adr/ADR-019-system-trait-detection.md` line 227: `AGENT_FACTORIES` -> `AGENT_CONFIGS`

**Step 3: Fix validation-summary references (WARN-20)**

- `docs/troubleshooting.md` line 211: `session/validation-summary/` -> `session/report-synthesis/`
- `docs/troubleshooting.md` line 211: Remove link to deleted `scoring-pipeline.md`
- `docs/troubleshooting.md` line 192: "default 20" -> "default 30" (WARN-22)
- `CONTRIBUTING.md` line 185: `validation-summary` -> `report-synthesis`

**Step 4: Commit**

```
docs: fix agent counts, AGENT_CONFIGS name, stale stage references (WARN-15/16/17/20/22)
```

---

## Task 12: Documentation - Remove Orphaned Module READMEs (WARN-18)

**Files:**
- Delete: `haytham/context/README.md`
- Delete: `haytham/feedback/README.md`
- Delete: `haytham/project/README.md`

These READMEs describe a 7-phase architecture (ContextLoader, UserFeedbackLoop, ProjectManager with exponential backoff) that does not match the current Burr-workflow architecture. They will mislead contributors.

**Step 1: Delete the three files**

**Step 2: Commit**

```
docs: remove orphaned module READMEs describing old architecture (WARN-18)
```

---

## Task 13: Documentation - Fix Em Dashes (WARN-21)

**Files:**
- Modify: `docs/plans/2026-02-25-research-brief-stage-plan.md`

Only the prose em dashes on lines 682-684 violate the style guide. The ones inside Python code blocks (lines 322, 366, 509, 601) are intentional comment separators.

**Step 1: Replace em dashes in prose lines 682-684**

```
- `test_burr_actions_metadata.py` — verifies ...
+ `test_burr_actions_metadata.py`: verifies ...
```

Apply same pattern to all three lines.

**Step 2: Commit**

```
docs: replace em dashes with colons in plan prose (WARN-21)
```

---

## Task 14: Open-Source Readiness - Pre-commit Config (WARN-31)

**Files:**
- Create: `.pre-commit-config.yaml`

**Step 1: Create .pre-commit-config.yaml**

```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.9.7
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format
```

**Step 2: Commit**

```
chore: add pre-commit config (WARN-31)
```

---

## Task 15: Final Verification

**Step 1: Run lint**

Run: `uv run ruff check haytham/ --fix && uv run ruff format haytham/`

**Step 2: Run tests**

Run: `uv run pytest tests/ -v -m "not integration" -x`

**Step 3: Verify no regressions**

All 783+ tests should pass. No new lint errors.

---

## Execution Order

Tasks are ordered by dependency and risk:

1. **Tasks 1-3** (Security): Independent, can run in parallel. No cross-deps.
2. **Task 4** (CRIT-01 fail-fast): Core architecture fix. Must pass before Task 5.
3. **Task 5** (WARN-01 context validation): Depends on Task 4 pattern.
4. **Task 6** (WARN-05 config validation): Independent.
5. **Task 7** (WARN-23 dedup): Independent code hygiene.
6. **Task 8** (WARN-28 annotations): Independent code hygiene.
7. **Tasks 9-13** (Documentation): Independent of code changes. Can run in parallel.
8. **Task 14** (Open-source): Independent.
9. **Task 15** (Final verification): Must be last.
