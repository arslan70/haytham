# Roadmap

This document tracks the concrete work items that follow from Haytham's positioning as a specification-driven control plane for software systems. See [VISION.md](../VISION.md) for the full narrative.

All items below advance **Milestone 1: Genesis** unless noted otherwise. Genesis is complete when: idea in, working validated MVP out.

---

## 1. Formalize the Execution Contract

**Priority:** High — foundational for everything below

The docs describe the Phase 4 story output as an "execution contract" and a "universal interface." Today it is markdown files in `session/{stage-slug}/`. For the control plane claim to be real, the output needs a machine-readable format with traceability tags parseable by external agents — not just readable by humans.

### What this means concretely

- Define a structured schema (JSON) for story work items: acceptance criteria, capability references (`implements:CAP-*`), architecture decision references (`uses:DEC-*`), entity references (`touches:ENT-*`), system traits context
- Phase 4 outputs this format alongside the existing markdown
- The schema is the contract between Haytham (specification) and any downstream executor (agent or human)

### What this does NOT mean

- Changing the internal session persistence format
- Breaking existing Streamlit UI rendering
- Building a generic "work item protocol" — the schema serves Haytham's output, not an industry standard

---

## 2. First Coding Agent Integration (Phase 5)

**Priority:** High — closes the Genesis loop
**Depends on:** Item 1 (execution contract)

Build the dispatch path from Phase 4 output to a single coding agent. The agent receives a traced story with full specification context and produces an implementation.

### Recommended first target: Claude Code

- Already used by the team — lowest integration friction
- CLI-based — can be invoked programmatically with structured input
- Supports tool use and file operations needed for implementation

### Scope

- Take one traced story from Phase 4 output
- Assemble the execution context: the story, its capability spec, relevant architecture decisions, system traits
- Dispatch to the coding agent
- Collect the result (files created/modified, tests generated)
- Record the outcome with traceability (which story was implemented, by which agent)

### Out of scope (for now)

- Multiple agent support — build one, learn, then generalize
- Autonomous multi-story execution — start with single-story dispatch with human approval between stories
- Agent selection logic — the user picks the agent, Haytham provides the context

---

## 3. Capability Validation (Phase 6)

**Priority:** High — without this, Genesis is incomplete
**Depends on:** Item 2 (coding agent integration)

After a coding agent implements stories, validate the result against the capability model and acceptance criteria. This is what separates a control plane from a task dispatcher.

### What validation means

- For each implemented story: do the produced artifacts satisfy the acceptance criteria?
- For each capability: is it covered by at least one implemented story?
- For the system as a whole: do the system traits (interface type, auth model, deployment target) match the implementation?

### Open questions

- How much validation can be automated vs. requiring human review?
- Should validation use the same LLM agents as specification, or different tooling (static analysis, test execution)?
- What is the feedback loop when validation fails — re-dispatch to the coding agent with guidance, or surface to the human?

---

## 4. Google Stitch Integration

**Priority:** Medium — proof point for MCP-native service pattern
**Depends on:** Item 1 (execution contract)
**Reference:** [ADR-021](adr/ADR-021-design-ux-workflow-stage.md)

Already planned and referenced in VISION.md, how-it-works.md, and architecture/overview.md as the concrete example of the control plane pattern. Implementing it turns a narrative example into a working demonstration.

### What exists

- ADR-021 defines the approach: `ux_designer` agent connects to Stitch's MCP endpoint via Strands `mcp_client` tool
- The agent participates in the existing Burr state machine, `StageExecutionConfig`, and approval gates

### What remains

- Implement the `ux_designer` agent and its prompt
- Register in `AGENT_FACTORIES` and `STAGE_CONFIGS`
- Add the stage to the Phase 2 workflow (after system traits, before Gate 2)
- Handle Stitch MCP endpoint authentication and error cases

---

## 5. Spec-Driven Export (OpenSpec + Spec Kit)

**Priority:** Medium — strengthens the "specification layer" positioning before GTM launch
**Depends on:** Item 1 (execution contract)

Haytham's GTM narrative is "the specification layer for the AI coding agent ecosystem." Two open formats already exist for feeding specifications to coding agents: [OpenSpec](https://github.com/Fission-AI/OpenSpec) (Fission AI) and [Spec Kit](https://github.com/github/spec-kit) (GitHub). Rather than invent a proprietary format, export to both — letting any AI coding agent (Claude Code, Cursor, Copilot, Devin) consume Haytham's output natively.

### Why both

| Format | Strength | Best for |
|--------|----------|----------|
| **OpenSpec** | Lightweight, change-management via spec deltas, capability-oriented | Teams iterating on an existing spec (aligns with EVOLUTION milestone) |
| **Spec Kit** | Richer artifacts (data models, API contracts, constitution), GitHub-native | Greenfield projects going straight to implementation |

