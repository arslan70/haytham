# Plan: Replace Phase 4 (Stories) with Phase 4 (Specs)

## Context

Phase 4 currently generates implementation stories (stories.json + execution-contract.json) designed for human development teams. The goal is to produce implementation-ready specifications that a coding agent can use to build the system from zero.

Stories provide effort estimates, human-sized work units, and weekly schedules. Specs provide SHALL requirements, Gherkin acceptance criteria, architecture context, and integration details. For agent handoff, specs are strictly superior.

## Design Decisions

- **Single agent, not split.** Per CLAUDE.md's pitfall on splitting holistic reasoning. One `spec-generator` agent receives all upstream context and produces a coherent OpenSpec bundle.
- **OpenSpec format, not custom JSON.** The founder directive from the dogfood run explicitly chose OpenSpec. The codebase already has documentation (`docs/openspec-output.md`), a validation skill (`test-openspec-export`), and a blog post describing the format. The agent produces OpenSpec files directly, eliminating the need for a separate export step.
- **Multiple output files.** Unlike other agents that write 1-2 JSON files, the spec-generator writes an OpenSpec directory tree (config.yaml + project.md + specs/\*/spec.md). This is the right trade-off: the format is the deliverable.
- **Model: opus.** Same as the current story-planner. This is the heaviest synthesis task in the pipeline.
- **Clean break.** Output directory changes from `phase-4-stories/` to `phase-4-specs/`. Old session data from prior runs becomes orphaned. No migration needed.

## OpenSpec Output Structure

The agent writes to `.haytham/session/phase-4-specs/openspec/`:

```
openspec/
  config.yaml                  # Project metadata, system traits, appetite
  project.md                   # Tech stack, architecture decisions, build/buy
  specs/
    {domain-slug}/
      spec.md                  # SHALL statements + Gherkin scenarios (functional)
    cross-cutting/
      spec.md                  # Non-functional requirements as SHALL statements
```

### config.yaml

```yaml
name: short-project-name
description: Full idea description from concept anchor
appetite: Small | Medium | Large
generated_at: ISO timestamp
traits:
  interface: [browser]
  auth: multi_user
  deployment: [cloud_hosted]
  data_layer: remote_db
  realtime: false
  communication: none
  payments: none
  scheduling: none
```

Source: `system-traits.json`, `concept-anchor.json`, `mvp-scope.md`

### project.md

```markdown
# {Project Name}

## Tech Stack

From architecture decisions: framework, language, database, hosting.

## Architecture Decisions

### DEC-STACK-001: Technology Stack Selection

**Decision:** Use Next.js with TypeScript
**Rationale:** Fits the system traits (browser interface, cloud hosted)
**Trade-offs:** ...

### DEC-AUTH-001: Authentication Approach

**Decision:** Use Supabase Auth
**Rationale:** From build/buy analysis (BUY recommendation)

## Build/Buy Analysis

| Component | Recommendation | Service |
|-----------|---------------|---------|
| Auth | BUY | Supabase Auth |
| Database | BUY | Supabase Postgres |
| Hosting | BUY | Vercel |

## Dependencies

| Package | Version | Purpose | Dev Only |
|---------|---------|---------|----------|
| next | ^14.0.0 | Web framework | false |
```

Source: `architecture-decisions.json`, `build-buy.json`, `system-traits.json`

### specs/{domain-slug}/spec.md

```markdown
# {Domain Name}

## Purpose

What this domain covers and why it exists in the MVP.

### Requirement: {Capability Name} [CAP-F-001]

The system SHALL {bare infinitive verb} {what the system does}.

#### Scenario: {Happy path name}

- **Given** {precondition}
- **When** {action}
- **Then** {expected outcome}

#### Scenario: {Error case name}

- **Given** {precondition}
- **When** {invalid action}
- **Then** {error handling}
```

Source: `capabilities.json` (functional capabilities grouped by domain)

### specs/cross-cutting/spec.md

```markdown
# Cross-Cutting Requirements

## Purpose

Non-functional requirements that apply across all domains.

### Requirement: {NF Capability Name} [CAP-NF-001]

The system SHALL {bare infinitive verb} {what the system does}.

#### Scenario: {Verification scenario}

- **Given** {precondition}
- **When** {trigger}
- **Then** {measurable outcome}
```

Source: `capabilities.json` (non-functional capabilities)

