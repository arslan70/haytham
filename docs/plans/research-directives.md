# Plan: Add Research Directives to Haytham Pipeline

## Context

Dogfooding revealed that spec-driven builds produce structurally correct but implementation-thin output. The gap: specs describe WHAT (SHALL + GWT) but not HOW for capabilities requiring domain-specific intelligence (prompt engineering, algorithms, API patterns). Per Guiding Principle 7 (Control Plane, Not Data Plane), Haytham should classify and direct, not research and prescribe. The solution: Research Directives — the architect classifies each capability and generates specific questions for the build agent to answer before implementing.

### Design Decision: Directives stay out of specs

OpenSpec spec files capture observable behavior (SHALL + GWT). Embedding `#### Research Directive` SHOULD sections inside them would mix concerns and rely on the executor LLM noticing embedded hints, which is unreliable.

`research-directives.json` remains a standalone Phase 3 artifact. Spec files stay clean.

### Design Decision: Consumption path uses OpenSpec change artifacts, not IMPLEMENT.md

**Verified by experiment (2026-03-15).** We tested what `openspec instructions apply --change <name> --json` actually passes to the coding agent. The `contextFiles` field contains only change-level artifacts:

```json
{
  "contextFiles": {
    "proposal": "openspec/changes/<name>/proposal.md",
    "specs": "openspec/changes/<name>/specs/**/*.md",
    "design": "openspec/changes/<name>/design.md",
    "tasks": "openspec/changes/<name>/tasks.md"
  }
}
```

The top-level `openspec/project.md` is **not** in `contextFiles`. Content placed in `project.md` or `IMPLEMENT.md` does not reach the coding agent through OpenSpec's machinery.

This rules out three approaches we considered:
1. ~~Route into `project.md`~~ — not in `contextFiles`, never reaches executor
2. ~~Route into `IMPLEMENT.md`~~ — `build.md` completion directs users to `/opsx:propose`, which generates its own proposal/design/tasks workflow. `IMPLEMENT.md` is bypassed.
3. ~~Inject into CLAUDE.md~~ — wrong mechanism (project-level instructions vs. session-specific research)

**The viable path:** `build.md` pre-seeds the OpenSpec change's `design.md` with research directives, then lets `/opsx:propose` complete the remaining artifacts. The `design.md` artifact is described as "Technical design document with implementation details" and its template includes a "Context" section. Research directives fit naturally here as pre-implementation research context.

### Design Decision: Pre-seed design.md, let `/opsx:propose` finish the rest

**Verified by experiment (2026-03-15).** OpenSpec's `spec-driven` schema has a strict artifact dependency chain:

```
proposal → design + specs → tasks
                              ↓
                    apply (requires tasks)
```

`openspec new change` creates only `.openspec.yaml`, no artifact files. `applyRequires: ["tasks"]` means `/opsx:apply` is blocked until `tasks.md` exists. Writing `design.md` directly marks the `design` artifact as `done`, but `specs` still needs `proposal`, and `tasks` needs both `design` and `specs`.

This rules out skipping `/opsx:propose`:
- ~~Skip propose, go straight to apply~~ — apply returns `state: "blocked"` without tasks.md. Tasks depends on specs, which depends on proposal. You'd have to seed all four artifacts manually.

**The viable path:** `build.md` creates the change, seeds `design.md` with research directives, and copies specs into the change. OpenSpec marks both as `done`. When the user runs `/opsx:propose initial-mvp`, it finds the existing change, skips the `done` artifacts, and only generates `proposal.md` and `tasks.md`. The seeded `design.md` (with research directives) flows through to `/opsx:apply` via `contextFiles`.

Specifically, `build.md` will:
1. Read `research-directives.json`
2. Run `openspec new change initial-mvp`
3. Copy Haytham's specs into the change's `specs/` directory (marks `specs` artifact as `done`)
4. Write `design.md` with a `## Pre-Implementation Research` section (marks `design` artifact as `done`)
5. Tell the user to run `/opsx:propose initial-mvp` — it will only need to generate `proposal.md` and `tasks.md`

## Changes (7 source files, 2 fixture files)

### 1. `scripts/validate_schema.py` — Add schema + validation

- Add `"research-directives.json": ["directives", "summary"]` to SCHEMAS dict
- Add validation block (after build-buy.json block):
  - Classification enum: `llm_dependent`, `algorithm_dependent`, `integration_dependent`, `domain_dependent`, `standard`
  - `standard` is exclusive: if present, it must be the only classification
  - `research_required: true` -> `classifications` must not include `"standard"`, `questions` must be non-empty list
  - `research_required: false` -> `classifications` must be exactly `["standard"]`
  - `summary.total` matches `len(directives)`
  - `summary.requiring_research` matches actual count
  - Cross-file check (guarded by `os.path.exists`): every `capability_id` exists in `capabilities.json`, every CAP-F-* has a directive

### 2. Test fixtures + tests

- Create `tests/fixtures/valid_research_directives.json` — 3 directives (1 standard, 1 llm_dependent, 1 algorithm_dependent)
- Create `tests/fixtures/invalid_research_directives.json` — bad classification, empty questions with research_required:true, standard mixed with other classifications, summary mismatch
- Add 4-5 test cases in `tests/test_plugin_sanity.py` under `TestSchemaValidation`

### 3. `agents/architect.md` — Add Part 3: Research Directives

