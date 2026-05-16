# Haytham

Lifecycle control plane for AI-built products. Delivered as a Claude Code plugin. Orchestrates specialist agents across validate, specify, design, plan, build, and evolve phases while maintaining a reasoning graph that links every decision to its origin.

## Tech Stack

- **Runtime:** Claude Code (LLM access, tool dispatch, slash command surface, hook lifecycle, plugin marketplace).
- **Agent runtime:** Anthropic Claude models, dispatched via Claude Code's Agent tool. Haiku for compilation (research-briefer), Sonnet for analysis (most agents), Opus for synthesis (report-synthesizer, spec-generator).
- **Tool surface:** Read, Write, Bash, WebSearch, WebFetch, Agent, Glob, Grep — all provided by Claude Code.
- **Hook scripts:** Python 3 (validate_schema.py, validate_openspec.py, validate_som.py) and Bash (check_phase_prereqs.sh, post_bash_seed.sh). Both interpreters are present by default on macOS, Linux, and WSL.
- **State persistence:** Filesystem. Pipeline artifacts under `.haytham/session/phase-N/`. Maintained reasoning graph under `openspec/`. Demo exports under a separate demos repository chosen by the user.
- **Distribution:** Claude Code plugin marketplace. Source-of-truth GitHub repository (https://github.com/arslan70/haytham), MIT licensed.

## Architecture Decisions

### DEC-DELIVERY-001: Claude Code Plugin as Sole Delivery Form

**Decision:** Distribute Haytham only as a Claude Code plugin via `.claude-plugin/marketplace.json` and `.claude-plugin/plugin.json`. No standalone app, no SaaS, no separate UI. Bump version inside `plugins[0]` in marketplace.json, not in plugin.json.

**Rationale:** Setup friction kills adoption. A plugin install is two commands; a standalone implementation reproduces tool dispatch, slash commands, and the hook lifecycle for no benefit. The version-in-marketplace-only rule is forced by Claude Code's loader behaviour.

**Trade-offs:** Tied to Claude Code's release cycle and breaking changes. Acceptable because Claude Code is the user's existing runtime.

### DEC-ORCH-001: Eight Specialist Agents Split by Tool or Model Need

**Decision:** Split work into eight specialist agents. Splits are justified only by different tool needs (web search vs analysis), different model tiers (Haiku/Sonnet/Opus), or genuine independence (market vs competitor research can parallelize).

**Rationale:** Multi-agent split costs context. A documented experiment showed a single agent with full context (8 PASS / 4 PARTIAL / 0 FAIL) beat a 4-agent + 6-validator pipeline on the same inputs (1 PASS / 3 PARTIAL / 8 FAIL). The split criterion limits when splitting is worth the context cost.

**Trade-offs:** Eight agents is more surface area than one. Acceptable because each split is load-bearing.

### DEC-COMM-001: File-Based Agent Communication

**Decision:** Agents communicate by writing files to `.haytham/session/phase-N-name/`. No in-memory state, no shared context object. Downstream agents read upstream files by path. Known values (concept anchor, GO/NO-GO verdict) are passed as file context, never re-extracted from prose.

**Rationale:** Files are inspectable, debuggable, and resumable. The pattern enforces drift-prevention discipline structurally: if a value is in a file, the next agent reads it. CLAUDE.md documents in-prose value passing as a failure mode.

**Trade-offs:** Filesystem coupling means agents see stale data if upstream files are not written before downstream reads. Mitigated by the linear pipeline structure.

### DEC-VALIDATION-001: Hook Scripts Enforce Deterministic Rules

**Decision:** Hook scripts (PreToolUse and PostToolUse) enforce non-negotiable rules: phase prerequisites, output schemas, SHALL grammar, Gherkin completeness, capability coverage. LLM prompts handle qualitative judgement only.

**Rationale:** Rules whose violation produces silently malformed downstream artifacts must be structural, not advisory. CLAUDE.md PITFALL: LLM Text Overriding Deterministic Rules names this boundary.

**Trade-offs:** Two interpreters (Python and Bash) to maintain. Acceptable; both are default-installed.

### DEC-SYNTH-001: Single-Agent Synthesis for Holistic Reasoning

**Decision:** Tasks requiring cross-referencing across findings are handled by a single agent with full context, not by deterministic glue between multiple synthesizers. report-synthesizer is single-agent by design.

**Rationale:** Cross-reference reasoning loses signal when split across agents connected by glue. Validated experimentally and documented in CLAUDE.md.

**Trade-offs:** Larger prompt size for the synthesizer. Acceptable for one synthesis call per pipeline.

### DEC-EVOLVE-001: Three Parallel Variant Proposers with Orchestrator Synthesis

**Decision:** /haytham:evolve launches three read-only proposers in parallel with framings (minimal touch, clean refactor, pragmatic middle). The orchestrator detects invariant conflicts, synthesizes a recommendation with a single specific reason and a cited file, and asks for confirmation. The chosen variant then executes code and graph updates in one commit.

**Rationale:** A single-proposer evolve produces one plausible plan with no visible tradeoff. The three-framing pattern forces explicit alternatives. Three is enough to span the tradeoff space without overwhelming the user.

**Trade-offs:** Higher token spend per evolve run. Acceptable for the change-quality gain.

### DEC-ANCHOR-001: Concept Anchor Passed Unchanged

**Decision:** The Phase 1 concept anchor (invariants, identity, intent, term flags) is written to a file and read verbatim by every downstream agent. Agents may add context but must not modify anchor invariants.

**Rationale:** Multi-agent pipelines drift without an anchor. Pinning invariants in a downstream-read file breaks the telephone game. The same anchor is what /haytham:evolve uses as the conflict-detection contract.

**Trade-offs:** A wrong anchor in Phase 1 propagates downstream. Mitigated by the Phase 1 approval gate.

### DEC-CTRL-PLANE-001: Haytham Declares Intent; Downstream Tools Execute

**Decision:** Haytham is a control plane. It classifies, directs, validates, and gates. It does not run user code, deploy, or operate infrastructure. Phase 5 scaffolds and delegates to a separate Claude Code session.

**Rationale:** A control plane is portable across execution backends. Coupling Haytham to execution in Genesis would block delegation in Evolution and autonomy in Sentience.

**Trade-offs:** Founders must context-switch between sessions for implementation. Acceptable; the spec carries the context across sessions.

## Build/Buy Analysis

Almost every infrastructure category resolves to PLATFORM (Claude Code, filesystem, marketplace, git) or BUILD (agents, commands, hooks). There is no BUY decision: no managed service fits a control plane delivered as a plugin. State is filesystem because scale is one product per directory and inspectability beats schema enforcement at this size. Distribution piggybacks the Claude Code marketplace. Total managed services: zero. Total operational footprint: zero beyond the user's existing Claude Code subscription.

## Project Structure

```
.claude-plugin/
  plugin.json                  # Plugin manifest
  marketplace.json             # Marketplace registration with version

agents/                        # Specialist agent definitions
  idea-analyst.md
  market-researcher.md
  competitor-researcher.md
  research-briefer.md
  report-synthesizer.md
  mvp-scoper.md
  capability-modeler.md
  architect.md
  spec-generator.md
  outreach-summarizer.md

commands/                      # User-facing slash commands
  haytham.md                   # /haytham — full pipeline
  validate.md                  # /haytham:validate — Phase 1
  specify.md                   # /haytham:specify — Phase 2
  design.md                    # /haytham:design — Phase 3
  plan.md                      # /haytham:plan — Phase 4
  build.md                     # /haytham:build — Phase 5 setup
  evolve.md                    # /haytham:evolve — graph-maintaining change
  export.md                    # /haytham:export
  demo.md                      # /haytham:demo
  review-depth.md
  review-fidelity.md
  review-consistency.md
  review-actionability.md
  ux-review.md

hooks/
  hooks.json                   # PreToolUse and PostToolUse wiring

scripts/
  check_phase_prereqs.sh       # PreToolUse Agent matcher
  validate_schema.py           # PostToolUse Write matcher
  validate_openspec.py         # Phase 4 output validator
  validate_som.py              # Market sizing arithmetic
  post_bash_seed.sh            # PostToolUse Bash matcher

openspec/                      # Reasoning graph for haytham itself (this file's home)
  config.yaml
  project.md
  context/
    concept-anchor.json
    capabilities.json
    architecture-decisions.json
    system-traits.json
    build-buy.json
    mvp-scope.md
    idea-analysis.md
    validation-report.md
  specs/
    validation/spec.md
    specification/spec.md
    design/spec.md
    planning/spec.md
    evolution/spec.md
    distribution/spec.md
    cross-cutting/spec.md

CLAUDE.md                      # Project instructions (collaboration stance, design pitfalls, UX standards)
VISION.md                      # Roadmap (Genesis, Evolution, Sentience)
README.md
LICENSE                        # MIT
```

## Data Schemas

### `.haytham/session/phase-1-why/concept-anchor.json`

Fields: `archetype`, `intent` (goal, explicit_constraints, non_goals), `invariants[]` (property, value, source, confidence, scope_risk), `identity` (features, why_distinctive), `term_flags[]`, `founder_intent`, `founder_profile`, `strategic_signals`.

### `.haytham/session/phase-2-what/capabilities.json`

Fields: `summary` (system_name, system_purpose, primary_user_segment, input_method, mvp_scope_respected, launch_posture_note), `capabilities` (functional[] with id, name, description, serves_scope_item, user_flow, acceptance_criteria, rationale; non_functional[] with id, name, description, category, requirement, measurement, rationale), `traceability`, `metadata`.

### `.haytham/session/phase-2-what/system-traits.json`

Fields: `traits` (interface, auth, deployment, data_layer, realtime, communication, payments, scheduling), `explanations` (one paragraph per trait grounded in the anchor).

### `.haytham/session/phase-3-how/architecture-decisions.json`

Fields: `decisions[]` (id, name, description, rationale, serves_capabilities[], implements_recommendation, alternatives_considered[]), `coverage_check`, `summary`.

### `.haytham/session/phase-3-how/build-buy.json`

Fields: `system_summary`, `infrastructure_requirements[]`, `recommended_stack[]` (name, category, recommendation BUY/BUILD/PLATFORM, rationale, capabilities_served[], free_tier, estimated_monthly_cost), `stack_rationale`, `alternatives`, `total_integration_effort`, `estimated_monthly_cost`.

### `.haytham/session/phase-4-specs/openspec/`

Directory tree with `config.yaml`, `project.md`, `context/*.{json,md}`, `specs/<domain>/spec.md`. Validated by `scripts/validate_openspec.py`.

## Component Map

| Component | File(s) | Capabilities |
|---|---|---|
| Validation phase | `commands/validate.md`, `agents/idea-analyst.md`, `agents/market-researcher.md`, `agents/competitor-researcher.md`, `agents/research-briefer.md`, `agents/report-synthesizer.md` | CAP-F-001 |
| Specification phase | `commands/specify.md`, `agents/mvp-scoper.md`, `agents/capability-modeler.md` | CAP-F-002 |
| Design phase | `commands/design.md`, `agents/architect.md` | CAP-F-003 |
| Planning phase | `commands/plan.md`, `agents/spec-generator.md` | CAP-F-004 |
| Build setup | `commands/build.md` | CAP-F-005 |
| Full pipeline | `commands/haytham.md` | CAP-F-006 |
| Evolution | `commands/evolve.md` | CAP-F-007 |
| Export | `commands/export.md`, `agents/outreach-summarizer.md` | CAP-F-008 |
| Demo | `commands/demo.md` | CAP-F-009 |
| Reviews | `commands/review-depth.md`, `commands/review-fidelity.md`, `commands/review-consistency.md`, `commands/review-actionability.md` | CAP-F-010 |
| UX review | `commands/ux-review.md` | CAP-F-011 |
| Plugin distribution | `.claude-plugin/marketplace.json`, `.claude-plugin/plugin.json` | CAP-F-012 |
| Concept anchor preservation | `agents/idea-analyst.md`, downstream agents' reads | CAP-NF-001 |
| Hook-based deterministic validation | `hooks/hooks.json`, `scripts/check_phase_prereqs.sh`, `scripts/validate_schema.py`, `scripts/validate_openspec.py` | CAP-NF-002, CAP-NF-005 |
| Zero-setup distribution | `.claude-plugin/*`, `scripts/*` (Python and Bash only) | CAP-NF-003 |
| Archetype genericity | All prompts and hooks (enforced by review discipline) | CAP-NF-004 |
