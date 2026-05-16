# Hand-authored openspec/ for haytham — judgment-call notes

Date: 2026-05-16
Author: hand-authored against the running codebase (no agent generation)

This file is the record of decisions made while writing `openspec/` for haytham itself. It exists for two reasons:

1. **TBD list** — gaps observed between documented intent (CLAUDE.md, VISION.md, README) and the running code. Future evolve runs should resolve these one way or the other.
2. **Import notes** — judgment calls a future `/haytham:import` command would need to make. Each call has a "what I did" and "why" so the eventual import logic can be designed against evidence rather than speculation.

---

## TBDs (intent vs code divergences)

These are places where the documented design and the actual codebase do not quite line up. None is a bug; each is a small piece of either undocumented choice or unimplemented intent. Surface them; do not fix them silently.

- **CAP-F-010 reviews and CAP-F-011 ux-review have no architecture decisions.** Both are real capabilities with real commands but they do not produce or consume artifacts beyond reading existing ones, so no architectural choice was needed. The architecture-decisions.json `coverage_check.uncovered` lists them. If reviews ever grow non-trivial state, give them a decision.
- **`/haytham:validate --from N` resume semantics.** Mentioned in the validate.md argument hint but the orchestrator's behavior when resuming with partial state is not fully specified anywhere. The cross-cutting spec asserts a scenario; the code does not necessarily implement it cleanly today. Worth a closer look on the next evolve pass that touches the orchestrator.
- **Genericity-across-archetypes evidence.** CAP-NF-004 asserts the pipeline works on web/CLI/API/marketplace inputs. We have evidence for marketplace (GiftKaro) and developer-tool (haytham itself). TinyTales is web-app-shaped and is the cross-archetype test still in flight. No evidence yet for API service or embedded.
- **`scripts/validate_som.py` is referenced indirectly** (it exists in `scripts/` and presumably runs as part of validate_schema or another hook) but its place in the pipeline is undocumented in CLAUDE.md. The current graph models it as a hook helper; a future evolve run should either document it explicitly or remove it if it has been superseded.
- **`scripts/post_bash_seed.sh`** is wired in hooks.json but its purpose is undocumented. The graph mentions it as "seeds session state after Bash calls"; that is a guess from the filename and may be wrong.
- **DEC-AUTH / DEC-DEPLOY / DEC-DB analogues are absent** because the system has no auth, no managed deployment, no database. Listing them as "N/A" felt heavier than omitting them entirely. The architecture-decisions.json reflects this. If a future feature introduces any of these (e.g., a hosted dashboard for the reasoning graph), they get added.
- **The relationship between `.haytham/session/` and `openspec/` for the same product is fuzzy.** Phase 4 writes the OpenSpec under `.haytham/session/phase-4-specs/openspec/`, but `/haytham:evolve` reads from `./openspec/` in the cwd. The handoff is "copy phase 4 output into your project root", but no command explicitly does that copy for an existing-but-built product. `/haytham:build` does it for a fresh scaffold. The graph for haytham itself is hand-authored at the repo root precisely because no command would have produced it there.

---

## Import notes for a future `/haytham:import` command

This section captures the judgment calls a generic import command would have to make if we were to productize this work. Each call is recorded so the eventual command can be designed against real evidence rather than speculation.

### Sourcing

- **Where does the concept anchor come from for an existing system?** I started from the demo's `concept-anchor.json` (produced by `/haytham:demo` against the haytham repo) and reconciled it against CLAUDE.md and VISION.md, replacing the invariants entirely because the demo only read the README. Lesson: the demo-style anchor is shallow because it only sees the public surface. A serious import command needs to read CLAUDE.md (or its equivalent project-instructions file), VISION.md (or the roadmap doc), AND the README, and merge the three. The README gives elevator-pitch invariants; the constitution file gives architectural invariants; the roadmap file gives milestone-scope invariants.
- **Where does the capabilities list come from?** I enumerated capabilities from `commands/*.md` (one per user-facing command) because commands are the unit of user value. Lesson: for a Claude Code plugin specifically, commands are a reliable enumeration source. For a generic codebase (Next.js app, CLI, API service), the equivalent unit is fuzzier — routes for web apps, subcommands for CLIs, endpoints for APIs. The import command needs a per-archetype source-of-truth strategy, not a one-size-fits-all.
- **Where do architecture decisions come from?** I lifted them from CLAUDE.md's "Key Design Decisions" and "PITFALL" sections, each of which already reads like a half-formed ADR. Lesson: most serious projects already have de-facto ADRs scattered in CONTRIBUTING.md, ARCHITECTURE.md, RFC docs, or commit messages. The import command should look for these in a known set of locations before trying to derive decisions from code reading alone.

### Granularity choices

