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

Before launching any agents, tell the user:

> **Phase 1: Idea Validation**
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

After the agent completes, read `.haytham/session/phase-1-why/idea-analysis.md` and present a structured digest:

> **Idea analysis complete.** Here's what we extracted:
>
> - **Core concept:** [One-line summary of what this product does]
> - **Top problems:** [List the top 2-3 problems identified, one line each]
> - **Primary segment:** [The primary user segment and their defining behavior]
> - **UVP:** [The unique value proposition as written]
> - **Concept health:** Pain Clarity: [X], Trigger Strength: [X], WTP Signal: [X]
>
> Proceeding to market research. (You can steer by responding, e.g., "focus on competitor X" or "skip research, I know the market", or let it continue.)

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

### Step 3: Research Brief

Tell the user:
> Research gathered. Compiling a neutral summary for your review. No scores or judgments, just facts.

Launch a **research-briefer** agent with this task:
> Read idea analysis from `.haytham/session/phase-1-why/idea-analysis.md` and market research from `.haytham/session/phase-1-why/market-research.md`. Compile a neutral research brief. Write to `.haytham/session/phase-1-why/research-brief.md`.

After the agent completes, read `.haytham/session/phase-1-why/research-brief.md` and present a structured digest:

> **Research brief compiled.** Quick summary before you review:
>
> - **Our read of your idea:** [One-line problem + audience from the brief]
> - **Market size:** [TAM/SAM/SOM figures from the brief]
> - **Competitors found:** [Number] — [list names]
> - **Data gaps:** [Key things we couldn't verify]
>
> Full brief below for your review.

### Step 4: Founder Review

Read `.haytham/session/phase-1-why/research-brief.md` and present it to the user.

Ask:
> **Review the brief above. Specifically:**
> - Is the problem statement right?
> - Are we missing any key competitors?
> - Is the market size in the right ballpark?
>
> Reply with corrections, or say "looks good" to continue to the validation report.

If the user has corrections, update the relevant files and re-run the affected steps.

### Step 5: Validation Report

Tell the user:
> **Step 5/6: Validation Report**
> Weighing the evidence to produce a GO, PIVOT, or NO-GO recommendation.

Launch a **report-synthesizer** agent with this task:
> Read all Phase 1 files and produce the validation report. Write to `.haytham/session/phase-1-why/validation-report.md` and `.haytham/session/phase-1-why/validation-report.json`.

After the agent completes, read `.haytham/session/phase-1-why/validation-report.json` and `.haytham/session/phase-1-why/validation-report.md` and present a structured digest:

> **Validation report complete.**
>
> - **Recommendation:** [GO/PIVOT/NO-GO] — [recommendation_reasoning from JSON]
> - **Composite score:** [X.X/5.0]
> - **Risk level:** [HIGH/MEDIUM/LOW]
> - **Strongest point:** [strongest_point from JSON]
> - **Competitive snapshot:** [competitive_snapshot from JSON]
> - **What to do next:** [closing_remark from JSON]

### Step 6: Gate 1

Read `.haytham/session/phase-1-why/validation-report.json` and extract the recommendation.
Read `.haytham/session/phase-1-why/validation-report.md` and present the key findings to the user.

Present the recommendation:
- **GO**: "The analysis recommends proceeding. [Summary of why]"
- **PIVOT**: "The analysis suggests pivoting. [Pivot direction]"
- **NO-GO**: "The analysis recommends against proceeding. [Key reasons]"

Ask:
> **Review the recommendation. Specifically:**
> - Does the evidence support the verdict?
> - Are there risks the report missed?
> - Do you agree with the recommended direction?
>
> Approve to proceed to MVP specification, or explain why you disagree.

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

Before launching any agents, tell the user:

> **Phase 2: MVP Specification**
>
> This will run 3 steps:
> 1. MVP Scope — define what's in, what's out, and the core flows (~1 min)
> 2. Capability Model — extract capabilities and system traits (~1 min)
> 3. Gate 2 — you approve the specification ← YOU DECIDE HERE
>
> Estimated total: ~3 minutes.

### Step 7: MVP Scope

Verify `.haytham/session/phase-1-why/gate-decision.json` exists.

Tell the user:
> **Step 1/3: MVP Scope**
> Translating the validated idea into a concrete MVP definition. What's in, what's out, and what the core user flow looks like.

Launch an **mvp-scoper** agent with this task:
> Read the validation report, idea analysis, and concept anchor. Define the MVP scope. Write to `.haytham/session/phase-2-what/mvp-scope.md`.

After the agent completes, read `.haytham/session/phase-2-what/mvp-scope.md` and present a structured digest:

> **MVP scope defined.** Here's the shape of your MVP:
>
> - **The One Thing:** [The single sentence MVP purpose]
> - **IN scope:** [List the key items that are in]
> - **OUT scope:** [List the key items explicitly excluded]
> - **Appetite:** [Time/effort budget]
> - **Core flow:** [One-line description of the primary user journey]

### Step 8: Capability Model

Tell the user:
> Scope is set. Now extracting the specific capabilities your MVP needs and classifying system traits.

Launch a **capability-modeler** agent with this task:
> Read the MVP scope, idea analysis, and concept anchor. Produce the capability model and system traits. Write to `.haytham/session/phase-2-what/capabilities.json` and `.haytham/session/phase-2-what/system-traits.json`.

After the agent completes, read `.haytham/session/phase-2-what/capabilities.json` and `.haytham/session/phase-2-what/system-traits.json` and present a structured digest:

> **Capability model complete.**
>
> - **Functional capabilities:** [Count] — [list capability names]
> - **Non-functional capabilities:** [Count] — [list capability names]
> - **System traits:** [List key traits like auth model, data sensitivity, etc.]
> - **Traceability:** Each capability traces to [IN SCOPE items / problems from Phase 1]

### Step 9: Gate 2

Read `.haytham/session/phase-2-what/capabilities.json` and present the capabilities summary to the user. Show functional and non-functional capabilities with their traceability.

Ask:
> **Review the MVP specification. Specifically:**
> - Does the IN/OUT scope match your vision?
> - Are the core capabilities right?
> - Is there anything critical missing?
>
> Approve to proceed to technical design, or request changes.

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

Before launching any agents, tell the user:

> **Phase 3: Technical Design**
>
> This will run 3 steps:
> 1. Architecture — build/buy analysis and technology decisions (~2 min)
> 2. Review — you review the architecture
> 3. Gate 3 — you approve the design ← YOU DECIDE HERE
>
> Estimated total: ~3 minutes.

### Step 10: Architecture

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

### Step 11: Gate 3

Ask:
> **Review the technical design. Specifically:**
> - Does the technology stack fit your team's skills?
> - Are the build/buy decisions reasonable?
> - Is the estimated cost acceptable?
>
> Approve to proceed to story planning, or request changes.

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

Before launching any agents, tell the user:

> **Phase 4: Implementation Plan**
>
> This will run 3 steps:
> 1. Story Planning — generate stories with dependencies and acceptance criteria (~2 min)
> 2. Review — you review the implementation plan
> 3. Detail Review — drill into specific stories if needed ← YOU DECIDE HERE
>
> Estimated total: ~3 minutes.

### Step 12: Story Planning

Verify `.haytham/session/phase-3-how/gate-decision.json` exists.

Tell the user:
> **Step 1/3: Story Planning**
> Turning capabilities and architecture decisions into implementation-ready stories with dependencies.

Launch a **story-planner** agent with this task:
> Read all Phase 2 and Phase 3 outputs plus the concept anchor. Generate story skeletons, detail specs, and the execution contract. Write to `.haytham/session/phase-4-stories/stories.json` and `.haytham/session/phase-4-stories/execution-contract.json`.

After the agent completes, read `.haytham/session/phase-4-stories/execution-contract.json` and `.haytham/session/phase-4-stories/stories.json` and present a structured digest:

> **Story planning complete.**
>
> - **Total stories:** [Count]
> - **Layer breakdown:** [e.g., Infrastructure: X, Backend: X, Frontend: X, Integration: X]
> - **Critical path:** [The first 2-3 stories that must be built first]
> - **Coverage:** [All capabilities covered? Any gaps?]

### Step 13: Final Review

Read `.haytham/session/phase-4-stories/execution-contract.json` and present to the user:
- Total story count and layer breakdown
- Dependency graph (which stories depend on which)
- Coverage check (all capabilities and decisions covered)

Ask:
> **Review the implementation plan. Specifically:**
> - Is the story breakdown granular enough to start building?
> - Are the dependencies in the right order?
> - Is anything missing from the coverage check?
>
> Say "looks good" or request changes.

### Completion

Summarize what was produced:
- `.haytham/session/phase-1-why/` - Validation report with recommendation
- `.haytham/session/phase-2-what/` - MVP scope and capability model
- `.haytham/session/phase-3-how/` - Architecture and build/buy decisions
- `.haytham/session/phase-4-stories/` - Implementation stories and execution contract

Tell the user: "Your specification is complete. Ran 8 agents across 4 phases. All output files are in `.haytham/session/`. You can use `/haytham:validate`, `/haytham:specify`, `/haytham:design`, or `/haytham:plan` to re-run individual phases."