They serve different workflows. Supporting both is low marginal cost once the first is built.

### Mapping from Haytham output

| Artifact | Haytham source |
|----------|---------------|
| Specs / requirements | Capability Model (CAP-F-\*, CAP-NF-\*) — acceptance criteria become requirements, user flows become scenarios |
| Technical plan / design | Architecture Decisions (DEC-\*) + Build/Buy Analysis |
| Tasks | Stories (dependency-ordered, layered) |
| Proposal / project context | MVP Scope + Validation Summary (verdict, risk level, scores) |
| Constitution / config | System Traits + validation constraints |
| Data models / contracts | Layer 0 (foundation) and Layer 3 (API) story sections |

### Scope

- New `ExportableProject` model that aggregates full session context (capabilities, decisions, stories, scope, validation) — the story-only `ExportableStory` is insufficient for spec-driven formats
- `OpenSpecExporter` — produces the `openspec/` directory tree (config.yaml, specs/, changes/initial-mvp/)
- `SpecKitExporter` — produces the `.speckit/` directory tree (constitution.md, specs/NNN-feature/)
- Directory-tree export method on `BaseExporter` (`export_tree() → dict[str, str]`) alongside existing `export() → str`
- Template-based transformation (deterministic, no LLM pass) — acceptance criteria → SHALL statements, user flows → Given/When/Then
- UI integration: export button in Streamlit after STORIES phase completes

### What this does NOT mean

- Replacing the internal session format — OpenSpec/Spec Kit are export targets, not persistence formats
- LLM-enhanced scenario generation — start with templates, upgrade later if quality is insufficient
- Building OpenSpec/Spec Kit CLI integrations — just produce the directory structure; users run their own tooling
- Changing how stories are generated — the export transforms existing output, it does not influence upstream agents

---

## 6. Do NOT Build an Agent Adapter Abstraction (Yet)

**Priority:** Explicit deferral

The narrative describes four executor types (hosted coding agents, design agents, cloud service agents, humans). The temptation is to build a generic adapter interface before any concrete integration exists.

**Do not do this.** Build two concrete integrations (Items 2 and 4), observe what they actually share, then extract the abstraction from real code. Three similar lines of code are better than a premature abstraction.

This item exists to prevent scope creep. Revisit after Items 2 and 4 are complete.

---

## 7. Go-To-Market Strategy

**Priority:** High — begins in parallel with technical milestones
**Depends on:** Items 1-3 (GTM launch requires the closed Genesis loop)

Haytham's strongest positioning is not "another AI validation tool" — it is the **specification layer for the AI coding agent ecosystem**. The $22B+ funded coding agent market (Devin, Cursor, Replit) has a garbage-in-garbage-out problem: they build whatever you tell them, validated or not. Haytham is the quality gate.

**Positioning statement:** *"Haytham turns startup ideas into validated, traceable specifications that any coding agent can execute — so you build the right thing, not just the fast thing."*

### Market context

- 50 million new startups launched annually; 42% fail because they built something nobody wanted
- Every direct competitor (ValidatorAI, DimeADozen, IdeaProof, Aicofounder, FounderPal, RebeccAI, siift) is bootstrapped — no VC-backed player exists
- Coding agents (Devin $10.2B, Cursor $9.9B, Replit $1.16B) all operate downstream — none validate whether the thing should be built
- No existing tool bridges the validate-to-specify gap with capability traceability

### Phase 0: Foundation (Now – Month 3)

**Goal:** Close the Genesis loop, get the product to a demoable state.

| Action | Why | Timeline |
|--------|-----|----------|
| Complete Items 1-3 (execution contract → agent dispatch → validation) | Cannot sell "idea to MVP" without the MVP part | Month 1-3 |
| Record 3 diverse end-to-end demos (web app, CLI, marketplace) | Prove genericity across product types | Month 2-3 |
| Deploy hosted single-tenant instance | Nobody will `git clone` and configure AWS Bedrock credentials | Month 2 |
| Basic auth + session isolation | Minimum for letting anyone try it | Month 2 |

Free credibility plays:

- **"42% post"**: Deep analysis of why 42% of startups fail from no market need, with live demo of Haytham catching a bad idea. Target Hacker News, r/startups, IndieHackers
- **Open-source the scoring methodology**: Publish Stage-Gate + evidence validation as a standalone framework
- **"Haytham vs. ChatGPT" comparison**: Same idea, single-prompt validation vs. 21-agent evidence-gated pipeline

### Phase 1: Developer-led growth (Month 3–9)

**Goal:** 100 active users, 10 paying customers, validated willingness-to-pay.

**Target segment:** Technical founders who already use AI coding agents. They pay for Devin ($500/mo) or Cursor ($20/mo), they understand the value of specifications, and they have seen agents build the wrong thing.