## Mapping from Upstream Artifacts

| Haytham Artifact | OpenSpec Location |
|---|---|
| System traits (`system-traits.json`) | `config.yaml` traits section |
| Concept anchor (`concept-anchor.json`) | `config.yaml` name/description |
| MVP scope (`mvp-scope.md`) | Domain grouping in `specs/` |
| Architecture decisions (`architecture-decisions.json`) | `project.md` Architecture Decisions |
| Build/buy (`build-buy.json`) | `project.md` Build/Buy Analysis + Dependencies |
| Functional capabilities (`capabilities.json`) | `specs/{domain}/spec.md` as SHALL statements |
| Non-functional capabilities (`capabilities.json`) | `specs/cross-cutting/spec.md` as SHALL statements |
| Acceptance criteria (derived) | Gherkin scenarios under each requirement |

## Implementation Sequence

### Phase A: Create new agent + fixtures (no breakage)

1. **Create `agents/spec-generator.md`**
   - Frontmatter: `name: spec-generator`, `tools: Read, Write`, `model: opus`
   - Reads 6 upstream files: capabilities.json, mvp-scope.md, system-traits.json, architecture-decisions.json, build-buy.json, concept-anchor.json
   - Writes OpenSpec directory tree to `.haytham/session/phase-4-specs/openspec/`
   - Three-part prompt:
     1. `config.yaml` from system traits + concept anchor + appetite
     2. `project.md` from architecture decisions + build/buy analysis
     3. `specs/*/spec.md` from capabilities grouped by domain, with SHALL statements and Gherkin scenarios
   - Self-check: every CAP-F-* and CAP-NF-* appears as a SHALL requirement, concept anchor compliance, SHALL grammar uses bare infinitive verbs, every scenario has Given/When/Then
   - Appetite-bound limits on spec complexity (derived from the existing story limits: Small/8 stories ≈ 10 requirements across 3 domains, Medium/15 ≈ 20 across 5, Large/25 ≈ 35 across 8; scenarios per requirement cap prevents verbose agents from generating exhaustive edge cases):

     | Appetite | Max Domains | Max Requirements | Max Scenarios per Req |
     |----------|-------------|------------------|-----------------------|
     | Small (1-2 weeks) | 3 | 10 | 3 |
     | Medium (3-4 weeks) | 5 | 20 | 4 |
     | Large (5-6 weeks) | 8 | 35 | 5 |

2. **Create `tests/fixtures/valid_openspec/`**
   - `config.yaml` with all required fields (name, description, appetite, traits, generated_at)
   - `project.md` with Tech Stack, Architecture Decisions, Build/Buy Analysis sections
   - `specs/test-domain/spec.md` with valid SHALL statements and Gherkin scenarios
   - `specs/cross-cutting/spec.md` with non-functional requirements

3. **Create `tests/fixtures/invalid_openspec/`**
   - `config.yaml` missing `traits` key
   - `specs/test-domain/spec.md` with bad SHALL grammar ("SHALL ensures" instead of "SHALL ensure")

### Phase B: Update validation infrastructure

4. **Update `scripts/validate_schema.py`**
   - Remove `stories.json` and `execution-contract.json` from the `SCHEMAS` dict
   - Remove the stories.json-specific dependency validation (lines 133-143)
   - Do NOT add OpenSpec validation here. The PostToolUse hook is JSON-only by design (filters on `.endswith(".json")`, uses `json.load()`). OpenSpec output is YAML + Markdown, which requires YAML parsing (no `pyyaml` dependency exists) and Markdown section detection (regex-based, fragile). Forcing this into the per-file hook would be an architectural mismatch. OpenSpec validation belongs in a standalone script (see step 5).

