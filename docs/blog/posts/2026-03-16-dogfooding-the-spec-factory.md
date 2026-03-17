---
date: 2026-03-16
authors:
  - haytham
categories:
  - Multi-Agent Systems
  - Architecture
tags:
  - dogfooding
  - specs
  - capability-modeling
  - quality
description: "We pointed Haytham at itself and got structurally correct but shallow specs. Tracing the root cause led us to rethink how capabilities map to scope."
---

# Dogfooding the Spec Factory

We pointed Haytham at itself. The idea: "a plugin that takes a startup idea and produces an implementation-ready spec." Five scoped features, the usual pipeline run, a working spec at the end.

The output passed every validation check. Right structure, right file layout, right agent count. But when we read the generated agent prompts, they were first drafts. The research agent had no gating logic. The architect had no platform assessment. The spec writer had no quality constraints. The system *worked*, but it wouldn't work *well*.

<!-- more -->

## The obvious fix was wrong

The spec writer is the last agent in the pipeline. It produces the visible output. So when the output is shallow, the instinct is to fix the spec writer. Make it smarter. Give it more guidance. Teach it to produce richer specs.

We almost did that. But the spec writer wasn't doing a bad job. It was doing a fine job with too little input. The shallowness was baked in before the spec writer ever ran.

## One feature is not always one behavior

The problem started two stages earlier, in how we broke features into capabilities.

We had a simple rule: one capability per scoped feature. For straightforward features, that's fine. "Display a ranked leaderboard" is one behavior. You can write three or four test scenarios for it and cover the important cases.

But "research and validate the startup idea" is not one behavior. It's web search, competitor analysis, market sizing, trend assessment, and risk evaluation. Five distinct things with different inputs, different outputs, and different failure modes. Our rule forced all five into a single capability slot.

The downstream math was brutal. Five features times one capability each times five scenarios per capability gave us 25 scenarios to describe a system with roughly 191 distinct behavioral rules. That's a 7.6:1 compression ratio. Something had to get dropped.

## Compression is selective, and it drops the wrong things

Here's what surprised us. The compression wasn't random. Given too little room, the spec writer consistently kept structural rules (file formats, schema fields, I/O contracts) and dropped quality rules (calibration thresholds, evidence discipline, reasoning constraints).

That makes sense if you think about it. Structural rules produce output that a validator can check. Quality rules produce output that only a human would notice is better. When an LLM is forced to compress, it keeps the things that look like requirements and drops the things that look like suggestions.

For a web app, that trade-off is survivable. A coding agent can infer reasonable defaults for a login page. For an agentic system where the prompt *is* the implementation, losing quality rules means losing the product. "The research agent SHALL produce a market analysis" tells you what to build. It doesn't tell you to gate invalid ideas first, flag ambiguous terms, or weight evidence by source reliability. Those are the rules that separate a useful agent from a demo.

## The fix: decompose by behavior, not by feature

The insight was that we were conflating two things. A "feature" is what a user asks for. A "behavior" is what the system does. For simple features they're the same. For complex ones they're not.

Consider the difference. "Order processing" sounds like one feature. But it contains inventory verification, payment processing, and shipping label generation. Each has different inputs (stock levels vs. card details vs. addresses), different outputs (reservation vs. charge receipt vs. label PDF), and different error conditions (out of stock vs. payment declined vs. invalid address). Writing one combined test scenario for all three guarantees that at least two get shallow coverage.

The fix: instead of one capability per feature, one capability per distinct behavior. Simple features still produce one capability. Complex features produce several, all traced back to the same parent feature. "Order processing" becomes three capabilities, each with its own focused test scenarios, but all linked to the same scoped feature for traceability.

We needed a concrete rule to decide when to split, not just "use your judgment." The test we landed on: if two acceptance criteria describe behaviors with different inputs, different outputs, or different error conditions, they should be separate capabilities. And a counter-test to prevent over-splitting: if a user wouldn't describe two steps as separate things, keep them together. "Log in with email" and "log in with password" are one capability (authentication), not two.

## What changed in the numbers

We ran the same idea through both versions. The old pipeline produced 5 capabilities and 25 test scenarios. The new one produced 10 capabilities and 47 scenarios, nearly double. Complex features decomposed naturally (our research phase went from 1 capability to 4, our spec generation phase from 1 to 3) while simple features stayed at 1 each.

More importantly, coverage of the behavioral rules we cared about improved 2.67x. Still not complete, and honestly, still not where we want it. The remaining gaps are fine-grained constraints that live deep inside agent prompts and are outside the scope of system-level specs. But the specs went from "generic first draft" to "meaningful starting point," and the decomposition itself introduced zero scope creep. Every new capability traced back to an existing feature.

## The general lesson

In any multi-stage pipeline, quality problems in the output are usually *not* caused by the output stage. The output stage is compressing what it was given. If you keep fixing the last stage, you end up with increasingly clever compensation logic that obscures the real constraint.

We see this pattern everywhere. A coding agent produces generic code? The instinct is to improve the coding agent's prompt. But often the spec it received was too vague, and the vague spec came from a vague capability model, and the vague capability model came from a rule that was too rigid three stages upstream.

Trace the chain backwards. Find the stage where information gets lost. Fix it there. In our case, the binding constraint was a one-to-one mapping rule that seemed reasonable in isolation but created an information bottleneck for everything downstream.

## What's next

The 2.67x coverage improvement is real but the absolute number (20% of behavioral rules covered) is honest about how far we still have to go. The next pieces are teaching the capability modeler to recognize meta-capabilities for pipeline systems (gating steps, self-checks, validation hooks) and giving the spec writer depth guidance for LLM-orchestrated capabilities. The behavioral decomposition change lands first because it changes the input to everything downstream, and the other improvements build on having the right number of capabilities to work with.
