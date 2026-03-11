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
> This will run 4 steps:
> 1. MVP Scope — define what's in, what's out, and the core flows (~1 min)
> 2. Scope Review — you shape the scope before capabilities are derived ← YOU STEER HERE
> 3. Capability Model — extract capabilities and system traits from your approved scope (~1 min)
> 4. Gate 2 — you approve the final capabilities ← YOU DECIDE HERE
>
> Estimated total: ~4 minutes.

## Step 1: MVP Scope

Create `.haytham/session/phase-2-what/` directory if it doesn't exist.

Tell the user:
> **Step 1/4: MVP Scope**
> Translating the validated idea into a concrete MVP definition. What's in, what's out, and what the core user flow looks like.

Launch an **mvp-scoper** agent with this task:
> Read the validation report from `.haytham/session/phase-1-why/validation-report.md`, idea analysis from `.haytham/session/phase-1-why/idea-analysis.md`, and concept anchor from `.haytham/session/phase-1-why/concept-anchor.json`. Define the MVP scope. Write to `.haytham/session/phase-2-what/mvp-scope.md`.

After the agent completes, read `.haytham/session/phase-2-what/mvp-scope.md` and present a structured digest:

> **MVP scope defined.** Here's the shape of your MVP:
>
> - **The One Thing:** [The single sentence MVP purpose]
> - **IN scope:** [List the key items that are in]
> - **OUT scope:** [List the key items explicitly excluded]
> - **Appetite:** [Time/effort budget]
> - **Core flow:** [One-line description of the primary user journey]

## Step 2: Scope Review

This is a refinement loop. The user must approve the scope BEFORE capabilities are derived from it.

Ask:
> **Review the MVP scope above. Specifically:**
> - Is "The One Thing" right? Does it capture what matters?
> - Are the IN/OUT scope boundaries correct?
> - Is the appetite realistic?
> - Are the core flows right?
>
> Say "looks good" to proceed to capability extraction, or tell me what to change.

**If the user requests changes:**
1. Re-launch the **mvp-scoper** agent with this task:
   > Read the current MVP scope from `.haytham/session/phase-2-what/mvp-scope.md`, the validation report from `.haytham/session/phase-1-why/validation-report.md`, idea analysis from `.haytham/session/phase-1-why/idea-analysis.md`, and concept anchor from `.haytham/session/phase-1-why/concept-anchor.json`. The user reviewed the scope and requested these changes: [PASTE THE USER'S EXACT CORRECTIONS HERE]. Revise the MVP scope to incorporate these changes. Write the updated scope to `.haytham/session/phase-2-what/mvp-scope.md`.
2. Read the updated `.haytham/session/phase-2-what/mvp-scope.md` and present the revised digest
3. Ask the user to review again. **Repeat until the user approves.**

**If the user approves:** Proceed to Step 3.

## Step 3: Capability Model & System Traits

Tell the user:
> **Step 3/4: Capability Model**
> Scope approved. Now extracting the specific capabilities your MVP needs from the scope you just approved.

Read `.haytham/session/phase-2-what/mvp-scope.md` and count the number of IN SCOPE items in the MVP Boundaries table. Then launch a **capability-modeler** agent with this task:
> Read the MVP scope from `.haytham/session/phase-2-what/mvp-scope.md`, idea analysis from `.haytham/session/phase-1-why/idea-analysis.md`, and concept anchor from `.haytham/session/phase-1-why/concept-anchor.json`. The MVP scope has [N] IN SCOPE items. Produce exactly one functional capability per IN SCOPE item. Write to `.haytham/session/phase-2-what/capabilities.json` and `.haytham/session/phase-2-what/system-traits.json`.

After the agent completes, read `.haytham/session/phase-2-what/capabilities.json` and `.haytham/session/phase-2-what/system-traits.json` and present a structured digest:

> **Capability model complete.**
>
> - **Functional capabilities:** [Count] — [list capability names]
> - **Non-functional capabilities:** [Count] — [list capability names]
> - **System traits:** [List key traits like auth model, data sensitivity, etc.]
> - **Traceability:** Each capability traces to [IN SCOPE items / problems from Phase 1]

## Step 4: Gate 2

Read `.haytham/session/phase-2-what/capabilities.json` and output the following inline in your response (the user must see this without expanding anything):
- Functional capabilities with traceability to scope items
- Non-functional capabilities
- System traits classification

Ask:
> **Review the capabilities. Specifically:**
> - Are the capabilities the right decomposition of the scope?
> - Are there capabilities that should be merged, split, or removed?
> - Are the non-functional requirements right for this type of product?
>
> Approve to proceed to technical design, or request changes.

**If the user requests changes:**
1. Re-launch the **capability-modeler** agent with this task:
   > Read the MVP scope from `.haytham/session/phase-2-what/mvp-scope.md`, idea analysis from `.haytham/session/phase-1-why/idea-analysis.md`, concept anchor from `.haytham/session/phase-1-why/concept-anchor.json`, and the current capabilities from `.haytham/session/phase-2-what/capabilities.json`. The user reviewed the capabilities and requested these changes: [PASTE THE USER'S EXACT CORRECTIONS HERE]. Revise the capability model to incorporate these changes. Write updated files to `.haytham/session/phase-2-what/capabilities.json` and `.haytham/session/phase-2-what/system-traits.json`.
2. Read the updated files and present the revised digest
3. Ask the user to review again. **Repeat until the user approves.**

**When the user approves**, write gate decision to `.haytham/session/phase-2-what/gate-decision.json`:
```json
{
  "phase": 2,
  "user_decision": "approved|rejected",
  "scope_revisions": 0,
  "capability_revisions": 0,
  "notes": "Any user feedback",
  "decided_at": "[ISO timestamp]"
}
```

Set `scope_revisions` and `capability_revisions` to the number of times each was re-generated based on user corrections. This tracks how much steering was needed.

Tell the user: "Phase 2 complete. Output saved to `.haytham/session/phase-2-what/`. Run `/haytham:design` to proceed to Phase 3."
