# Plan: Hard Pivot to Claude Code Plugin

## Context

Haytham has two parallel systems: a standalone Python pipeline (200 files, 38K LOC) and a Claude Code plugin (18 files, 2.4K LOC). The plugin is the product. The standalone system is dead weight. The user wants fast feedback, which means a clean repo that IS a plugin.

This plan covers three things:
1. Archive and clean the repo structure
2. Consolidate 37 ADRs into a single system-evolution.md
3. Rewrite all docs for the plugin (keeping the blog)

---

## Part 1: Archive and Restructure

### Step 1: Archive current state

```bash
git tag v0.1-standalone -m "Standalone system: Burr + Strands + Streamlit + 23 agents"
git branch archive/standalone
```

### Step 2: Promote plugin to repo root

Move `haytham-plugin/` contents to repo root:

```
.claude-plugin/plugin.json
agents/                        # 8 agent markdown files
commands/                      # 5 command markdown files
hooks/hooks.json
scripts/                       # validate_schema.py, check_phase_prereqs.sh, validate_som.py
```

### Step 3: Delete standalone system

Remove entirely:
- `haytham/` (standalone Python, 200 files)
- `frontend_streamlit/` (Streamlit UI, 31 files)
- `tests/` (tests for standalone, 88 files)
- `outputs/` (old requirement dumps, 25 files)
- `session/` (old session data, 46 files)
- `backlog/` (generated app backlog, 110 files)
- `site/` (built mkdocs, 136 files)
- `.haytham/` (test run output, 17 files)
- `pyproject.toml`, `uv.lock`, `Makefile`
- `.pre-commit-config.yaml`, `.env.example`
- `audit-report.md`, `haytham-idea-validation-report.pdf`
- `CODE_OF_CONDUCT.md`, `CONTRIBUTING.md`, `SECURITY.md`, `NOTICE`
- `.serena/`, `.playwright-mcp/`, `.cache/`, `.ruff_cache/`, `.pytest_cache/`

### Step 4: Keep and update

- `README.md` - Rewrite (see Part 3)
- `CLAUDE.md` - Rewrite (see Part 3)
- `VISION.md` - Keep (still relevant, update current state references)
- `LICENSE` - Keep
- `.gitignore` - Simplify
- `docs/` - Rewrite (see Part 3)
- `mkdocs.yml` - Update nav (see Part 3)

---

## Part 2: ADRs → system-evolution.md

### What

Consolidate 37 ADR files into a single `docs/system-evolution.md`. This extracts the lessons that matter for the plugin and summarizes what was tried and abandoned.

### Structure

