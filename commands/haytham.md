---
description: Validate a startup idea and produce an implementation-ready specification
argument-hint: [startup idea]
allowed-tools: Read, Write, Edit, Bash, Glob, Agent, WebSearch, WebFetch
---

# Haytham: Startup Idea Validation & Specification

You are orchestrating a 4-phase startup validation workflow. Follow each phase in order. Do not skip phases. Do not proceed to the next phase without user approval at the gate.

**IMPORTANT:** Always read agent output from files, not from conversation history. Before each phase, verify previous phase output files exist by reading them.

## Upstream Dependencies

| Phase | Agent | Reads From |
|-------|-------|------------|
| 1 | idea-analyst | `.haytham/project.yaml` (user input) |
| 1 | market-researcher | `phase-1-why/idea-analysis.md`, `phase-1-why/concept-anchor.json` |
| 1 | research-briefer | `phase-1-why/idea-analysis.md`, `phase-1-why/market-research.md` |
| 1 | report-synthesizer | `phase-1-why/research-brief.md`, `phase-1-why/concept-anchor.json`, `phase-1-why/founder-corrections.json` (if exists) |
| 2 | mvp-scoper | `phase-1-why/validation-report.md`, `phase-1-why/idea-analysis.md`, `phase-1-why/concept-anchor.json` |
| 2 | capability-modeler | `phase-2-what/mvp-scope.md`, `phase-1-why/idea-analysis.md`, `phase-1-why/concept-anchor.json` |
| 3 | architect | `phase-2-what/capabilities.json`, `phase-2-what/system-traits.json`, `phase-2-what/mvp-scope.md` |
| 4 | spec-generator | `phase-2-what/capabilities.json`, `phase-2-what/mvp-scope.md`, `phase-2-what/system-traits.json`, `phase-3-how/architecture-decisions.json`, `phase-3-how/build-buy.json`, `phase-1-why/concept-anchor.json` |

All paths relative to `.haytham/session/`.

## Setup

1. Create `.haytham/` directory if it doesn't exist
2. Create `.haytham/session/phase-1-why/`, `.haytham/session/phase-2-what/`, `.haytham/session/phase-3-how/`, `.haytham/session/phase-4-specs/` directories
3. Write the user's startup idea to `.haytham/project.yaml`:
   ```yaml
   idea: |
     [The user's startup idea exactly as provided]
   created_at: [current ISO timestamp]
   state:
     phase_1:
       last_completed_step: 0
       updated_at: [current ISO timestamp]
   ```

## State Updates

After each step completes successfully, update `.haytham/project.yaml` to set the appropriate `state.phase_N.last_completed_step` and `updated_at`. Use the Edit tool to update only the state section.

---

## Phase 1: WHY (Idea Validation)

**Goal:** Understand the idea, research the market, and produce a GO/PIVOT/NO-GO recommendation.

Before launching any agents, read `${CLAUDE_PLUGIN_ROOT}/.claude-plugin/marketplace.json` and extract the `version` field from `plugins[0]`. Then tell the user (replacing VERSION with the actual version string you just read):

> **Phase 1: Idea Validation** (haytham vVERSION)
>
> This will run 6 steps:
> 1. Idea Analysis — expand and classify your idea (~1 min)
> 2. Market Research — web search for competitors, sizing, sentiment (~3 min)
> 3. Research Brief — neutral summary of findings (~1 min)
> 4. Founder Review — you review and correct ← YOU DECIDE HERE
> 5. Validation Report — GO/PIVOT/NO-GO analysis (~1 min)
> 6. Gate Decision — you approve or reject
>
> Step 2 is the heaviest step (runs web searches). Estimated total: ~7 minutes.

### Step 1: Idea Analysis

Tell the user:
> **Step 1/6: Idea Analysis**
> Expanding your idea into a structured concept so we have a clear foundation for research.

Launch an **idea-analyst** agent with this task:
> Read the startup idea from `.haytham/project.yaml`. Analyze it following your instructions. Write idea analysis to `.haytham/session/phase-1-why/idea-analysis.md` and concept anchor to `.haytham/session/phase-1-why/concept-anchor.json`.

