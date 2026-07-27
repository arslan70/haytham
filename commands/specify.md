---
description: Run Phase 2 (WHAT) - Define MVP scope and capability model from a validated idea
argument-hint: (no arguments - uses existing Phase 1 output)
allowed-tools: Read, Write, Edit, Bash, Glob, Agent, TodoWrite
---

# Haytham: MVP Specification (Phase 2 - WHAT)

You are running Phase 2 of the Haytham validation workflow. This phase defines what the MVP includes and models its capabilities.

**IMPORTANT:** Always read agent output from files, not from conversation history.

## Progress Tracking

After prerequisites pass, call `TodoWrite` once with:

1. Step 1 — MVP scope
2. Step 2 — Scope review (founder)
3. Step 3 — Capability model
4. Step 4 — Capability review (checker)
5. Step 5 — Gate 2

Mark each todo `in_progress` when its step begins and `completed` when its output file is written or its gate decision is recorded. If the founder requests scope or capability revisions, set the relevant todo back to `in_progress` for the re-run.

## Prerequisites

Verify `.haytham/session/phase-1-why/gate-decision.json` exists. If it doesn't, tell the user:
> "Phase 1 (validation) must be completed first. Run `/haytham:validate` to start."

Read the gate decision. If the recommendation was NO-GO and the user didn't override, warn:
> "Phase 1 recommended NO-GO. Are you sure you want to proceed with MVP specification?"

## Roadmap

Before launching any agents, tell the user:

> **Phase 2: MVP Specification**
>
> This will run 5 steps:
> 1. MVP Scope — define what's in, what's out, and the core flows (~1 min)
> 2. Scope Review — you shape the scope before capabilities are derived ← YOU STEER HERE
> 3. Capability Model — extract capabilities and system traits from your approved scope (~1 min)
> 4. Capability Review — an adversarial pass hunts for gaps in the model (~1 min)
> 5. Gate 2 — you approve the final capabilities ← YOU DECIDE HERE
>
> Estimated total: ~5 minutes.

## Step 1: MVP Scope

Create `.haytham/session/phase-2-what/` directory if it doesn't exist.

Tell the user:
> **Step 1/5: MVP Scope**
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
>
> Full scope document: `.haytham/session/phase-2-what/mvp-scope.md` — review the details (boundaries, flows, success criteria) before approving.

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
> **Step 3/5: Capability Model**
> Scope approved. Now extracting the specific capabilities your MVP needs from the scope you just approved.

Read `.haytham/session/phase-2-what/mvp-scope.md` and count the number of IN SCOPE items in the MVP Boundaries table. Then launch a **capability-modeler** agent with this task:
> Read the MVP scope from `.haytham/session/phase-2-what/mvp-scope.md`, idea analysis from `.haytham/session/phase-1-why/idea-analysis.md`, and concept anchor from `.haytham/session/phase-1-why/concept-anchor.json`. The MVP scope has [N] IN SCOPE items. Produce one functional capability per distinct user-observable behavior. Simple IN SCOPE items produce one capability. Complex items (multi-step pipelines, processes with multiple distinct behaviors) produce one per behavior, each referencing the same serves_scope_item. Write to `.haytham/session/phase-2-what/capabilities.json`, `.haytham/session/phase-2-what/system-traits.json`, and `.haytham/session/phase-2-what/gate-summary.md`.

After the agent completes, read `.haytham/session/phase-2-what/capabilities.json` and `.haytham/session/phase-2-what/system-traits.json` and present a structured digest:

> **Capability model complete.**
>
> - **Functional capabilities:** [Count] — [list capability names]
> - **Non-functional capabilities:** [Count] — [list capability names]
> - **System traits:** [List key traits like auth model, data sensitivity, etc.]
> - **Traceability:** Each capability traces to [IN SCOPE items / problems from Phase 1]
>
> Full details: `.haytham/session/phase-2-what/capabilities.json` and `.haytham/session/phase-2-what/system-traits.json` — review before approving.

## Step 4: Capability Review

A generation pass reliably under-produces capabilities. This step runs an adversarial reviewer that hunts for gaps the modeler missed, before you approve at Gate 2.

Tell the user:
> **Step 4/5: Capability Review**
> Running an adversarial pass over the capability model: hunting for missing capabilities and criteria the approved scope already implies.

Track two counters across this step: CHECKER_ROUNDS (number of checker runs) and ADDITIONS_ACCEPTED (number of proposals you accepted). Maintain a REJECTED list of proposals the founder declined.

**Checker loop** (maximum 3 checker runs):