```markdown
# System Evolution

How Haytham got here. 29 ADRs from Jan 2025 to Mar 2026 documented a standalone
Python system that was replaced by a Claude Code plugin. The lessons below tell
the coding agent what was tried, what failed, and what to preserve.

## The Journey
[Timeline: Notes App PoC → multi-phase workflow → quality crisis → plugin pivot]

## Lessons

### 1. Four-Phase Workflow (ADR-016)

The workflow has four phases: WHY (validate the idea), WHAT (scope the MVP),
HOW (architecture decisions), SPECS (specification generation). Each phase ends
with a human approval gate. The gate after WHY is the most important: it
produces a GO/PIVOT/NO-GO recommendation backed by evidence.

Why four and not three: early versions combined validation and scoping. This
consistently produced MVPs that included unvalidated assumptions. Separating
"is this worth building" from "what should the MVP include" forces the evidence
to exist before scoping begins.

### 2. Concept Fidelity (ADR-022)

Progressive genericization is the #1 failure mode in multi-phase pipelines.
Each agent slightly generalizes the idea to hedge its analysis, and by Phase 3
the output describes a generic SaaS platform, not the user's actual idea.

The fix: extract "concept anchors" from the raw idea in Phase 1 (specific
nouns, verbs, and constraints the user chose). Every downstream agent receives
these anchors and is instructed to preserve them. Post-validation checks that
anchor terms appear in the output. If a user says "gym leaderboard with
anonymous handles," downstream output must reference gyms, leaderboards, and
anonymity, not "a community engagement platform with privacy features."

### 3. Single Agent for Synthesis (ADR-026)

A single agent with full upstream context scored 8 PASS / 4 PARTIAL / 0 FAIL
on report quality criteria. A 4-agent pipeline with 6 deterministic validators
processing the same inputs scored 1 PASS / 3 PARTIAL / 8 FAIL.

The failure mode: splitting reasoning across agents creates information loss at
boundaries. A scorer agent produces numbers without narrative context. A
narrator agent writes prose without access to the scoring rationale. A merge
function stitches them together. Validators catch inconsistencies that wouldn't
exist if one agent had the full picture. If you're adding a validator to fix
disagreements between two agents, you have an architecture problem.

Multi-agent IS justified when agents need different tools (web search vs.
analysis), different model tiers, or operate on genuinely independent tasks.
Gathering information: split. Synthesizing information: don't split.

### 4. System Traits Over Categories (ADR-019)

Don't classify ideas into categories (e.g., "marketplace," "SaaS," "social").
Categories are mutually exclusive and miss hybrid ideas. Instead, detect traits:
has_user_auth, has_payments, has_real_time, has_marketplace_dynamics,
needs_mobile. Traits compose. A gym leaderboard has user_auth + real_time +
social_features. A freelance marketplace has user_auth + payments +
marketplace_dynamics. The architecture and spec generation respond to traits,
not categories.

### 5. Evidence Must Match Evaluation (ADR-023)

Don't create scoring dimensions that your evidence sources can't populate.
The original market validation had 8 scoring dimensions but only 5 evidence
clusters from web research. Three dimensions were scored by the LLM
hallucinating plausible-sounding analysis with no backing data. Reduced to 6
dimensions, each mapped to a specific evidence source. The rule: if you can't
name the upstream data that populates a score, delete the score.

### 6. Deterministic Post-Processing (ADR-028)

LLM agents produce qualitative output (analysis, recommendations, prose).
Deterministic code transforms it into structured artifacts (JSON schemas,
execution contracts, dependency graphs). Never ask an LLM to produce a
perfectly formatted JSON structure. Ask it to reason, then parse the reasoning
into structure with code. This separation also means validation rules
(arithmetic checks, required fields, cross-references) run in code, not as
LLM re-prompts.

### 7. Build vs Buy Guidance (ADR-013)

Always recommend BUY for commodity components: authentication (Auth0, Clerk),
payments (Stripe), email (SendGrid), file storage (S3/CloudFlare R2). The
signal: if a component has multiple mature SaaS providers and isn't a
differentiator for the startup, it's a BUY. Only recommend BUILD for
capabilities that are core to the startup's value proposition.

### 8. Agent Testing (ADR-018)

Test agent output with LLM-as-Judge, not snapshot tests or mocks. Snapshot
tests are brittle (any rewording breaks them). Mocks test the harness, not
the agent. LLM-as-Judge evaluates against a criteria checklist using real
inputs and real model calls. Each criterion has PASS/PARTIAL/FAIL with
specific definitions. Run against multiple test ideas (different archetypes:
B2C app, B2B tool, marketplace) to catch overfitting.

### 9. The Plugin Pivot (ADR-029)

Why: close the Genesis loop (spec to code in one tool), zero-setup
distribution (no Python/AWS/Streamlit), reduce maintenance surface (markdown
agents replace Strands SDK + Burr + OTEL + agent factory).

The biggest trade-off: deterministic workflow enforcement (Burr state machine)
is replaced by instruction-following (Claude reading skill markdown). This is
probabilistic, not guaranteed. Mitigations: file-based checkpoints (each phase
writes a completion marker), hook scripts (validate schemas post-output),
phase prerequisite checks. These reduce risk but don't eliminate it.

The second trade-off: structured output validation. Strands enforced Pydantic
schemas at generation time. In the plugin, agents return text and hook scripts
validate after the fact. Errors propagate further before they're caught.

Fallback if the trade-offs prove too costly: run the workflow engine as an MCP
server that Claude Code calls, preserving deterministic enforcement while
keeping the plugin UX.

### 10. Export Format: OpenSpec (ADR-029 addendum)

OpenSpec over SpecKit. 1:1 mapping between capabilities and output artifacts.
No workflow metadata redundancy. Native change management for the Evolution
milestone (diff a capability, generate targeted specs, implement, validate).

## What Was Tried and Abandoned

- **VectorDB for session state (ADR-003, abandoned ADR-027)**: Built semantic
  search over session artifacts. Nobody queried it. File-based session state
  (read the markdown, grep for what you need) was simpler and sufficient.
- **Multi-agent validation pipeline (ADR-026)**: 4 specialist agents (scorer,
  narrator, merger, summarizer) connected by 6 deterministic validators.
  Produced worse output than a single agent with the same context. The
  validators existed to patch inconsistencies that the architecture created.
- **8 scoring dimensions for market validation (ADR-023)**: Only 5 evidence
  clusters from web research. Three dimensions were hallucinated. Reduced to 6
  with explicit evidence-source mapping.
- **Streamlit UI (ADR-008, iterated ADR-017)**: Built a full workflow UI with
  progress bars, decision gates, and results panels. Blocked adoption because
  it required Python + Streamlit + browser. The planning intelligence was
  sound; the delivery mechanism was wrong.

## References
Original ADRs preserved in `archive/standalone` branch.
```

