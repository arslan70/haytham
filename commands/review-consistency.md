---
description: Review cross-stage consistency and traceability across Haytham output
argument-hint: (no arguments - reads from .haytham/session/)
allowed-tools: Read, Glob, Agent
---

# Haytham: Internal Consistency Review

Invoke the **reviewer-consistency** agent with this task:

> Review all available Haytham phase output in `.haytham/session/` for cross-stage consistency. Follow your instructions exactly. Emit the findings table and any high-confidence inconsistency calls inline. Write the structured summary to `.haytham/session/review-consistency.json`.

After the agent completes, the findings are visible in the conversation; the summary JSON is on disk for later inspection.
