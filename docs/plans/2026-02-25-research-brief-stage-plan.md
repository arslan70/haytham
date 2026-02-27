# Research Brief Stage Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a `research_brief` stage between `market_context` and `report_synthesis` that presents non-opinionated research findings for user review before synthesis.

**Architecture:** New stage in the WHY phase pipeline. A LIGHT-tier agent formats upstream research (idea_analysis + market_context + concept_anchor) into a two-section brief. The user-validated brief replaces raw upstream data as the single input to report_synthesis.

**Tech Stack:** Burr (workflow), Strands SDK (agent), existing stage/agent patterns.

**Design doc:** `docs/plans/2026-02-25-research-brief-stage-design.md`

---

### Task 1: Register research_brief in Stage Registry

**Files:**
- Modify: `haytham/workflow/stage_registry.py:136-157`
- Test: `tests/test_burr_actions_metadata.py` (existing tests will catch missing action/config)

**Step 1: Write the failing test**

Add to `tests/test_workflow_specs.py` in `TestIdeaValidationTransitions`:

```python
def test_idea_validation_has_four_stages(self):
    """Research brief adds a 4th stage to idea-validation."""
    assert len(IDEA_VALIDATION_SPEC.stages) == 4

def test_linear_transitions_with_research_brief(self):
    """idea_analysis -> market_context -> research_brief -> report_synthesis."""
    assert IDEA_VALIDATION_SPEC.transitions == [
        ("idea_analysis", "market_context"),
        ("market_context", "research_brief"),
        ("research_brief", "report_synthesis"),
    ]
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_workflow_specs.py::TestIdeaValidationTransitions -v`
Expected: FAIL (still 3 stages, old transitions)

**Step 3: Add StageMetadata to stage_registry.py**

Insert after market-context (line 136), before report-synthesis (line 137):

```python
StageMetadata(
    slug="research-brief",
    action_name="research_brief",
    display_name="Research Brief",
    display_index="2b",
    description=(
        "Presents the system's understanding of your idea and the research findings "
        "for your review. Our recommendations are only as good as the research they're "
        "based on, so please verify the facts, flag anything missing, and correct any "
        "misunderstandings before we proceed to analysis."
    ),
    state_key="research_brief",
    status_key="research_brief_status",
    workflow_type=WorkflowType.IDEA_VALIDATION,
    query_template=(
        "Create a non-opinionated research brief that presents the system's understanding "
        "of the idea and the market research findings. No scores, ratings, or recommendations."
    ),
    agent_names=["research_brief"],
    required_context=["idea-analysis", "market-context"],
),
```

Also update report-synthesis `required_context` from `["idea-analysis", "market-context"]` to `["research-brief"]`:

```python
# In the report-synthesis StageMetadata (around line 156 after insertion):
required_context=["research-brief"],
```

**Step 4: Tests still fail (need Burr action + workflow spec). Continue to Task 2.**

**Step 5: Commit**

```bash
git add haytham/workflow/stage_registry.py tests/test_workflow_specs.py
git commit -m "feat: register research-brief stage metadata in registry"
```

---

### Task 2: Add Burr Action and Update Workflow Spec

**Files:**
- Modify: `haytham/workflow/burr_actions.py:57-72`
- Modify: `haytham/workflow/workflow_specs.py:84-104`
- Test: `tests/test_workflow_specs.py`, `tests/test_burr_actions_metadata.py`

**Step 1: Add Burr action in `burr_actions.py`**

Insert after `market_context` (line 57), before `report_synthesis` (line 60):

```python
@action(
    reads=[
        "system_goal",
        "idea_analysis",
        "market_context",
        "research_brief_status",
        "session_manager",
    ],
    writes=["research_brief", "research_brief_status", "current_stage"],
)
def research_brief(state: State) -> State:
    """Stage 2b: Present research findings for user review."""
    return execute_stage("research-brief", state)
```

**Step 2: Update report_synthesis action reads**

Change report_synthesis reads (line 61-66) to read `research_brief` instead of `idea_analysis` + `market_context`:

```python
@action(
    reads=[
        "system_goal",
        "research_brief",
        "report_synthesis_status",
        "session_manager",
    ],
    writes=["report_synthesis", "report_synthesis_status", "current_stage", "recommendation"],
)
def report_synthesis(state: State) -> State:
    """Stage 3: Synthesize validation report from validated research brief."""
    return execute_stage("report-synthesis", state)
```

