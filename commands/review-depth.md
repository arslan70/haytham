---
description: Review Phase 1 output for analysis depth and evidence quality
argument-hint: (no arguments - reads from .haytham/session/phase-1-why/)
allowed-tools: Read, Glob, Agent
---

# Haytham: Analysis Depth Review

Invoke the **reviewer-depth** agent with this task:

> Review Phase 1 output in `.haytham/session/phase-1-why/`. Follow your instructions exactly. Emit the findings table and improvement suggestions inline. Write the structured summary to `.haytham/session/reviews/depth.json`.

After the agent completes, the findings are visible in the conversation; the summary JSON is on disk for later inspection.
