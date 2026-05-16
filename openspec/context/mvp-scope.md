# MVP Scope

---

## Pass 1: Core Identity

### 1. The One Thing

The MVP will enable **technical founders building AI-built products** to **maintain a reasoning graph from idea to evolvable system** so they can **make every decision traceable and every change targeted** without losing context as the product grows.

Validation:
- One action: maintain a reasoning graph across the product lifecycle
- One benefit: traceable decisions and targeted changes
- No compound outcomes
- Plain language test: "You describe an idea or a change; Haytham keeps the graph that explains why the system is the way it is."

---

### 2. Primary User Segment

**Segment:** Solo technical founders or two-person teams building a first AI-built product who are willing to pause for structured validation before coding.

**Profile:** Technical founders who already use Claude Code, have an idea (or a running product) and want to avoid the "vibe-coded then abandoned" trap. They value rigor over speed and are willing to spend 20 minutes on validation before days on implementation.

**Why First:** This segment self-selects for receptiveness. They are already inside Claude Code, already comfortable with markdown-first tooling, and already feel the pain of products that drift from their original intent. Adoption requires no behaviour change beyond installing one plugin.

**Key Need:** A way to convert a raw idea into a validated, traceable specification, and to evolve that specification without losing the reasoning trail when the product changes.

---

### 3. Primary Input Method

**Input Method:** Slash command in a Claude Code CLI session, taking either a free-text idea or a URL (Reddit post, GitHub repo).

**Why This Method:** Founders are already in Claude Code. A slash command adds zero setup friction. Free text accepts any idea; URL acceptance enables batch validation of external sources (used by `/haytham:demo`).

**What This Excludes:** No web form, no separate desktop or mobile app, no API for external callers. The plugin is the only interface at MVP.

---

### 4. Appetite

**Appetite:** Medium. Genesis (Phases 1-4 + build setup) is already shipped. Evolution v1 (`/haytham:evolve`) shipped this sprint. The remaining work in scope for MVP is hardening Evolution against real change requests on GiftKaro and TinyTales.

**If we had HALF the time:** Cut the four review commands (`review-depth`, `review-fidelity`, `review-consistency`, `review-actionability`) and rely on the hook-based deterministic validators only. The reviews are useful but secondary; the core loop is validate → specify → design → plan → build → evolve.

Half-time validation: Reviews are quality-of-output tooling, not part of the core loop. Their absence does not block the founder from running the pipeline; their presence makes the pipeline more reliable. At half-time, the core loop is non-negotiable; the reviews are first to cut.

---

## Pass 2: Boundaries

### Concept Anchor Compliance

The fifteen invariants from the concept anchor are addressed below.

| Invariant | scope_risk | Status |
|-----------|-----------|--------|
| access_model: Claude Code plugin install | low | IN SCOPE |
| interaction_model: Slash commands with human approval gates | low | IN SCOPE |
| session_medium: Claude Code CLI session | low | IN SCOPE |
| reasoning_graph_is_core_asset | high | IN SCOPE (this is the product) |
| control_plane_not_data_plane | high | IN SCOPE (architectural invariant) |
| fix_root_cause_not_symptom | high | IN SCOPE (development principle) |
| meta_system_genericity | high | IN SCOPE (prompts enforce principles, not prescriptions) |
| deterministic_rules_in_hooks_qualitative_in_llm | medium | IN SCOPE |
| drift_prevention_via_concept_anchor | medium | IN SCOPE |
| single_agent_for_holistic_reasoning | medium | IN SCOPE |
| specialist_agent_split_criteria | medium | IN SCOPE |
| output_artifact_shape: OpenSpec directory | medium | IN SCOPE |
| verdict_model: honest GO/PIVOT/NO-GO | low | IN SCOPE |
| milestone_scope_genesis_plus_evolution | high | IN SCOPE (this MVP) |
| agent_communication_via_files | medium | IN SCOPE |

**Flagged scope risks:**

- `reasoning_graph_is_core_asset` (high): The graph is the product, not a side artifact. A change that produces code without updating the graph violates this invariant. `/haytham:evolve` is the primary safeguard.
- `control_plane_not_data_plane` (high): Any proposal to have Haytham execute (run code, deploy, monitor) rather than declare and delegate is rejected. This is the principle that makes Evolution and Sentience tractable.
- `meta_system_genericity` (high): Every prompt must work for a CLI tool AND a web app AND a marketplace. Prescription is rejected; principle is required.
- `milestone_scope_genesis_plus_evolution` (high): Sentience is OUT OF SCOPE. A proposal to add telemetry-driven autonomous improvement is rejected as out of milestone.

---

### 5. MVP Boundaries