**Step 3: Update workflow_specs.py**

Add import at top (line 20):

```python
from .burr_actions import (
    ...
    research_brief,
    ...
)
```

Update `IDEA_VALIDATION_SPEC` (lines 84-104):

```python
IDEA_VALIDATION_SPEC = WorkflowSpec(
    workflow_type=WorkflowType.IDEA_VALIDATION,
    actions={
        "idea_analysis": idea_analysis,
        "market_context": market_context,
        "research_brief": research_brief,
        "report_synthesis": report_synthesis,
    },
    transitions=[
        ("idea_analysis", "market_context"),
        ("market_context", "research_brief"),
        ("research_brief", "report_synthesis"),
    ],
    entrypoint="idea_analysis",
    tracking_project="haytham-validation",
    stages=[
        "idea_analysis",
        "market_context",
        "research_brief",
        "report_synthesis",
    ],
    extra_state_keys=["recommendation"],
    context_stages=[],
)
```

Also add `"research-brief"` to downstream workflow `context_stages` where they reference `"market-context"`:

In `MVP_SPECIFICATION_SPEC` (line 120-124), add `"research-brief"`:
```python
context_stages=[
    "report-synthesis",
    "research-brief",
    "idea-analysis",
    "market-context",
],
```

**Step 4: Update the old test assertions**

In `tests/test_workflow_specs.py`, update `TestIdeaValidationTransitions`:

Replace `test_idea_validation_has_three_stages` (line 163-165) with the new test from Task 1 Step 1.
Replace `test_linear_transitions` (line 167-172) with the new test from Task 1 Step 1.

**Step 5: Run tests to verify**

Run: `uv run pytest tests/test_workflow_specs.py tests/test_burr_actions_metadata.py -v`
Expected: Most pass. `TestAgentFactoryCompleteness::test_all_agent_names_have_configs` may fail (agent config not yet added). That's expected.

**Step 6: Commit**

```bash
git add haytham/workflow/burr_actions.py haytham/workflow/workflow_specs.py tests/test_workflow_specs.py
git commit -m "feat: add research_brief Burr action and update workflow spec"
```

---

### Task 3: Create Agent Prompt and Config

**Files:**
- Create: `haytham/agents/worker_research_brief/__init__.py`
- Create: `haytham/agents/worker_research_brief/worker_research_brief_prompt.txt`
- Modify: `haytham/config.py:339`

**Step 1: Create agent prompt file**

Create `haytham/agents/worker_research_brief/worker_research_brief_prompt.txt`:

```text
You are a research brief writer. Your job is to present research findings in a clear, factual, non-opinionated format for the founder to review.

You receive upstream research (idea analysis + market context) and produce a two-section brief.

## SECTION 1: Our Understanding of Your Idea

Present the system's interpretation of the founder's idea:
- Problem: What problem does this solve?
- Target Audience: Who is this for? (behavioral segments, not demographics)
- Value Proposition: What makes this different?

Source this from the concept anchor / idea analysis. This section lets the founder confirm: "Yes, you understood my idea correctly."

## SECTION 2: What We Found

Present the market research findings:

### Market Overview
- TAM/SAM/SOM numbers with source tags (e.g., [from Statista], [estimate])
- Market trends (factual observations only)

### Jobs-to-be-Done
- Core job statement
- Current solutions people use for this job

### Competitors Identified
For each competitor found:
- Name and what they do
- Traction numbers (downloads, funding, ratings) with sources
- Pricing (if found, or "not found")
- User sentiment quotes (from Reddit, G2, etc.)

### What We Couldn't Verify
- Explicit list of data gaps
- Low-confidence findings tagged as such

## STRICT RULES

You MUST NOT include:
- Scores, ratings, or rankings of any kind
- Recommendations or suggestions
- Judgment language: "strong", "weak", "promising", "concerning", "impressive", "worrying", "significant", "notable"
- Comparative value statements: "better than", "worse than", "leading", "lagging"
- Qualitative assessments: "large market", "tough competition", "clear opportunity"

You MUST:
- Present facts, numbers, and direct quotes only
- Tag every data point with its source
- Flag data gaps explicitly rather than omitting them
- Use neutral language throughout

The founder will review this brief and may ask you to correct misunderstandings, add missing information, or flag inaccuracies. Update the brief based on their feedback.
```

