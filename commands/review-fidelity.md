---
description: Review whether pipeline output stays faithful to the original idea throughout all phases
argument-hint: (no arguments - reads from .haytham/session/)
allowed-tools: Read, Glob, Agent
---

# Haytham: Concept Fidelity Review

Invoke the **reviewer-fidelity** agent with this task:

> Review all available Haytham phase output in `.haytham/session/` against the original idea in `.haytham/project.yaml`. Follow your instructions exactly. Emit the findings table, drift summary, and any high-confidence drift calls inline. Write the structured summary to `.haytham/session/reviews/fidelity.json`.

After the agent completes, the findings are visible in the conversation; the summary JSON is on disk for later inspection.
