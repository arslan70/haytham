# Haytham Evaluation Framework

Automated quality evaluation for Haytham pipeline output. Three phases, zero third-party dependencies beyond the Anthropic SDK.

## Setup

```bash
pip install -r evals/requirements.txt
export ANTHROPIC_API_KEY=your-key-here
```

## Phase 1: Triggering Evals

Tests whether the model correctly identifies which component handles a user prompt. 100 scenarios across 20 components with 5 types each (direct, paraphrased, edge_case, negative, semantic).

```bash
# Run all scenarios
python3 evals/triggering/run_triggering_evals.py

# Test a single component
python3 evals/triggering/run_triggering_evals.py --component validate

# Test a specific scenario type
python3 evals/triggering/run_triggering_evals.py --type semantic
```

Pass threshold: 85%. Costs ~$0.10 per full run (sonnet).

## Phase 2: Quality Evals

Grades session output against 22 criteria extracted from 4 review commands, organized into 8 rubric files. Uses opus as grader.

```bash
# Grade all rubrics against a session
python3 evals/quality/run_quality_evals.py --session-dir .haytham/session/

# Grade a specific rubric
python3 evals/quality/run_quality_evals.py --session-dir .haytham/session/ --rubric idea-analysis

# Compare against a baseline
python3 evals/quality/run_quality_evals.py --session-dir .haytham/session/ --compare-baseline evals/baselines/baseline_20260317.json

# Save as new baseline
python3 evals/quality/run_quality_evals.py --session-dir .haytham/session/ --update-baseline
```

Costs ~$1-2 per full run (opus grading 22 criteria).

### Rubric Files

| File | Criteria | Source |
|---|---|---|
| `idea-analysis.json` | Problem Articulation, Analysis Expansion | review-depth, review-fidelity |
| `competitor-research.json` | Competitor Evidence, Sentiment/Demand | review-depth |
| `market-research.json` | Market Sizing Basis | review-depth |
| `validation-report.json` | Brief Neutrality, Reasoning Chain, Risk Specificity, Report Fidelity | review-depth, review-fidelity |
| `capabilities.json` | Capability Fidelity, Scope Clarity, Flow Specificity, Capability Precision | review-fidelity, review-actionability |
| `architecture.json` | Architecture Fidelity, Architecture Specificity, Architecture Completeness | review-fidelity, review-actionability |
| `openspec.json` | Spec Fidelity, SHALL Precision, Scenario Completeness, Agent Readability | review-fidelity, review-actionability |
| `cross-phase.json` | Anchor Accuracy, Scope Fidelity | review-fidelity |

## Phase 3: Consistency + E2E

### Deterministic Consistency Checks (free, CI-safe)

5 checks that verify structural consistency without API calls:

```bash
python3 evals/e2e/consistency_checks.py --session-dir .haytham/session/
```

- Check 5: Capability Traceability (CAP-* IDs vs scope items)
- Check 7: Architecture Serves Capabilities (coverage_check)
- Check 8: Build/Buy Consistency (duplicate/conflicting categories)
- Check 9: Spec Coverage (CAP-* in spec files)
- Check 10: Cross-Reference Integrity (DEC-* IDs, trait matching)

### LLM-Graded Consistency Checks (optional)

5 additional checks requiring semantic judgment:

```bash
python3 evals/e2e/consistency_checks.py --session-dir .haytham/session/ --llm
```

- Check 1: Concept Anchor Preservation
- Check 2: Recommendation-Evidence Alignment
- Check 3: Idea Analysis to Report Continuity
- Check 4: Scope Traces to Validation
- Check 6: System Traits Agreement

### UX Transcript Grading

Grades a run transcript against 7 UX criteria from ux-review.md:

```bash
python3 evals/e2e/ux_grader.py --transcript path/to/transcript.txt
```

### Full E2E Runner

Combines all checks into a single run:

```bash
# Deterministic only (free)
python3 evals/e2e/run_e2e_eval.py --session-dir .haytham/session/

# Full run with LLM grading + UX
python3 evals/e2e/run_e2e_eval.py --session-dir .haytham/session/ --full --transcript transcript.txt
```

## Baselines

After a full run, save results as a baseline for regression detection:

```bash
python3 evals/quality/run_quality_evals.py --session-dir .haytham/session/ --update-baseline
```

Compare future runs against the baseline:

```bash
python3 evals/quality/run_quality_evals.py --session-dir .haytham/session/ --compare-baseline evals/baselines/baseline_YYYYMMDD.json
```

## CI Integration

The CI workflow runs deterministic consistency checks on every PR (free, no API key needed). API-dependent evals run manually or via a separate workflow with `ANTHROPIC_API_KEY`.