5. **Create `scripts/validate_openspec.py`**
   - Standalone script (not a PostToolUse hook) that validates a complete OpenSpec directory
   - Takes one argument: path to the openspec/ directory
   - Checks:
     - `config.yaml` exists and has required keys: name, description, appetite, traits, generated_at (parse YAML with simple regex or `yaml.safe_load` with a try/import fallback)
     - `project.md` exists and has required sections: `## Tech Stack`, `## Architecture Decisions`
     - At least one `specs/*/spec.md` exists
     - `specs/cross-cutting/spec.md` exists
     - SHALL grammar: use a blocklist of known bad third-person verbs (`ensures`, `provides`, `handles`, `validates`, `manages`, `supports`, `maintains`, `performs`, `creates`, `returns`, `displays`, `requires`, `allows`, `enables`). A suffix-based rule (rejecting any word ending in `-s`) would false-positive on bare infinitives like "process", "address", "access"
     - Gherkin completeness: every `#### Scenario:` block contains Given, When, Then
   - Accepts an optional second argument: path to `capabilities.json`. When provided, checks that every CAP-F-* and CAP-NF-* ID from capabilities.json appears in at least one spec file (coverage check)
   - Exits 0 with no output on success, exits 1 with warnings on failure
   - Called by the orchestrating commands (plan.md, haytham.md) after the agent completes, not by the PostToolUse hook

6. **Update `scripts/check_phase_prereqs.sh`**
   - Change `story-planner` to `spec-generator` in the agent name grep (line 52)

### Phase C: Update commands (main breaking change)

7. **Update `commands/plan.md`**
   - Rename to reflect specs: "Run Phase 4 (SPECS) - Generate implementation-ready OpenSpec"
   - Launch `spec-generator` agent instead of `story-planner`
   - Output path: `.haytham/session/phase-4-specs/openspec/`
   - After agent completes, run deterministic coverage check: read `capabilities.json`, glob `phase-4-specs/openspec/specs/*/spec.md`, grep for CAP-F-* and CAP-NF-* references across all spec files, report any missing capabilities. Run `scripts/validate_openspec.py` with the openspec directory and capabilities.json path. If validation fails, report the warnings to the user before the digest.
   - Update digest format:
     > **OpenSpec generated.** Here's what was produced:
     >
     > - **Domains:** [count] — [list domain names]
     > - **Requirements:** [count] SHALL statements across all domains
     > - **Scenarios:** [count] Gherkin scenarios
     > - **Architecture decisions:** [count] documented in project.md
     > - **Coverage:** All [N] functional + [M] non-functional capabilities covered
   - Update review questions: "Are the domain groupings right?", "Do the SHALL statements capture what matters?", "Are the scenarios testable?"

8. **Update `commands/haytham.md`**
   - Line 16: Directory setup: `phase-4-specs/` instead of `phase-4-stories/`
   - Line 332 (Gate 3 ask): "proceed to specification generation" instead of "story planning"
   - Phase 4 section header (line 347): "SPECS (OpenSpec Generation)" instead of "STORIES (Implementation Plan)"
   - Step 13 (line 370): Launch `spec-generator`, update file paths and digest. After agent completes, run `scripts/validate_openspec.py` with the openspec directory and capabilities.json path. Report any validation warnings before the digest.
   - Step 14 (line 382): Review OpenSpec sections instead of stories
   - Completion (line 397): Update file listing to show `phase-4-specs/openspec/` directory
   - Completion message (line 405): "specification" instead of "stories and execution contract"

9. **Update `commands/design.md`**
   - Line 68 (Gate 3 ask): "proceed to specification generation" instead of "story planning"
   - Line 80 (completion message): "specification generation" instead of "story planning"

### Phase D: Update tests

10. **Update `tests/test_plugin_sanity.py`**
    - Remove `test_valid_stories` and `test_invalid_stories_broken_dependency`
    - Add `test_valid_openspec`: calls `validate_openspec.py` against `tests/fixtures/valid_openspec/`, asserts exit 0
    - Add `test_valid_openspec_with_coverage`: calls `validate_openspec.py` with both the valid fixture directory and a capabilities fixture, asserts all CAP-* IDs are found
    - Add `test_invalid_openspec_bad_shall`: calls `validate_openspec.py` against `tests/fixtures/invalid_openspec/`, asserts exit 1 and output contains SHALL grammar warning
    - Add `test_invalid_openspec_missing_traits`: asserts exit 1 and output contains missing traits warning
    - Verify `validate_openspec.py` compiles (already covered by `test_python_scripts_compile`)

### Phase E: Update review commands

These are full rewrites of the Phase 4 sections, not just text swaps. Each review command references stories.json, execution-contract.json, depends_on, and story-specific language throughout the Phase 4 checks.