**Step 2: Create `__init__.py`**

Create `haytham/agents/worker_research_brief/__init__.py` (empty file).

**Step 3: Add agent config to `config.py`**

Insert in `AGENT_CONFIGS` after `competitor_analysis` (around line 339):

```python
# Research Brief - non-opinionated research presenter for user review
"research_brief": AgentConfig(
    name="research_brief_agent",
    prompt_key="worker_research_brief",
    max_tokens=TOKENS_LARGE,  # ~4000 tokens for full brief with two sections
    model_tier=ModelTier.LIGHT,
),
```

Note: using `TOKENS_LARGE` (4000) instead of `TOKENS_MEDIUM` (1000) because the brief includes the full concept understanding + all research findings reformatted.

**Step 4: Run tests**

Run: `uv run pytest tests/test_burr_actions_metadata.py::TestAgentFactoryCompleteness -v`
Expected: PASS (agent config now registered)

**Step 5: Commit**

```bash
git add haytham/agents/worker_research_brief/ haytham/config.py
git commit -m "feat: add research_brief agent prompt and config"
```

---

### Task 4: Add Stage Execution Config

**Files:**
- Modify: `haytham/workflow/stages/configs.py:95-96`
- Modify: `haytham/workflow/stages/idea_validation.py` (add programmatic executor)

**Step 1: Write the programmatic executor in `idea_validation.py`**

Add at the end of `haytham/workflow/stages/idea_validation.py` (after line 346):

```python
# =============================================================================
# Research Brief — Programmatic executor with full upstream context
# =============================================================================


def run_research_brief(state: State) -> tuple[str, str]:
    """Run research-brief with full upstream context embedded in the query.

    Embeds idea_analysis, market_context, and concept_anchor directly in the
    query so the research brief agent has all facts available for formatting.

    Returns:
        Tuple of (output, status) for stage_executor compatibility.
    """
    system_goal = state.get("system_goal", "")
    idea_analysis = state.get("idea_analysis", "")
    market_context = state.get("market_context", "")
    session_manager = state.get("session_manager")

    anchor_str = get_anchor_context_string(state)

    query_parts = [
        "Create a research brief from the upstream research below.",
        "Present facts only. No scores, ratings, or recommendations.",
    ]

    if system_goal:
        query_parts.append(f"\n## Original Idea\n\n{system_goal}")

    if anchor_str:
        query_parts.append(f"\n## Concept Anchor\n\n{anchor_str}")

    if idea_analysis:
        query_parts.append(f"\n## Idea Analysis\n\n{idea_analysis}")

    if market_context:
        query_parts.append(f"\n## Market Context\n\n{market_context}")

    query = "\n".join(query_parts)

    logger.info(
        f"Research brief query built: {len(query)} chars "
        f"(idea_analysis={len(idea_analysis)}, market_context={len(market_context)})"
    )

    # Pass empty context dict — all data is already in the query
    result = run_agent("research_brief", query, {}, session_manager)

    output = result.get("output", "")
    status = result.get("status", "failed")

    return output, status
```

**Step 2: Add stage config in `configs.py`**

First, add import in `configs.py` (update line 30-36):

```python
from .idea_validation import (
    extract_competitor_data_processor,
    extract_recommendation_processor,
    run_market_context_sequential,
    run_report_synthesis,
    run_research_brief,
    save_final_output,
)
```

Then insert in `STAGE_CONFIGS` after `"market-context"` (after line 95):

```python
"research-brief": StageExecutionConfig(
    stage_slug="research-brief",
    programmatic_executor=run_research_brief,
),
```

**Step 3: Run tests**

Run: `uv run pytest tests/test_burr_actions_metadata.py tests/test_workflow_specs.py -v`
Expected: PASS

**Step 4: Commit**

```bash
git add haytham/workflow/stages/idea_validation.py haytham/workflow/stages/configs.py
git commit -m "feat: add research_brief stage executor and config"
```

---

### Task 5: Update Report Synthesis to Read research_brief

**Files:**
- Modify: `haytham/workflow/stages/idea_validation.py:293-345` (`run_report_synthesis`)

**Step 1: Write a failing test**

Create `tests/test_research_brief_integration.py`:

```python
"""Tests for research_brief data flow into report_synthesis."""

from unittest.mock import MagicMock, patch

from haytham.workflow.stages.idea_validation import run_report_synthesis


class TestReportSynthesisReadsResearchBrief:
    """Verify report_synthesis reads research_brief, not raw upstream data."""

    @patch("haytham.workflow.stages.idea_validation.run_agent")
    def test_query_contains_research_brief(self, mock_run_agent):
        """Report synthesis query should embed the research_brief content."""
        mock_run_agent.return_value = {
            "output": '{"recommendation": "GO", "executive_summary": {}, "report": "test"}',
            "status": "completed",
        }

        state = MagicMock()
        state.get.side_effect = lambda key, default="": {
            "system_goal": "A fitness app",
            "research_brief": "## Our Understanding\nFitness tracking\n## What We Found\nTAM: $5B",
            "idea_analysis": "old idea analysis that should NOT appear",
            "market_context": "old market context that should NOT appear",
            "session_manager": MagicMock(),
            "concept_anchor_str": "",
            "concept_anchor": None,
        }.get(key, default)

        run_report_synthesis(state)

        call_args = mock_run_agent.call_args
        query = call_args[0][1]  # Second positional arg is query

        assert "research_brief" in query.lower() or "Research Brief" in query
        assert "old idea analysis that should NOT appear" not in query
        assert "old market context that should NOT appear" not in query
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_research_brief_integration.py -v`
Expected: FAIL (run_report_synthesis still reads idea_analysis + market_context)

**Step 3: Update `run_report_synthesis` in `idea_validation.py`**

Replace the function (lines 293-345) with:

```python
def run_report_synthesis(state: State) -> tuple[str, str]:
    """Run report-synthesis with the validated research brief as input.

    The research_brief is the user-validated single source of truth,
    replacing raw idea_analysis and market_context as synthesis input.
    See design doc: docs/plans/2026-02-25-research-brief-stage-design.md

    Returns:
        Tuple of (output, status) for stage_executor compatibility.
    """
    system_goal = state.get("system_goal", "")
    research_brief = state.get("research_brief", "")
    session_manager = state.get("session_manager")

    anchor_str = get_anchor_context_string(state)

    # Build query with validated research brief inline
    query_parts = [
        "Produce a comprehensive validation report based on the validated research brief below.",
    ]

    if system_goal:
        query_parts.append(f"\n## Original Idea (system_goal)\n\n{system_goal}")

    if anchor_str:
        query_parts.append(f"\n## Concept Anchor\n\n{anchor_str}")

    if research_brief:
        query_parts.append(f"\n## Validated Research Brief\n\n{research_brief}")

    query = "\n".join(query_parts)

    logger.info(
        f"Report synthesis query built: {len(query)} chars "
        f"(research_brief={len(research_brief)})"
    )

    # Pass empty context dict — all data is already in the query
    result = run_agent("report_synthesis", query, {}, session_manager, output_as_json=True)

    output = result.get("output", "")
    status = result.get("status", "failed")

    return output, status
```

**Step 4: Run tests to verify**

Run: `uv run pytest tests/test_research_brief_integration.py -v`
Expected: PASS

Run: `uv run pytest tests/ -v -m "not integration" -x`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add haytham/workflow/stages/idea_validation.py tests/test_research_brief_integration.py
git commit -m "feat: update report_synthesis to read research_brief as single input"
```

---

### Task 6: Add Judgment Language Post-Validator

**Files:**
- Modify: `haytham/workflow/validators/report_guardrails.py`
- Modify: `haytham/workflow/stages/configs.py`

**Step 1: Write the failing test**

Add to `tests/test_research_brief_integration.py`:

```python
from haytham.workflow.validators.report_guardrails import validate_no_judgment_language


class TestJudgmentLanguageValidator:
    """Verify the research brief post-validator catches opinion language."""

    def test_clean_brief_returns_no_warnings(self):
        output = "## Our Understanding\nA fitness app.\n## What We Found\nTAM: $5B [from Statista]"
        warnings = validate_no_judgment_language(output, None)
        assert warnings == []

    def test_catches_judgment_words(self):
        output = "This is a promising market with strong growth potential."
        warnings = validate_no_judgment_language(output, None)
        assert len(warnings) > 0
        assert any("promising" in w.lower() or "strong" in w.lower() for w in warnings)

    def test_catches_recommendation_language(self):
        output = "We recommend focusing on the enterprise segment."
        warnings = validate_no_judgment_language(output, None)
        assert len(warnings) > 0

    def test_ignores_judgment_words_in_section_headers(self):
        """Words in headers like 'What We Couldn't Verify' should not trigger."""
        output = "## What We Couldn't Verify\nPricing data not found for 3 competitors."
        warnings = validate_no_judgment_language(output, None)
        assert warnings == []
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_research_brief_integration.py::TestJudgmentLanguageValidator -v`
Expected: FAIL (function doesn't exist yet)

**Step 3: Implement validator in `report_guardrails.py`**

Add at the end of `haytham/workflow/validators/report_guardrails.py`:

```python
# =============================================================================
# Research Brief: Judgment Language Validator
# =============================================================================

