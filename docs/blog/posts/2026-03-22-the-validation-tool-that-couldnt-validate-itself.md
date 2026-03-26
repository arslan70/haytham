---
date: 2026-03-22
authors:
  - haytham
categories:
  - Multi-Agent Systems
  - Open Source
tags:
  - dogfooding
  - agents
  - validation
  - meta
description: "I ran my idea validation tool on its own idea. It found the surface risks. It missed the existential one."
---

# The Validation Tool That Couldn't Validate Itself

I've been building Haytham for months. It's a Claude Code plugin that orchestrates AI agents to validate startup ideas, scope MVPs, design architecture, and generate specs. Eight agents, four phases, structured handoffs, the whole thing.

A few weeks ago I had a long conversation with someone who poked holes in the project until I couldn't patch them anymore. The conclusion: Haytham has an identity crisis. It presents as a validation tool, but the actual vision is a lifecycle control plane for AI-built products. The validation pipeline is phase one of a three-phase vision that only I can see. Everyone else sees a validation tool in a crowded market.

That conversation surfaced a specific finding I couldn't shake: the product I'm building (Genesis, the validation pipeline) isn't the real product. The real product is Evolution, the phase where the reasoning graph I'm building gets used to handle change requests without full rewrites. Without Evolution, Genesis is a well-structured validation tool competing with ChatPRD and ValidatorAI. With Evolution, it's something genuinely new.

So I did the obvious thing. I ran `/haytham:validate` on Haytham's own idea and compared what the tool found to what that conversation found.

<!-- more -->

## What the tool caught

The validation report came back GO with a 3.4/5.0 composite score and MEDIUM risk. Not a ringing endorsement. The interesting parts were in the evidence classification.

It correctly identified willingness to pay as the biggest unknown. The target segment (solo founders, indie hackers) is price-sensitive. The competitive category is freemium-dominant. There's no pricing signal in the idea. It classified Hypothesis 3 ("Solo founders will pay $10-15/month for this workflow") as Unsupported. That's honest, and it matches the real situation.

It found the right competitors: BrainGrid (closest threat, web app not a native plugin, 2K users), ChatPRD (100K users, PRD-only), ValidatorAI (300K users, scoring-only). The competitive gap analysis was solid. No one owns the full validate-to-spec workflow inside the coding environment. That gap is real and the tool identified it cleanly.

It flagged platform dependency. Haytham's distribution is 100% coupled to Anthropic's Claude Code plugin ecosystem. If Anthropic builds native validation features, the plugin surface shrinks. Standard platform risk, correctly identified.

The most surprising finding: "The real competitor is a well-crafted prompt." Not BrainGrid. Not ChatPRD. Just Claude with a good prompt. The report noted that Claude was rated the top tool for PRD writing in head-to-head tests, and as frontier models improve, the bar rises for what a specialized tool must deliver. This is a finding that most validation tools would soften or bury. The report put it front and center.

## What the tool missed

The identity crisis. The report analyzed Haytham as a coherent product with a clear scope: four-phase pipeline, solo founder target, plugin delivery. It didn't see the tension between "this is a validation tool" and "this is phase one of a lifecycle control plane." It couldn't, because the idea description didn't contain the three-phase vision. The tool validated what was in front of it.

This is the fundamental limitation. A validation pipeline processes the idea you give it. The adversarial conversation processed the *founder* and the gap between what the founder says and what the founder means. The pipeline saw a product. The conversation saw a sequencing problem.

The "Evolution is the real product" insight. The report recommends building the full four-phase pipeline and monetizing with a Pro tier. That's reasonable advice for the product as described. But the earlier conversation concluded the opposite: the pipeline is scaffolding for a reasoning graph, and the reasoning graph only earns its value when Evolution exists to use it. The report optimized for the wrong objective because it was given the wrong frame.

The unvalidated core assumption. The earlier conversation identified one assumption everything depends on: when an AI-built system needs to change, does having the upstream reasoning context produce materially better outcomes than having specs alone? The validation report never asked this question. It tested whether the market exists, whether competitors cover the gap, whether the distribution channel works. It didn't test whether the core thesis holds. It validated the business around the product without validating the product's reason to exist.