If the agent writes `.haytham/session/phase-1-why/idea-clarification.md`, read it and present the clarification questions or suggestions to the user. Wait for their response, update `.haytham/project.yaml` with the refined idea, and re-run Step 1.

After the agent completes, read `.haytham/session/phase-1-why/idea-analysis.md` and `.haytham/session/phase-1-why/concept-anchor.json`. Present a structured digest:

> **Step 1 complete.** We analyzed your idea and saved two files:
> - `idea-analysis.md` — problem analysis, target segments, UVP, and concept health
> - `concept-anchor.json` — invariants that keep downstream agents faithful to your idea
>
> Here's the summary:
>
> - **Core concept:** [One-line summary of what this product does]
> - **Top problems:**
>   a. [Problem 1] (Pain: [intensity])
>   b. [Problem 2] (Pain: [intensity])
>   c. [Problem 3] (Pain: [intensity])
> - **Primary segment:** [The primary user segment and their defining behavior]
> - **UVP:** [The unique value proposition as written]
> - **Concept health:** Pain Clarity: [X], Trigger Strength: [X], WTP Signal: [X]

Then read `strategic_signals` and `founder_profile` from `concept-anchor.json` and present them:

> **Strategic assumptions** (inferred from your idea, correct anything wrong):
> - **Founder profile:** [technical_level] ([inference_basis])
> - **Business model:** [business_model]
> - **Success metric:** [success_metric]
> - **Competitive stance:** [competitive_stance]
> - **Distribution:** [distribution]
>
> **What next?**
> 1. Looks good, continue to market research
> 2. I need to correct some assumptions (say which ones and what they should be)
> 3. I want to steer research toward specific competitors or topics

If the user corrects any strategic signals, update `concept-anchor.json` using the Edit tool to reflect their corrections before proceeding.

Update state: `last_completed_step: 1`.

### Step 2: Market Research

Read `.haytham/session/phase-1-why/idea-analysis.md` to confirm it exists. Extract the domain/category.

Tell the user:
> **Step 2/6: Market Research**
> Checking if anyone else is solving this, and how big the opportunity is. Searching for competitors, market sizing, and user sentiment in [domain from idea analysis].
> This is the longest step (~3 min) because it runs web searches.

Launch a **market-researcher** agent with this task:
> Read the idea analysis from `.haytham/session/phase-1-why/idea-analysis.md` and concept anchor from `.haytham/session/phase-1-why/concept-anchor.json`. Research the market and competitors. Write results to `.haytham/session/phase-1-why/market-research.md`.

After the agent completes, read `.haytham/session/phase-1-why/market-research.md` and present a structured digest:

> **Market research complete.** Here's what we found:
>
> - **Market:** [Primary category], TAM: [X], SAM: [X], SOM: [X]
> - **Competitors:** [List each competitor name + one-line description]
> - **User sentiment:** [One key "love" and one key "hate" quote from real users]
> - **Key gap:** [The most significant gap or unmet need found]
> - **Top risk:** [The biggest market-structural risk or challenge]

Update state: `last_completed_step: 2`.

### Step 3: Research Brief

Tell the user:
> Research gathered. Compiling a neutral summary for your review. No scores or judgments, just facts.

Launch a **research-briefer** agent with this task:
> Read idea analysis from `.haytham/session/phase-1-why/idea-analysis.md` and market research from `.haytham/session/phase-1-why/market-research.md`. Compile a neutral research brief. Write to `.haytham/session/phase-1-why/research-brief.md`.

After the agent completes, read `.haytham/session/phase-1-why/research-brief.md` and output its FULL contents inline in your response. The user must be able to read the entire brief without expanding anything or opening a file. Do NOT summarize or abbreviate — print every line.

Update state: `last_completed_step: 3`.

### Step 4: Founder Review

