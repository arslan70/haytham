# ADR-026: Simplified Validation Pipeline

## Status
**Accepted** - 2026-02-21

## Context

### The Problem

The WHY phase validation pipeline (risk-assessment, pivot-strategy, validation-summary) uses 4 agents, 6 post-validators, a merge function, and deterministic scoring machinery to produce a validation report. Analysis against industry benchmarks ([Issue #12](https://github.com/arslan70/haytham/issues/12)) identified 10 systemic quality gaps (S1-S10) in the report output.

Investigation into root causes revealed two classes of gaps:

**Architecture-caused** (context fragmentation prevents quality output regardless of prompt quality):

- **S5** (scoring dimensions don't cross-reference): Each dimension is scored independently. A contradicted claim in risk-assessment doesn't affect the scorer's dimension scores because the scorer treats dimensions in isolation.
- **S7** (generic next steps): The narrator generates next steps from scorer JSON, losing the holistic context needed to produce idea-specific guidance.
- **S10** (sections don't synthesize): Each agent operates on its slice. No single agent sees everything at once.

**Prompt-content gaps** (missing functionality that could be addressed by better prompts within the existing architecture, but are easier to add in a single-agent design):

- **S1** (tautological claims): The startup_validator mechanically extracts claims and validates them against upstream context. Despite extensive prompt guidance, it treats founder statements as validatable claims. A prompt fix might work, but the scorer-narrator split makes it harder because claim evaluation happens in one agent and narrative in another.
- **S2** (no financial feasibility): No stage produces financial analysis, but Revenue Viability gets a numeric score anyway, creating false confidence. This is a missing section, not strictly an architecture problem. However, adding it to the current pipeline would require deciding which agent produces it and how it flows through the scorer-narrator-merge path.

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

**Important caveat**: This experiment tests the combined effect of a single-agent architecture AND an improved prompt. Several criteria (financial feasibility, pre-build validation, network dependencies) are new sections that don't exist in the current pipeline's prompts. The fair isolation of the architecture variable would require running the improved prompt through the existing pipeline, which we did not do because the scorer-narrator-merge path has no mechanism to add free-form report sections without restructuring the output model. This confirms the architecture is the bottleneck for extensibility, even if the raw quality comparison overstates the architecture's contribution.

### Results

Single-pass manual evaluation by one reviewer against 12 quality criteria. Not blinded (reviewer knew which output was DSPy vs baseline). Each idea was generated once per approach (no replication runs).

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
| No fabricated UVP metrics | PASS | **PARTIAL** (regression) |
| Concept fidelity | PARTIAL | PASS |
| **Totals** | **1 PASS / 3 PARTIAL / 8 FAIL** | **8 PASS / 4 PARTIAL / 0 FAIL** |

The single agent scored zero FAILs. The current pipeline scored 8 FAILs. The DSPy output regressed on "No fabricated UVP metrics" (PASS to PARTIAL), showing that removing structured constraints can increase hallucination risk in specific areas. The remaining PARTIAL scores (TAM scoping, arithmetic consistency) are prompt refinement issues.

**Evaluation limitations**: Single reviewer, single run, not blinded. LLM outputs are non-deterministic, so the results may vary across runs. The dramatic gap (8 vs 0 FAILs) is large enough to be directionally reliable, but the exact scores should not be treated as precise measurements.

**Observed regressions in PoC outputs**: The T6 output contains a SOM arithmetic inconsistency (summary says $320K, breakdown calculates $3.2M). The removed `som_sanity` validator would have caught this. This confirms that removing validators trades consistency checking for coherence, and motivates the post-synthesis guardrails described in the Decision section.

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
  -> Produces: complete validation report (8 sections)
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
- `ValidationReport` structured output model covering all 8 sections, including a typed `recommendation` field (GO/PIVOT/NO-GO) for downstream consumption
- **Post-synthesis guardrails** (lightweight, deterministic):
  - Extract `recommendation` from structured output for Gate 1 and UI rendering
  - SOM arithmetic check: verify that the SOM figure in the summary matches the SOM calculation in the breakdown (flag mismatch to user, do not silently override)
  - Safety veto: if the report mentions regulated domain keywords (HIPAA, PCI-DSS, COPPA) AND recommends GO, flag for user attention ("This idea involves regulatory compliance. Confirm you've reviewed the Risk Assessment section before proceeding.")
  - These guardrails check for internal consistency, not substance. They are not validators in the old sense (they don't reject or rewrite output). They surface concerns for the human reviewer.

### What Gets Preserved (as report sections, not as machinery)

- Knockout criteria (dealbreaker checks as a report section)
- Counter-signal reasoning (addressed in the Go/No-Go recommendation section)
- Claims analysis (holistic evidence evaluation, not mechanical extraction)
- Pivot options (included in the report when applicable)

## Consequences

### Positive

- Addresses the 3 architecture-caused quality gaps (S5, S7, S10) that cannot be fixed by prompt changes alone
- Makes the 2 prompt-content gaps (S1, S2) easy to address by adding report sections to a single prompt, rather than threading them through the scorer-narrator-merge path
- Removes ~2000 lines of scoring/validation/merge machinery
- Single prompt is easier to iterate on than 4 prompts + 6 validators
- Report quality is empirically better (0 FAIL vs 8 FAIL), though part of this improvement comes from the improved prompt content, not just the architecture change
- Pipeline is extensible: adding a new report section means adding a paragraph to the prompt, not a new agent + output model field + validator

### Negative

- **Deterministic scoring formula is removed.** The GO/PIVOT/NO-GO recommendation becomes the LLM's judgment, not a formula output. The current `_evaluate_core()` rules (knockout FAIL = NO-GO, HIGH risk caps GO to PIVOT, dimension floor caps composite) are auditable and consistent. Replacing them with LLM judgment trades consistency for nuance. Mitigation: the `ValidationReport` structured output model includes a typed `recommendation` field, and the post-synthesis guardrails (see "What Gets Created") surface regulated-domain GO recommendations for user review.
- **Loss of structured data.** The current pipeline produces `ValidationSummaryOutput` JSON consumed by the UI and downstream stages. The new pipeline must produce a `ValidationReport` structured output model with at minimum a `recommendation` field for Gate 1 approval and a renderable report body for the UI. This is not optional, it is a migration requirement.
- **Wider output variance.** The PoC regressed on "No fabricated UVP metrics" (PASS to PARTIAL). Rule-based systems are crude but consistent. LLM judgment is better on average but has a wider variance. The post-synthesis guardrails partially address this, but some classes of errors (fabricated statistics, hallucinated metrics) can only be caught by human review.
- **Human-in-the-loop as quality gate.** The user reviews the report and can refine it via chat. This is a better quality gate than validators that check form over substance, but it assumes the user will catch arithmetic inconsistencies in a long report. The SOM mismatch in the T6 PoC output shows this assumption is not always safe, which motivates the SOM arithmetic guardrail.
- **Longer single LLM call.** Estimated token budget: ~5-10K input tokens per upstream stage (idea-analysis + market-context), plus the original idea and system prompt, totaling ~15-25K input tokens. Output is ~4-8K tokens for 8 sections. This is within Bedrock model context windows but should be monitored. Very complex ideas with extensive market research could approach limits.

### Risks

- **Prompt regression**: Changes to the synthesis prompt could degrade quality across all report sections simultaneously (single point of failure vs distributed failure). Mitigation: test across idea archetypes (T1-T6) before deploying prompt changes. Consider adding a "generate then review" pattern in the future (a second agent that checks the report for internal consistency) if prompt regression becomes a recurring problem.
- **Fabricated metrics regression**: The PoC showed increased fabrication risk compared to the baseline. This needs prompt iteration to resolve (e.g., stronger "tag as [estimate]" instructions). Not an architectural blocker, but must be addressed before shipping.
- **Non-deterministic evaluation**: The PoC results are based on single runs. LLM outputs vary between runs, so the quality scores should be treated as directional, not precise. Future prompt changes should be evaluated across multiple runs per idea.

## Design Principle (New)

**When multi-agent IS justified**: When agents need different tools (web search vs analysis), different model tiers, or operate on genuinely independent tasks. Gathering information is a valid reason to split. A "generate then review" pattern (one agent produces output, a second checks it for consistency) is also justified because the two agents have different roles, not fragmented context.

**When multi-agent is NOT justified**: When the task requires holistic reasoning across a shared context. Synthesizing information into a coherent output should be one agent with full context, not multiple agents with partial context connected by deterministic glue.

**The wrong split vs the right split**: The current pipeline's problem is not that it used multiple agents for validation. It's that it split the *reasoning* (scorer extracts structure, narrator produces prose from structure, merge recombines). A different multi-agent design (one agent produces the full report, another reviews it) could capture both single-agent coherence and automated quality checking. This is a potential future improvement if the post-synthesis guardrails prove insufficient.

## References

- [Issue #12: Report output: close decision-making gaps](https://github.com/arslan70/haytham/issues/12)
- [Design doc: Report Quality Redesign](../plans/2026-02-20-report-quality-redesign.md)
- [DSPy PoC outputs](../../tests/dspy_poc/outputs/)
- [ADR-023: Scorer Dimension Reduction](ADR-023-scorer-dimension-reduction.md) (predecessor, incremental improvement within the existing architecture)
