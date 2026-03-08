---
description: Run Phase 1 (WHY) - Validate a startup idea with market research and produce a GO/PIVOT/NO-GO recommendation
argument-hint: [startup idea]
allowed-tools: Read, Write, Edit, Bash, Glob, Agent, WebSearch, WebFetch
---

# Haytham: Idea Validation (Phase 1 - WHY)

You are running Phase 1 of the Haytham validation workflow. This phase analyzes the startup idea, researches the market, and produces a recommendation.

**IMPORTANT:** Always read agent output from files, not from conversation history.

## Setup

1. Create `.haytham/` and `.haytham/session/phase-1-why/` directories if they don't exist
2. Write the user's startup idea to `.haytham/project.yaml`:
   ```yaml
   idea: |
     [The user's startup idea exactly as provided]
   created_at: [current ISO timestamp]
   ```

## Roadmap

Before launching any agents, read `.claude-plugin/marketplace.json` and extract the `version` field from `plugins[0]`. Then tell the user (replacing VERSION with the actual version string you just read):

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

## Step 1: Idea Analysis

Tell the user:
> **Step 1/6: Idea Analysis**
> Expanding your idea into a structured concept so we have a clear foundation for research.

Launch an **idea-analyst** agent with this task:
> Read the startup idea from `.haytham/project.yaml`. Analyze it following your instructions. Write idea analysis to `.haytham/session/phase-1-why/idea-analysis.md` and concept anchor to `.haytham/session/phase-1-why/concept-anchor.json`.

If the agent writes `.haytham/session/phase-1-why/idea-clarification.md`, read it and present the questions/suggestions to the user. Wait for their response, update `.haytham/project.yaml`, and re-run.

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

## Step 2: Market Research

Verify `.haytham/session/phase-1-why/idea-analysis.md` exists. Read it and extract the domain/category.

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

## Step 3: Research Brief

Tell the user:
> Research gathered. Compiling a neutral summary for your review. No scores or judgments, just facts.

Launch a **research-briefer** agent with this task:
> Read idea analysis and market research from `.haytham/session/phase-1-why/`. Compile a neutral research brief. Write to `.haytham/session/phase-1-why/research-brief.md`.

After the agent completes, read `.haytham/session/phase-1-why/research-brief.md` and output its FULL contents inline in your response. The user must be able to read the entire brief without expanding anything or opening a file. Do NOT summarize or abbreviate — print every line.

## Step 4: Founder Review

Ask:
> **Review the brief above. Specifically:**
> - Is the problem statement right?
> - Are we missing any key competitors?
> - Is the market size in the right ballpark?
>
> Reply with corrections, or say "looks good" to continue to the validation report.

## Step 5: Validation Report

Tell the user:
> **Step 5/6: Validation Report**
> Weighing the evidence to produce a GO, PIVOT, or NO-GO recommendation.

Launch a **report-synthesizer** agent with this task:
> Read all Phase 1 files and produce the validation report. Write to `.haytham/session/phase-1-why/validation-report.md` and `.haytham/session/phase-1-why/validation-report.json`.

After the agent completes, read `.haytham/session/phase-1-why/validation-report.md` and output its FULL contents inline in your response. The user must be able to read the entire report without expanding anything or opening a file. Do NOT summarize or abbreviate — print every line of the report.

After the full report, tell the user:
> Full report saved to `.haytham/session/phase-1-why/validation-report.md`

## Step 6: Gate 1

Ask:
> **Review the report above. Specifically:**
> - Does the evidence support the verdict?
> - Are there risks the report missed?
> - Do you agree with the recommended direction?
>
> You can ask questions about the report, request changes, or say "approve" to proceed.

Write gate decision to `.haytham/session/phase-1-why/gate-decision.json`:
```json
{
  "phase": 1,
  "recommendation": "GO|PIVOT|NO-GO",
  "user_decision": "approved|rejected|overridden",
  "notes": "Any user feedback",
  "decided_at": "[ISO timestamp]"
}
```

Tell the user: "Phase 1 complete. Ran 4 agents across 6 steps. Run `/haytham:specify` to proceed to MVP specification (Phase 2), or `/haytham:haytham` to run the full workflow."