Ask:
> **Review the brief above.** Check these dimensions:
> - **Problem statement** — is this the right problem?
> - **Competitors** — are we missing anyone, or including wrong ones?
> - **Market size** — in the right ballpark?
> - **Competitive positioning** — are you a direct competitor, complementary, or serving a different segment?
> - **Business model** — does the assumption match your intent?
>
> **What next?**
> 1. Looks good, continue to the validation report
> 2. I have corrections (say which dimensions and what to change)

If the user provides corrections, write them to `.haytham/session/phase-1-why/founder-corrections.json`:
```json
{
  "corrections": [
    {
      "dimension": "problem | competition | market_size | positioning | business_model | other",
      "correction": "What the founder said, verbatim or close paraphrase"
    }
  ],
  "updated_at": "[ISO timestamp]"
}
```

Then update the relevant upstream files (re-run affected steps if factual corrections, or note the strategic corrections for the report-synthesizer). If the corrections are primarily about framing or positioning (not factual errors), you do NOT need to re-run research. Instead, proceed to Step 5 and the report-synthesizer will read the corrections file.

Update state: `last_completed_step: 4`.

### Step 5: Validation Report

Tell the user:
> **Step 5/6: Validation Report**
> Weighing the evidence to produce a GO, PIVOT, or NO-GO recommendation.

Launch a **report-synthesizer** agent with this task:
> Read all Phase 1 files and produce the validation report. Write to `.haytham/session/phase-1-why/validation-report.md` and `.haytham/session/phase-1-why/validation-report.json`.

After the agent completes, read `.haytham/session/phase-1-why/validation-report.md` and output its FULL contents inline in your response. The user must be able to read the entire report without expanding anything or opening a file. Do NOT summarize or abbreviate — print every line of the report.

After the full report, tell the user:
> Full report saved to `.haytham/session/phase-1-why/validation-report.md`

Update state: `last_completed_step: 5`.

### Step 6: Gate 1

Ask:
> **Review the report above. Specifically:**
> - Does the evidence support the verdict?
> - Are there risks the report missed?
> - Do you agree with the recommended direction?
>
> You can ask questions about the report, request changes, or say "approve" to proceed to MVP specification.

- If **NO-GO** and user agrees: Stop and explain the key reasons.
- If **PIVOT** and user agrees: Note the pivot direction, update `.haytham/project.yaml` with the pivoted idea, and restart from Step 1.
- If **GO** and user approves: Write gate decision and continue.
- If user disagrees with recommendation: Discuss and proceed based on their decision.

Write gate decision:
```json
// .haytham/session/phase-1-why/gate-decision.json
{
  "phase": 1,
  "recommendation": "GO|PIVOT|NO-GO",
  "user_decision": "approved|rejected|overridden",
  "notes": "Any user feedback",
  "decided_at": "[ISO timestamp]"
}
```

Update state: `last_completed_step: 6`.

---

## Phase 2: WHAT (MVP Specification)

**Goal:** Define what the MVP includes and model its capabilities.

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

### Step 7: MVP Scope

Verify `.haytham/session/phase-1-why/gate-decision.json` exists.

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

Update state: `last_completed_step: 7`.

### Step 8: Scope Review

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

**If the user approves:** Proceed to Step 9.

Update state: `last_completed_step: 8`.

### Step 9: Capability Model

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

Update state: `last_completed_step: 9`.

### Step 10: Gate 2

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

**When the user approves**, write gate decision:
```json
// .haytham/session/phase-2-what/gate-decision.json
{
  "phase": 2,
  "user_decision": "approved|rejected",
  "scope_revisions": 0,
  "capability_revisions": 0,
  "notes": "Any user feedback",
  "decided_at": "[ISO timestamp]"
}
```

Set `scope_revisions` and `capability_revisions` to the number of times each was re-generated based on user corrections.

Update state: `last_completed_step: 10`.

---

## Phase 3: HOW (Technical Design)

**Goal:** Decide on infrastructure and architecture.

Before launching any agents, tell the user:

> **Phase 3: Technical Design**
>
> This will run 3 steps:
> 1. Architecture — build/buy analysis and technology decisions (~2 min)
> 2. Review — you review the architecture
> 3. Gate 3 — you approve the design ← YOU DECIDE HERE
>
> Estimated total: ~3 minutes.

