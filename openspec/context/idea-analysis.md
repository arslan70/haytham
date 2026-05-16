## 0. Intent Analysis

- **Expectations:** Build a Claude Code plugin that takes a startup idea and produces a validated, traceable, implementation-ready product specification. Success means founders ship products that hold up over time, not just fast prototypes.
- **Conditions [inferred]:** Solo founder, no external funding signals, zero-infra constraint (no Python, no API keys, works within existing Claude Code subscription).
- **Targets:** Technical founders and indie hackers who use AI coding tools but get trapped between "app that works" and "product that survives."
- **Context:** The rise of vibe-coding tools (Lovable, Bolt, v0) creates fast apps but no durable product foundation. Haytham fills the gap between "AI built it" and "AI can maintain it."
- **Information:** Founder has already built the tool (8 agents, 4 phases, working plugin). The idea description reads like a product page. This is validation-for-distribution, not raw idea validation.

WHY-refinement: The stated idea is "build a lifecycle control plane." The deeper goal is credibility in the AI agent ecosystem and establishing a workflow standard before competitors do. Success means founders choose Haytham as the default starting point for AI-built products, not just a one-time experiment.

Backward-chain: If Haytham succeeds, founders have a durable reasoning graph linking intent to production. For that to happen, the tool must (a) produce output that prevents scope drift, (b) run fast enough to use on real ideas, and (c) be trusted enough that founders don't override it. The MVP already exists. The question is whether it drives adoption, not whether it works.

---

## 1. Problem Analysis

**Problem 1: AI-built apps have no traceable structure, so they break under change**
- **Trigger Moment:** "The user reaches for this product when they ask Claude to add a new feature and it silently breaks three existing ones, with no way to know why."
- **Trigger Confidence:** Observed (directly implied by the "evolvable" framing and the EVOLUTION milestone; the concept anchor mechanism exists specifically to solve this)
- **Current Workaround:** Founders manually maintain READMEs, comment code, or redo the entire build from scratch when the AI loses context.
  - **Effort:** High
  - Time estimates: [estimate: 2-8 hrs per major change] -- assumes a moderately complex app with no formal spec
- **Pain Intensity:** High (actively blocking; vibe-coders hit this wall within weeks of launch)

**Problem 2: Founders skip validation and build the wrong thing**
- **Trigger Moment:** "The user reaches for this product when they've spent three weeks building with Bolt and only then discover two direct competitors already own the niche."
- **Trigger Confidence:** Observed (Phase 1 is explicitly a GO/NO-GO verdict; the "if it says NO-GO, it tells you why — that's the point" line signals this is a real, witnessed failure mode)
- **Current Workaround:** Ad hoc Google searches, asking ChatGPT, or skipping validation entirely.
  - **Effort:** Medium
  - Time estimates: [estimate: 1-3 hrs of searching] -- assumes some effort; many founders do zero structured research
- **Pain Intensity:** High (the cost isn't time, it's weeks of wasted build effort)

**Problem 3: AI coding tools produce working code but not implementation-ready specs**
- **Trigger Moment:** "The user reaches for this product when they hand a vague prompt to Claude Code and get back something that works for the demo but diverges from what they actually intended."
- **Trigger Confidence:** Inferred (the Gherkin/OpenSpec/SHALL framing implies this is a known failure mode; not stated by a direct user quote)
- **Current Workaround:** Founders write specs in Notion or Google Docs, inconsistently, or rely on verbal corrections mid-build.
  - **Effort:** High
  - Time estimates: [estimate: 4-12 hrs for a real spec] -- assumes a non-trivial product with auth, data model, and 3+ flows
- **Pain Intensity:** Medium (causes friction and rework; some founders tolerate it by iterating post-build rather than pre-specifying)

---

## 2. Target User Segments

**Primary Segment: Technical founders who vibe-code MVPs and hit the maintenance wall**
- **Defining Behavior:** Regularly prompts Claude Code, Cursor, or similar tools to build features; has shipped at least one AI-built project; has experienced context loss or regression mid-build
- **Where to Find Them:** r/ClaudeAI, r/SideProject, Indie Hackers, Claude Code Discord, Hacker News "Show HN" posts about AI-built products
- **Trigger Context:** First time a feature addition breaks something unexpected, or first time they try to continue a build in a new AI session and it loses context
- **Budget Indicator:** Professional discretionary (already paying for Claude Pro or similar) [needs validation]
- **Urgency Driver:** They're mid-build. The pain hits at a specific moment, not in the abstract. Every day without a solution is compounding technical debt.

**Secondary Segment: Indie hackers who want to validate before building**
- **Defining Behavior:** Has multiple unfinished or failed projects; regularly evaluates new ideas; uses AI tools to test concepts quickly; treats validation as a step, not an afterthought
- **Where to Find Them:** Product Hunt, Indie Hackers, X/Twitter #buildinpublic, Hacker News
- **Trigger Context:** Before starting a new build, after a previous failed launch, or when they have two competing ideas and need to pick one
- **Budget Indicator:** Student to professional discretionary [needs validation]
- **Urgency Driver:** Opportunity cost. They've wasted time on bad ideas before and want a faster, honest kill signal before committing weeks of effort.

---

## 3. Unique Value Proposition

"Technical founders get a validated, traceable product spec from a single Claude Code command, in under 20 minutes."

---

## 4. Solution Concept

- **Core Value Delivery:** Run one command. Get a GO/NO-GO verdict backed by market evidence, then a traceable path from validated need to implementation-ready spec. Every decision links back to a real requirement.
- **Key Capabilities:**
  - Market research + honest GO/NO-GO verdict -> addresses Problem 2
  - MVP scope with explicit in/out boundaries -> addresses Problem 2 and Problem 3
  - Concept anchor extraction (prevents downstream genericization of the idea) -> addresses Problem 1 and Problem 3
  - Full traceability graph: validated need -> capability -> decision -> spec -> addresses Problem 1
  - OpenSpec with Gherkin scenarios, ready for any coding agent -> addresses Problem 3

---

## 5. Lean Canvas Summary

- **Problem:** (1) AI-built apps break under change with no traceable structure. (2) Founders skip validation and build the wrong thing. (3) AI tools produce working code but not durable specs.
- **Segments:** Technical founders hitting the maintenance wall (primary). Indie hackers who want pre-build validation (secondary).
- **UVP:** Technical founders get a validated, traceable product spec from a single Claude Code command, in under 20 minutes.
- **Solution:** Single-command Claude Code plugin. Eight specialist agents. Market research, GO/NO-GO verdict, MVP scope, capability model, architecture decisions, OpenSpec with Gherkin scenarios. Concept anchors prevent drift. Full traceability from idea to spec.
- **Unfair Advantage:** Zero setup (no Python, no API keys, works inside existing Claude Code subscription). Self-referential credibility: Haytham was built using the process it advocates. The reasoning graph is a structural moat if EVOLUTION and SENTIENCE milestones ship.

---

## 6. Concept Health Signals

- **Pain Clarity:** Clear
- **Trigger Strength:** Strong (Problems 1 and 2 are Observed; both have sharp trigger moments tied to documented failure modes in the vibe-coding workflow)
- **Willingness to Pay Signal:** Present (target users already pay for Claude Pro; zero-setup removes the activation friction barrier)
