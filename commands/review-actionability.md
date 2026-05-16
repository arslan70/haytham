---
description: Review whether the specification is detailed enough to implement
argument-hint: (no arguments - reads from .haytham/session/)
allowed-tools: Read, Glob, Agent
---

# Haytham: Specification Actionability Review

Invoke the **reviewer-actionability** agent with this task:

> Review the completed Phase 2-4 output in `.haytham/session/` to evaluate whether the specification is detailed enough for a developer to start building. Follow your instructions exactly. Emit the findings table and any high-confidence actionability gaps inline. Write the structured summary to `.haytham/session/phase-4-specs/review-actionability.json`.

After the agent completes, the findings are visible in the conversation; the summary JSON is on disk for later inspection.