### Delete
- `docs/adr/` (entire directory, 37 files)

---

## Part 3: Docs Overhaul

### Docs to DELETE (standalone-specific, no plugin equivalent)

| File/Dir | Reason |
|---|---|
| `docs/technology.md` | Describes Burr, Strands, Streamlit, OTEL |
| `docs/architecture/overview.md` | Describes standalone architecture |
| `docs/architecture/` (dir) | Also contains `scoring-pipeline.md` |
| `docs/contributing/agent-development-guide.md` | Strands SDK agent creation |
| `docs/contributing/architecture-patterns.md` | Python code hygiene for standalone |
| `docs/contributing/` (dir) | Empty after above |
| `docs/example-session/` (12 files) | Streamlit screenshots |
| `docs/plans/` (13 files) | Design docs for standalone features |
| `docs/proposals/` (3 files) | Implementation proposals |
| `docs/dogfood/` (2 files) | Historical only |
| `docs/troubleshooting.md` | Python/uv/Bedrock debugging |
| `docs/roadmap.md` | Standalone Evolution plans |
| `docs/exports.md` | Dual OpenSpec+SpecKit from standalone |
| `docs/README.md` | Docs index (replaced by nav) |

### Docs to REWRITE

#### `docs/index.md` (landing page)
Current: references `uv sync`, `make run`, Burr, Strands, Streamlit.
New: Plugin-focused landing page.
- Hero: same value prop (idea → spec)
- Same 4-phase cards (these are correct)
- Quick start: `/plugin install haytham` then `/haytham <idea>`
- "What you get" section: update to reference OpenSpec output
- Remove technology footer (no Burr/Strands/Streamlit)

#### `docs/getting-started.md`
Current: Python 3.11+, uv, .env, 4 LLM providers.
New: Plugin installation.
- Prerequisites: Claude Code
- Install: `/plugin install haytham` (or local dev: clone + symlink)
- First run: `/haytham "your startup idea"`
- What to expect: 4 phases, gates, output in `.haytham/session/`
- Local development: how to edit agents/commands and test

#### `docs/how-it-works.md`
Current: 4-phase pipeline with agent diagram. **Partially reusable.**
New: Keep the phase structure and agent descriptions. Update:
- Remove Streamlit/Burr references
- Update agent names to match plugin (idea-analyst, market-researcher, etc.)
- Update state management section (`.haytham/session/` files)
- Update diagram if needed (the mermaid flowchart is mostly correct)

#### `docs/exports.md` → rename to `docs/openspec-output.md`
Current: Dual OpenSpec + Spec Kit export.
New: OpenSpec-only output. What gets produced, directory structure, how to use it with `/opsx:apply` or other coding agents.

### Docs to CREATE

#### `docs/system-evolution.md`
The ADR consolidation document (see Part 2).

### Docs to KEEP AS-IS

- `docs/blog/index.md` - Blog landing
- `docs/blog/posts/*.md` - All 3 blog posts (still relevant)
- `docs/images/` - Logos, yes-machine-problem.png
- `docs/overrides/` - mkdocs theme overrides
- `docs/stylesheets/` - Custom CSS
- `blog/posts/2026-03-03-build-where-developers-already-are.md` - Actually about the plugin pivot, very relevant

### mkdocs.yml update

New nav:
```yaml
nav:
  - Home: index.md
  - How It Works: how-it-works.md
  - Getting Started: getting-started.md
  - OpenSpec Output: openspec-output.md
  - Blog:
    - blog/index.md
  - Reference:
    - System Evolution: system-evolution.md
```

Remove: Architecture section, Decision Records section, Contributing section, Example Session, Troubleshooting, Roadmap.

### README.md rewrite

Plugin-focused:
- What Haytham does (1 paragraph)
- Install: `/plugin install haytham`
- Usage: `/haytham <your startup idea>`
- Phase commands: `/haytham:validate`, `/haytham:specify`, `/haytham:design`, `/haytham:plan`
- What you get (4-phase output → OpenSpec)
- Link to docs site
- License

