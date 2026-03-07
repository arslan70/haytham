---
description: Run Phase 2 (WHAT) - Define MVP scope and capability model from a validated idea
argument-hint: (no arguments - uses existing Phase 1 output)
allowed-tools: Read, Write, Edit, Bash, Glob, Agent
---

# Haytham: MVP Specification (Phase 2 - WHAT)

You are running Phase 2 of the Haytham validation workflow. This phase defines what the MVP includes and models its capabilities.

**IMPORTANT:** Always read agent output from files, not from conversation history.

## Prerequisites

Verify `.haytham/session/phase-1-why/gate-decision.json` exists. If it doesn't, tell the user:
> "Phase 1 (validation) must be completed first. Run `/haytham:validate` to start."

Read the gate decision. If the recommendation was NO-GO and the user didn't override, warn:
> "Phase 1 recommended NO-GO. Are you sure you want to proceed with MVP specification?"

## Step 1: MVP Scope

Create `.haytham/session/phase-2-what/` directory if it doesn't exist.

Launch an **mvp-scoper** agent with this task:
> Read the validation report from `.haytham/session/phase-1-why/validation-report.md`, idea analysis from `.haytham/session/phase-1-why/idea-analysis.md`, and concept anchor from `.haytham/session/phase-1-why/concept-anchor.json`. Define the MVP scope. Write to `.haytham/session/phase-2-what/mvp-scope.md`.

Read the output and present to the user: The One Thing, IN/OUT scope table, user flows, appetite.

## Step 2: Capability Model & System Traits

Launch a **capability-modeler** agent with this task:
> Read the MVP scope from `.haytham/session/phase-2-what/mvp-scope.md`, idea analysis, and concept anchor. Produce the capability model and system traits. Write to `.haytham/session/phase-2-what/capabilities.json` and `.haytham/session/phase-2-what/system-traits.json`.

## Step 3: Gate 2

Read `.haytham/session/phase-2-what/capabilities.json` and present:
- Functional capabilities with traceability to scope items
- Non-functional capabilities
- System traits classification

Ask: **"Do you approve this MVP specification? Ready to proceed to technical design?"**

Write gate decision to `.haytham/session/phase-2-what/gate-decision.json`:
```json
{
  "phase": 2,
  "user_decision": "approved|rejected",
  "notes": "Any user feedback",
  "decided_at": "[ISO timestamp]"
}
```

Tell the user: "Phase 2 complete. Run `/haytham:design` to proceed to technical design (Phase 3)."
