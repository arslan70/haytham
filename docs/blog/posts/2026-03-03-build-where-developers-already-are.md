---
date: 2026-03-03
authors:
  - haytham
categories:
  - Open Source
  - Strategy
tags:
  - distribution
  - solo-founder
  - agentic-frameworks
  - claude-code
description: "Nine setup steps. Zero users. So I deleted the infrastructure and shipped it as a Claude Code plugin. Here's why and what I learned."
---

# Why You Should Ship Your Agentic Workflow as a Claude Code Plugin

Haytham takes a startup idea and stress-tests it: is the market real, what's the MVP, how should you build it? You review the findings at each step. At the end, you get a spec detailed enough to hand straight to a coding agent.

I started out with a full-fledged agentic framework (Strands SDK). That gives you a lot of flexibility and control over the agents, but it also comes with a lot of overhead. If the overhead was on the system only, it would have been fine, but it was on the user too.

My goal was to validate the idea from users, which ironically is the product I was building. In my test runs it worked great, but I didn't realise that the setup was a deal breaker for most people. This made me rethink my approach, and I decided to sacrifice the bells and whistles for something that can be tested with one prompt, if you already have Claude Code.

Starting today, you can install it inside Claude Code:

```
/plugin marketplace add arslan70/haytham
/plugin install haytham@haytham
```

No Python. No AWS credentials. No Streamlit. Your existing Claude Code subscription handles everything.

If you're building AI-powered developer tools, the trade-offs below might save you some time.

<!-- more -->

## The setup that killed adoption

This is what the setup looked like before the plugin:

1. Clone the repo
2. Install Python and UV
3. Run `uv sync`
4. Create an AWS account (if you don't have one)
5. Request access to Claude models on Amazon Bedrock
6. Configure AWS credentials locally
7. Set environment variables for three model IDs and a region
8. Run `make run` to start Streamlit
9. Open a browser, paste an idea, and wait

Nine steps before any value. Steps 4 through 7 are where everyone dropped off. People would star the repo, maybe clone it, then disappear. Zero issues filed, zero discussions opened. The Bedrock credential wall alone (IAM roles, model access requests, region-specific config) was enough to kill adoption for anyone without an enterprise AWS setup.

As a solo founder, I spent most of my time on the engineering and assumed that was the hard part. Getting someone to actually run it and tell me what's broken turned out to be much harder. I proved the intelligence end-to-end by generating a spec for a gym leaderboard app and building the whole thing from the output. But that was just me testing my own assumptions. Without real users hitting real edges, I had no idea if any of it actually held up.

## Why a plugin changes things

I noticed that the developers I wanted to reach already had a coding agent in their terminal and were already paying for the subscription. So the question became: what if the planning workflow just lived inside that tool? The setup cost drops to zero, and you also get something I hadn't thought about initially. The specification pipeline can hand off directly to code implementation in the same session. The spec isn't documentation you copy into a coding agent anymore, it's the direct input in the same conversation. You go from idea to working code without leaving the terminal.

The port turned out to be surprisingly clean. Agent prompts became subagent markdown files, the phased workflow became skill instructions, and decision gates mapped to Claude Code's built-in question prompts. Session state just writes to files. The planning logic all carried over, and I was able to throw out the rest of the infrastructure.

## What this costs

There are real trade-offs, and I want to be honest about them because you'll hit the same ones if you go down this path.

Burr's state machine guaranteed phases ran in order. In a plugin, that relies on Claude following instructions, which is probabilistic, and you lose OTEL tracing entirely. Multi-model routing becomes a coarser choice of sonnet, opus, or haiku per agent. The upside is that every test run against Bedrock used to cost real money, and during development you run the pipeline a lot. That bill goes to zero.

The one that worries me most is **structured output**. With Strands, agent output gets validated against Pydantic models at generation time, so the schema is enforced as the tokens are produced. In Claude Code, agents return text. You can validate with hook scripts after the output is written, but that's a weaker guarantee. If a market analysis agent returns malformed JSON, you catch it after it's already in the session state, not before. For a pipeline where each phase builds on the last, that means errors can propagate further before they're caught. I don't have a clean answer for this yet.

If that loss proves too costly, there's a fallback I've been thinking about: running the workflow engine as an MCP server that Claude Code calls into. That would keep deterministic enforcement while still distributing as a plugin. I'd rather not need it, but it's good to know the option exists.

## The bigger bet

The Claude Code plugin marketplace is early. The catalog is small, platform APIs are still evolving, and discovery is basic. I'm betting that Anthropic keeps investing in the extension model, things like richer subagent capabilities, structured output support, and a proper marketplace with reviews and rankings. If that happens, this could become a real distribution channel for developer tools. That's a big "if," and I know I'm building on a platform I don't control. But the alternative was maintaining my own infrastructure stack while nobody used it, and that felt like a worse bet.

If you're building something similar, I'd say focus on whether the output is actually good. Nobody's going to care about your architecture if the results aren't useful.

## Try it

```
/plugin marketplace add arslan70/haytham
/plugin install haytham@haytham
```

Once installed, run `/haytham` and paste your startup idea. The workflow goes through four phases (validate, specify, design, plan), and each one has a gate where you review findings and decide whether to keep going. At the end you get an OpenSpec that Claude Code can implement directly.

The [system evolution doc](https://github.com/arslan70/haytham/blob/main/docs/system-evolution.md) covers the lessons and trade-offs in detail. The [Haytham repo](https://github.com/arslan70/haytham) is open source. If you hit problems or have ideas, [open an issue](https://github.com/arslan70/haytham/issues).
