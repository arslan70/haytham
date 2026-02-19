# Roadmap

Here's where Haytham is headed and where you can help.

Haytham's first milestone, **Genesis** (idea to validated specification), is complete. The items below advance **Milestone 2: Evolution**, extending the system from specification into execution so the loop closes end-to-end: idea in, working validated MVP out. See [VISION.md](../VISION.md) for the full narrative.

**Contribution key:** Items marked **Community Welcome** are good candidates for external contributors. Items marked **Core Team** require deep familiarity with the pipeline internals. If you're unsure, open a discussion or look at the [Contributing Guide](../CONTRIBUTING.md) for starter ideas.

---

## 1. Formalize the Execution Contract

**Priority:** High | **Contribution:** Core Team

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

**Priority:** High | **Contribution:** Core Team
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

**Priority:** High | **Contribution:** Core Team
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

**Priority:** Medium | **Contribution:** Community Welcome
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

**Priority:** Medium | **Contribution:** Community Welcome
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

## 7. Dogfooding: Haytham Specs Itself

**Priority:** Deferred | **Contribution:** Community Welcome | **Depends on:** Evolution (M2)

Run Haytham on itself to generate improvement stories, publish results, and create a community backlog. See [Proposal 001](../proposals/001-docs-review-and-dogfooding-plan.md) for the full plan.

**Why deferred:** Genesis produces greenfield specifications. Running it on Haytham would generate stories for building the system from scratch, not for improving what exists. Meaningful dogfooding requires Evolution's codebase-aware story generation, so the output is targeted changes rather than a full rewrite. Scaffolding (`docs/dogfood/`) is in place and ready for when Evolution lands.

---

## Sequencing

```
Item 1 (Execution Contract)
  ├── Item 2 (Coding Agent Integration) ── Item 3 (Capability Validation)
  ├── Item 4 (Stitch Integration)
  └── Item 5 (Spec-Driven Export)

Item 6: Deferred until Items 2 + 4 are complete
Item 7: Deferred until Evolution (M2) is operational
```

Items 2, 4, and 5 can proceed in parallel once Item 1 is done. Item 3 depends on Item 2. Items 6 and 7 are deliberately deferred.
