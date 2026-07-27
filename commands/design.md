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
> Read capabilities from `.haytham/session/phase-2-what/capabilities.json`, MVP scope from `.haytham/session/phase-2-what/mvp-scope.md`, and system traits from `.haytham/session/phase-2-what/system-traits.json`. Produce build/buy analysis, architecture decisions, research directives, and the founder-facing gate summary. Write to `.haytham/session/phase-3-how/build-buy.json`, `.haytham/session/phase-3-how/architecture-decisions.json`, `.haytham/session/phase-3-how/research-directives.json`, and `.haytham/session/phase-3-how/gate-summary.md`.

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

Read `.haytham/session/phase-3-how/gate-summary.md` and output it inline in your response, verbatim (the user must see this without expanding anything). Do not rewrite it, summarize it further, or substitute your own digest. The agent wrote it knowing which alternatives it rejected and which unknowns remain; a re-render loses that.

Then add one line pointing at the detail:
> Full details: `.haytham/session/phase-3-how/build-buy.json`, `.haytham/session/phase-3-how/architecture-decisions.json`, and `.haytham/session/phase-3-how/research-directives.json`.

Record the exact text the founder is seeing, before asking the gate question:

```bash
shasum -a 256 .haytham/session/phase-3-how/gate-summary.md
```

Keep that digest as SUMMARY_SHA for the gate decision below.

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
  "summary_shown": ".haytham/session/phase-3-how/gate-summary.md",
  "summary_sha256": "[SUMMARY_SHA]",
  "notes": "Any user feedback",
  "decided_at": "[ISO timestamp]"
}
```

Set `summary_sha256` to SUMMARY_SHA, the digest of the summary as it was rendered at the moment of approval. The approval record then names the exact text the founder read, and a later edit to the file is detectable.

Tell the user: "Phase 3 complete. Ran 1 agent across 3 steps. Output saved to `.haytham/session/phase-3-how/` (`build-buy.json`, `architecture-decisions.json`, `research-directives.json`, `gate-summary.md`). Run `/haytham:plan` to proceed to Phase 4."
