---
description: Review cross-stage consistency and traceability across Haytham output
argument-hint: (no arguments - reads from .haytham/session/)
allowed-tools: Read, Glob
---

# Haytham: Internal Consistency Review

You are reviewing whether outputs across pipeline stages agree with each other. Inconsistencies between stages indicate lost context, mangled handoffs, or agents re-deriving values instead of reading upstream files.

## Prerequisites

Before evaluating anything, check which phases have been completed by reading the files below. You need at minimum Phase 1 complete. Record which phases are available so you only evaluate what exists.

**Phase 1 (required minimum):**
1. `.haytham/session/phase-1-why/concept-anchor.json`
2. `.haytham/session/phase-1-why/idea-analysis.md`
3. `.haytham/session/phase-1-why/validation-report.json`
4. `.haytham/session/phase-1-why/validation-report.md`

If any Phase 1 file is missing, stop and say:
> "Cannot run consistency review. Missing: [list files]. Run `/haytham:validate` to produce Phase 1 output first."

**Phase 2 (optional, enables more checks):**
5. `.haytham/session/phase-2-what/mvp-scope.md`
6. `.haytham/session/phase-2-what/capabilities.json`
7. `.haytham/session/phase-2-what/system-traits.json`

**Phase 3 (optional, enables more checks):**
8. `.haytham/session/phase-3-how/build-buy.json`
9. `.haytham/session/phase-3-how/architecture-decisions.json`

**Phase 4 (optional, enables more checks):**
10. `.haytham/session/phase-4-specs/openspec/config.yaml`
11. `.haytham/session/phase-4-specs/openspec/project.md`
12. `.haytham/session/phase-4-specs/openspec/specs/*/spec.md`

Read each file that exists. For files that don't exist, note "Phase N not yet completed" and skip the checks that depend on those files. Do NOT guess what missing files might contain.

## Phase 1 Checks (always run)

### 1. Concept Anchor Preservation

Read `concept-anchor.json`. Check that the `invariants` and `identity` values appear (by meaning, not exact wording) in `validation-report.md`. The concept anchor defines what the idea IS. If the validation report contradicts or ignores an invariant, that's a consistency failure.

- PASS: All invariants from concept anchor are reflected in the report
- PARTIAL: Some invariants present, others not mentioned
- FAIL: Report contradicts an invariant, or invariants are entirely absent from the report

### 2. Recommendation-Evidence Alignment

Read `validation-report.json` and extract the `recommendation` (GO/PIVOT/NO-GO). Read `validation-report.md` and check whether the evidence presented supports the recommendation.

- PASS: Evidence clearly supports the stated recommendation
- PARTIAL: Evidence is mixed but recommendation is plausible
- FAIL: Evidence contradicts the recommendation (e.g., strong competition + no differentiator but GO, or clear opportunity but NO-GO)

### 3. Idea Analysis to Report Continuity

Compare the core concept in `idea-analysis.md` with how the idea is described in `validation-report.md`. Are they describing the same thing?

- PASS: Same concept, same target user, same problem
- PARTIAL: Same concept but target user or problem has shifted without explanation
- FAIL: Report describes a different concept than what idea analysis produced

## Phase 2 Checks (if Phase 2 files exist)

### 4. Scope Traces to Validation

Check that IN-scope items in `mvp-scope.md` align with the recommendation reasoning in `validation-report.md`. If the report recommended focusing on X, is X in scope?

- PASS: Scope items align with validation findings and recommendation
- PARTIAL: Mostly aligned but some scope items have no connection to validation findings
- FAIL: Scope includes items the validation explicitly cautioned against, or excludes items the validation identified as critical

### 5. Capability Traceability

Read `capabilities.json`. Check that every functional capability has a non-empty `serves_scope_item` that matches an actual IN-scope item from `mvp-scope.md`.

- PASS: All capabilities trace to real scope items
- PARTIAL: Some capabilities have vague or missing traceability
- FAIL: Capabilities reference scope items that don't exist, or multiple capabilities have no traceability

### 6. System Traits Agreement

Read `system-traits.json`. Check that traits are consistent with the idea's archetype from `concept-anchor.json`. For example, a marketplace archetype should have traits related to multi-sided platforms, not single-user tools.

- PASS: Traits align with archetype and MVP scope
- PARTIAL: Some traits are generic and not clearly derived from the specific idea
- FAIL: Traits contradict the archetype or describe a different kind of system

## Phase 3 Checks (if Phase 3 files exist)

### 7. Architecture Serves Capabilities

Read `architecture-decisions.json` and check the `coverage_check` field. Verify that decisions reference capabilities from `capabilities.json` and that no capability is left unserved.

- PASS: All capabilities covered by at least one architecture decision
- PARTIAL: Most covered, 1-2 gaps
- FAIL: Multiple capabilities have no architecture decision serving them

### 8. Build/Buy Consistency

Read `build-buy.json`. Check that the `recommended_stack` entries are internally consistent (no conflicting technology choices, no duplicate categories with different choices).

- PASS: Stack is internally consistent, no conflicts
- PARTIAL: Minor overlap or redundancy
- FAIL: Contradictory recommendations (e.g., two different auth providers both marked BUY)

## Phase 4 Checks (if Phase 4 files exist)

### 9. Spec Coverage

Read all `specs/*/spec.md` files. Check that every CAP-F-* and CAP-NF-* from `capabilities.json` appears as a SHALL requirement in at least one spec file.

- PASS: Full coverage, every capability referenced by at least one requirement
- PARTIAL: 1-2 gaps in coverage
- FAIL: Multiple capabilities have no corresponding requirement

### 10. Cross-Reference Integrity

Read `project.md`. Check that all DEC-* IDs referenced match entries in `architecture-decisions.json`, and that `config.yaml` traits match `system-traits.json`.

- PASS: All cross-references resolve correctly
- PARTIAL: Minor inconsistencies (e.g., a trait value differs)
- FAIL: Missing decision references or major trait mismatches

## Output Format

Only include checks for phases that are present. Do not list checks for missing phases.

```
| # | Check                        | Phase | Result  | Evidence |
|---|------------------------------|-------|---------|----------|
| 1 | Concept Anchor Preservation  | 1     | PASS    | All 3 invariants reflected in report |
| 2 | Recommendation-Evidence      | 1     | PARTIAL | GO rec but report notes "strong competition" |
| ... | ... | ... | ... | ... |
```

**Phases reviewed: 1, 2** (or whichever are present)
**Score: X PASS, Y PARTIAL, Z FAIL out of N applicable checks**

### Suggested Improvements

For each PARTIAL or FAIL, state:
1. The specific inconsistency (quote both sides)
2. Which upstream file is likely the source of truth
3. Which agent prompt needs the fix, and whether it's a **missing instruction**, **weak instruction**, or **structural gap**
