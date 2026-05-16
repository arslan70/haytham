# Haytham: A Technical Brief for Potential Collaborators

## The Vision

Haytham is an autonomous control plane for startups. You describe an idea. It validates whether the idea is worth building, generates an implementation-ready specification, hands that spec to coding agents, deploys the result, monitors production, and continuously improves the system based on what it observes.

The full loop: **validate → specify → build → deploy → monitor → improve.** Each cycle tightens. Human approval gates control how much autonomy the system has at each stage. Early on, you approve everything. Over time, you define policies: auto-approve bug fixes and performance optimizations, require human sign-off on new features and UX changes. The system earns trust incrementally.

This isn't a single product. It's three milestones, each adding a new loop to the control plane:

- **GENESIS** (current): Idea → validated specification. Market research, MVP scoping, architecture decisions, implementation-ready spec. The system tells you whether to build, then tells agents *what* to build and *why*.
- **EVOLUTION** (next): Running system + change request → updated, validated system. You say "add PDF export" or "fix login on Safari." The control plane traces the change through the specification, determines what's affected, generates the updated spec, delegates execution, and validates the result.
- **SENTIENCE** (long-term): Running system + production telemetry → continuous autonomous improvement. The system detects a slow API endpoint, analyzes the root cause, proposes a fix, executes it within approval policies, and validates the outcome. No human in the loop for changes that fall within policy. Human approval for everything else.

The architectural bet: as coding agents commoditize execution, the durable value moves to the layer that holds business context, enforces traceability, and governs what gets built. Haytham is that layer. It specifies intent and delegates execution. This is the design constraint that every architectural decision must preserve.

## Where We Are: GENESIS

The first milestone is working. Four phases, ten specialist agents, human approval gates between phases.

```
Phase 1 (WHY)   Idea analysis → market research → competitor research → GO/PIVOT/NO-GO
Phase 2 (WHAT)  MVP scoping → capability decomposition → system trait classification
Phase 3 (HOW)   Build-vs-buy analysis → architecture decisions → research directives
Phase 4 (SPECS)  OpenSpec generation with SHALL requirements and Gherkin scenarios
```

Delivered as a Claude Code plugin. One install command, zero infrastructure. The user types `/haytham "my startup idea"` and gets a structured session directory with validated artifacts at each phase.

This is the foundation the other milestones build on. GENESIS establishes the traceability chain (every requirement traces to a capability, every capability to a user need, every architecture decision to a rationale). EVOLUTION and SENTIENCE depend on that chain being intact, because you can't safely automate changes to a system you can't reason about structurally.

## What I've Learned Building This

This section is why I'm writing. The interesting part isn't the product. It's the failure modes I've hit in multi-agent system design and what they reveal about how these systems should be built.

### Multi-agent pipelines are lossy compressors

I started with a 4-agent synthesis pipeline for the validation report: a drafter, a critic, a reviser, and a finalizer. Six validators ran between stages to catch inconsistencies. The result: 1 PASS, 3 PARTIAL, 8 FAIL on quality criteria.

Then I replaced it with a single agent that had full upstream context. Same inputs, same criteria. Result: 8 PASS, 4 PARTIAL, 0 FAIL.

The failure wasn't in any individual agent. It was at the boundaries. Each handoff is lossy compression. Stack enough of them and you get noise. Research backs this up (Kim et al., 2025: 34% context overlap after 10 interactions, 17.2x error amplification in decentralized multi-agent systems).

The lesson: split agents along tool boundaries (web search vs. analysis) or model tier boundaries, not along reasoning steps. If a task requires holistic reasoning over a shared context, keep it in one agent. If you're adding a validator to catch inconsistencies between two agents' outputs, you probably have an architecture problem, not a validation problem.

### LLMs drift toward the generic

Every agent in the pipeline has a gravitational pull toward its training data median. A "gym community leaderboard with anonymous handles" becomes "a fitness tracking app" by Phase 3 if you don't actively prevent it.

The fix: concept anchors. Extract specific invariants (nouns, verbs, constraints) from the raw idea in Phase 1, store them in a JSON file, and pass them unchanged to every downstream agent. Not embedded in prose for re-extraction. Passed as structured data, like function arguments.

This was the single biggest lever against genericization. It works because it treats the problem as an information architecture problem, not a prompt engineering problem.

### Deterministic rules must override LLM judgment

