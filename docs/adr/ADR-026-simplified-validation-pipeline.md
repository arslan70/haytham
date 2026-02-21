# ADR-026: Simplified Validation Pipeline

## Status
**Accepted** - 2026-02-21

## Context

### The Problem

The WHY phase validation pipeline (risk-assessment, pivot-strategy, validation-summary) uses 4 agents, 6 post-validators, a merge function, and deterministic scoring machinery to produce a validation report. Analysis against industry benchmarks ([Issue #12](https://github.com/arslan70/haytham/issues/12)) identified 10 systemic quality gaps (S1-S10) in the report output.

Investigation into root causes revealed that most gaps stem from the pipeline's architecture, not from individual agent prompts:

- **S5** (scoring dimensions don't cross-reference): Each dimension is scored independently. A contradicted claim in risk-assessment doesn't affect the scorer's dimension scores because the scorer treats dimensions in isolation.
- **S1** (tautological claims): The startup_validator mechanically extracts claims and validates them against upstream context. Despite extensive prompt guidance, it treats founder statements as validatable claims.
- **S2** (no financial feasibility): No stage produces financial analysis, but Revenue Viability gets a numeric score anyway, creating false confidence.
- **S7** (generic next steps): The narrator generates next steps from scorer JSON, losing the holistic context needed to produce idea-specific guidance.
- **S10** (sections don't synthesize): Each agent operates on its slice. No single agent sees everything at once.

The 6 post-validators (revenue_evidence, claim_origin, concept_health, dim8_inputs, som_sanity, jtbd_match) exist specifically to catch inconsistencies that the multi-agent split introduces. They are patches for an architecture problem.

### The Hypothesis

A single LLM with full upstream context (idea analysis + market research) would produce a more coherent, cross-referenced, actionable report than the 4-agent pipeline, because:

1. Cross-referencing happens naturally when one agent sees all findings
2. No information is lost at agent boundaries
3. No validators needed to patch inconsistencies that don't arise

### The Experiment

We built a DSPy proof-of-concept with a single `ReportSynthesis` Signature. The prompt defines 11 report sections covering all the gaps identified in Issue #12 (financial feasibility, pre-build validation, domain-risk detection, network dependencies, specific next steps, etc.).

We ran both approaches on the same inputs (idea-analysis + market-context outputs) for three test ideas spanning different archetypes:

- T1: Web app (gym leaderboard)
- T2: CLI tool (markdown to PDF)
- T6: Wellness app (Power of 8, regulated domain, concept fidelity constraints)

### Results

Manual evaluation against 12 quality criteria:

| Criterion | Baseline (4 agents + 6 validators) | DSPy (single agent) |
|-----------|-------------------------------------|---------------------|
| Idea-specific next steps | FAIL | PASS |
| Realistic cost/revenue estimates | FAIL | PASS |
| TAM/SAM/SOM scoped realistically | PARTIAL | PARTIAL |
| TAM/SAM/SOM shows arithmetic | FAIL | PARTIAL |
| No tautological claims | PARTIAL | PARTIAL |
| Sections cross-reference | FAIL | PASS |
| Domain-specific risks (HIPAA) | PARTIAL | PASS |
| Network dependencies (cold-start) | FAIL | PASS |
| Pre-build validation experiment | FAIL | PASS |
| Coherent narrative | FAIL | PASS |
| No fabricated UVP metrics | PASS | PARTIAL |
| Concept fidelity | PARTIAL | PASS |
| **Totals** | **1 PASS / 3 PARTIAL / 8 FAIL** | **8 PASS / 4 PARTIAL / 0 FAIL** |

The single agent scored zero FAILs. The current pipeline scored 8 FAILs. The remaining PARTIAL scores in the DSPy output (TAM scoping, arithmetic consistency, fabricated statistics) are prompt refinement issues, not architectural problems.

## Decision

Replace the three validation stages (risk-assessment, pivot-strategy, validation-summary) with a single synthesis stage that produces the complete validation report in one LLM call.

### Simplified Pipeline

```
Raw idea
  |
Stage 1: UNDERSTAND (idea-analysis, keep as-is)
  -> Structures the idea, surfaces assumptions, detects domain signals
  -> User reviews and refines
  |
Stage 2: RESEARCH (market-context, keep as-is)
  -> Web research: market sizing, competitors, pricing, user sentiment
  -> Two agents (market_intelligence + competitor_analysis) justified by needing different tools
  |
Stage 3: VALIDATE (new single synthesis agent)
  -> Receives: original idea + Stage 1 output + Stage 2 output
  -> Produces: complete validation report (11 sections)
  -> One agent, one pass, one coherent document
```

### What Gets Removed

- `risk-assessment` stage (startup_validator agent, risk_classification tool, ValidationOutput model)
- `pivot-strategy` stage (pivot_strategy agent)
- `validation-summary` stage (validation_scorer agent, validation_narrator agent, merge function)
- 6 post-validators (revenue_evidence, claim_origin, concept_health, dim8_inputs, som_sanity, jtbd_match)
- Recommendation tooling (record_knockout, record_dimension_score, record_counter_signal)
- Scoring models (ScorerOutput, NarrativeFields, ValidationSummaryOutput)

### What Gets Created

- `report_synthesis` agent with a single comprehensive prompt
- `ValidationReport` output model covering all 11 sections

### What Gets Preserved (as report sections, not as machinery)

- Knockout criteria (dealbreaker checks as a report section)
- Counter-signal reasoning (addressed in the Go/No-Go recommendation section)
- Claims analysis (holistic evidence evaluation, not mechanical extraction)
- Pivot options (included in the report when applicable)

## Consequences

### Positive

- Eliminates 10 systemic quality gaps identified in Issue #12
- Removes ~2000 lines of scoring/validation/merge machinery
- Single prompt is easier to iterate on than 4 prompts + 6 validators
- Report quality is empirically better (0 FAIL vs 8 FAIL)
- New report sections (financial feasibility, pre-build validation, domain risks) come free from the prompt, no new stages needed

### Negative

- Deterministic scoring formula is removed. The GO/PIVOT/NO-GO recommendation is now the LLM's judgment, not a formula output. Safety overrides (e.g., HIGH risk caps GO to PIVOT) need to be enforced differently (prompt-level or lightweight post-check).
- Single point of failure: if the synthesis agent produces poor output, there's no downstream validator to catch it. Mitigation: the prompt is comprehensive and testable with DSPy.
- Longer single LLM call vs several shorter ones. May hit token limits for very complex ideas. Mitigation: upstream context is already bounded by Stage 1 and Stage 2 output sizes.

### Risks

- Prompt regression: changes to the synthesis prompt could degrade quality across all report sections simultaneously. Mitigation: test across idea archetypes (T1-T6) before deploying prompt changes.
- The remaining PARTIAL scores (TAM scoping, fabricated statistics) need prompt iteration to resolve. These are not architectural blockers.

## Design Principle (New)

**When multi-agent IS justified**: When agents need different tools (web search vs analysis), different model tiers, or operate on genuinely independent tasks. Gathering information is a valid reason to split.

**When multi-agent is NOT justified**: When the task requires holistic reasoning across a shared context. Synthesizing information into a coherent output should be one agent with full context, not multiple agents with partial context connected by deterministic glue.

## References

- [Issue #12: Report output: close decision-making gaps](https://github.com/arslan70/haytham/issues/12)
- [Design doc: Report Quality Redesign](docs/plans/2026-02-20-report-quality-redesign.md)
- [DSPy PoC outputs](tests/dspy_poc/outputs/)
- [ADR-023: Scorer Dimension Reduction](docs/adr/ADR-023-scorer-dimension-reduction.md) (predecessor, addressed symptoms of the same root cause)