**Where they are:** Hacker News, r/SideProject, r/startups, IndieHackers, AI coding agent Discord servers, Twitter/X AI builder community, ProductHunt.

#### Pricing

Do not compete with $5–29/mo validation tools. They sell reports. Haytham sells a specification pipeline.

| Tier | Price | Includes | Target |
|------|-------|---------|--------|
| **Open Source** | Free | Self-hosted, BYO API keys, community support | Developers, contributors |
| **Starter** | $79/mo | 3 ideas/month, hosted, all 4 phases, PDF export | Solo founders |
| **Pro** | $199/mo | Unlimited ideas, Phase 5 agent dispatch, priority support | Serious founders |
| **Team** | $499/mo | 5 seats, shared sessions, accelerator dashboard | Accelerators, studios |

#### Launch sequence

- **Month 3:** ProductHunt launch + Show HN. Lead with full idea-to-stories demo. 50 free Pro trials for early adopters
- **Month 4–6:** Content-led growth. Weekly posts: "We ran [famous failed startup] through Haytham." Autopsy series analyzing real failures through the Stage-Gate lens
- **Month 6–9:** Integration partnerships — Claude Code, Replit, Amazon Q Developer. Haytham outputs as native input to coding agent sessions

### Phase 2: Accelerator channel (Month 6–15)

**Goal:** 5 accelerator partnerships, $50K+ MRR.

Accelerators are the highest-leverage channel: top 50 accelerators evaluate 500–5,000 ideas each per year. Screening is manual and inconsistent. Every accepted startup becomes a Haytham user.

**Value proposition to accelerators:** *"Your partners manually evaluate 2,000 applications per cohort. Haytham runs every idea through a Stage-Gate framework with evidence-based scoring in minutes, not days."*

| Package | Price | Includes |
|---------|-------|---------|
| **Screening** | $2,000/cohort | Batch validation of up to 500 ideas, ranked by composite score |
| **Full Pipeline** | $5,000/cohort | Screening + full 4-phase spec for top 20 accepted startups |
| **Enterprise** | $10,000/cohort | Full pipeline + custom scoring dimensions + API access |

**Targets (prioritized):** Y Combinator, Techstars, 500 Global (dream); Antler, Entrepreneur First, Founders Factory (mid-tier); vertical accelerators (climate, health, fintech); university programs (Stanford StartX, MIT delta v).

### Phase 3: Platform play (Month 12–24)

**Goal:** Become the specification standard that coding agents consume.

- **Export to open specification formats** (OpenSpec, Spec Kit) — Item 5 delivers this earlier, Phase 3 extends with ecosystem adoption
- **Build integrations** so Claude Code, Devin, Amazon Q, and Cursor consume the format natively
- **API-first** — let other tools generate compatible output (network effects)
- **Marketplace** — third-party agents that extend the pipeline (industry validators, compliance checkers)

### Key metrics

| Metric | Month 3 | Month 9 | Month 18 |
|--------|---------|---------|----------|
| GitHub stars | 500 | 2,000 | 5,000 |
| Active users (monthly) | 50 | 500 | 2,000 |
| Paying customers | 0 | 10 | 100 |
| MRR | $0 | $5K | $50K |
| Ideas validated (total) | 200 | 5,000 | 50,000 |
| Accelerator partners | 0 | 2 | 10 |
| Coding agent integrations | 0 | 1 | 3 |

### What this does NOT mean

- Building a sales team before PMF — content + community + accelerator partnerships get to $50K MRR
- Chasing enterprise before the product is ready — ship to founders first
- Trying to be an AI coding agent — be the brain that feeds Devin, not a competitor to Devin
- Launching on ProductHunt without Phase 5 — "we generate specifications" is lukewarm; "idea in, working app out" is a headline

---

## Sequencing

```
Item 1 (Execution Contract)
  ├── Item 2 (Coding Agent Integration) ── Item 3 (Capability Validation)
  ├── Item 4 (Stitch Integration)
  └── Item 5 (Spec-Driven Export)

Item 6: Deferred until Items 2 + 4 are complete

Item 7 (GTM):
  Phase 0 runs in parallel with Items 1-3
  Phase 1 launches when Items 1-3 are complete (Genesis closed)
  Phase 2 launches at Month 6
  Phase 3 launches at Month 12 (Item 5 accelerates this)
```

Items 2, 4, and 5 can proceed in parallel once Item 1 is done. Item 3 depends on Item 2. Item 5 strengthens the GTM Phase 1 launch ("export to Claude Code/Cursor via OpenSpec") and delivers the Phase 3 "open specification format" goal early. Item 6 is deliberately deferred. GTM Phase 0 (foundation) runs alongside technical work; Phase 1 launch is gated on a closed Genesis loop.
