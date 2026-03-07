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
6. `.haytham/session/phase-4-stories/stories.json`
7. `.haytham/session/phase-4-stories/execution-contract.json`

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

### 5. Story Completeness

Read `stories.json`. For each story, check whether it has enough detail for a developer to start work.

Evaluate a random sample of 3-5 stories. Each story should have:
- A clear description of what to build
- Acceptance criteria that are testable (not "works correctly" but "returns 200 with user object when valid token provided")
- Dependencies that make sense (doesn't depend on unrelated stories)

- PASS: Sampled stories all have clear descriptions, testable acceptance criteria, and sensible dependencies
- PARTIAL: Some stories are well-specified, others have vague acceptance criteria or missing detail
- FAIL: Most stories are high-level placeholders without testable acceptance criteria

### 6. Acceptance Criteria Testability

Across the sampled stories, are acceptance criteria written as verifiable conditions?

- PASS: Criteria use concrete, testable language ("user sees error message when password is under 8 characters")
- PARTIAL: Mix of testable and vague criteria ("system handles errors gracefully")
- FAIL: Criteria are subjective or untestable ("good user experience", "performant")

### 7. Dependency Chain Viability

Read `execution-contract.json`. Does the dependency ordering make practical sense? Could a developer follow Layer 0 → Layer 1 → ... and build the system incrementally?

- PASS: Layer 0 stories set up foundations (infra, auth, data models), subsequent layers build on them logically
- PARTIAL: Ordering is mostly sensible but some stories seem misplaced (a UI story before its API dependency)
- FAIL: Ordering is illogical, or layers have circular-feeling dependencies that would require parallel development

### 8. Appetite Compliance

Read `execution-contract.json` metadata. Is the total story count reasonable for the stated appetite in `mvp-scope.md`?

- PASS: Story count is within or near the appetite constraint, and stories are right-sized
- PARTIAL: Slightly over appetite but stories are reasonable in scope
- FAIL: Significantly over appetite (a 6-week appetite with 40+ stories), or stories are so large they're epics in disguise

## Output Format

```
| # | Criterion                  | Result  | Evidence |
|---|----------------------------|---------|----------|
| 1 | Scope Clarity              | PASS    | The One Thing: "Anonymous gym leaderboard..." IN/OUT items are feature-specific |
| 2 | User Flow Specificity      | PARTIAL | Flow 1 has steps, Flow 2 just says "admin manages content" |
| ... | ... | ... | ... |
```

**Score: X/8 PASS, Y/8 PARTIAL, Z/8 FAIL**

### Stories Sampled

List which stories you evaluated for criteria 5-6:
> Reviewed: STORY-001, STORY-004, STORY-007, STORY-012

### Suggested Improvements

For each PARTIAL or FAIL, state:
1. What was observed (quote the output)
2. What a developer would need to know that's missing
3. Which agent prompt needs the fix (`agents/mvp-scoper.md`, `agents/capability-modeler.md`, `agents/architect.md`, or `agents/story-planner.md`)
4. Whether it's a **missing instruction**, **weak instruction**, or **structural gap**
