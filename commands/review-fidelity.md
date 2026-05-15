---
description: Review whether pipeline output stays faithful to the original idea throughout all phases
argument-hint: (no arguments - reads from .haytham/session/)
allowed-tools: Read, Glob
---

# Haytham: Concept Fidelity Review

You are reviewing whether the pipeline preserves the founder's original idea faithfully through every phase. Concept drift is when downstream agents reshape, narrow, or expand the idea beyond what the founder intended. This review catches drift early.

## Prerequisites

Before evaluating anything, read the following files. ALL are required.

**Required:**
1. `.haytham/project.yaml` — the original idea as the founder stated it
2. `.haytham/session/phase-1-why/concept-anchor.json` — the invariants extracted from the idea
3. `.haytham/session/phase-1-why/idea-analysis.md` — the expanded analysis

If any of these three files is missing, stop and say:
> "Cannot run fidelity review. Missing: [list files]. Run `/haytham:validate` to produce Phase 1 output first."

**Optional (enables deeper checks):**
4. `.haytham/session/phase-1-why/validation-report.md`
5. `.haytham/session/phase-2-what/mvp-scope.md`
6. `.haytham/session/phase-2-what/capabilities.json`
7. `.haytham/session/phase-3-how/architecture-decisions.json`
8. `.haytham/session/phase-4-specs/openspec/`

Read each optional file that exists. For files that don't exist, skip the checks that depend on them. Do NOT guess what missing files might contain.

## Evaluation

### 1. Anchor Accuracy

Compare `project.yaml` (the raw idea) with `concept-anchor.json` (the extracted invariants). Did the idea-analyst correctly identify what makes this idea THIS idea, or did it impose assumptions?

- PASS: Invariants and identity match the founder's stated idea without adding or removing core elements
- PARTIAL: Mostly accurate but one invariant is an assumption not stated in the original idea
- FAIL: Anchor adds significant elements the founder didn't mention, or drops a core element they did mention

Quote the original idea and the invariants side by side.

### 2. Analysis Expansion vs. Invention

Compare `project.yaml` with `idea-analysis.md`. The analysis should expand and clarify the idea, not invent new features or pivot the concept.

- PASS: Analysis elaborates on what the founder said without introducing new product concepts
- PARTIAL: Mostly faithful but suggests features or user segments the founder didn't mention, presented as part of the idea rather than as suggestions
- FAIL: Analysis describes a materially different product than what the founder stated

### 3. Validation Report Fidelity (if validation-report.md exists)

Does the validation report evaluate the idea the founder actually described, or a modified version?

- PASS: Report evaluates the original concept as stated
- PARTIAL: Report evaluates the concept but subtly shifts emphasis (e.g., founder said "community" but report focuses on "gamification")
- FAIL: Report evaluates a different product concept

### 4. Scope Fidelity (if mvp-scope.md exists)

Does the MVP scope preserve the founder's core intent, or does it reshape the idea into something different "for MVP purposes"?

- PASS: The One Thing and IN-scope items are clearly derived from the founder's original idea
- PARTIAL: Scope is related but has shifted emphasis without acknowledging the trade-off
- FAIL: Scope describes a different product justified as "MVP simplification"

### 5. Capability Fidelity (if capabilities.json exists)

Do the extracted capabilities serve the founder's idea, or do they describe a generic version of the product category?

- PASS: Capabilities are specific to this idea's unique angle, not generic category features
- PARTIAL: Mix of idea-specific and generic capabilities
- FAIL: Capabilities could describe any product in this category, nothing specific to the founder's vision

### 6. Architecture Fidelity (if architecture-decisions.json exists)

Do architecture decisions serve the specific needs of this idea, or are they generic best practices?

- PASS: Decisions reference specific capabilities and constraints from this idea
- PARTIAL: Some decisions are idea-specific, others are generic defaults
- FAIL: Architecture is a generic template with no connection to the specific idea

### 7. Specification Fidelity (if phase-4-specs/openspec/ exists)

Do the SHALL statements and Gherkin scenarios describe building the product the founder envisioned? Check that domain groupings reflect the founder's emphasis, SHALL statements preserve the idea's distinctive features, and config.yaml traits match the concept anchor.

- PASS: Specs collectively describe the founder's product
- PARTIAL: Specs describe the product but domain emphasis has drifted from the original
- FAIL: Specs describe a generic product, or are so template-like they could apply to any similar project

## Output Format

Only include checks for files that exist. State clearly which phases were available.

```
| # | Check                    | Result  | Evidence |
|---|--------------------------|---------|----------|
| 1 | Anchor Accuracy          | PASS    | Idea: "gym leaderboard with anonymous handles" → Invariant: "anonymity is non-negotiable" |
| 2 | Analysis Expansion       | PARTIAL | Analysis adds "social feed" not in original idea |
| ... | ... | ... | ... |
```

**Files reviewed: [list]**
**Score: X PASS, Y PARTIAL, Z FAIL out of N applicable checks**

### Confidence Discipline

Every drift call must carry a confidence score 0-100:

- 90-100: Specific drift with quoted evidence from both the original idea and the downstream output. The drift is visible side-by-side.
- 80-89: Drift is named with evidence but lower blast radius (e.g., emphasis shift, single missing element).
- 60-79: Plausible drift without specific evidence. Likely interpretive.
- <60: Style preference or speculative.

**Surface only drift calls with confidence ≥ 80.** Collapse the rest into a single trailing line:

> N drift signals below threshold suppressed.

A confidence score without quoting both the original and the drifted output is invalid. Score the citation, not the vibe.

### Drift Summary

If any check is PARTIAL or FAIL with confidence ≥ 80, describe the overall drift pattern:
- Is the idea being **narrowed** (losing distinctive elements)?
- Is it being **expanded** (accumulating features the founder didn't ask for)?
- Is it being **substituted** (replaced with a more generic version)?

For each drift call, prefix with **[confidence]** and quote both the original idea and the downstream output side by side.

Name the specific agent prompt(s) where the drift likely originates, and whether it's a **missing instruction** (no fidelity guard), **weak instruction** (guard exists but isn't followed), or **structural gap** (no mechanism to enforce fidelity at this stage).
