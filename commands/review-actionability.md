---
description: Review whether the specification is detailed enough to implement
argument-hint: (no arguments - reads from .haytham/session/)
allowed-tools: Read, Glob
---

# Haytham: Specification Actionability Review

You are reviewing whether the output specification is detailed enough for a developer to start building. A specification that reads well but can't be implemented without major assumptions is not actionable.

## Prerequisites

This review requires Phases 2-4 to be complete. Before evaluating anything, verify ALL of the following files exist by reading each one.

**Required:**
1. `.haytham/session/phase-2-what/mvp-scope.md`
2. `.haytham/session/phase-2-what/capabilities.json`
3. `.haytham/session/phase-2-what/system-traits.json`
4. `.haytham/session/phase-3-how/build-buy.json`
5. `.haytham/session/phase-3-how/architecture-decisions.json`
6. `.haytham/session/phase-4-specs/openspec/config.yaml`
7. `.haytham/session/phase-4-specs/openspec/project.md`

If any file is missing, stop and tell the user exactly which files are missing:
> "Cannot run actionability review. Missing: [list files]. This review requires a complete run through Phase 4. Run the missing phases first:
> - Phase 2: `/haytham:specify`
> - Phase 3: `/haytham:design`
> - Phase 4: `/haytham:plan`"

Do NOT proceed past this point if any file is missing. Do NOT guess what the content might be.

## Evaluation

Read all seven files. Evaluate the following criteria.

### 1. Scope Clarity

Read `mvp-scope.md`. Can a developer read The One Thing and the IN/OUT table and know unambiguously what to build and what not to build?

- PASS: The One Thing is a single clear sentence. IN/OUT items are specific enough to make decisions against ("User profile pages" not "user management")
- PARTIAL: The One Thing is clear but some IN/OUT items are vague categories rather than specific features
- FAIL: The One Thing is abstract, or IN/OUT items are so vague that a developer would need to make significant interpretation calls

### 2. User Flow Specificity

Read user flows in `mvp-scope.md`. Does each flow describe concrete steps a user takes, or just name the flow?

- PASS: Flows describe step-by-step user actions with entry point, key interactions, and end state
- PARTIAL: Flows describe the general purpose but steps are vague ("user interacts with the feature")
- FAIL: Flows are just names ("onboarding flow", "main flow") with no step detail

### 3. Capability Precision

Read `capabilities.json`. Are functional capabilities specific enough to implement, or would a developer need to make major design decisions?

- PASS: Each capability describes a specific behavior with clear inputs and outputs or user-visible result
- PARTIAL: Most capabilities are specific, but some are high-level categories ("manage content") rather than behaviors
- FAIL: Capabilities are abstract categories that could mean many different things

### 4. Architecture Specificity

Read `architecture-decisions.json` and `build-buy.json`. Are technology choices named (specific services, frameworks, libraries), or just categories?

- PASS: Named technologies with rationale tied to specific capabilities (e.g., "Supabase for auth because CAP-001 requires social login")
- PARTIAL: Named technologies but rationale is generic ("industry standard", "popular choice")
- FAIL: Only categories named ("a database", "an auth provider") with no specific technology selected

### 5. SHALL Precision

Statements use bare infinitive verbs, are specific (not vague "manage content"), and are individually testable.

- PASS: All SHALL statements are specific, use bare infinitive verbs, and describe a single testable behavior
- PARTIAL: Most are specific, but some are vague categories rather than testable behaviors
- FAIL: Statements are generic or use third-person verb forms

### 6. Scenario Completeness

Every requirement has at least one happy-path and one error/edge-case scenario. Scenarios use concrete values, not placeholders.

- PASS: Every requirement has happy-path and error scenarios with concrete values
- PARTIAL: Some requirements missing error scenarios, or scenarios use placeholder values
- FAIL: Most requirements have only a single generic scenario

### 7. Architecture Completeness

`project.md` covers all DEC-* decisions with rationale. Build/Buy table is complete. Dependencies list is specific (named packages with versions).

- PASS: All decisions documented with rationale, dependencies are specific
- PARTIAL: Some decisions lack rationale or dependencies are vague
- FAIL: Major gaps in architecture documentation

### 8. Agent Readability

A coding agent can pick up `openspec/` and start implementing without ambiguity. `config.yaml` provides enough context to bootstrap the project. Spec files are self-contained per domain.

- PASS: A coding agent could start implementing from the spec alone
- PARTIAL: Some cross-domain dependencies are unclear or config is incomplete
- FAIL: Significant ambiguity that would require human clarification

## Output Format

```
| # | Criterion                  | Result  | Evidence |
|---|----------------------------|---------|----------|
| 1 | Scope Clarity              | PASS    | The One Thing: "Anonymous gym leaderboard..." IN/OUT items are feature-specific |
| 2 | User Flow Specificity      | PARTIAL | Flow 1 has steps, Flow 2 just says "admin manages content" |
| ... | ... | ... | ... |
```

**Score: X/8 PASS, Y/8 PARTIAL, Z/8 FAIL**

### Domains Reviewed

List which domain specs were evaluated:
> Reviewed: specs/identity/spec.md, specs/leaderboard/spec.md, specs/community/spec.md

### Suggested Improvements

For each PARTIAL or FAIL, state:
1. What was observed (quote the output)
2. What a developer would need to know that's missing
3. Which agent prompt needs the fix (`agents/mvp-scoper.md`, `agents/capability-modeler.md`, `agents/architect.md`, or `agents/spec-generator.md`)
4. Whether it's a **missing instruction**, **weak instruction**, or **structural gap**
