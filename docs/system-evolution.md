# System Evolution

How Haytham got here. 29 ADRs from Jan 2025 to Mar 2026 documented a standalone Python system that was replaced by a Claude Code plugin. The lessons below tell the coding agent what was tried, what failed, and what to preserve.

## The Journey

**Jan 2025**: Started as a Notes App PoC. A single agent that took a startup idea and produced a loose requirements document. No validation, no phases, no traceability.

**Feb-Apr 2025**: Built the multi-phase workflow. Added market research with web search, competitor analysis, MVP scoping, architecture decisions, and story generation. Introduced Burr as the workflow engine, Strands SDK for agent orchestration, and Streamlit for the UI. Agent count grew from 1 to 23.

**May-Aug 2025**: Quality crisis. Output looked plausible but failed on inspection. The "telephone problem" (ADR-022): each agent slightly genericized the idea until the output described a different product. Scoring dimensions didn't match evidence sources (ADR-023). A 4-agent validation pipeline produced worse output than a single agent (ADR-026).

**Sep 2025 - Feb 2026**: Fixes and stabilization. Concept anchors (ADR-022), dimension reduction (ADR-023), single-agent synthesis (ADR-026), system trait detection (ADR-019), execution contract schema (ADR-028), and spec export (OpenSpec + Spec Kit). Validated end-to-end with a gym leaderboard idea that produced 10 stories, executed into a working Next.js app.

**Mar 2026**: Plugin pivot (ADR-029). The planning intelligence worked. The distribution was broken (9-step setup, zero adoption). Rebuilt as a Claude Code plugin: 23 agents consolidated to 8 markdown files, Burr state machine replaced by skill instructions, Streamlit UI replaced by terminal interaction. One command to install, zero credentials to configure.

## Lessons

### 1. Four-Phase Workflow (ADR-016)

The workflow has four phases: WHY (validate the idea), WHAT (scope the MVP), HOW (architecture decisions), SPECS (specification generation). Each phase ends with a human approval gate. The gate after WHY is the most important: it produces a GO/PIVOT/NO-GO recommendation backed by evidence.

Why four and not three: early versions combined validation and scoping. This consistently produced MVPs that included unvalidated assumptions. Separating "is this worth building" from "what should the MVP include" forces the evidence to exist before scoping begins.

### 2. Concept Fidelity (ADR-022)

Progressive genericization is the #1 failure mode in multi-phase pipelines. Each agent slightly generalizes the idea to hedge its analysis, and by Phase 3 the output describes a generic SaaS platform, not the user's actual idea.

The fix: extract "concept anchors" from the raw idea in Phase 1 (specific nouns, verbs, and constraints the user chose). Every downstream agent receives these anchors and is instructed to preserve them. Post-validation checks that anchor terms appear in the output. If a user says "gym leaderboard with anonymous handles," downstream output must reference gyms, leaderboards, and anonymity, not "a community engagement platform with privacy features."

### 3. Single Agent for Synthesis (ADR-026)

A single agent with full upstream context scored 8 PASS / 4 PARTIAL / 0 FAIL on report quality criteria. A 4-agent pipeline with 6 deterministic validators processing the same inputs scored 1 PASS / 3 PARTIAL / 8 FAIL.

The failure mode: splitting reasoning across agents creates information loss at boundaries. A scorer agent produces numbers without narrative context. A narrator agent writes prose without access to the scoring rationale. A merge function stitches them together. Validators catch inconsistencies that wouldn't exist if one agent had the full picture. If you're adding a validator to fix disagreements between two agents, you have an architecture problem.

Multi-agent IS justified when agents need different tools (web search vs. analysis), different model tiers, or operate on genuinely independent tasks. Gathering information: split. Synthesizing information: don't split.

### 4. System Traits Over Categories (ADR-019)

Don't classify ideas into categories (e.g., "marketplace," "SaaS," "social"). Categories are mutually exclusive and miss hybrid ideas. Instead, detect traits: has_user_auth, has_payments, has_real_time, has_marketplace_dynamics, needs_mobile. Traits compose. A gym leaderboard has user_auth + real_time + social_features. A freelance marketplace has user_auth + payments + marketplace_dynamics. The architecture and spec generation respond to traits, not categories.

