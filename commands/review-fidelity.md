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
8. `.haytham/session/phase-4-stories/stories.json`

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

### 7. Story Fidelity (if stories.json exists)

Do the implementation stories, when read together, describe building the product the founder envisioned?

- PASS: Stories collectively describe the founder's product
- PARTIAL: Stories describe the product but have drifted from the original emphasis
- FAIL: Stories describe a different product, or are so generic they could apply to any similar project

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

### Drift Summary

If any check is PARTIAL or FAIL, describe the overall drift pattern:
- Is the idea being **narrowed** (losing distinctive elements)?
- Is it being **expanded** (accumulating features the founder didn't ask for)?
- Is it being **substituted** (replaced with a more generic version)?

Name the specific agent prompt(s) where the drift likely originates, and whether it's a **missing instruction** (no fidelity guard), **weak instruction** (guard exists but isn't followed), or **structural gap** (no mechanism to enforce fidelity at this stage).
