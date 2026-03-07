---
description: Analyze a Haytham run transcript for UX guideline compliance and suggest improvements
argument-hint: [path to transcript file]
allowed-tools: Read, Glob
---

# Haytham: UX Review

You are reviewing a transcript of a Haytham run against the Agent UX Standards defined in CLAUDE.md. Your job is to evaluate what the user actually saw and flag where the experience fell short.

## Input

Read the transcript file provided as the argument. If no argument was provided, ask the user to provide the path to a transcript file (a saved copy of the conversation output from a `/haytham`, `/haytham:validate`, `/haytham:specify`, `/haytham:design`, or `/haytham:plan` run).

## Evaluation Checklist

Evaluate the transcript against each standard below. For each, assign **PASS**, **PARTIAL**, or **FAIL** with a one-line rationale and a direct quote from the transcript as evidence (or note the absence of expected text).

### 1. Roadmap

Was a numbered step list shown before any agent was launched? Did it include step names, time estimates, and mark which steps involve user decisions?

- PASS: Full roadmap with steps, times, and decision markers
- PARTIAL: Step list shown but missing times or decision markers
- FAIL: No roadmap, or agents launched before any plan was shown

### 2. Pre-Agent Framing

Before each agent call, was there a message explaining what the agent will do and why, in purpose-driven language?

- PASS: Every agent call was preceded by a purpose-driven framing message
- PARTIAL: Some agent calls were framed, others were launched without context
- FAIL: Agent calls launched with no framing, or framing was procedural ("Launching agent X")

### 3. Post-Agent Digest

After each agent completed, was there a one-line summary of what was found (read from the output file)?

- PASS: Every agent completion followed by a concrete summary of findings
- PARTIAL: Some digests present, others missing or generic ("done")
- FAIL: No post-agent digests, or only generic "complete" messages

### 4. Purpose-Driven Transitions

Did transition messages explain why the next step exists relative to the user's goal, rather than just naming the step?

- PASS: Transitions explain purpose ("Checking if anyone else is solving this")
- PARTIAL: Mix of purpose-driven and procedural transitions
- FAIL: All transitions are procedural ("Moving to Step 3: Research Brief")

### 5. Guided Review Questions

At review/gate steps, were questions specific and actionable with named dimensions to evaluate? Was a low-effort escape provided ("say 'looks good' to continue")?

- PASS: Specific dimensions listed, low-effort escape provided
- PARTIAL: Question is specific but missing escape, or has escape but is too open-ended
- FAIL: Open-ended "anything to correct?" style questions

### 6. Soft Checkpoint

After idea analysis (or the first major agent), was there a visible window for the user to steer without a blocking question?

- PASS: Informational pause that signals the user can interject but doesn't require a response
- PARTIAL: Checkpoint present but worded as a blocking question
- FAIL: No checkpoint; system proceeds from first agent directly to next without pause

### 7. Completion Summary

At the end of the phase/workflow, was there a summary noting how many agents ran and how many steps were completed?

- PASS: Completion message includes agent/step counts
- PARTIAL: Completion message present but missing counts
- FAIL: No completion summary, or just "done"

## Output Format

Present your findings as a table, then provide specific improvement suggestions.

```
| # | Standard              | Result  | Evidence |
|---|-----------------------|---------|----------|
| 1 | Roadmap               | PASS    | "This will run 6 steps: ..." |
| 2 | Pre-Agent Framing     | PARTIAL | Steps 1-3 framed, Step 5 missing |
| 3 | Post-Agent Digest     | FAIL    | No digests after any agent call |
| 4 | Purpose Transitions   | PASS    | "Checking if anyone else is solving this..." |
| 5 | Guided Questions      | PASS    | "Is the problem statement right? ..." |
| 6 | Soft Checkpoint       | FAIL    | No pause after idea analysis |
| 7 | Completion Summary    | PARTIAL | "Phase 1 complete" but no agent count |
```

**Score: X/7 PASS, Y/7 PARTIAL, Z/7 FAIL**

### Suggested Improvements

For each PARTIAL or FAIL, suggest a specific fix. Reference the command file and section that needs to change. For example:

> **Post-Agent Digest (FAIL):** After the market-researcher agent completes, the command should read `.haytham/session/phase-1-why/market-research.md` and emit a one-liner like "Found 4 competitors, TAM estimated at $7.4B." This instruction exists in `commands/validate.md` Step 2 but the orchestrator did not follow it. Consider strengthening the instruction or making the digest text more explicit.

### Root Cause Notes

If the same standard fails across multiple steps, note whether the likely cause is:
- **Missing instruction**: The command file doesn't include the UX instruction at all
- **Weak instruction**: The instruction is present but not prominent enough for the LLM to follow consistently
- **Platform constraint**: Claude Code's rendering or subagent behavior prevents the instruction from being followed
