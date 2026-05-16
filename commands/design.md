---
description: Run Phase 3 (HOW) - Produce build/buy analysis and architecture decisions
argument-hint: (no arguments - uses existing Phase 2 output)
allowed-tools: Read, Write, Edit, Bash, Glob, Agent, TodoWrite, WebSearch, WebFetch
---

# Haytham: Technical Design (Phase 3 - HOW)

You are running Phase 3 of the Haytham validation workflow. This phase decides on infrastructure and architecture.

**IMPORTANT:** Always read agent output from files, not from conversation history.

## Progress Tracking

After prerequisites pass, call `TodoWrite` once with:

1. Step 1 — Architecture (build/buy, decisions, research directives)
2. Step 2 — Review
3. Step 3 — Gate 3

Mark each todo `in_progress` when its step begins and `completed` when its output file is written or its gate decision is recorded.

## Prerequisites

Verify `.haytham/session/phase-2-what/gate-decision.json` exists. If it doesn't, tell the user:
> "Phase 2 (MVP specification) must be completed first. Run `/haytham:specify` to start."

## Roadmap

Before launching any agents, tell the user:

> **Phase 3: Technical Design**
>
> This will run 3 steps:
> 1. Architecture — build/buy analysis and technology decisions (~2 min)
> 2. Review — you review the architecture
> 3. Gate 3 — you approve the design ← YOU DECIDE HERE
>
> Estimated total: ~3 minutes.

## Step 1: Architecture

Create `.haytham/session/phase-3-how/` directory if it doesn't exist.

Tell the user:
> **Step 1/3: Architecture**
> Deciding what to build, what to buy, and how the pieces fit together.

Launch an **architect** agent with this task:
> Read capabilities from `.haytham/session/phase-2-what/capabilities.json`, MVP scope from `.haytham/session/phase-2-what/mvp-scope.md`, and system traits from `.haytham/session/phase-2-what/system-traits.json`. Produce build/buy analysis, architecture decisions, and research directives. Write to `.haytham/session/phase-3-how/build-buy.json`, `.haytham/session/phase-3-how/architecture-decisions.json`, and `.haytham/session/phase-3-how/research-directives.json`.

After the agent completes, read `.haytham/session/phase-3-how/build-buy.json`, `.haytham/session/phase-3-how/architecture-decisions.json`, and `.haytham/session/phase-3-how/research-directives.json` and present a structured digest:

> **Architecture designed.** Here's the technical plan:
>
> - **Stack:** [Key technologies chosen]
> - **Build vs Buy:** [Summary of what's built custom vs. third-party services]
> - **Key decisions:** [List the 2-3 most important architecture decisions]
> - **Research directives:** [N] capabilities flagged ([list classifications used])
> - **Estimated monthly cost:** [Cost range]
> - **Integration effort:** [Effort estimate]
>
> Full details: `.haytham/session/phase-3-how/build-buy.json`, `.haytham/session/phase-3-how/architecture-decisions.json`, and `.haytham/session/phase-3-how/research-directives.json` — review before approving.

## Step 2: Review

Read all three output files and output the following inline in your response (the user must see this without expanding anything):
- **Recommended Stack**: Service name, category, BUILD/BUY/HYBRID, rationale
- **Architecture Decisions**: ID, name, what it covers, capabilities served
- **Research Directives:** [N] of [M] capabilities require pre-implementation research
  - CAP-F-NNN (Capability Name): classification(s) — N findings resolved, N questions remaining
  - (Repeat for each non-standard capability)
- **Integration Effort**: Estimated days
- **Monthly Cost**: Estimated range

## Step 3: Gate 3

Ask:
> **Review the technical design. Specifically:**
> - Does the technology stack fit your team's skills?
> - Are the build/buy decisions reasonable?
> - Is the estimated cost acceptable?
>
> Approve to proceed to specification generation, or request changes.

Write gate decision to `.haytham/session/phase-3-how/gate-decision.json`:
```json
{
  "phase": 3,
  "user_decision": "approved|rejected",
  "notes": "Any user feedback",
  "decided_at": "[ISO timestamp]"
}
```

Tell the user: "Phase 3 complete. Ran 1 agent across 3 steps. Output saved to `.haytham/session/phase-3-how/` (`build-buy.json`, `architecture-decisions.json`, `research-directives.json`). Run `/haytham:plan` to proceed to Phase 4."