_JUDGMENT_WORDS = frozenset([
    "strong", "weak", "promising", "concerning", "impressive", "worrying",
    "significant", "notable", "excellent", "poor", "remarkable", "alarming",
    "recommend", "should", "must", "better", "worse", "leading", "lagging",
    "opportunity", "threat", "advantage", "disadvantage",
])

_JUDGMENT_RE = re.compile(
    r"\b(" + "|".join(re.escape(w) for w in sorted(_JUDGMENT_WORDS)) + r")\b",
    re.IGNORECASE,
)

# Lines starting with # are headers — skip them
_HEADER_RE = re.compile(r"^\s*#+\s")


def validate_no_judgment_language(output: str, state: "State") -> list[str]:
    """Flag judgment or recommendation language in the research brief.

    The research brief must be non-opinionated. This validator surfaces
    instances of judgment words so the user or system can review.
    """
    warnings: list[str] = []
    found_words: set[str] = set()

    for line in output.splitlines():
        # Skip markdown headers
        if _HEADER_RE.match(line):
            continue
        for match in _JUDGMENT_RE.finditer(line):
            found_words.add(match.group(1).lower())

    if found_words:
        sorted_words = ", ".join(sorted(found_words))
        warnings.append(
            f"Research brief contains judgment language: {sorted_words}. "
            "The brief should present facts without opinion."
        )

    return warnings
```

**Step 4: Wire up in configs.py**

Add import in `configs.py`:

```python
from haytham.workflow.validators.report_guardrails import (
    validate_no_judgment_language,
    validate_regulated_domain_safety,
    validate_som_arithmetic,
)
```

Update the `"research-brief"` config to include post_validators:

```python
"research-brief": StageExecutionConfig(
    stage_slug="research-brief",
    programmatic_executor=run_research_brief,
    post_validators=[validate_no_judgment_language],
),
```

**Step 5: Run tests to verify**

Run: `uv run pytest tests/test_research_brief_integration.py -v`
Expected: PASS

**Step 6: Commit**

```bash
git add haytham/workflow/validators/report_guardrails.py haytham/workflow/stages/configs.py tests/test_research_brief_integration.py
git commit -m "feat: add judgment language validator for research brief"
```

---

### Task 7: Run Full Test Suite and Lint

**Step 1: Run ruff check and format**

```bash
uv run ruff check haytham/ --fix && uv run ruff format haytham/
```

**Step 2: Run full unit test suite**

```bash
uv run pytest tests/ -v -m "not integration" -x
```

Expected: ALL PASS. Key tests to watch:
- `test_burr_actions_metadata.py`: verifies action reads/writes match registry
- `test_workflow_specs.py`: verifies transitions and stage lists
- `test_research_brief_integration.py`: verifies data flow and validator

**Step 3: Fix any failures and re-run**

**Step 4: Commit any fixes**

```bash
git add -A && git commit -m "fix: resolve lint and test issues from research_brief addition"
```

---

### Task 8: Update report_synthesis prompt to reference research brief

**Files:**
- Modify: `haytham/agents/worker_report_synthesis/worker_report_synthesis_prompt.txt`

**Step 1: Read current prompt**

Read the file and identify where it references "idea analysis" and "market context" as inputs.

**Step 2: Update references**

Replace references to raw upstream data with references to the "validated research brief". The prompt should say it receives a user-reviewed research brief as its primary input.

**Step 3: Run tests**

```bash
uv run pytest tests/ -v -m "not integration" -x
```

**Step 4: Commit**

```bash
git add haytham/agents/worker_report_synthesis/worker_report_synthesis_prompt.txt
git commit -m "feat: update report_synthesis prompt to reference validated research brief"
```