11. **Update `commands/review-fidelity.md`** (full rewrite of Check 7)
    - Line 28: Change file path from `phase-4-stories/stories.json` to `phase-4-specs/openspec/`
    - Lines 84-90: Rewrite Check 7 entirely. Current text references "implementation stories" and "stories collectively describe" 4 times.
    - New Check 7 "Specification Fidelity (if phase-4-specs/openspec/ exists)": Do the SHALL statements and Gherkin scenarios describe building the product the founder envisioned? Check that domain groupings reflect the founder's emphasis, SHALL statements preserve the idea's distinctive features, and config.yaml traits match the concept anchor.
    - PASS: Specs collectively describe the founder's product
    - PARTIAL: Specs describe the product but domain emphasis has drifted from the original
    - FAIL: Specs describe a generic product, or are so template-like they could apply to any similar project

12. **Update `commands/review-consistency.md`** (full rewrite of Checks 9-10)
    - Lines 34-35: Change file paths from `phase-4-stories/stories.json` and `execution-contract.json` to `phase-4-specs/openspec/` files
    - Lines 109-125: Rewrite Checks 9-10 entirely. Current text references stories.json, execution-contract.json, depends_on, "implementing story."
    - New Check 9 "Spec Coverage": Read all `specs/*/spec.md` files. Check that every CAP-F-* and CAP-NF-* from capabilities.json appears as a SHALL requirement in at least one spec file.
    - New Check 10 "Cross-Reference Integrity": Read `project.md`. Check that all DEC-* IDs referenced match entries in `architecture-decisions.json`, and that config.yaml traits match `system-traits.json`.

13. **Update `commands/review-actionability.md`** (full rewrite of Criteria 5-8 + prerequisites)
    - Lines 21-22: Change prerequisite file paths from `phase-4-stories/stories.json` and `execution-contract.json` to `phase-4-specs/openspec/config.yaml` and `phase-4-specs/openspec/project.md` (plus at least one `specs/*/spec.md`)
    - Lines 69-103: Rewrite Criteria 5-8 entirely. Current text references stories, acceptance criteria testability, dependency chain viability, and appetite compliance in story terms.
    - New Criterion 5 "SHALL Precision": Statements use bare infinitive verbs, are specific (not vague "manage content"), and are individually testable
    - New Criterion 6 "Scenario Completeness": Every requirement has at least one happy-path and one error/edge-case scenario. Scenarios use concrete values, not placeholders
    - New Criterion 7 "Architecture Completeness": project.md covers all DEC-* decisions with rationale. Build/Buy table is complete. Dependencies list is specific (named packages with versions)
    - New Criterion 8 "Agent Readability": A coding agent can pick up `openspec/` and start implementing without ambiguity. config.yaml provides enough context to bootstrap the project. Spec files are self-contained per domain.
    - Line 127: Change agent reference from `agents/story-planner.md` to `agents/spec-generator.md`

### Phase F: Delete old files

14. **Delete `agents/story-planner.md`**
15. **Delete `tests/fixtures/valid_stories.json`**
16. **Delete `tests/fixtures/invalid_stories.json`**

### Phase G: Update documentation and blog

17. **`CLAUDE.md`** — Agent list (story-planner to spec-generator), plugin structure (phase-4-stories to phase-4-specs), output description (stories.json to openspec/)

18. **`docs/how-it-works.md`** — This file has ~15 story references across multiple sections. Update all of the following:
    - Line 10: "Every story traces to a capability" → "Every requirement traces to a capability"; "When stories reach a developer" → "When specs reach a developer"
    - Lines 41-47: Mermaid diagram. Rename `stories` node, `stories_phase` subgraph label ("SPECS: Specification" instead of "STORIES: Tasks"), `stories[Story Planner]` → `specs[Spec Generator]`, output label ("Implementation-Ready OpenSpec" instead of "Implementation-Ready Backlog")
    - Line 88: "story generation defaults to web-app patterns" → "spec generation defaults to web-app patterns"
    - Line 103: "proceed to story generation" → "proceed to specification generation"
    - Lines 108-114: Rewrite Phase 4 section entirely. Replace Story Planner description with Spec Generator description. Replace story/execution contract language with OpenSpec language (SHALL statements, Gherkin scenarios, domain specs).
    - Line 129: Agents table. "Story Planner | STORIES | Story generation, validation, and dependency ordering" → "Spec Generator | SPECS | OpenSpec generation with SHALL statements and Gherkin scenarios"
    - Line 135: "story IDs" → "requirement IDs"
    - Lines 156-158: Directory tree. `phase-4-stories/` → `phase-4-specs/openspec/`, replace `stories.json` and `execution-contract.json` with `config.yaml`, `project.md`, `specs/*/spec.md`