### Step 11: Architecture

Verify `.haytham/session/phase-2-what/gate-decision.json` exists.

Tell the user:
> **Step 1/3: Architecture**
> Deciding what to build, what to buy, and how the pieces fit together.

Launch an **architect** agent with this task:
> Read the capabilities, MVP scope, and system traits. Produce build/buy analysis and architecture decisions. Write to `.haytham/session/phase-3-how/build-buy.json` and `.haytham/session/phase-3-how/architecture-decisions.json`.

After the agent completes, read `.haytham/session/phase-3-how/build-buy.json` and `.haytham/session/phase-3-how/architecture-decisions.json` and present a structured digest:

> **Architecture designed.** Here's the technical plan:
>
> - **Stack:** [Key technologies chosen]
> - **Build vs Buy:** [Summary of what's built custom vs. third-party services]
> - **Key decisions:** [List the 2-3 most important architecture decisions]
> - **Estimated monthly cost:** [Cost range]
> - **Integration effort:** [Effort estimate]

Update state: `last_completed_step: 11`.

### Step 12: Gate 3

Ask:
> **Review the technical design. Specifically:**
> - Does the technology stack fit your team's skills?
> - Are the build/buy decisions reasonable?
> - Is the estimated cost acceptable?
>
> Approve to proceed to specification generation, or request changes.

Write gate decision:
```json
// .haytham/session/phase-3-how/gate-decision.json
{
  "phase": 3,
  "user_decision": "approved|rejected",
  "notes": "Any user feedback",
  "decided_at": "[ISO timestamp]"
}
```

Update state: `last_completed_step: 12`.

---

## Phase 4: SPECS (OpenSpec Generation)

**Goal:** Generate an implementation-ready OpenSpec that a coding agent can use to build the system.

Before launching any agents, tell the user:

> **Phase 4: Specification Generation**
>
> This will run 3 steps:
> 1. OpenSpec Generation — produce SHALL requirements with Gherkin scenarios (~2 min)
> 2. Review — you review the specification
> 3. Detail Review — drill into specific domains if needed ← YOU DECIDE HERE
>
> Estimated total: ~3 minutes.

### Step 13: OpenSpec Generation

Verify `.haytham/session/phase-3-how/gate-decision.json` exists.

Tell the user:
> **Step 1/3: OpenSpec Generation**
> Turning capabilities and architecture decisions into a complete specification with SHALL requirements and testable scenarios.

Launch a **spec-generator** agent with this task:
> Read all Phase 2 and Phase 3 outputs plus the concept anchor. Generate the OpenSpec directory tree. Write to `.haytham/session/phase-4-specs/openspec/` (config.yaml, project.md, and specs/*/spec.md).

After the agent completes, run validation:
```bash
python3 scripts/validate_openspec.py .haytham/session/phase-4-specs/openspec/ .haytham/session/phase-2-what/capabilities.json
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

Update state: `last_completed_step: 13`.

### Step 14: Final Review

Read the OpenSpec files and output the following inline in your response (the user must see this without expanding anything):
- Domain list with requirement counts per domain
- Coverage check (all capabilities and decisions covered)
- config.yaml traits summary

Ask:
> **Review the specification. Specifically:**
> - Are the domain groupings right?
> - Do the SHALL statements capture what matters?
> - Are the scenarios testable?
>
> Say "looks good" or request changes.

Update state: `last_completed_step: 14`.

### Completion

Summarize what was produced:

```
Command               Output Directory
/haytham:validate  →  .haytham/session/phase-1-why/
/haytham:specify   →  .haytham/session/phase-2-what/
/haytham:design    →  .haytham/session/phase-3-how/
/haytham:plan      →  .haytham/session/phase-4-specs/openspec/
```

Tell the user: "Your specification is complete. Ran 8 agents across 4 phases. All output files are in `.haytham/session/`. Run `/haytham:build` to set up your project for implementation with OpenSpec."