After Part 2 self-check, add:
- Classification definitions (5 types, capability can have multiple except standard which is exclusive)
- Archetype-awareness instruction: "Use the concept anchor's archetype and system traits to frame questions appropriate to the product's runtime context. A CLI plugin's integration questions differ from a mobile app's."
- Instructions: classify each CAP-F-*, generate 2-4 questions for non-standard capabilities
- Questions must focus on approach/strategy, not technology selection (technology is already decided in Parts 1-2)
- JSON schema for `research-directives.json` (directives array + summary)
- Self-check (7 items matching existing style)
- Update intro line: "two tasks" -> "three tasks"
- Update File I/O write list: add `research-directives.json`

### 4. `commands/build.md` — Route directives into OpenSpec change's `design.md`

This is the critical consumption path. The coding agent reads `design.md` from `contextFiles` during `/opsx:apply`, so research directives placed here are guaranteed to reach the executor.

Changes:

- Add a read of `research-directives.json` early in the flow (after prerequisite checks, read from `.haytham/session/phase-3-how/research-directives.json`)
- After Step 3 (copy specs), replace the existing Step 4 (Generate Implementation Prompt) with a new step:

**New Step 4: Seed OpenSpec change with research directives**

1. Create the initial change: `openspec new change initial-mvp`
2. Copy Haytham's specs into the change directory: copy all `<project-directory>/openspec/specs/*/` into `<project-directory>/openspec/changes/initial-mvp/specs/`. This marks the `specs` artifact as `done` in OpenSpec's dependency chain.
3. If `research-directives.json` has any directives where `research_required: true`, write a `design.md` into the change directory (`<project-directory>/openspec/changes/initial-mvp/design.md`) with this content:

```markdown
## Context

Implementation design for the initial MVP build.

## Pre-Implementation Research

Some capabilities require domain research before implementation. For each item below, research the questions BEFORE writing code for that capability. Apply your findings to the implementation approach.

### {Capability Name} [{capability_id}]
**Classification:** {classifications}
- {question 1}
- {question 2}
...

## Goals / Non-Goals

**Goals:** Build the full initial MVP from specs.
**Non-Goals:** No optimization, no deployment, no testing infrastructure beyond what specs require.
```

4. If no capabilities require research, do not create `design.md` (let `/opsx:propose` generate it naturally)

- Only include capabilities where `research_required: true`
- Remove the existing Step 4 (Generate Implementation Prompt / `IMPLEMENT.md`). The OpenSpec change replaces it.
- Update the completion message: tell the user the change `initial-mvp` has been pre-seeded with specs and research context, and to run `/opsx:propose initial-mvp`. OpenSpec will find the existing change, skip the `done` artifacts (specs, design), and only generate `proposal.md` and `tasks.md` before the user can run `/opsx:apply`.

### 5. `commands/design.md` — Update digest and review

- Step 1 agent task: add `research-directives.json` to write list
- Step 1 digest: add `Research directives: [N] capabilities flagged ([classifications])`
- Step 2 review: show directives inline with this format:
  ```
  - **Research Directives:** [N] of [M] capabilities require pre-implementation research
    - CAP-F-001 (Capability Name): llm_dependent — 3 questions
    - CAP-F-003 (Capability Name): algorithm_dependent — 2 questions
  ```
- Completion message: add `research-directives.json` to file listing

### 6. `commands/haytham.md` — Update Phase 3 and Phase 5

- Upstream dependencies table: add `phase-3-how/research-directives.json` to a new build row (build reads it during OpenSpec change seeding)
- Step 11 agent task: add `research-directives.json` to write list
- Step 11 digest: add research directives count
- Completion summary: add file to Phase 3 listing

### 7. `commands/plan.md` — Update file listing only

- Completion file listing: add `research-directives.json` under Phase 3
- No agent task changes needed (spec-generator does not read directives)

## What does NOT change

- **`agents/spec-generator.md`** — No changes. Spec files stay clean: only SHALL statements and GWT scenarios. The spec-generator does not read or embed research directives. This keeps specs focused on observable behavior (what OpenSpec expects) and avoids SHOULD sections that the executor might ignore.
- **Heading hierarchy in specs** — No new H4 sections. `#### Scenario:` and `#### Output Format` remain the only H4 patterns.

## Implementation Order

1. `validate_schema.py` — validation first (deterministic rules before LLM prompts)
2. Test fixtures + tests — verify validation works
3. `architect.md` — Part 3 addition
4. `build.md` — OpenSpec change seeding with research directives (closes the loop)
5. `design.md` — Phase 3 command updates
6. `haytham.md` — full pipeline updates
7. `plan.md` — file listing update

## Verification

1. Run `python3 -m pytest tests/test_plugin_sanity.py -v` — all existing + new tests pass
2. Run `/haytham:design` on a test idea — verify `research-directives.json` is produced with valid classifications and archetype-appropriate questions
3. Run `/haytham:build` — verify:
   a. The OpenSpec change `initial-mvp` is created
   b. `openspec/changes/initial-mvp/specs/` contains the copied spec directories
   c. `openspec/changes/initial-mvp/design.md` contains a Pre-Implementation Research section with the correct capabilities and questions
   d. Standard capabilities have NO entry in the Pre-Implementation Research section
   e. `openspec status --change initial-mvp --json` shows `specs` and `design` as `done`, `proposal` as `ready`, `tasks` as `blocked`
4. Run `/opsx:propose initial-mvp` — verify:
   a. OpenSpec detects the existing change and skips `done` artifacts
   b. It generates `proposal.md` and `tasks.md` only
   c. `openspec instructions apply --change initial-mvp --json` shows all four artifacts in `contextFiles`
5. Check that spec.md files contain NO `#### Research Directive` sections (specs stay clean)
6. Run `/opsx:apply initial-mvp` — verify the coding agent references the research questions before implementing the relevant capabilities