- **Capability granularity = per-command for user-facing CAP-F-*.** I rejected per-agent (too implementation-specific) and per-phase (too coarse for evolve to operate on). For a non-plugin codebase the analog would be: per-route for web apps, per-subcommand for CLIs, per-endpoint for APIs, per-screen for mobile apps. Import needs an archetype-aware granularity selector.
- **Non-functional capabilities = cross-cutting concerns the codebase enforces structurally.** I extracted CAP-NF-* from the things CLAUDE.md treats as non-negotiable invariants (anchor preservation, deterministic-vs-qualitative, zero setup, genericity, phase gating). Lesson: non-functional capabilities are the things that, if violated, would not break a feature but would degrade the system's character. Look for them in the constitution file, not in the feature list.
- **Spec domain grouping.** Seven domains (validation, specification, design, planning, evolution, distribution, cross-cutting) mapping to product-lifecycle phases. Each domain owns 1-3 capabilities. Cross-cutting owns all CAP-NF-* and any capabilities that span multiple domains. Lesson: domain count should be roughly half the capability count. For 12 functional caps I ended up with 6 product-flow domains plus cross-cutting. Holds up.

### Things I deliberately did not do

- **I did not run any agent to generate any file.** Every file is hand-authored from reading the source. A serious import command should consider whether agent-assisted enumeration is acceptable; my call here is no, because agent-generation of a retroactive graph produces fiction at scale.
- **I did not auto-generate spec.md files from capabilities.json.** A future import command could template SHALL/Gherkin from acceptance_criteria, but the templating produces shallow scenarios that miss the real failure modes. I wrote scenarios from observed behavior, not from templated criteria. The import command may want to do both: a template-fill pass followed by an LLM-augment pass that adds scenarios for "what happens when this breaks".
- **I did not copy market-research.md or competitor-research.md from the demo.** The demo did not produce them (batch mode skips the depth-review step?), and evolve does not read them, so they have zero downstream consumers. Lesson: import should not produce files no downstream consumer reads. Audit each file against evolve's file list and the validator's coverage check before generating it.
- **I did not write `idea-analysis.md` and `validation-report.md` from scratch.** I copied them verbatim from the demo. They are historical snapshots, not load-bearing. Lesson: for an existing product, the validation report is a museum piece; the concept anchor is the living artifact. Import should treat them differently.

### Open import-design questions

- **How does import handle a codebase that contradicts its README?** I encountered a mild version of this (README says "concept anchor passed unchanged" but actually the spec-generator agent reads and may reorder, even if it doesn't modify). My call: trust the code, file a TBD against the README. Generic answer: import should produce a "documented vs observed" diff report and surface it to the user before committing the graph.
- **How does import handle a codebase with no constitution file?** Haytham is unusual because CLAUDE.md is rich. Most projects do not have this. Import would have to either (a) infer invariants from code structure (hard), (b) prompt the founder to author a few invariants interactively (matches Genesis Phase 1 idea-analysis structure), or (c) ship with an empty anchor and accept that the first evolve run will surface conflicts that force the founder to author invariants reactively. Option (c) is probably the right MVP for import; (b) is the polish path.
- **How does import handle a brownfield codebase with hidden architectural decisions?** Decisions baked into the structure (e.g., "this is a monolith, not microservices") may not be documented anywhere. Import should produce a draft architecture-decisions.json with placeholders and have the founder confirm. The decision is the founder's; import's job is to make it visible.

### Effort estimate revisited

Originally estimated 4-6 hours. Actual: about 2 hours of focused authoring after the planning conversation, supported by aggressive parallel file reads from giftkaro.pk as a structural reference. The reasoning graph for a codebase you already understand deeply takes less time than expected because the bottleneck is judgment, not authoring. For a brownfield codebase the import command does not understand, the bottleneck inverts.

### What import would NOT replace

- **The collaboration conversation.** This graph would be wrong without the back-and-forth on Q1-Q9. Import can produce a draft; the founder must answer the same set of meta-questions (MVP vs vision scope, capability granularity, which invariants matter) before the draft is useful.
- **The TBD list.** Every brownfield import will produce TBDs. They are the value, not a bug. Import should surface them prominently.

---

## Recommended next steps

1. Commit `openspec/` to the repo. The graph is now the canonical reasoning trail; CLAUDE.md remains the collaboration contract. When they overlap (design decisions), `openspec/architecture-decisions.json` wins.
2. Run `/haytham:evolve "<a small change>"` against this graph as a round-trip smoke test. Look for surprises in the three variant proposals — surprises here are evidence that the graph either lies or omits something important.
3. After the round-trip succeeds, the meta loop is open: every future change to haytham flows through `/haytham:evolve`, which reads this graph, produces variants, and commits code-plus-graph together.
4. When time allows (post kill-or-keep deadline), revisit this note and design `/haytham:import` against the import-notes section above.