### 5. Evidence Must Match Evaluation (ADR-023)

Don't create scoring dimensions that your evidence sources can't populate. The original market validation had 8 scoring dimensions but only 5 evidence clusters from web research. Three dimensions were scored by the LLM hallucinating plausible-sounding analysis with no backing data. Reduced to 6 dimensions, each mapped to a specific evidence source. The rule: if you can't name the upstream data that populates a score, delete the score.

### 6. Deterministic Post-Processing (ADR-028)

LLM agents produce qualitative output (analysis, recommendations, prose). Deterministic code transforms it into structured artifacts (JSON schemas, execution contracts, dependency graphs). Never ask an LLM to produce a perfectly formatted JSON structure. Ask it to reason, then parse the reasoning into structure with code. This separation also means validation rules (arithmetic checks, required fields, cross-references) run in code, not as LLM re-prompts.

### 7. Build vs Buy Guidance (ADR-013)

Always recommend BUY for commodity components: authentication (Auth0, Clerk), payments (Stripe), email (SendGrid), file storage (S3/CloudFlare R2). The signal: if a component has multiple mature SaaS providers and isn't a differentiator for the startup, it's a BUY. Only recommend BUILD for capabilities that are core to the startup's value proposition.

### 8. Agent Testing (ADR-018)

Test agent output with LLM-as-Judge, not snapshot tests or mocks. Snapshot tests are brittle (any rewording breaks them). Mocks test the harness, not the agent. LLM-as-Judge evaluates against a criteria checklist using real inputs and real model calls. Each criterion has PASS/PARTIAL/FAIL with specific definitions. Run against multiple test ideas (different archetypes: B2C app, B2B tool, marketplace) to catch overfitting.

### 9. The Plugin Pivot (ADR-029)

Why: close the Genesis loop (spec to code in one tool), zero-setup distribution (no Python/AWS/Streamlit), reduce maintenance surface (markdown agents replace Strands SDK + Burr + OTEL + agent factory).

The biggest trade-off: deterministic workflow enforcement (Burr state machine) is replaced by instruction-following (Claude reading skill markdown). This is probabilistic, not guaranteed. Mitigations: file-based checkpoints (each phase writes a completion marker), hook scripts (validate schemas post-output), phase prerequisite checks. These reduce risk but don't eliminate it.

The second trade-off: structured output validation. Strands enforced Pydantic schemas at generation time. In the plugin, agents return text and hook scripts validate after the fact. Errors propagate further before they're caught.

Fallback if the trade-offs prove too costly: run the workflow engine as an MCP server that Claude Code calls, preserving deterministic enforcement while keeping the plugin UX.

### 10. Export Format: OpenSpec (ADR-029 addendum)

OpenSpec over SpecKit. 1:1 mapping between capabilities and output artifacts. No workflow metadata redundancy. Native change management for the Evolution milestone (diff a capability, generate targeted specs, implement, validate).

## What Was Tried and Abandoned

- **VectorDB for session state (ADR-003, abandoned ADR-027)**: Built semantic search over session artifacts. Nobody queried it. File-based session state (read the markdown, grep for what you need) was simpler and sufficient.
- **Multi-agent validation pipeline (ADR-026)**: 4 specialist agents (scorer, narrator, merger, summarizer) connected by 6 deterministic validators. Produced worse output than a single agent with the same context. The validators existed to patch inconsistencies that the architecture created.
- **8 scoring dimensions for market validation (ADR-023)**: Only 5 evidence clusters from web research. Three dimensions were hallucinated. Reduced to 6 with explicit evidence-source mapping.
- **Streamlit UI (ADR-008, iterated ADR-017)**: Built a full workflow UI with progress bars, decision gates, and results panels. Blocked adoption because it required Python + Streamlit + browser. The planning intelligence was sound; the delivery mechanism was wrong.

## References

Original ADRs preserved in `archive/standalone` branch.
