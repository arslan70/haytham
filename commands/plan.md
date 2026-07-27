---
description: Run Phase 4 (SPECS) - Generate implementation-ready OpenSpec
argument-hint: (no arguments - uses existing Phase 3 output)
allowed-tools: Read, Write, Edit, Bash, Glob, Agent, TodoWrite
---

# Haytham: Specification Generation (Phase 4 - SPECS)

You are running Phase 4 of the Haytham validation workflow. This phase generates an implementation-ready OpenSpec that a coding agent can use to build the system.

**IMPORTANT:** Always read agent output from files, not from conversation history.

## Progress Tracking

After prerequisites pass, call `TodoWrite` once with:

1. Step 1 — OpenSpec generation
2. Step 2 — Review
3. Step 3 — Detail review (optional drill-in)

Mark each todo `in_progress` when its step begins and `completed` when its output is produced or the founder finishes the review. Step 3 completes immediately if the founder says "looks good" without requesting a drill-in.

## Prerequisites

Verify `.haytham/session/phase-3-how/gate-decision.json` exists. If it doesn't, tell the user:
> "Phase 3 (technical design) must be completed first. Run `/haytham:design` to start."

## Roadmap

Before launching any agents, tell the user:

> **Phase 4: Specification Generation**
>
> This will run 3 steps:
> 1. OpenSpec Generation — produce SHALL requirements with Gherkin scenarios (~2 min)
> 2. Review — you review the specification
> 3. Detail Review — drill into specific domains if needed
>
> Estimated total: ~3 minutes.

## Step 1: OpenSpec Generation

Create `.haytham/session/phase-4-specs/` directory if it doesn't exist.

Tell the user:
> **Step 1/3: OpenSpec Generation**
> Turning capabilities and architecture decisions into a complete specification with SHALL requirements and testable scenarios.

Launch a **spec-generator** agent with this task:
> Read capabilities from `.haytham/session/phase-2-what/capabilities.json`, MVP scope from `.haytham/session/phase-2-what/mvp-scope.md`, system traits from `.haytham/session/phase-2-what/system-traits.json`, architecture decisions from `.haytham/session/phase-3-how/architecture-decisions.json`, build/buy analysis from `.haytham/session/phase-3-how/build-buy.json`, and concept anchor from `.haytham/session/phase-1-why/concept-anchor.json`. Generate the OpenSpec directory tree. Write to `.haytham/session/phase-4-specs/openspec/` (config.yaml, project.md, and specs/*/spec.md).

After the agent completes, run validation:
```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/validate_openspec.py" .haytham/session/phase-4-specs/openspec/ .haytham/session/phase-2-what/capabilities.json
```

If validation produces warnings, report them to the user before the digest.

Then read the generated files and present a structured digest:

> **OpenSpec generated.** Here's what was produced:
>
> - **Domains:** [count] — [list domain names]
> - **Requirements:** [count] SHALL statements across all domains
> - **Scenarios:** [count] Gherkin scenarios
> - **Architecture decisions:** [count] documented in project.md
> - **Coverage:** All [N] functional + [M] non-functional capabilities covered
>
> Full details: `.haytham/session/phase-4-specs/openspec/` — review before approving.

## Step 2: Review

Read the OpenSpec files and output the following inline in your response (the user must see this without expanding anything):

- **Domains**: List each domain with its requirement count
- **Coverage Check**: All capabilities (CAP-*) and decisions (DEC-*) covered
- **System Traits**: config.yaml traits summary
- **Architecture**: Key decisions from project.md

For each domain, show a summary:
```
specs/{domain-slug}/ — [N] requirements
  [CAP-ID] {Requirement title} — [M] scenarios
```

## Step 3: Detail Review

Ask:
> **Your specification is ready.**
> Would you like to drill into any specific domains? Enter domain names (e.g., user-authentication, leaderboard-management), or say "looks good" to finish.

If the user requests specific domains, read the corresponding `specs/{domain}/spec.md` and output the full content inline in your response.

## Completion

Summarize the full specification:

```
Haytham Specification Complete

Phase 1 (WHY): .haytham/session/phase-1-why/
  - validation-report.md - Full validation report
  - validation-report.json - Structured recommendation
  - concept-anchor.json - Idea invariants

Phase 2 (WHAT): .haytham/session/phase-2-what/
  - mvp-scope.md - MVP scope and boundaries
  - capabilities.json - Capability model
  - system-traits.json - System classification
  - gate-summary.md - What you approved at Gate 2

Phase 3 (HOW): .haytham/session/phase-3-how/
  - build-buy.json - Infrastructure decisions
  - architecture-decisions.json - Architecture choices
  - research-directives.json - Pre-implementation research questions
  - gate-summary.md - What you approved at Gate 3

Phase 4 (SPECS): .haytham/session/phase-4-specs/openspec/
  - config.yaml - Project metadata and system traits
  - project.md - Tech stack, architecture decisions, build/buy
  - specs/*/spec.md - Domain requirements with Gherkin scenarios
  - specs/cross-cutting/spec.md - Non-functional requirements
```

Tell the user:

> **Your specification is ready.** Ran 1 agent across 3 steps. Output saved to `.haytham/session/phase-4-specs/openspec/`.
>
> **Next:** Run `/haytham:build` to set up your project for implementation with OpenSpec.
