---
description: Run Phase 3 (HOW) - Produce build/buy analysis and architecture decisions
argument-hint: (no arguments - uses existing Phase 2 output)
---

# Haytham: Technical Design (Phase 3 - HOW)

You are running Phase 3 of the Haytham validation workflow. This phase decides on infrastructure and architecture.

**IMPORTANT:** Always read agent output from files, not from conversation history.

## Prerequisites

Verify `.haytham/session/phase-2-what/gate-decision.json` exists. If it doesn't, tell the user:
> "Phase 2 (MVP specification) must be completed first. Run `/haytham:specify` to start."

## Step 1: Architecture

Create `.haytham/session/phase-3-how/` directory if it doesn't exist.

Launch an **architect** agent with this task:
> Read capabilities from `.haytham/session/phase-2-what/capabilities.json`, MVP scope from `.haytham/session/phase-2-what/mvp-scope.md`, and system traits from `.haytham/session/phase-2-what/system-traits.json`. Produce build/buy analysis and architecture decisions. Write to `.haytham/session/phase-3-how/build-buy.json` and `.haytham/session/phase-3-how/architecture-decisions.json`.

## Step 2: Review

Read both output files and present to the user:
- **Recommended Stack**: Service name, category, BUILD/BUY/HYBRID, rationale
- **Architecture Decisions**: ID, name, what it covers, capabilities served
- **Integration Effort**: Estimated days
- **Monthly Cost**: Estimated range

## Step 3: Gate 3

Ask: **"Do you approve this technical design? Ready to proceed to story planning?"**

Write gate decision to `.haytham/session/phase-3-how/gate-decision.json`:
```json
{
  "phase": 3,
  "user_decision": "approved|rejected",
  "notes": "Any user feedback",
  "decided_at": "[ISO timestamp]"
}
```

Tell the user: "Phase 3 complete. Run `/haytham:plan` to proceed to story planning (Phase 4)."
