---
date: 2026-03-18
authors:
  - haytham
categories:
  - Multi-Agent Systems
  - Open Source
tags:
  - dogfooding
  - agents
  - openspec
  - meta
description: "I ran my AI pipeline tool on its own idea. It recommended scope cuts I'd already made, honest market sizing I didn't want to hear, and built a working MVP that showed me the gap between a prompt and a production system."
---

# I Fed My AI Pipeline Its Own Idea

Haytham is a Claude Code plugin that takes a startup idea through four phases: market research, MVP scoping, architecture decisions, and spec generation. Eight agents, structured handoffs, validation hooks. I've been building it for months.

At some point I had to try the obvious thing: feed Haytham its own idea and see what comes out.

So I typed this into a fresh Claude Code session: *"An open source Claude Code plugin that takes an Idea, researches it, provides recommendations on the research and competitors, proposes a MVP, suggests architecture, produce standardised specs and finally builds the system."* Then I sat back and let it run.

<!-- more -->

## What it said about my idea

The validation report came back GO, but barely. Composite score: 3.2 out of 5. Risk level: HIGH.

The market researcher estimated the addressable market at $3.6M. The report synthesizer, working from the same data, re-did the math with realistic open-source conversion rates and revised it down to $144K-$180K per year. One agent inflated the number. The next agent caught it and corrected it. This is the [synthesis pattern](../posts/2026-02-20-agents-playing-telephone.md) I wrote about earlier, and it was good to see it working on a real run rather than a test case.

The honest parts landed hard. "Break-even on opportunity cost is not realistic in Year 1 through direct monetisation." And: "If success requires revenue, this is the wrong approach. Pivot to a commercial SaaS." The system didn't know it was talking about itself. It just ran the numbers and said what the numbers said. And it's right. An open source developer tool with no paid tier, targeting a narrow ecosystem, has real financial risk. I'm building this because I think the problem is worth solving and the community will tell me if the solution is useful, not because the revenue math works out on a spreadsheet. It's worth being honest about that, especially when your own tool is the one telling you.

The scope recommendation matched a decision I'd already made months earlier: ship only the first four pipeline stages, defer spec generation and code build. The AI arrived at the same conclusion through the same reasoning, which was reassuring.

## What it built

Haytham generated a working Claude Code plugin. A real one, with a manifest, commands, skills, and an OpenSpec directory. It runs. I was genuinely curious whether the system could handle an input this far outside its usual territory (an AI pipeline tool, not a web app), and it produced a working MVP with reasonable architecture decisions and a sensible scope.

The generated plugin is simpler than the real system at every level: four skills instead of eight agents, in-context conversation history instead of structured JSON files, no web search for research, strict approval tokens instead of flexible checkpoints. The AI chose simplicity at every turn, which is the right instinct for an MVP.

The architecture summary landed on something I've been slow to fully accept: "The key architectural risks are all in prompt quality, making prompt engineering and stage skill design the primary engineering concern, not integration or infrastructure." The build-buy analysis concluded every component is PLATFORM. No database, no backend, no auth, zero monthly cost. Seeing the AI state that so plainly was a useful mirror.

If you showed this to someone unfamiliar with the project, they'd say the problem was solved. And as an MVP, maybe it is. But I've been building the real version for months, and I know where the simple version breaks.

## The gap

The input to this process was one paragraph. Sixty-some words. The real system behind those words has a CLAUDE.md with design pitfalls, 29 architecture decision records, eight agent prompts with carefully scoped responsibilities, hook scripts, and semantic checks that cross-reference outputs across files. Thousands of lines of accumulated knowledge from months of iteration. One paragraph can't carry that density. It can describe the *what*. It can't describe the *why not*.

The generated system has no concept anchors, no deterministic validation, no crash recovery. Why does the real system have these? Because without concept anchors, "invite-only marketplace for vintage furniture restorers" becomes "open marketplace" by phase three. I watched it happen repeatedly and wrote a [whole blog post](../posts/2026-02-20-agents-playing-telephone.md) about why. Because without deterministic validation, an earlier [dogfood run](https://github.com/arslan70/haytham/pull/51) produced a mega-capability that swallowed six scope items, and it passed validation because validation only checked JSON syntax, not whether the content made sense. The generated system doesn't know these failure modes exist, because they're not in the problem description. They're in the runtime behavior over dozens of runs.

These aren't bugs. They're the absence of scar tissue. Each piece of complexity in the real system traces back to a specific incident where the simpler version broke. The generated system is clean because it's never been run. The real system is messy because it has.

The generated system also produced some things the real system doesn't have: pre-implementation research questions per capability, and a half-time cut analysis that forces you to name what you'd drop under pressure. Small but useful ideas I'm adopting.

## What this means

I keep seeing people say that LLMs have solved software. For proof of concepts, that's close enough to true. A version of the tool exists at the end of the session. It works. But a proof of concept is not a production system. The gap between them is the accumulated knowledge of solving the problem: the failure modes, the edge cases, the constraints you add because you watched the simpler version break. That knowledge doesn't fit in a prompt. It fits in a codebase that's been run, broken, and fixed repeatedly. It's in your git history, not any training set.

The next step for Haytham is trying to close this gap. The current system takes an idea and produces an MVP. The next phase I'm working on takes a working MVP and a change request, and iterates it into an improved system. Whether the system can take the dogfood MVP, apply what I've learned from operating the real one, and iterate it toward something production-ready is an open question. But it's the right question to be working on.

The [Haytham repo](https://github.com/arslan70/haytham) is open source. The full dogfood session output is linked from the repo. If you want to run the same experiment on your own tool: `/haytham "your own tool's description here"`.