19. **`docs/getting-started.md`**
    - Line 31: Command table. "STORIES" → "SPECS", "Dependency-ordered stories with acceptance criteria" → "OpenSpec with SHALL requirements and Gherkin scenarios"
    - Line 44: Directory listing. `phase-4-stories/` → `phase-4-specs/`, "Implementation-ready stories" → "Implementation-ready OpenSpec"

20. **`docs/openspec-output.md`** — Update to reflect that Phase 4 now produces OpenSpec directly (no separate export step). Remove "After the STORIES phase completes" framing. Replace "What Gets Exported" with "What Gets Produced". Remove references to export pipelines and zip files.

21. **`docs/index.md`** — Phase cards, mermaid diagram

22. **`README.md`**
    - Line 5: "story generation" → "specification generation"
    - Line 34: `/haytham:plan` description. "What are the tasks?" → "What are the specs?"
    - Line 46: Output table. "Dependency-ordered stories with acceptance criteria" → "OpenSpec with SHALL requirements and Gherkin scenarios"
    - Line 48: "Every story traces to a capability" → "Every requirement traces to a capability"
    - Line 50: Remove "can be exported as OpenSpec" framing (it now produces OpenSpec directly)

23. **`VISION.md`** — This file has ~15 story references across Genesis, Evolution, and Sentience sections. All need updating:
    - Line 7: "ordered stories" → "ordered requirements" or "OpenSpec"
    - Line 33: "Hand stories to coding agents" → "Hand specs to coding agents"
    - Line 38: "ordered user stories" → "an OpenSpec specification"; "execution context that Phases 5-6 feed to coding agents" stays
    - Line 42: "10 implementation-ready stories" → "an implementation-ready OpenSpec"
    - Line 46: "execution contract" → "OpenSpec"
    - Line 59: "every story traces to a capability" → "every requirement traces to a capability"
    - Line 65: "Generates targeted stories" → "Generates targeted specs"
    - Lines 72, 74, 76: "generates implementation stories" / "generates a fix story" / "generates stories with clear before/after" → use "spec" or "requirement" language
    - Line 98: "Generate improvement stories" → "Generate improvement specs"
    - Line 156: "A coding agent implementing a story knows the capability it serves" → "A coding agent implementing a requirement knows the capability it serves"
    - Line 157: "story → capability → decision → rationale" → "requirement → capability → decision → rationale"
    - Line 184: "dispatches stories to coding agents" → "dispatches specs to coding agents"
    - Line 212: "story to capability, implementation to story" → "requirement to capability, implementation to requirement"

24. **`docs/system-evolution.md`** — Phase name references (lines 9, 13, 21, 41, 71)

25. **`docs/pivot-plan.md`** — Story references in three locations:
    - Line 87: "STORIES (implementation plan)" → "SPECS (specification generation)"
    - Line 133: "The architecture and story generation respond to traits" → "The architecture and spec generation respond to traits"
    - Line 196: "generate targeted stories, implement, validate" → "generate targeted specs, implement, validate"

26. **Bump `marketplace.json` version** — Per CLAUDE.md: "Bump it with every release." Update `version` in `.claude-plugin/marketplace.json` `plugins[0]` from `0.1.8` to `0.2.0` (minor version bump for a breaking output format change).

27. **Update `test-openspec-export` skill** at `.claude/skills/test-openspec-export/SKILL.md` — Reframe from "export validation" to "output validation". The skill was designed to validate OpenSpec after a separate export/conversion step. Now that Phase 4 produces OpenSpec directly, the skill's purpose is validating agent output quality. Changes:
    - Line 3 (description): Remove "zip export" and "export quality after pipeline runs". New description: "Use when reviewing or testing OpenSpec output from Phase 4, validating spec quality, or when the user provides an openspec directory for review"
    - Line 6-8: Remove "zip" framing. "Validate an OpenSpec directory against the expected format and known quality issues."
    - Line 17: Change extraction step to read from `.haytham/session/phase-4-specs/openspec/` directly instead of unzipping
    - Line 86: Remove "exporter" fix location. Fixes belong in the **spec-generator agent** or **upstream data**.

