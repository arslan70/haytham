# Scoring & Validation Pipeline

> **Contributor reference.** This document describes the internals of the validation scoring pipeline. For a higher-level overview, see [How It Works — Phase 1](../how-it-works.md#phase-1-should-this-be-built).

Reference documentation for the validation-summary stage: scorer → narrator → merge.

## Data Flow

```
User Input
  ↓
Concept Anchor (anchor_extractor)
  ↓
Idea Analysis (concept_expansion)
  ↓
Market Context (market_intelligence → competitor_analysis)
  ↓
Risk Assessment (startup_validator)
  ↓  [optional]
Pivot Strategy (pivot_strategy)
  ↓
┌─────────────────────────────────────┐
│ Validation Summary (sequential)     │
│                                     │
│  1. Scorer (REASONING tier)         │
│     → knockouts, dim scores,        │
│       counter-signals, verdict      │
│                                     │
│  2. Narrator (HEAVY tier)           │
│     → exec summary, lean canvas,    │
│       findings, next steps          │
│                                     │
│  3. Merge (deterministic)           │
│     → ValidationSummaryOutput JSON  │
└─────────────────────────────────────┘
  ↓
Post-Validators (6 cross-checks)
```

## Scorer Agent

**Model tier**: REASONING (strongest model for cross-referencing and conditional logic)

The scorer receives full untruncated upstream context inline in its query (not via the generic `_build_context_summary()` which truncates). It records assessments step-by-step using 5 tool functions.

### Scorer Tool Functions

All tools operate on a module-level `_scorecard` accumulator. Lifecycle is managed by `clear_scorecard()` / `get_scorecard()` in the stage executor.

| # | Tool | Signature | Behavior |
|---|------|-----------|----------|
| 1 | `record_knockout` | `(criterion, result, evidence)` | Appends to `_scorecard["knockouts"]`. Call 3× (Problem Reality, Channel Access, Regulatory/Ethical). |
| 2 | `record_counter_signal` | `(signal, source, affected_dimensions, evidence_cited, why_score_holds, what_would_change_score)` | Validates `source` against `_VALID_SOURCES`. Appends to `_scorecard["counter_signals"]`. |
| 3 | `record_dimension_score` | `(dimension, score, evidence)` | Validates evidence quality (rubric phrase rejection, source tag for score ≥ 4, evidence dedup). Appends to `_scorecard["dimensions"]`. |
| 4 | `set_risk_and_evidence` | `(risk_level, external_supported, external_total, contradicted_critical)` | Sets `_scorecard["risk_level"]` and `_scorecard["evidence_quality"]`. Call once. |
| 5 | `compute_verdict` | `()` | Reads accumulated scorecard, delegates to `evaluate_recommendation()`. Returns JSON with verdict, composite, warnings, flags. |

### Evidence Validation Gates

Applied inside `record_dimension_score()` before appending:

1. **Rubric phrase rejection** (all scores): Evidence containing verbatim rubric text (e.g., "users pay for workarounds today", "strong domain knowledge") is REJECTED. List in `_RUBRIC_PHRASES`.

2. **Source tag validation** (score ≥ 4): Evidence must contain `(source: stage_name)` with a valid stage from `_VALID_SOURCES`: `idea_analysis`, `market_context`, `risk_assessment`, `concept_anchor`, `pivot_strategy`, `founder_context`.

3. **Evidence dedup** (all scores): Evidence with >70% word overlap against an already-recorded dimension's evidence is REJECTED. Forces distinct evidence per dimension.

### Verdict Computation Layers

Applied inside `evaluate_recommendation()` in this order:

1. **Knockout check**: Any knockout FAIL → immediate NO-GO (composite = 0.0).
2. **Composite average**: `sum(scores) / len(scores)`.
3. **Floor rule**: If any dimension scores ≤ 2 AND composite > 3.0, cap composite at 3.0.
4. **Counter-signal consistency**: Check for unreconciled signals on high-scored (≥ 4) dimensions. Reconciliation requires: (a) all 3 structured fields populated + evidence ≥ 30 chars + no circular phrases, OR (b) legacy `reconciliation` text ≥ 20 chars.
5. **Counter-signal penalty**: If ≥ 2 warnings (inconsistencies + low-signal-count), apply −0.5 to composite.
6. **Threshold mapping**: NO-GO ≤ 2.0 / PIVOT 2.1–3.5 / GO > 3.5.
7. **Risk veto**: HIGH risk caps GO → PIVOT unless ≥ 2 counter-signals are well-reconciled (stricter bar: structured evidence ≥ 30 chars or legacy ≥ 50 chars).
8. **Confidence hint**: Computed from evidence quality metrics (external_supported/total, contradicted_critical, risk_level).

### Confidence Hint Rubric

| Priority | Condition | Result |
|----------|-----------|--------|
| 1 | Any contradicted critical claim | LOW |
| 2 | HIGH risk + < 50% external supported | LOW |
| 2 | HIGH risk + ≥ 50% external supported | MEDIUM |
| 3 | < 40% external supported | LOW |
| 4 | 40–69% external supported | MEDIUM |
| 5 | ≥ 70% external supported + risk ≠ HIGH | HIGH |

## Narrator Agent

**Model tier**: HEAVY

Receives scorer JSON output + full upstream context. Generates prose fields: executive summary, lean canvas, validation findings, and next steps. Outputs `NarrativeFields` structured JSON.

## Merge Function

`merge_scorer_narrator(scorer_data, narrator_data)` in `validation_summary_models.py`:

- Combines scorer analytical fields (knockouts, scorecard, counter-signals, verdict, composite) with narrator prose fields (executive summary, lean canvas, findings, next steps).
- **Verdict fix**: If narrator's executive summary contains a verdict that contradicts scorer's recommendation, patches the text deterministically via `_fix_exec_summary_verdict()`.
- Output validates as `ValidationSummaryOutput` Pydantic model.

## Post-Validators

Six cross-check validators run after the validation-summary stage:

| Validator | File | What it checks |
|-----------|------|----------------|
| `validate_revenue_evidence` | `validators/revenue_evidence.py` | Revenue Viability score consistency with Revenue Evidence Tag and WTP signals |
| `validate_claim_origin` | `validators/claim_origin.py` | Score consistency with external claim support ratio |
| `validate_jtbd_match` | `validators/jtbd_match.py` | JTBD match alignment between MI and CA outputs |
| `validate_concept_health_bindings` | `validators/concept_health.py` | Dimension score caps when concept health signals are weak |
| `validate_dim8_inputs` | `validators/dim8_inputs.py` | Adoption & Engagement Risk inputs (trigger confidence, switching cost) |
| `validate_som_sanity` | `validators/som_sanity.py` | SOM plausibility relative to TAM/SAM |

## Evidence-to-Dimension Mapping

| Dimension | Primary Upstream Evidence |
|-----------|-------------------------|
| Problem Severity | Pain signals, concept health, forum complaints |
| Market Opportunity | TAM/SAM/SOM, industry reports, growth trends |
| Competitive Differentiation | Gaps, switching costs, review site data |
| Execution Feasibility | Technical + operational claims (merged) |
| Revenue Viability | Revenue Evidence Tag, WTP, pricing benchmarks |
| Adoption & Engagement Risk | Trigger confidence, workaround effort, switching cost |

## Key Files Index

| File | Role |
|------|------|
| `haytham/agents/tools/recommendation.py` | Scorer tools, evidence validation, verdict computation |
| `haytham/agents/worker_validation_scorer/worker_validation_scorer_prompt.txt` | Scorer agent prompt |
| `haytham/agents/worker_validation_narrator/` | Narrator agent prompt + models |
| `haytham/agents/worker_validation_summary/validation_summary_models.py` | Pydantic models, merge function, markdown rendering |
| `haytham/workflow/stages/idea_validation.py` | Orchestration: `run_validation_summary_sequential()` |
| `haytham/workflow/validators/` | Post-validator implementations |
| `haytham/workflow/anchor_schema.py` | ConceptAnchor, ConceptHealth, FounderPersona |