### CLAUDE.md rewrite

Strip standalone system references. Keep:
- Constitution (principles, meta-system design, system integrity traits)
- Documentation editing standards and blog writing style
- Guiding principles

Add:
- Plugin structure (agents/, commands/, hooks/, scripts/)
- How to modify agents (edit markdown, reload)
- How to add a new agent or command
- How to test (run `/haytham` with a test idea)

Remove:
- All Burr, Strands, StageRegistry, StageExecutor, Agent Factory references
- "Adding a New Stage/Workflow Type" checklists
- "Before Every Commit" Python lint/test commands
- DSPy, OTEL, Jaeger references
- Environment variables section (AWS, Bedrock model IDs)
- Package boundaries
- PITFALLs specific to the standalone system: Agent Registration, Entry Validator Registration, Bypassing the Agent Factory, Imports Inside Function Bodies

Rewrite (not delete) these PITFALLs in plugin-native language:
- **"Splitting LLM Reasoning Across Multiple Agents"** — still applies to the 8 plugin agents. Reframe examples around agent markdown files instead of Strands SDK.
- **"LLM Text Overriding Deterministic Rules"** — still applies to hook validation scripts. Reframe around hooks enforcing rules, not agent output.
- **"Agents Re-deriving Known Values"** — still applies. Agent markdowns should receive known values (recommendation, concept anchors) as explicit context, not embedded in prose for re-extraction.
- **"Evidence Must Match Evaluation"** — still applies to any future quality work or scoring in agent prompts.

### VISION.md update

Minor updates:
- Update "Current State" to reflect plugin delivery
- Update Genesis status to note plugin pivot
- Keep Evolution and Sentience vision (still valid)

### .gitignore simplify

Remove Python entries (*.pyc, __pycache__, .venv, .ruff_cache, etc.).
Keep: `.haytham/`, `.DS_Store`, `site/`, `.env`

---

## Execution Order

1. Git tag + archive branch (safety net)
2. Move `haytham-plugin/*` to repo root, delete `haytham-plugin/`
3. Delete standalone directories (haytham/, frontend_streamlit/, tests/, etc.)
4. Delete standalone files (pyproject.toml, Makefile, etc.)
5. Delete obsolete docs (technology.md, architecture/, contributing/, plans/, proposals/, dogfood/, example-session/, troubleshooting.md, roadmap.md, exports.md, docs/README.md)
6. Delete `docs/adr/` entirely
7. Write `docs/system-evolution.md` (ADR consolidation)
8. Rewrite `docs/index.md` (landing page)
9. Rewrite `docs/getting-started.md` (plugin install)
10. Rewrite `docs/how-it-works.md` (update agent refs)
11. Write `docs/openspec-output.md` (OpenSpec export docs)
12. Update `mkdocs.yml` (new nav)
13. Rewrite `README.md`
14. Rewrite `CLAUDE.md`
15. Update `VISION.md`
16. Simplify `.gitignore`
17. Commit

---

## Verification

### Structural checks

1. Repo root: `.claude-plugin/`, `agents/`, `commands/`, `hooks/`, `scripts/`, `docs/`, `README.md`, `CLAUDE.md`, `VISION.md`, `LICENSE`, `.gitignore`, `mkdocs.yml`
2. No Python files except scripts/ (validate_schema.py, validate_som.py)
3. No pyproject.toml, Makefile, uv.lock
4. `git tag` shows `v0.1-standalone`
5. `git branch` shows `archive/standalone`
6. `docs/` contains: index.md, getting-started.md, how-it-works.md, openspec-output.md, system-evolution.md, blog/, images/, overrides/, stylesheets/
7. No references to Burr, Strands, Streamlit, `uv sync`, or `make run` in any remaining file
8. mkdocs nav points to existing files only
9. Blog posts render correctly

### Functional checks

10. Plugin manifest (`plugin.json`) paths resolve correctly after promotion to repo root
11. Hook scripts (`hooks/hooks.json`) reference correct relative paths to scripts/
12. Install the plugin locally from the restructured repo (symlink or local path install)
13. Run `/haytham "a gym community leaderboard with anonymous handles"` through at least Phase 1 (validate) and confirm: idea-analyst agent is invoked, market-researcher produces output, files are written to `.haytham/session/phase-1-why/`, gate decision is presented to user
14. Verify that concept anchors from Phase 1 appear in downstream output (if running beyond Phase 1)
