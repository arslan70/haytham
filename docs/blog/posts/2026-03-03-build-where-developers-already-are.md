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
description: "Haytham is now a Claude Code plugin. One command to install, no AWS, no Python. Here's why I rebuilt it and what I learned."
---

# Haytham Is Now a Claude Code Plugin

Haytham turns a startup idea into a validated, implementation-ready specification. Market research with live web search, MVP scoping, architecture decisions, dependency-ordered stories with acceptance criteria. Four phases, each with a human approval gate before the next one starts.

Starting today, you can install it inside Claude Code:

```
/plugin marketplace add arslan70/haytham
/plugin install haytham@haytham
```

No Python. No AWS credentials. No Streamlit. Your existing Claude Code subscription handles everything.

This post is about why I rebuilt it this way, what I gave up, and what I think it means for developer tools.

<!-- more -->

## How I got here

I originally built Haytham as a standalone system. Strands SDK for agent orchestration, Burr for a deterministic workflow engine, Streamlit for the UI, OTEL with Jaeger for tracing. Each choice was individually reasonable. Together, they created a setup process that looked like this:

1. Clone the repo
2. Install Python and UV
3. Run `uv sync`
4. Create an AWS account (if you don't have one)
5. Request access to Claude models on Amazon Bedrock
6. Configure AWS credentials locally
7. Set environment variables for three model IDs and a region
8. Run `make run` to start Streamlit
9. Open a browser, paste an idea, and wait

Nine steps before any value. Steps 4 through 7 are where everyone dropped off. People would star the repo, maybe clone it, then disappear. Zero issues filed, zero discussions opened. Nobody was getting past the setup.

The system worked. I proved it end-to-end by generating a spec for a gym leaderboard app and building the whole thing from the generated stories. The planning intelligence was real. The distribution was broken.

## Why a plugin

Developers already have a coding agent in their terminal. They're already paying for the subscription. If the planning workflow lives *inside* that tool, the setup cost drops to zero and something else becomes possible: the specification pipeline can hand off directly to code implementation in the same session. The spec stops being documentation you copy into a coding agent. It becomes the direct input, in the same conversation. Idea in, working code out, one tool.

The agent prompts port to subagent markdown files. The phased workflow becomes skill instructions. Decision gates use Claude Code's built-in question prompts. Session state writes to files. The intelligence survives. The scaffolding gets deleted.

## AWS is leaving the door open

The Bedrock credential wall deserves its own mention. AWS builds for enterprises with procurement teams and infrastructure budgets. That's a fine business. But it means an individual developer who wants to experiment with an open-source AI tool hits a wall of IAM roles, model access requests, and region-specific configurations before they write a single prompt.

Anthropic's direct API has the same models with a credit card and an API key. Claude Code goes further: plugin users don't need *any* credentials. The developer experience gap between "configure AWS Bedrock" and "install a plugin" is enormous. For solo founders and small teams building on these models, AWS is creating friction that pushes builders toward platforms with lower barriers. That's an audience worth competing for.

## What I'm giving up

I'm trading real capabilities for distribution, and I want to be specific about what's lost.

Burr's state machine guaranteed phases ran in order. In a plugin, I'm relying on Claude following instructions, which is probabilistic. OTEL tracing is gone. Multi-model routing becomes a coarser choice of sonnet, opus, or haiku per agent.

The loss I worry about most is **structured output**. Strands validates agent output against Pydantic models at generation time. The schema is enforced as the tokens are produced. In Claude Code, agents return text. I can validate with hook scripts after the output is written, but that's a fundamentally weaker guarantee. If a market analysis agent returns malformed JSON, I catch it after it's already in the session state, not before. For a pipeline where each phase builds on the last, late validation means errors propagate further before they're caught. I don't have a clean answer for this yet. It's the biggest open risk.

If the loss proves too costly, there's a fallback: run the workflow engine as an MCP server that Claude Code calls, keeping deterministic enforcement while still distributing as a plugin. I'd rather not need it.

## The bigger bet

The Claude Code plugin marketplace feels like the early days of mobile app stores. The catalog is small. The platform APIs are still evolving. Discovery is basic. If you squint, it looks like the App Store in 2008: a few hundred apps, obvious gaps everywhere, and a platform owner still figuring out what developers need.

If Anthropic keeps investing in the extension model (richer subagent capabilities, structured output support, a proper marketplace with reviews and rankings), this could become the distribution channel for developer tools the way app stores became the channel for mobile software. That's a big "if," and building on it is a bet. I'm making that bet because the alternative, maintaining my own infrastructure stack while nobody uses it, is a worse one.

For other solo founders building AI-powered developer tools: start on a platform. You get distribution, LLM costs handled, and tool integration without building any of it yourself. Optimize for the feedback loop. A messy version that 100 people try is worth more than an elegant one nobody runs. And don't count your agents. Nobody cares how many you have. They care whether the output is good.

## Try it

```
/plugin marketplace add arslan70/haytham
/plugin install haytham@haytham
```

Once installed, start with `/haytham` and paste your startup idea. The workflow runs through four phases (validate, specify, design, plan), each with a gate where you review findings and decide whether to continue. At the end, you get an execution contract that Claude Code can implement directly.

The [system evolution doc](https://github.com/arslan70/haytham/blob/main/docs/system-evolution.md) covers the lessons and trade-offs in detail. The [Haytham repo](https://github.com/arslan70/haytham) is open source. If you hit problems or have ideas, [open an issue](https://github.com/arslan70/haytham/issues).