Early versions let the validation report agent decide whether SOM numbers were consistent. It was unreliable. Now, SOM arithmetic is checked by a Python script. Regulated domain detection (HIPAA, PCI-DSS, COPPA) is regex-based, not LLM-based.

The principle: LLMs do qualitative judgment (evaluating evidence, scoring feasibility). Code does deterministic rules (arithmetic, schema validation, prerequisite checks). Keep this boundary sharp. If you let LLM-generated text override a deterministic safety rule, you've introduced a class of bugs that are invisible until they're catastrophic.

### Evidence must match evaluation

Early agent prompts included scoring dimensions like "regulatory risk" and "competitive moat strength" without verifying that upstream research actually produced data for those dimensions. The agents scored them anyway, confidently. The scores were hallucinated.

The fix: if you can't name the specific data source that populates a score, delete the score. Every evaluation criterion must trace to an evidence source. This sounds obvious. It's easy to violate when you're writing prompts iteratively.

### The distribution problem is architectural

Haytham started as a standalone Python system: Burr state machine, Strands agents, OTEL tracing, Streamlit UI. Proper infrastructure. Zero users. The 9-step setup (install Python, configure AWS credentials, set up Streamlit) killed adoption before anyone saw the product.

The pivot to a Claude Code plugin traded deterministic workflow enforcement for probabilistic (Claude following instructions instead of a state machine). It traded structured output validation at generation time for post-hoc hook scripts. It traded OTEL tracing for file-based debugging.

These are real losses. But the gain was zero-setup distribution to every Claude Code subscriber. The product now meets developers where they already are, instead of asking them to set up a separate environment.

The fallback plan is documented: if probabilistic enforcement proves too unreliable, run the workflow engine as an MCP server that Claude Code calls. This preserves deterministic enforcement while keeping the plugin UX.

## Engineering State

- 8 agents, 5 commands, 3 validation scripts, 141 CI tests
- Eval framework: 22 quality criteria across 8 rubrics, LLM-as-Judge grading, baseline regression detection
- Zero production dependencies. Evals shell out to the `claude` CLI. No API keys in config
- 247 commits over 14 months. 29 architecture decision records documenting what was tried, what failed, and why
- MIT licensed, published to Claude Code plugin marketplace (v0.3.11)
- End-to-end validated: gym leaderboard idea → OpenSpec → working Next.js app

## Honest Assessment

**What works:** The four-phase workflow produces coherent, traceable output. Concept anchors prevent drift. The plugin distribution model eliminates setup friction. The eval framework measures output quality across 22 dimensions.

**What's unproven:** Only one end-to-end validation (idea → spec → working app). The EVOLUTION and SENTIENCE milestones are theoretical. Market demand is unvalidated (targeting 5 real users by April 1, 2026; haven't hit it yet). The dogfood run estimated a $144K-$180K/year addressable market for the open-source version, which doesn't break even on opportunity cost in Year 1.

**What I got wrong along the way:** I built a 4-agent pipeline where a single agent was better. I added 6 validators to fix a boundary problem instead of fixing the boundary. I built standalone infrastructure when distribution was the bottleneck. I created scoring dimensions without evidence sources. Each of these is documented in the ADR history.

## What I'm Looking For

I'm not pitching a job or an equity split. I'm looking for a software architect who reads the above and thinks: "I've hit these same problems" or "I see where this breaks next."

Specifically:

- **Does the control-plane thesis hold?** Is specification-as-orchestration the right abstraction for governing autonomous systems, or is there a better framing?
- **Where does GENESIS break?** What happens when ideas are more complex than a web app? When the capability model doesn't decompose cleanly? When the spec doesn't match what a coding agent actually builds?
- **Is the EVOLUTION milestone viable?** Can you take a running system + a change request + a traceability chain and produce a validated, safe update? Or does the real world break the traceability assumptions?
- **What does the monitor → improve loop actually look like?** SENTIENCE requires detecting problems from telemetry, tracing them back through the spec, and generating targeted fixes. What are the hard subproblems here?

If any of this resonates, I'd like to talk. Not to sell you on anything, but to find out if we think about these problems the same way.

**Repository:** https://github.com/arslan70/haytham
**Architecture decisions:** `docs/system-evolution.md`
**How it works:** `docs/how-it-works.md`

To try it: install the Claude Code plugin (`/plugin marketplace add arslan70/haytham`), then run `/haytham "your idea here"`.