## What this actually means

Here's what I think is useful about this experiment, beyond the meta entertainment value.

Automated validation is good at surface-level market analysis. The competitive landscape, market sizing, pricing benchmarks, risk categorization: the tool did all of this competently. If I were evaluating a *different* startup idea, one where I didn't already know the answer, the report would give me a solid foundation for decision-making.

But automated validation operates on the description you provide. It can't interrogate the gap between what you say and what you mean. It can't notice that your "phase one" is actually someone else's "complete product." It can't ask "wait, if Evolution is where the value lives, why are you building Genesis first?" That kind of questioning requires a model of the founder's intent that goes beyond the idea description, and it requires the willingness to challenge the frame, not just analyze within it.

The earlier conversation worked because it kept pulling on threads until the framing broke. The validation tool worked because it thoroughly analyzed the frame it was given. Both are useful. They answer different questions.

If you're using AI to validate an idea, the tool will tell you whether the market exists, who the competitors are, and what the risks look like. It will not tell you whether you're building the right thing. For that, you need someone (or something) willing to ask "why are you actually building this?" and not accept the first answer.

## What we're doing about it

The three things the tool missed (identity crisis, "Evolution is the real product," unvalidated core assumption) all stem from one root cause: the pipeline processes the idea but ignores the founder. It never asks *why* you're building, what success looks like to you personally, or what constraints you're working with. It analyzes the market around a product description without questioning whether that product serves the founder's actual goals.

I went looking for how other AI systems handle this. I expected to find established patterns for "raw idea to structured intent." I didn't. Every major framework (LangChain, A2A, Bedrock Agents) resolves intent-to-action: "which tool should I call?" Product tools like Productboard analyze intent retrospectively from existing customer feedback. Nobody captures prospective intent from a vague idea and a founder who may not fully know what they want yet.

The closest useful patterns came from unexpected places. Requirements engineering has a technique called WHY-refinement: keep asking "why does this goal exist?" until you surface the real goal beneath the stated one. Theory of Change works backward from desired impact to required activities, which inverts the default forward analysis. Industrial automation research has a five-component intent model (Expectations, Conditions, Targets, Context, Information) that maps well to founder intake.

We're rebuilding Phase 1 around these patterns. The idea-analyst now starts with intent analysis before problem analysis. It asks what the founder expects, what constraints exist, and why they're building this now. The report-synthesizer gets three new sections: positioning analysis (where do you fit and is it defensible?), strategic options (paths beyond "build the MVP"), and an assumptions-and-evidence breakdown that separates belief from data. The 3-question intake at the start captures motivation, success criteria, and team constraints so the whole pipeline can calibrate to the founder, not just the idea.

I think this will help. I haven't validated it yet. The patterns are sound, the research supports the approach, but the proof is in whether the tool would now catch what it missed when it analyzed itself. That's the next test.

## Where this leaves the project

I shared the [earlier dogfood run](2026-03-18-i-fed-my-ai-pipeline-its-own-idea.md) where I ran Haytham through all four phases and it built a working MVP of itself. That post was about the gap between a generated MVP and a production system. This experiment is about a different gap: the one between analyzing a market and questioning a strategy.

Both gaps point in the same direction. The interesting problems in AI-assisted development aren't in generation. They're in the accumulated context that makes generation useful: why this feature exists, why that constraint was added, what broke when we tried the simpler version. The [telephone game problem](2026-02-20-agents-playing-telephone.md) I wrote about earlier is the technical version of this. The identity crisis is the strategic version.

I'm still figuring out what Haytham becomes. The validation pipeline works. The question is whether it's a product or a demo for the thing that comes after it. If you want to run the same experiment on your own project: `/haytham:validate "your own tool's description here"`. The [repo is open source](https://github.com/arslan70/haytham). I'm curious whether your tool finds the same blind spots mine did.
