---
description: Run Phase 4 (STORIES) - Generate implementation-ready stories with dependency ordering
argument-hint: (no arguments - uses existing Phase 3 output)
allowed-tools: Read, Write, Edit, Bash, Glob, Agent
---

# Haytham: Story Planning (Phase 4 - STORIES)

You are running Phase 4 of the Haytham validation workflow. This phase generates implementation-ready stories with full detail specs and dependency ordering.

**IMPORTANT:** Always read agent output from files, not from conversation history.

## Prerequisites

Verify `.haytham/session/phase-3-how/gate-decision.json` exists. If it doesn't, tell the user:
> "Phase 3 (technical design) must be completed first. Run `/haytham:design` to start."

## Roadmap

Before launching any agents, tell the user:

> **Phase 4: Implementation Plan**
>
> This will run 3 steps:
> 1. Story Planning — generate stories with dependencies and acceptance criteria (~2 min)
> 2. Review — you review the implementation plan
> 3. Detail Review — drill into specific stories if needed
>
> Estimated total: ~3 minutes.

## Step 1: Story Planning

Create `.haytham/session/phase-4-stories/` directory if it doesn't exist.

Tell the user:
> **Step 1/3: Story Planning**
> Turning capabilities and architecture decisions into implementation-ready stories with dependencies.

Launch a **story-planner** agent with this task:
> Read capabilities from `.haytham/session/phase-2-what/capabilities.json`, MVP scope from `.haytham/session/phase-2-what/mvp-scope.md`, system traits from `.haytham/session/phase-2-what/system-traits.json`, architecture decisions from `.haytham/session/phase-3-how/architecture-decisions.json`, build/buy analysis from `.haytham/session/phase-3-how/build-buy.json`, and concept anchor from `.haytham/session/phase-1-why/concept-anchor.json`. Generate story skeletons, detail specs, and the execution contract. Write to `.haytham/session/phase-4-stories/stories.json` and `.haytham/session/phase-4-stories/execution-contract.json`.

After the agent completes, read `.haytham/session/phase-4-stories/execution-contract.json` and tell the user:
> Story planning complete. [One-line summary: total story count and layer breakdown.]

## Step 2: Review

Read `.haytham/session/phase-4-stories/execution-contract.json` and present:

- **Story Count**: Total stories and breakdown by layer
- **Appetite Compliance**: Whether story count fits within the appetite constraint
- **Dependency Graph**: Which stories depend on which (show as a readable list)
- **Coverage Check**: All capabilities (CAP-*) and decisions (DEC-*) covered
- **Layer Distribution**: How many stories per layer

For each story, show a one-line summary:
```
[STORY-ID] (Layer N) [Title] - implements [CAP/DEC references]
  depends on: [dependencies or "none"]
```

## Step 3: Detail Review

Ask:
> **Your implementation plan is ready.**
> Would you like to drill into any specific stories? Enter story IDs (e.g., STORY-001, STORY-005), or say "looks good" to finish.

If the user requests specific stories, read them from `.haytham/session/phase-4-stories/stories.json` and present the full detail spec.

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

Phase 3 (HOW): .haytham/session/phase-3-how/
  - build-buy.json - Infrastructure decisions
  - architecture-decisions.json - Architecture choices

Phase 4 (STORIES): .haytham/session/phase-4-stories/
  - stories.json - All stories with detail specs
  - execution-contract.json - Implementation contract
```

Tell the user: "Your implementation plan is ready. Ran 1 agent across 3 steps. Stories are ordered by dependency and can be implemented sequentially starting from Layer 0."
