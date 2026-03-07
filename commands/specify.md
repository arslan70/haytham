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

## Roadmap

Before launching any agents, tell the user:

> **Phase 2: MVP Specification**
>
> This will run 3 steps:
> 1. MVP Scope — define what's in, what's out, and the core flows (~1 min)
> 2. Capability Model — extract capabilities and system traits (~1 min)
> 3. Gate 2 — you approve the specification ← YOU DECIDE HERE
>
> Estimated total: ~3 minutes.

## Step 1: MVP Scope

Create `.haytham/session/phase-2-what/` directory if it doesn't exist.

Tell the user:
> **Step 1/3: MVP Scope**
> Translating the validated idea into a concrete MVP definition. What's in, what's out, and what the core user flow looks like.

Launch an **mvp-scoper** agent with this task:
> Read the validation report from `.haytham/session/phase-1-why/validation-report.md`, idea analysis from `.haytham/session/phase-1-why/idea-analysis.md`, and concept anchor from `.haytham/session/phase-1-why/concept-anchor.json`. Define the MVP scope. Write to `.haytham/session/phase-2-what/mvp-scope.md`.

After the agent completes, read the output and present to the user: The One Thing, IN/OUT scope table, user flows, appetite.

## Step 2: Capability Model & System Traits

Tell the user:
> Scope is set. Now extracting the specific capabilities your MVP needs and classifying system traits.

Launch a **capability-modeler** agent with this task:
> Read the MVP scope from `.haytham/session/phase-2-what/mvp-scope.md`, idea analysis, and concept anchor. Produce the capability model and system traits. Write to `.haytham/session/phase-2-what/capabilities.json` and `.haytham/session/phase-2-what/system-traits.json`.

After the agent completes, read `.haytham/session/phase-2-what/capabilities.json` and tell the user:
> Capability model complete. [One-line summary: number of functional and non-functional capabilities extracted.]

## Step 3: Gate 2

Read `.haytham/session/phase-2-what/capabilities.json` and present:
- Functional capabilities with traceability to scope items
- Non-functional capabilities
- System traits classification

Ask:
> **Review the MVP specification. Specifically:**
> - Does the IN/OUT scope match your vision?
> - Are the core capabilities right?
> - Is there anything critical missing?
>
> Approve to proceed to technical design, or request changes.

Write gate decision to `.haytham/session/phase-2-what/gate-decision.json`:
```json
{
  "phase": 2,
  "user_decision": "approved|rejected",
  "notes": "Any user feedback",
  "decided_at": "[ISO timestamp]"
}
```

Tell the user: "Phase 2 complete. Ran 2 agents across 3 steps. Run `/haytham:design` to proceed to technical design (Phase 3)."