28. **Update blog posts** — Blog is not yet live, so update references for accuracy.
    - `docs/blog/posts/2026-03-03-build-where-developers-already-are.md`:
      - Line 18: "dependency-ordered stories with acceptance criteria" → "SHALL requirements with Gherkin acceptance criteria" (or similar)
      - Line 49: "building the whole thing from the generated stories" → "building the whole thing from the generated spec"
      - Line 90: "you get an execution contract that Claude Code can implement directly" → "you get an OpenSpec that Claude Code can implement directly"
    - `docs/blog/posts/2026-03-01-idea-to-agent-ready-spec.md`:
      - Line 30: "decompose features into stories with clear acceptance criteria, ordered by dependency" → "decompose features into SHALL requirements with Gherkin scenarios"
      - Line 36: "STORIES (What are the tasks?)" → "SPECS (What are the specifications?)"; "Dependency-ordered user stories with Gherkin acceptance criteria" → "OpenSpec with SHALL requirements and Gherkin scenarios"
      - Line 40: **Full rewrite required.** The current text describes "a deterministic export pipeline (no LLM calls) that transforms structured data into OpenSpec." This entire concept is eliminated. Phase 4 now produces OpenSpec directly via the spec-generator agent. Replace with: "The SPECS phase produces OpenSpec directly. The spec-generator agent reads all upstream artifacts and writes the OpenSpec directory tree: config.yaml for project metadata, project.md for architecture context, and domain-grouped spec files with SHALL statements and Gherkin scenarios. Every capability becomes a requirement. Every architecture decision is documented with rationale."
      - Line 74: "Gherkin scenario pulled from the story acceptance criteria" → "Gherkin scenario generated from the capability model"
      - Line 90: "After the STORIES phase completes, use the export dropdown" → "After the SPECS phase completes, the OpenSpec directory is ready"
    - `docs/blog/posts/2026-02-20-agents-playing-telephone.md`:
      - Line 24: "write stories" → "write specs"
      - Lines 110-115: Code example references "stories" and `MAX_STORIES_SHORT`. Update variable names to use `requirements`/`MAX_REQUIREMENTS_SHORT` and update the comment to reference spec constraints instead of story counts
    - `docs/blog/posts/telephone-comic.svg`:
      - Lines 77, 83: SVG labels say "Stories". Update to "Specs"

### Phase H: Verify

29. Run `python3 -m pytest tests/test_plugin_sanity.py -v` — all tests must pass
30. Run `scripts/validate_openspec.py tests/fixtures/valid_openspec/ tests/fixtures/valid_capabilities.json` — must exit 0
31. Run the updated `test-openspec-export` skill against the valid fixture to confirm the format checks pass
32. Grep the full repo for residual "story-planner", "stories.json", "execution-contract.json", "phase-4-stories" references. Any hits outside `docs/plans/` and `docs/system-evolution.md` (historical record) are missed updates.

## Risks

1. **Agent prompt quality.** OpenSpec has strict formatting rules (SHALL grammar, Gherkin structure, heading hierarchy). The agent prompt needs embedded examples and explicit grammar rules. The existing `test-openspec-export` skill documents exactly what to check.
2. **Partial writes.** The spec-generator writes 4+ files (config.yaml, project.md, N domain specs, cross-cutting spec). If the agent hits a context limit or errors mid-generation, the output directory looks structurally valid but is missing content. Mitigated by the deterministic coverage check in the orchestrating commands: after the agent completes, `validate_openspec.py` runs with capabilities.json to verify every CAP-F-* and CAP-NF-* ID appears in at least one spec file. This catches partial writes without relying on the agent's in-prompt self-check.
3. **Domain grouping.** The agent must decide how to group functional capabilities into domain folders. The grouping should follow the IN SCOPE items from mvp-scope.md. The prompt should instruct the agent to use scope items as domain boundaries.
4. **Old session data.** Existing `phase-4-stories/` directories from prior runs become orphaned. No migration needed, this is a dev-time change.
5. **Cross-reference integrity.** The test `test_command_agent_refs_exist` checks that agent references in commands resolve to files in `agents/`. Phase F (deletion) must come after Phase C (command updates) to avoid test failures.
6. **YAML parsing dependency.** `validate_openspec.py` needs to parse config.yaml. Use `yaml.safe_load` with a try/import fallback to simple regex extraction for the required keys. Do not add pyyaml as a hard dependency; the script should work either way.
