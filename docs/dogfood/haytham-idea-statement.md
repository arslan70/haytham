# Haytham Idea Statement

> This is the input fed to Haytham's own pipeline for the dogfooding session. It describes Haytham as a startup idea, written in the same format a user would submit.

---

**Idea:**

A specification-driven control plane that transforms startup ideas into validated, implementation-ready specifications via multi-agent AI.

**The problem:**

Going from "I have a startup idea" to "I have a plan worth building" requires weeks of planning, domain expertise across product, market research, architecture, and engineering, and significant capital. Most founders skip this work and jump straight to building, leading to wasted effort on ideas that don't hold up, MVPs that miss the mark, and codebases that can't evolve.

AI coding agents have made building faster, but they haven't solved the harder problem: knowing *what* to build. Code generation without validated specification is speed in the wrong direction.

**Target users:**

- Technical founders who want evidence-based validation before committing to implementation
- Solo developers who lack access to product strategists, market researchers, and architects
- Agencies and studios that need to rapidly scope and spec client projects

**What it does:**

Haytham orchestrates 21 specialist AI agents through four sequential phases, each answering one question:

1. **Should this be built?** Market research, competitor analysis, risk assessment, and a GO/NO-GO/PIVOT verdict backed by evidence. If risks are high, pivot strategies are generated automatically.
2. **What exactly?** MVP scoping, capability modeling, and system trait classification.
3. **How to build it?** Build-vs-buy analysis and architecture decisions, each linked to the capabilities they serve.
4. **What are the tasks?** Implementation-ready user stories with acceptance criteria, dependency ordering, and full traceability back to capabilities and decisions.

A human approval gate separates each phase. Nothing proceeds without sign-off.

**What makes it different:**

- **Specification, not code generation.** The output is a traced specification (capabilities, decisions, stories) that any developer or coding agent can execute. This is the missing layer between "business intent" and "code."
- **Honesty over flattery.** The system can say NO-GO at the first gate. It validates assumptions against evidence rather than confirming what the founder wants to hear.
- **Traceability throughout.** Every story traces to a capability, every capability to a validated need, every decision to its rationale. This is what enables the system to evolve an existing application rather than starting from scratch each time.
- **Human-in-the-loop.** Four approval gates ensure humans make the decisions. The system provides analysis, humans provide judgment.

**Current state:**

Genesis (Milestone 1) is complete: four specification phases are implemented and validated end-to-end. A real startup idea ("gym community leaderboard") was run through the full pipeline, producing 10 implementation-ready stories that were executed into a working application.

Next milestone (Evolution) extends the system so that an existing application plus a change request produces an updated, validated system with full traceability.
