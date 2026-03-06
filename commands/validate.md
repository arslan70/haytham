---
description: Run Phase 1 (WHY) - Validate a startup idea with market research and produce a GO/PIVOT/NO-GO recommendation
argument-hint: [startup idea]
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

## Step 1: Idea Analysis

Launch an **idea-analyst** agent with this task:
> Read the startup idea from `.haytham/project.yaml`. Analyze it following your instructions. Write idea analysis to `.haytham/session/phase-1-why/idea-analysis.md` and concept anchor to `.haytham/session/phase-1-why/concept-anchor.json`.

If the agent writes `.haytham/session/phase-1-why/idea-clarification.md`, read it and present the questions/suggestions to the user. Wait for their response, update `.haytham/project.yaml`, and re-run.

## Step 2: Market Research

Verify `.haytham/session/phase-1-why/idea-analysis.md` exists.

Launch a **market-researcher** agent with this task:
> Read the idea analysis from `.haytham/session/phase-1-why/idea-analysis.md` and concept anchor from `.haytham/session/phase-1-why/concept-anchor.json`. Research the market and competitors. Write results to `.haytham/session/phase-1-why/market-research.md`.

## Step 3: Research Brief

Launch a **research-briefer** agent with this task:
> Read idea analysis and market research from `.haytham/session/phase-1-why/`. Compile a neutral research brief. Write to `.haytham/session/phase-1-why/research-brief.md`.

## Step 4: Founder Review

Read `.haytham/session/phase-1-why/research-brief.md` and present it to the user.

Ask: **"Does this accurately capture your idea and the market landscape? Would you like to correct anything before we produce the validation report?"**

## Step 5: Validation Report

Launch a **report-synthesizer** agent with this task:
> Read all Phase 1 files and produce the validation report. Write to `.haytham/session/phase-1-why/validation-report.md` and `.haytham/session/phase-1-why/validation-report.json`.

## Step 6: Gate 1

Read `.haytham/session/phase-1-why/validation-report.json`. Present the recommendation and key findings.

Ask: **"Do you approve this recommendation?"**

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

Tell the user: "Phase 1 complete. Run `/haytham:specify` to proceed to MVP specification (Phase 2), or `/haytham:haytham` to run the full workflow."
