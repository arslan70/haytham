---
date: 2026-05-27
authors:
  - haytham
categories:
  - Agentic Coding
  - Self-Improving Systems
tags:
  - claude-code
  - agents
  - reasoning-graph
  - telemetry
  - dogfooding
description: "Five runs over ten days. The first found broken instrumentation. The third caught an error in its own measurement framework. The fifth diagnosed garbage traffic instead of blaming the product. The interesting part isn't any single finding. It's the arc."
---

# Can you ask Claude Code to improve your system?

> **Status (2026-07-03): the commands this post describes were retired.** Haytham has since been re-scoped to a personal idea-to-MVP pipeline. `/haytham:propose-next-steps` and `/haytham:evolve` no longer exist in the plugin; their machinery is preserved at git tag [`v0.3.27-full`](https://github.com/arslan70/haytham/tree/v0.3.27-full). The post is kept as a record of what the loop found while it ran.

Open Claude Code, Cursor, or whatever agent you use. Ask it: "Look at this project and suggest a meaningful improvement." Watch what comes back.

<!-- more -->

You'll get a list. Add more tests. Improve error handling. Consider TypeScript. Maybe a remark about your folder structure. The advice is fine, often correct, and almost never about your system specifically. You could have written the same list before opening the IDE.

The agent's missing a reference frame.

When you ask "what should I improve?", it reads your code, maybe runs your tests, maybe greps your repo. Then it has to answer. The problem is the agent has no idea what your system is supposed to do. Nothing tells it what success looks like for your specific case. It has no view into what your users are actually doing in production. So it falls back to pattern-matching against the average of every "code improvement" article it saw during training. The output is the average of those articles, dressed up in your file names.

I've been thinking about what would change that.

The piece that's missing is a layer between intent and code that the agent can read. Really three artifacts: a declared intent at the top (what is this system trying to do), per-capability specs in the middle (which file serves which goal), and telemetry contracts at the bottom (what does "working" mean for this capability in production data). If those three exist as files the agent can read, "what should I improve?" stops being a guess about your codebase. The agent can compare your stated intent against your implementation against your production data, and look for mismatches. The interesting findings live in the gaps.

I've been building one. It's called [Haytham](https://github.com/arslan70/haytham), a Claude Code plugin that maintains the three-layer graph and a few commands that operate on it. A couple of weeks ago, for the first time, the whole loop closed end-to-end on a real product.

I'd been using Haytham to ship features on a small e-commerce site I'm building called GiftKaro, so I had real telemetry to point at. I ran a new command, `/haytham:propose-next-steps`. It read the telemetry contract, queried Google Analytics, and produced a ranked list of proposals. The top one said: the success threshold my contract used to judge this capability depended on a measurement that wasn't actually being captured, so the system couldn't tell whether the capability was working.

I routed that proposal into `/haytham:evolve`, which spawned three variant proposers in parallel. They came back with different things. One proposed expanding to new cities. But the variant that tackled the telemetry gap caught something the proposer missed: `item_category` wasn't absent from the data. It was being sent in the wrong shape, flat instead of inside GA4's `items` array, so GA4 silently dropped it. The variant found this by reading the actual code, which the proposer hadn't. I shipped that fix for the product page. The checkout page had the same bug and took a separate PR a few days later. By the end of the week the dimension populated. The loop closed, just not as cleanly as I'd expected.

That was the first run. One good run isn't a system. The real test is whether subsequent runs produce findings I wouldn't have caught from a five-minute manual scan of my analytics. If even one in ten does that, the bet pays. If they're all variations of "add more tests" in domain-specific clothing, it doesn't.

It's been five runs over ten days. The first two found instrumentation bugs: events firing in the wrong format, dimensions not populating. Plumbing. Useful, but if every run just found more broken pipes, the system would be an expensive linter.

The third run caught an error in its own measurement framework. A contract baseline had been computed from event counts instead of session counts, inflating the target by nearly three times. The contract was in permanent false-fail: it looked like the capability was underperforming, but only because the yardstick was miscalibrated. I wouldn't have caught that from a dashboard because I had no reason to doubt a baseline I'd already approved.

The fifth run found something different again. Two thresholds breached. The system diagnosed the first as garbage traffic, not a product regression. A spike of sessions with zero engagement from an unrecognized source had poisoned the metrics. It recommended blocking the traffic, not revising the thresholds. The second breach was a false alarm: a code change had swapped the terminal event in the checkout funnel, but the contract still measured the old one. The system traced the commit, confirmed the new event was firing, and recommended updating the contract instead of fixing the code.

The individual findings matter. But the real finding is the arc. First runs fix instrumentation. Middle runs fix the contracts. Later runs read what the data says. Each run compounds because the system remembers what it checked last time and what changed since. A manual analytics scan doesn't do that. You'd notice bounce rate spiked. You wouldn't remember that the terminal event in your funnel contract changed two commits ago, because you don't have a funnel contract.

That compounding is what I think makes this worth building. Not any single proposal. The fact that proposal quality improves as the measurement framework gets cleaned up underneath. The system earns the right to make behavioral recommendations by first proving it can measure correctly.

Two findings across five runs that I genuinely wouldn't have caught. Zero "add more tests" proposals in the entire history. The next open question is what happens at run fifteen, when the easy instrumentation fixes are exhausted and the system has to find subtler signals in cleaner data.
