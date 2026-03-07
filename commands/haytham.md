---
description: Validate a startup idea and produce an implementation-ready specification
argument-hint: [startup idea]
allowed-tools: Read, Write, Edit, Bash, Glob, Agent, WebSearch, WebFetch
---

# Haytham: Startup Idea Validation & Specification

You are orchestrating a 4-phase startup validation workflow. Follow each phase in order. Do not skip phases. Do not proceed to the next phase without user approval at the gate.

**IMPORTANT:** Always read agent output from files, not from conversation history. Before each phase, verify previous phase output files exist by reading them.

## Setup

1. Create `.haytham/` directory if it doesn't exist
2. Create `.haytham/session/phase-1-why/`, `.haytham/session/phase-2-what/`, `.haytham/session/phase-3-how/`, `.haytham/session/phase-4-stories/` directories
3. Write the user's startup idea to `.haytham/project.yaml`:
   ```yaml
   idea: |
     [The user's startup idea exactly as provided]
   created_at: [current ISO timestamp]
   ```

---

## Phase 1: WHY (Idea Validation)

**Goal:** Understand the idea, research the market, and produce a GO/PIVOT/NO-GO recommendation.

### Step 1: Idea Analysis

Launch an **idea-analyst** agent with this task:
> Read the startup idea from `.haytham/project.yaml`. Analyze it following your instructions. Write idea analysis to `.haytham/session/phase-1-why/idea-analysis.md` and concept anchor to `.haytham/session/phase-1-why/concept-anchor.json`.

If the agent writes `.haytham/session/phase-1-why/idea-clarification.md`, read it and present the clarification questions or suggestions to the user. Wait for their response, update `.haytham/project.yaml` with the refined idea, and re-run Step 1.

### Step 2: Market Research

Read `.haytham/session/phase-1-why/idea-analysis.md` to confirm it exists.

Launch a **market-researcher** agent with this task:
> Read the idea analysis from `.haytham/session/phase-1-why/idea-analysis.md` and concept anchor from `.haytham/session/phase-1-why/concept-anchor.json`. Research the market and competitors. Write results to `.haytham/session/phase-1-why/market-research.md`.

### Step 3: Research Brief

Read `.haytham/session/phase-1-why/market-research.md` to confirm it exists.

Launch a **research-briefer** agent with this task:
> Read idea analysis from `.haytham/session/phase-1-why/idea-analysis.md` and market research from `.haytham/session/phase-1-why/market-research.md`. Compile a neutral research brief. Write to `.haytham/session/phase-1-why/research-brief.md`.

### Step 4: Founder Review

Read `.haytham/session/phase-1-why/research-brief.md` and present it to the user.

Ask the user: **"Does this accurately capture your idea and the market landscape? Would you like to correct anything before we produce the validation report?"**

If the user has corrections, update the relevant files and re-run the affected steps.

### Step 5: Validation Report

Launch a **report-synthesizer** agent with this task:
> Read all Phase 1 files and produce the validation report. Write to `.haytham/session/phase-1-why/validation-report.md` and `.haytham/session/phase-1-why/validation-report.json`.

### Step 6: Gate 1

Read `.haytham/session/phase-1-why/validation-report.json` and extract the recommendation.
Read `.haytham/session/phase-1-why/validation-report.md` and present the key findings to the user.

Present the recommendation:
- **GO**: "The analysis recommends proceeding. [Summary of why]"
- **PIVOT**: "The analysis suggests pivoting. [Pivot direction]"
- **NO-GO**: "The analysis recommends against proceeding. [Key reasons]"

Ask the user: **"Do you approve proceeding to MVP specification? (Phase 2)"**

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

---

## Phase 2: WHAT (MVP Specification)

**Goal:** Define what the MVP includes and model its capabilities.

### Step 7: MVP Scope

Verify `.haytham/session/phase-1-why/gate-decision.json` exists.

Launch an **mvp-scoper** agent with this task:
> Read the validation report, idea analysis, and concept anchor. Define the MVP scope. Write to `.haytham/session/phase-2-what/mvp-scope.md`.

Read the output and present the MVP scope to the user (The One Thing, IN/OUT scope table, appetite).

### Step 8: Capability Model

Launch a **capability-modeler** agent with this task:
> Read the MVP scope, idea analysis, and concept anchor. Produce the capability model and system traits. Write to `.haytham/session/phase-2-what/capabilities.json` and `.haytham/session/phase-2-what/system-traits.json`.

### Step 9: Gate 2

Read `.haytham/session/phase-2-what/capabilities.json` and present the capabilities summary to the user. Show functional and non-functional capabilities with their traceability.

Ask the user: **"Do you approve this MVP specification? Ready to proceed to technical design? (Phase 3)"**

Write gate decision:
```json
// .haytham/session/phase-2-what/gate-decision.json
{
  "phase": 2,
  "user_decision": "approved|rejected",
  "notes": "Any user feedback",
  "decided_at": "[ISO timestamp]"
}
```

---

## Phase 3: HOW (Technical Design)

**Goal:** Decide on infrastructure and architecture.

### Step 10: Architecture

Verify `.haytham/session/phase-2-what/gate-decision.json` exists.

Launch an **architect** agent with this task:
> Read the capabilities, MVP scope, and system traits. Produce build/buy analysis and architecture decisions. Write to `.haytham/session/phase-3-how/build-buy.json` and `.haytham/session/phase-3-how/architecture-decisions.json`.

Read the outputs and present to the user:
- Recommended technology stack
- Key architecture decisions
- Estimated integration effort and monthly cost

### Step 11: Gate 3

Ask the user: **"Do you approve this technical design? Ready to proceed to story planning? (Phase 4)"**

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

---

## Phase 4: STORIES (Implementation Plan)

**Goal:** Generate implementation-ready stories with dependency ordering.

### Step 12: Story Planning

Verify `.haytham/session/phase-3-how/gate-decision.json` exists.

Launch a **story-planner** agent with this task:
> Read all Phase 2 and Phase 3 outputs plus the concept anchor. Generate story skeletons, detail specs, and the execution contract. Write to `.haytham/session/phase-4-stories/stories.json` and `.haytham/session/phase-4-stories/execution-contract.json`.

### Step 13: Final Review

Read `.haytham/session/phase-4-stories/execution-contract.json` and present to the user:
- Total story count and layer breakdown
- Dependency graph (which stories depend on which)
- Coverage check (all capabilities and decisions covered)

Ask the user: **"Your implementation plan is ready. Would you like to review any specific stories in detail?"**

### Completion

Summarize what was produced:
- `.haytham/session/phase-1-why/` - Validation report with recommendation
- `.haytham/session/phase-2-what/` - MVP scope and capability model
- `.haytham/session/phase-3-how/` - Architecture and build/buy decisions
- `.haytham/session/phase-4-stories/` - Implementation stories and execution contract

Tell the user: "Your specification is complete. All output files are in `.haytham/session/`. You can use `/haytham:validate`, `/haytham:specify`, `/haytham:design`, or `/haytham:plan` to re-run individual phases."