| IN SCOPE (MVP) | Requires | OUT OF SCOPE (Future) |
|----------------|----------|-----------------------|
| `/haytham:validate` Phase 1 (WHY): idea analysis, parallel market + competitor research, research brief, single-agent synthesis with GO/PIVOT/NO-GO verdict. Concept anchor extracted in idea analysis. | Nothing | Live telemetry integration; multi-product portfolio validation |
| `/haytham:specify` Phase 2 (WHAT): MVP scoping with concept-anchor compliance check, capability model with traceability, system trait classification. | Phase 1 output | Capability-level effort estimation; ROI modelling |
| `/haytham:design` Phase 3 (HOW): build-vs-buy analysis, architecture decisions citing the capabilities they serve, alternatives considered with rationale. | Phase 2 output | Multi-cloud architecture comparison; cost modelling at scale |
| `/haytham:plan` Phase 4 (SPECS): OpenSpec directory generation with project.md, capabilities.json, architecture-decisions.json, system-traits.json, build-buy.json, mvp-scope.md, concept-anchor.json, and per-domain specs/*/spec.md using SHALL grammar and Gherkin scenarios. | Phase 3 output | Per-task implementation breakdown; sprint planning |
| `/haytham:build` Phase 5 setup: scaffold a new project directory from Phase 4 output so a separate Claude Code session can implement against pure specs. | Phase 4 output | Actually generating implementation code from inside the plugin (the implementation runs in a separate session by design) |
| `/haytham` full-pipeline orchestrator: runs Phases 1-4 (and optionally build) in sequence with human approval gates at every phase boundary; BATCH_MODE auto-approves for demo or CI use. | Underlying phase commands | Branching pipelines; partial rerun without /haytham:validate --from N already covers this |
| `/haytham:evolve`: applies a change to a project with an `openspec/` graph; three parallel variant proposers (minimal touch, clean refactor, pragmatic middle) generate proposals; orchestrator synthesizes and recommends; user confirms; chosen variant executes with code and graph updates committed together. | Target project has `openspec/` (this graph satisfies that for haytham itself) | Multi-change batching; auto-merge to main without human confirmation |
| `/haytham:export` and `/haytham:demo`: export Phase 1 output as a shareable report to a demos repository; demo combines batch-mode validation with export in one unattended run. | Phase 1 output for export; URL input for demo | Outreach automation; multi-recipient broadcast |
| Four review commands (`review-depth`, `review-fidelity`, `review-consistency`, `review-actionability`) and `ux-review`: read pipeline outputs or transcripts and report on quality dimensions. | Pipeline output present | Auto-rerun of failed phases; quality gates that block progression |
| Hook-based deterministic validation: `check_phase_prereqs.sh` before Agent calls, `validate_schema.py` after Write calls, `post_bash_seed.sh` after Bash. Enforces phase prerequisites and output schemas without LLM judgement. | hooks/hooks.json wired | Hook-based quality scoring; runtime metric collection |
| Plugin distribution via marketplace.json: published to Claude Code plugin marketplace, MIT licensed, versioned in marketplace.json (not plugin.json). | None | Versioned API for external callers; webhook integrations |

**Dependency chain:** Validate → Specify → Design → Plan → Build (linear). Evolve is independent and operates post-build on any project that has the graph. Export/Demo depend only on Phase 1. Reviews observe other commands' output.

**Items moved OUT because they failed the half-time test or violate an invariant:**

- Sentience (autonomous telemetry-driven improvement): future milestone, explicitly OUT.
- Hosted Haytham as SaaS: violates `access_model` (plugin-only).
- In-plugin code execution: violates `control_plane_not_data_plane`. Build setup scaffolds; implementation runs in a separate session.
- Multi-product portfolio view: out of scope; one product per `openspec/` directory.
- Quality gates that block progression on review failure: review commands report, they do not gate. Hook-based deterministic rules gate; LLM-based reviews do not.
- Standalone app (Burr + Strands + Streamlit, previously archived): violates `access_model` and was explicitly retired.

---

### 6. Success Criteria

**Primary Metric:** GiftKaro ships a real change via `/haytham:evolve` and its graph remains coherent after the change.

**Target:** Three successful `/haytham:evolve` runs on GiftKaro before 2026-05-16, each producing a code change and a graph update committed together, with no manual graph repair required.

**Validation Criteria:**
- [x] Haytham itself has an `openspec/` graph that lets `/haytham:evolve` operate on its own codebase (meta loop)
- [ ] GiftKaro ships via `/haytham:evolve` in the kill-or-keep window
- [ ] GiftKaro is publicly live
- [ ] TinyTales cross-project test of `/haytham:evolve` succeeds (second product, different archetype)

**Failure Signals:**
- `/haytham:evolve` produces graph updates that contradict the concept anchor or the existing capabilities on more than one in three runs: the invariant check is not strict enough or the variant proposers lack context.
- Three parallel variants converge on identical proposals more than half the time: the framings are not generating useful tradeoff signal.
- Founders need to manually edit `openspec/` after an evolve run: the chosen variant did not implement what it proposed, or the proposer hallucinated files.

---

## Pass 3: User Flows

### 7. Core User Flows

Flow count: 2. Justification: Flow 1 is Genesis — idea to OpenSpec, the main entry point. Flow 2 is Evolution — change to deployed targeted update, which is the loop that makes Genesis output durable. Without Flow 2, Genesis output is a one-shot artifact that ages. Both flows must work for the MVP to be useful.

---

#### Flow 1: Genesis (Idea to OpenSpec)

**Trigger:** Technical founder has an idea, runs `/haytham "an idea"` (or `/haytham <URL>`) inside Claude Code.

**Steps:**
1. `idea-analyst` extracts problems, segments, value proposition, and concept anchor (with invariants, intent, identity, term flags).
2. `market-researcher` and `competitor-researcher` run in parallel using web search.
3. `research-briefer` compiles a neutral brief for founder review.
4. Human approval gate. Founder confirms or corrects.
5. `report-synthesizer` (single agent, full context) produces a validation report with GO/PIVOT/NO-GO verdict.
6. Human approval gate. If NO-GO, the pipeline stops; if GO or PIVOT, continues.
7. `mvp-scoper` defines core identity, boundaries, success criteria, user flows. `capability-modeler` produces capabilities.json and system-traits.json.
8. Human approval gate.
9. `architect` produces build-buy.json and architecture-decisions.json with capability traceability.
10. Human approval gate.
11. `spec-generator` produces the OpenSpec directory under `.haytham/session/phase-4-specs/openspec/`.
12. Outcome: A complete OpenSpec the founder can copy into a new project and hand to Claude Code (or any coding agent) for implementation.

**Success:** The OpenSpec validates against `scripts/validate_openspec.py` (config keys, project sections, SHALL grammar, Gherkin completeness, capability coverage). Concept anchor invariants are preserved verbatim from Phase 1 to Phase 4.

---

#### Flow 2: Evolution (Change to Targeted Update)

**Trigger:** Founder is in a project that has `openspec/` (output of Flow 1 or hand-authored). They want to apply a change. They run `/haytham:evolve "description of change"`.

**Steps:**
1. The command checks `./openspec/` exists and builds the file list (context files + every `specs/*/spec.md`).
2. Three variant proposers run in parallel with the same change description and file list. Each gets a different framing: minimal graph touch, clean refactor, pragmatic middle. Each is read-only and produces a proposal naming files, graph delta, tradeoff, and confidence.
3. The orchestrator detects invariant or scope conflicts (any variant returns `INVARIANT_CONFLICT:` or `SCOPE_CONFLICT:`) and surfaces them verbatim if present, stopping the run.
4. Otherwise the orchestrator renders a comparison table, names a recommended variant with one specific reason and a cited file, and explains what the rejected variants gave up.
5. Human confirmation gate. Founder picks A/B/C or asks for a hybrid.
6. The chosen variant executes: code changes, graph updates (capabilities, decisions, specs), and a single commit naming the variant.
7. Self-check: confidence-scored concerns above 80 surfaced; rest collapsed.

**Success:** Code change and graph update are in one commit. The graph is still internally consistent (no orphaned references, every CAP-F-* still appears in at least one spec). A subsequent run of `/haytham:evolve` with a fresh change reads the updated graph without errors.

Why Flow 2 cannot be deferred: Without Evolution, Genesis output is a one-time photograph of intent. Real products change. The kill-or-keep litmus depends on Flow 2 succeeding on a real change.

---

### Internal Consistency Check

- **Flow <-> Scope:** Flow 1 uses every capability under validation / specification / design / planning / cross-cutting domains. Flow 2 uses the evolution capability and reads the graph produced by Flow 1. No flow step requires an out-of-scope capability.
- **Dependencies <-> Scope:** Genesis is a linear chain with clear file handoffs. Evolution depends on a graph existing; that is the precondition the command checks.
- **Success Criteria <-> Scope:** GiftKaro shipping via evolve is measurable by inspecting the GiftKaro repo for graph-and-code commits. TinyTales cross-project test is measurable by running evolve on a different archetype.

---

### 8. Scope Metadata

```
MVP_SCOPE_COMPLETE: true
PRIMARY_USER_SEGMENT: Solo technical founders or two-person teams building AI-built products inside Claude Code
INPUT_METHOD: Slash command (free text or URL)
APPETITE: Medium
IN_SCOPE_COUNT: 11
OUT_SCOPE_COUNT: 6
FLOW_COUNT: 2
HALF_TIME_CUT: Four review commands and ux-review (rely on hook-based deterministic validation only)
```