1. Launch a **capability-checker** agent with this task:
   > Read the MVP scope from `.haytham/session/phase-2-what/mvp-scope.md`, capabilities from `.haytham/session/phase-2-what/capabilities.json`, and concept anchor from `.haytham/session/phase-1-why/concept-anchor.json`. This is round [CHECKER_ROUNDS + 1]. Previously rejected proposals (do not re-propose these, even reworded): [LIST EACH REJECTED PROPOSAL'S NAME AND DESCRIPTION, or "none"]. Audit the capability model for gaps implied by the approved scope. Write findings to `.haytham/session/phase-2-what/capability-review.json`.
2. Increment CHECKER_ROUNDS. Read `.haytham/session/phase-2-what/capability-review.json`.
3. **If `proposed_additions` is empty:** tell the user:
   > **Capability review clean.** The checker found no gaps[ after N rounds]. Proceeding to Gate 2.

   Exit the loop and proceed to Step 5.
4. **If there are proposals**, present each one inline (the user must see this without expanding anything):
   > **The checker found [N] gap(s) in the capability model:**
   >
   > **1. [proposed_name]** ([gap_class], [type])
   > - Proposes: [proposed_description]
   > - Scope item it serves: "[serves_scope_item]"
   > - Implied by: "[implied_by]"
   > - Why: [rationale]
   >
   > (Repeat for each proposal.)
   >
   > Accept or reject each: reply with numbers to accept (e.g. "1, 3"), "all", or "none".
5. Add declined proposals to REJECTED. Add the count of accepted proposals to ADDITIONS_ACCEPTED.
6. **If the founder accepted any proposals**, re-launch the **capability-modeler** agent with this task:
   > Read the MVP scope from `.haytham/session/phase-2-what/mvp-scope.md`, idea analysis from `.haytham/session/phase-1-why/idea-analysis.md`, concept anchor from `.haytham/session/phase-1-why/concept-anchor.json`, and the current capabilities from `.haytham/session/phase-2-what/capabilities.json`. The founder approved these additions from an adversarial review (treat them as authoritative corrections): [PASTE EACH ACCEPTED PROPOSAL: name, description, type, serves_scope_item, and target_capability for acceptance criteria]. Integrate them into the capability model. Do not remove or alter existing capabilities beyond these additions. Write updated files to `.haytham/session/phase-2-what/capabilities.json`, `.haytham/session/phase-2-what/system-traits.json`, and `.haytham/session/phase-2-what/gate-summary.md` (the summary must reflect the additions, not the pre-review model).

   Then, if CHECKER_ROUNDS < 3, return to 1 (additions can expose new gaps — the loop stops when a run proposes nothing new or the cap is hit). If CHECKER_ROUNDS is already 3, tell the user the round cap was reached and proceed to Step 5.
7. **If the founder rejected everything**, proceed to Step 5.

## Step 5: Gate 2

Read `.haytham/session/phase-2-what/gate-summary.md` and output it inline in your response, verbatim (the user must see this without expanding anything). Do not rewrite it, summarize it further, or substitute your own digest. The agent wrote it with the full context of what it cut and what it assumed; a re-render loses that.

Then add one line pointing at the detail:
> Full details: `.haytham/session/phase-2-what/capabilities.json` and `.haytham/session/phase-2-what/system-traits.json`.

Record the exact text the founder is seeing, before asking the gate question:

```bash
shasum -a 256 .haytham/session/phase-2-what/gate-summary.md
```

Keep that digest as SUMMARY_SHA for the gate decision below.

Ask:
> **Review the capabilities. Specifically:**
> - Are the capabilities the right decomposition of the scope?
> - Are there capabilities that should be merged, split, or removed?
> - Are the non-functional requirements right for this type of product?
>
> Approve to proceed to technical design, or request changes.

**If the user requests changes:**
1. Re-launch the **capability-modeler** agent with this task:
   > Read the MVP scope from `.haytham/session/phase-2-what/mvp-scope.md`, idea analysis from `.haytham/session/phase-1-why/idea-analysis.md`, concept anchor from `.haytham/session/phase-1-why/concept-anchor.json`, and the current capabilities from `.haytham/session/phase-2-what/capabilities.json`. The user reviewed the capabilities and requested these changes: [PASTE THE USER'S EXACT CORRECTIONS HERE]. Revise the capability model to incorporate these changes. Write updated files to `.haytham/session/phase-2-what/capabilities.json`, `.haytham/session/phase-2-what/system-traits.json`, and `.haytham/session/phase-2-what/gate-summary.md`.
2. Re-render the updated `.haytham/session/phase-2-what/gate-summary.md` inline and recompute SUMMARY_SHA
3. Ask the user to review again. **Repeat until the user approves.**

**When the user approves**, write gate decision to `.haytham/session/phase-2-what/gate-decision.json`:
```json
{
  "phase": 2,
  "user_decision": "approved|rejected",
  "scope_revisions": 0,
  "capability_revisions": 0,
  "checker_rounds": 0,
  "checker_additions_accepted": 0,
  "summary_shown": ".haytham/session/phase-2-what/gate-summary.md",
  "summary_sha256": "[SUMMARY_SHA]",
  "notes": "Any user feedback",
  "decided_at": "[ISO timestamp]"
}
```

Set `scope_revisions` and `capability_revisions` to the number of times each was re-generated based on user corrections. Set `checker_rounds` to CHECKER_ROUNDS and `checker_additions_accepted` to ADDITIONS_ACCEPTED from Step 4. This tracks how much steering was needed and how much the checker caught.

Set `summary_sha256` to SUMMARY_SHA, the digest of the summary as it was rendered at the moment of approval. The approval record then names the exact text the founder read, and a later edit to the file is detectable.

Tell the user: "Phase 2 complete. Output saved to `.haytham/session/phase-2-what/` (`mvp-scope.md`, `capabilities.json`, `system-traits.json`, `gate-summary.md`). Run `/haytham:design` to proceed to Phase 3."
