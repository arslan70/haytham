# ADR-026 Implementation Plan: Simplified Validation Pipeline

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace the 3-stage validation pipeline (risk-assessment, pivot-strategy, validation-summary) with a single `report-synthesis` stage that produces a complete validation report in one LLM call.

**Approach:** Top-down. Delete old code first, then build replacements. Linter errors serve as a natural checklist. Reference `main` branch for anything needed.

**Branch:** `feature/report-quality-redesign` | **ADR:** [ADR-026](../adr/ADR-026-simplified-validation-pipeline.md) | **Issue:** [#12](https://github.com/arslan70/haytham/issues/12)

---

## Context

The DSPy PoC proved that a single agent with full upstream context (idea-analysis + market-context) produces dramatically better validation reports (8 PASS / 4 PARTIAL / 0 FAIL vs 1 PASS / 3 PARTIAL / 8 FAIL). The PoC used DSPy; this implementation uses the production Strands SDK with a structured output model.

Key decisions:
- Single PR (branch is isolated, `main` available as reference)
- Strands structured output with minimal `ValidationReport` model (recommendation + report)
- All 3 post-synthesis guardrails included
- Top-down execution (delete first, build second)

---

## Task 1: Delete Old Agents, Tools, Models

**Delete entire directories:**
- `haytham/agents/worker_startup_validator/`
- `haytham/agents/worker_pivot_strategy/`
- `haytham/agents/worker_validation_scorer/`
- `haytham/agents/worker_validation_narrator/`

**Delete files:**
- `haytham/agents/tools/recommendation.py` (scorecard tools and verdict logic)
- `haytham/agents/tools/risk_classification.py` (classify_risk_level tool)

**Verify:** `git diff --stat` shows only deletions. No other file should be modified in this step.

---

## Task 2: Delete Old Validators

**Delete files:**
- `haytham/workflow/validators/revenue_evidence.py`
- `haytham/workflow/validators/claim_origin.py`
- `haytham/workflow/validators/concept_health.py`
- `haytham/workflow/validators/dim8_inputs.py`
- `haytham/workflow/validators/jtbd_match.py`
- `haytham/workflow/validators/som_sanity.py`
- `haytham/workflow/validators/_scorecard_utils.py`

**Update:** `haytham/workflow/validators/__init__.py` to remove deleted imports and `__all__` entries. Keep `story_coherence` and `trait_propagation`.

---

## Task 3: Delete Old Tests

**Delete files:**
- `tests/test_validation_summary_sequential.py`
- `tests/test_verdict_drivers.py`
- `tests/test_counter_signal_scoring.py`
- `tests/test_evidence_validation.py`
- `tests/test_revenue_evidence.py`
- `tests/test_claim_origin.py`
- `tests/test_claim_severity.py`
- `tests/test_som_sanity.py`

**Verify:** These tests all import from deleted modules. Removing them prevents import errors.

---

## Task 4: Delete Old Agent Configs and Tool Profiles

**File:** `haytham/config.py`

- Remove 4 entries from `AGENT_CONFIGS`: `startup_validator`, `pivot_strategy`, `validation_scorer`, `validation_narrator`
- Remove 2 `ToolProfile` enum values: `RISK_CLASSIFICATION`, `RECOMMENDATION`
- Remove tool resolver functions: `_tools_risk_classification`, `_tools_recommendation`
- Remove entries from `_TOOL_RESOLVERS` dict
- Remove `TOKENS_SCORECARD` constant (check if used elsewhere first)
- Remove any now-unused imports

---

## Task 5: Create ValidationReport Model

**Create:** `haytham/agents/worker_report_synthesis/report_synthesis_models.py`

```python
from enum import Enum
from pydantic import BaseModel

class Recommendation(str, Enum):
    GO = "GO"
    PIVOT = "PIVOT"
    NO_GO = "NO-GO"

class ValidationReport(BaseModel):
    recommendation: Recommendation
    report: str
```

Also create `haytham/agents/worker_report_synthesis/__init__.py` (empty).

---

## Task 6: Create Report Synthesis Agent Prompt

**Create:** `haytham/agents/worker_report_synthesis/worker_report_synthesis_prompt.txt`

Adapt the DSPy PoC prompt from `tests/dspy_poc/signatures.py` (the `ReportSynthesis` docstring). The 11-section structure is already validated across T1/T2/T6. Key adaptations from DSPy to Strands:

- Move the prompt content from a Python docstring to a `.txt` file (standard Haytham pattern)
- Add explicit instruction to output the `recommendation` field as one of GO/PIVOT/NO-GO
- Add the concept anchor / founder persona instructions that the old pipeline injected via context
- Strengthen the "tag as [estimate]" instructions to address the fabrication regression seen in the PoC

The prompt should reference:
- `{system_goal}` - the original idea
- `{idea_analysis}` - structured concept expansion
- `{market_context}` - market intelligence + competitor analysis
- `{concept_anchor}` - concept anchor from ADR-022 (if available)

---

## Task 7: Register Report Synthesis Agent

**File:** `haytham/config.py`

Add to `AGENT_CONFIGS`:

```python
"report_synthesis": AgentConfig(
    name="report_synthesis",
    prompt_path="worker_report_synthesis/worker_report_synthesis_prompt.txt",
    model_tier=ModelTier.REASONING,
    max_tokens=DEFAULT_MAX_TOKENS,
    structured_output_model_path="haytham.agents.worker_report_synthesis.report_synthesis_models.ValidationReport",
),
```

No tool profile needed (pure synthesis, no tools).

---

## Task 8: Add Stage to Registry

**File:** `haytham/workflow/stage_registry.py`

- Delete `StageMetadata` entries for: `risk-assessment`, `pivot-strategy`, `validation-summary`
- Add new entry:

```python
StageMetadata(
    slug="report-synthesis",
    action_name="report_synthesis",
    display_name="Validation Report",
    display_index=3,
    description="Synthesizes a comprehensive validation report from idea analysis and market research",
    state_key="report_synthesis",
    status_key="report_synthesis_status",
    workflow_type=WorkflowType.IDEA_VALIDATION,
    query_template="...",  # See task 6
    agent_names=["report_synthesis"],
)
```

- Update downstream stages' `required_context` lists:
  - `mvp-scope`: replace `["risk-assessment", "validation-summary"]` with `["report-synthesis"]`
  - `capability-model`: same replacement
  - Any other stages referencing removed slugs

---

## Task 9: Add Burr Action

**File:** `haytham/workflow/burr_actions.py`

- Delete actions: `risk_assessment`, `pivot_strategy`, `validation_summary`
- Add new `report_synthesis` action:
  - Reads: `system_goal`, `idea_analysis`, `market_context`, `session_manager`
  - Writes: `report_synthesis`, `report_synthesis_status`, `current_stage`
- Update `mvp_scope` action: remove reads of `risk_assessment`, `validation_summary`, `pivot_strategy`. Add read of `report_synthesis`.
- Update `capability_model` action: same changes.
- Check other downstream actions for stale reads.

---

## Task 10: Update Workflow Specs

**File:** `haytham/workflow/workflow_specs.py`

- Update `IDEA_VALIDATION_SPEC`:
  - Actions: remove `risk_assessment`, `pivot_strategy`, `validation_summary`. Add `report_synthesis`.
  - Transitions: replace conditional branching with `market_context -> report_synthesis`.
  - Stages list: `["idea_analysis", "market_context", "report_synthesis"]`
  - Remove `extra_state_keys: ["risk_level"]`
- Update downstream specs' `context_stages`:
  - `MVP_SPECIFICATION_SPEC`: replace `"risk-assessment"` / `"validation-summary"` with `"report-synthesis"`
  - `BUILD_BUY_ANALYSIS_SPEC`: replace `"validation-summary"` with `"report-synthesis"`
  - `ARCHITECTURE_DECISIONS_SPEC`: same
  - `STORY_GENERATION_SPEC`: same
- Update imports: remove old actions, add `report_synthesis`

---

## Task 11: Update Stage Execution Config

**File:** `haytham/workflow/stages/configs.py`

- Delete configs for: `risk-assessment`, `pivot-strategy`, `validation-summary`
- Delete imports: `extract_risk_level_processor`, `run_validation_summary_sequential`, 6 validator imports, `_ValidationSummaryOutput`
- Add new config:

```python
"report-synthesis": StageExecutionConfig(
    stage_slug="report-synthesis",
    post_processor=extract_recommendation_processor,
    additional_save=save_final_output,
    post_validators=[validate_som_arithmetic, validate_regulated_domain_safety],
),
```

---

## Task 12: Update Orchestration Functions

**File:** `haytham/workflow/stages/idea_validation.py`

- Delete: `extract_risk_level_processor` function
- Delete: `run_validation_summary_sequential` function (entire scorer+narrator pipeline, ~180 lines)
- Delete: all imports from `recommendation.py` and `validation_summary_models.py`
- Simplify: `extract_recommendation_processor` to read from `ValidationReport` structured output (recommendation is a typed field, not extracted from JSON)
- Keep: `save_final_output` (adapt if needed)
- Keep: `run_market_context_sequential` and all market-context related code (unchanged)

---

## Task 13: Implement Post-Synthesis Guardrails

**Create:** `haytham/workflow/validators/report_guardrails.py`

Two lightweight validators (signature: `(output: str, state: State) -> list[str]`):

1. `validate_som_arithmetic`: Regex-scan the report markdown for SOM figures. If a summary SOM differs from the breakdown calculation, return a warning string. No rejection.

2. `validate_regulated_domain_safety`: Scan for regulatory keywords (HIPAA, PCI-DSS, COPPA, FDA, SOX, GDPR, FERPA). If found AND recommendation is GO, return a warning: "This idea involves regulatory compliance. Review the Risk Assessment section before proceeding."

Register both in `validators/__init__.py`.

---

## Task 14: Update Entry Validators

**File:** `haytham/workflow/entry_validators/mvp_specification.py`

- `_check_idea_validation_complete`: check for `"report-synthesis"` as terminal stage (was `"validation-summary"`)
- `_check_validation_summary`: load from `"report-synthesis"` output. Remove `"risk-assessment"` fallback.
- `_extract_recommendation`: load from `"report-synthesis"`. Read `recommendation.json` (written by post-processor). Remove `"risk-assessment"` and `"validation-summary"` fallbacks. Remove legacy verdict regex patterns.

---

## Task 15: Update Burr Workflow Runner

**File:** `haytham/workflow/burr_workflow.py`

- `_extract_recommendation`: update Tier 3 fallback to read `report_synthesis` key (was `validation-summary`)
- `_extract_results`: remove special-case for `risk-assessment` / `risk_level`

---

## Task 16: Update Output Utils

**File:** `haytham/agents/output_utils.py`

- Delete: `_format_validation_summary_output()` function (~120 lines of scorecard/counter-signal rendering)
- Replace with: `_format_validation_report(data: dict) -> str` that renders the `ValidationReport` model (recommendation badge + report markdown)
- Update: `FORMATTERS` dict to map `"ValidationReport"` to the new formatter

---

## Task 17: Update Feedback Agent

**File:** `haytham/feedback/feedback_agent.py`

- Update import: `ValidationSummaryOutput` -> `ValidationReport`
- Update any code that accesses fields from the old model (scorecard dimensions, counter-signals, etc.) to work with the new minimal model

---

## Task 18: Update Report PDF Config

**File:** `haytham/agents/tools/report_configs.py`

- Delete: `_build_risk_assessment()`, `_build_pivot_strategy()`, `_build_scorecard()`
- Rewrite: `build_idea_validation_config()` to extract cover data (verdict) from `recommendation.json` and report sections from the new report markdown
- Adapt: section builders to parse the 11-section markdown structure instead of loading from separate stage directories

---

## Task 19: Update Streamlit UI

**File:** `frontend_streamlit/views/discovery.py`

- Replace 3 stage entries (risk-assessment, pivot-strategy, validation-summary) with 1 (report-synthesis) in the `STAGES` list
- Delete: `has_pivot_strategy()` function
- Simplify: `extract_metrics()` to read recommendation from `recommendation.json`. Remove composite_score (no longer exists). Remove claims_supported/total.
- Simplify: `render_metrics_dashboard()` to show recommendation badge only (or recommendation + confidence if extractable from markdown)
- Remove: pivot decision point UI (lines 640-746). The new pipeline produces a PIVOT recommendation in the report, no separate pivot stage.
- Update: all stage slug references from old slugs to `report-synthesis`

---

## Task 20: Write New Tests

**Create/update test files:**

1. **`tests/test_validation_report_model.py`** (new):
   - `ValidationReport` model round-trip (JSON serialize/deserialize)
   - Recommendation enum values (GO, PIVOT, NO-GO)
   - Report field accepts arbitrary markdown

2. **`tests/test_report_guardrails.py`** (new):
   - SOM arithmetic check: matching figures (no warning)
   - SOM arithmetic check: mismatching figures (warning returned)
   - SOM arithmetic check: no SOM section (no warning)
   - Safety veto: regulated domain + GO (warning returned)
   - Safety veto: regulated domain + PIVOT (no warning)
   - Safety veto: non-regulated + GO (no warning)

3. **Update `tests/test_workflow_specs.py`**:
   - IDEA_VALIDATION_SPEC has 3 stages (was 5)
   - No conditional branching (was risk_level=HIGH)
   - Terminal stage is `report_synthesis` (was `validation_summary`)

4. **Update `tests/test_stage_config.py`**:
   - `report-synthesis` config exists
   - No `risk-assessment`, `pivot-strategy`, `validation-summary` configs

5. **Update `tests/test_entry_validators.py`**:
   - MVP entry validator checks `report-synthesis` output
   - Recommendation extraction from `recommendation.json`

6. **Update `tests/test_recommendation_extraction.py`**:
   - `extract_recommendation_processor` works with `ValidationReport` JSON

7. **Check and fix:** `test_stage_executor.py`, `test_session_manager.py`, `test_context_loader.py`, `test_feedback_cascade.py` for any stale references

---

## Task 21: Verify

Run the full pre-commit check:

```bash
uv run ruff check haytham/ --fix && uv run ruff format haytham/ && uv run pytest tests/ -v -m "not integration" -x
```

All tests must pass. No lint errors. No unused imports.

---

## Task 22: Update CLAUDE.md

- Update "Scoring & Validation Pipeline" section to reflect the new architecture
- Remove references to scorer, narrator, merge, 6 validators
- Update "Four-Phase Workflow" key transitions (remove conditional risk_level branching)
- Update file references in "Key files" sections

---

## Summary

| Metric | Before | After |
|--------|--------|-------|
| WHY phase stages | 5 (idea-analysis, market-context, risk-assessment, pivot-strategy, validation-summary) | 3 (idea-analysis, market-context, report-synthesis) |
| Agents in validation | 4 (startup_validator, pivot_strategy, validation_scorer, validation_narrator) | 1 (report_synthesis) |
| Post-validators | 6 (revenue_evidence, claim_origin, concept_health, dim8_inputs, jtbd_match, som_sanity) | 2 (som_arithmetic, regulated_domain_safety) |
| Conditional branching | risk_level=HIGH -> pivot-strategy | None |
| Output model fields | ~15 (ValidationSummaryOutput) | 2 (recommendation, report) |
| LLM calls for validation | 3-4 (validator + scorer + narrator, optional pivot) | 1 |
