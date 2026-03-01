# OpenSpec + Spec Kit Documentation Update Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Update all documentation to reflect the completed OpenSpec + Spec Kit export feature, and write a blog post for community outreach.

**Architecture:** Documentation-only changes across 10 existing files + 2 new files. No code changes. Each task is one file edit, verified with `mkdocs build --strict`.

**Tech Stack:** MkDocs Material, Markdown, YAML

**Design doc:** `docs/plans/2026-03-01-openspec-speckit-docs-design.md`

---

### Task 1: Update README.md with export bullet

**Files:**
- Modify: `README.md:69-73` (the "What You Get" bullet list)

**Step 1: Add the export bullet**

After the existing "Ordered user stories" bullet (line 73), add:

```markdown
- **Agent-ready exports**: download as [OpenSpec](https://github.com/Fission-AI/OpenSpec) or [Spec Kit](https://github.com/github/spec-kit) and hand the spec directly to Claude Code, Cursor, or Copilot.
```

**Step 2: Verify**

Run: `cat README.md | head -76 | tail -15`
Expected: six bullets under "What You Get", the last one being "Agent-ready exports".

**Step 3: Commit**

```bash
git add README.md
git commit -m "docs: add OpenSpec/Spec Kit export to README"
```

---

### Task 2: Update landing page (docs/index.md)

**Files:**
- Modify: `docs/index.md:103-109` (after the "Ordered user stories" card, before `</div>`)

**Step 1: Add a sixth card**

After the "Ordered user stories" card block (ending line 107) and before the closing `</div>` (line 109), add:

```markdown

-   :material-export:{ .lg .middle } **Agent-ready exports**

    ---

    Download as [OpenSpec](https://github.com/Fission-AI/OpenSpec) or [Spec Kit](https://github.com/github/spec-kit). Feed your spec directly to Claude Code, Cursor, or Copilot.
```

**Step 2: Verify MkDocs builds**

Run: `uv run mkdocs build --strict 2>&1 | tail -5`
Expected: no errors.

**Step 3: Commit**

```bash
git add docs/index.md
git commit -m "docs: add export card to landing page"
```

---

### Task 3: Update how-it-works.md with export section

**Files:**
- Modify: `docs/how-it-works.md:134-138` (after the "Final Output" subsection, before the `---` divider and "Agents at a Glance")

**Step 1: Add "Spec-Driven Export" subsection**

After the "Final Output" paragraph (line 136) and before the `---` on line 138, insert:

```markdown

### Spec-Driven Export

Once the stories phase completes, you can export the full specification (not just stories, but capabilities, architecture decisions, system traits, and traced requirements) in two formats designed for AI coding agents:

| Format | Best for | What it produces |
|--------|----------|-----------------|
| **[OpenSpec](https://github.com/Fission-AI/OpenSpec)** | Iterating on an existing spec, change management via spec deltas | `openspec/` directory with `config.yaml`, `project.md`, and per-domain `spec.md` files with SHALL statements and Gherkin scenarios |
| **[Spec Kit](https://github.com/github/spec-kit)** | Greenfield projects going straight to implementation, GitHub-native workflows | `.specify/` directory with `constitution.md`, per-feature spec/plan/tasks, data models, and API contracts |

Both exports are available as zip downloads from the export dropdown in the stories view. See [Exports](exports.md) for the full format reference and usage with coding agents.
```

**Step 2: Verify MkDocs builds**

Run: `uv run mkdocs build --strict 2>&1 | tail -5`
Expected: This will warn about a broken link to `exports.md` (which we create in Task 8). That's expected at this point.

**Step 3: Commit**

```bash
git add docs/how-it-works.md
git commit -m "docs: add spec-driven export section to how-it-works"
```

---

### Task 4: Update getting-started.md with export step

**Files:**
- Modify: `docs/getting-started.md:140-142` (after step 6, before the "Each phase takes a few minutes" note)

**Step 1: Add step 7**

After step 6 (line 140) and before "Each phase takes a few minutes" (line 142), insert:

```markdown

7. **Export your spec.** After stories are generated, use the export dropdown to download your specification as **OpenSpec** or **Spec Kit** zip. These are structured formats that AI coding agents (Claude Code, Cursor, Copilot) can consume directly. Unzip into your project root and point your coding agent at the spec directory.
```

**Step 2: Verify MkDocs builds**

Run: `uv run mkdocs build --strict 2>&1 | tail -5`
Expected: no new errors.

**Step 3: Commit**

```bash
git add docs/getting-started.md
git commit -m "docs: add export step to getting-started"
```

---

### Task 5: Update example-session/index.md

**Files:**
- Modify: `docs/example-session/index.md:85` (after item 9, at end of file)

**Step 1: Add item 10**

After the last line of item 9 (line 85), append:

```markdown

---

### 10. Export as OpenSpec or Spec Kit

After stories are generated, the export dropdown includes **OpenSpec (zip)** and **Spec Kit (zip)** alongside the existing Jira CSV and other formats. Selecting either produces a zip archive containing the full specification, not just stories, but capabilities mapped to requirements, architecture decisions, system traits, and Gherkin scenarios.

The OpenSpec export produces a directory tree like:

```
openspec/
├── config.yaml          # Project metadata and system traits
├── project.md           # Tech stack and architecture decisions
└── specs/
    ├── authentication/
    │   └── spec.md      # SHALL statements + Gherkin scenarios
    ├── core-features/
    │   └── spec.md
    └── cross-cutting/
        └── spec.md      # Non-functional requirements
```

The Spec Kit export produces:

```
.specify/
├── memory/
│   └── constitution.md  # System principles + quality attributes
└── specs/
    ├── 001-authentication/
    │   ├── spec.md      # Requirements + user scenarios
    │   ├── plan.md      # Architecture decisions + build/buy
    │   ├── tasks.md     # Phased implementation tasks
    │   └── data-model.md
    └── 002-core-features/
        ├── spec.md
        ├── plan.md
        ├── tasks.md
        └── contracts/
            └── api.md   # API contracts
```

Unzip either into your project root and point your coding agent at the spec directory.
```

**Step 2: Verify MkDocs builds**

Run: `uv run mkdocs build --strict 2>&1 | tail -5`
Expected: no new errors.

**Step 3: Commit**

```bash
git add docs/example-session/index.md
git commit -m "docs: add OpenSpec/Spec Kit export to example session"
```

---

### Task 6: Update roadmap.md to mark export as complete

**Files:**
- Modify: `docs/roadmap.md:103-145` (Item 5 section)
- Modify: `docs/roadmap.md:170-182` (Sequencing section)

**Step 1: Update Item 5 header and status**

Replace lines 103-106:
```
## 5. Spec-Driven Export (OpenSpec + Spec Kit)

**Priority:** Medium | **Contribution:** Community Welcome
**Depends on:** Item 1 (execution contract)
```

With:
```
## 5. Spec-Driven Export (OpenSpec + Spec Kit) ✅

**Status:** Complete (PRs #37, #38, #39)
**Depends on:** Item 1 (execution contract)
```

**Step 2: Update the sequencing diagram**

Replace lines 172-182:
```
Item 1 (Execution Contract)
  ├── Item 2 (Coding Agent Integration) ── Item 3 (Capability Validation)
  ├── Item 4 (Stitch Integration)
  └── Item 5 (Spec-Driven Export)

Item 6: Deferred until Items 2 + 4 are complete
Item 7: Deferred until Evolution (M2) is operational
```

Items 2, 4, and 5 can proceed in parallel once Item 1 is done. Item 3 depends on Item 2. Items 6 and 7 are deliberately deferred.

With:
```
Item 1 (Execution Contract) ✅
  ├── Item 2 (Coding Agent Integration) ── Item 3 (Capability Validation)
  ├── Item 4 (Stitch Integration)
  └── Item 5 (Spec-Driven Export) ✅

Item 6: Deferred until Items 2 + 4 are complete
Item 7: Deferred until Evolution (M2) is operational
```

Items 2 and 4 can proceed in parallel. Item 3 depends on Item 2. Items 1 and 5 are complete. Items 6 and 7 are deliberately deferred.

**Step 3: Verify MkDocs builds**

Run: `uv run mkdocs build --strict 2>&1 | tail -5`
Expected: no new errors.

**Step 4: Commit**

```bash
git add docs/roadmap.md
git commit -m "docs: mark spec-driven export as complete on roadmap"
```

---

### Task 7: Update architecture/overview.md

**Files:**
- Modify: `docs/architecture/overview.md:174-193` (Project Structure tree)

**Step 1: Add exporters to project structure tree**

In the project structure tree, after the `formatters/` line (line 182), add the exporters line:

```
├── exporters/              # Story-level + project-level (OpenSpec, Spec Kit) exports
```

**Step 2: Verify MkDocs builds**

Run: `uv run mkdocs build --strict 2>&1 | tail -5`
Expected: no new errors.

**Step 3: Commit**

```bash
git add docs/architecture/overview.md
git commit -m "docs: add exporters to architecture project structure"
```

---

### Task 8: Create new exports page (docs/exports.md)

**Files:**
- Create: `docs/exports.md`
- Modify: `mkdocs.yml:97` (nav section, after "Example Session" line)

**Step 1: Create the exports page**

Create `docs/exports.md` with the following content:

```markdown
# Exports

Haytham exports your specification in two formats designed for AI coding agents. Both are available as zip downloads after the STORIES phase completes.

## Why Two Formats

| | OpenSpec | Spec Kit |
|--|---------|----------|
| **Maintainer** | [Fission AI](https://github.com/Fission-AI/OpenSpec) | [GitHub](https://github.com/github/spec-kit) |
| **Strength** | Lightweight, capability-oriented, change management via spec deltas | Richer artifacts (data models, API contracts, constitution), GitHub-native |
| **Best for** | Teams iterating on an existing spec | Greenfield projects going straight to implementation |
| **Output** | `openspec/` directory | `.specify/` directory |

They serve different workflows. Supporting both lets you pick the format your coding agent ecosystem prefers.

---

## What Gets Exported

Both formats receive the full specification, not just stories. Here's what maps where:

| Haytham Artifact | OpenSpec | Spec Kit |
|-----------------|----------|----------|
| Capabilities (CAP-F-*, CAP-NF-*) | `specs/{domain}/spec.md` as SHALL statements | `specs/{feature}/spec.md` as functional requirements |
| Acceptance criteria | Gherkin scenarios in `spec.md` | User scenarios in `spec.md`, success criteria |
| Architecture decisions (DEC-*) | `project.md` | `specs/{feature}/plan.md` |
| Build/buy recommendations | `project.md` | `specs/{feature}/plan.md` |
| System traits | `config.yaml` | `memory/constitution.md` as system principles |
| Non-functional capabilities | `specs/cross-cutting/spec.md` | `memory/constitution.md` as quality attributes |
| Stories (dependency-ordered) | Referenced in spec scenarios | `specs/{feature}/tasks.md` (phased) |
| Data models (Layer 2 stories) | - | `specs/{feature}/data-model.md` |
| API contracts (Layer 3 stories) | - | `specs/{feature}/contracts/api.md` |

---

## Directory Structures

### OpenSpec

```
openspec/
├── config.yaml              # Project name, version, appetite, system traits
├── project.md               # Tech stack overview + architecture decisions
└── specs/
    ├── authentication/
    │   └── spec.md           # SHALL statements + Gherkin scenarios
    ├── core-features/
    │   └── spec.md
    ├── social-features/
    │   └── spec.md
    └── cross-cutting/
        └── spec.md           # Non-functional requirements
```

Each `spec.md` contains:
- A purpose section describing the domain
- Requirements as SHALL statements derived from capabilities
- Gherkin scenarios (Given/When/Then) from acceptance criteria

### Spec Kit

```
.specify/
├── memory/
│   └── constitution.md       # System principles + quality attributes + versioning
└── specs/
    ├── 001-authentication/
    │   ├── spec.md           # User scenarios, functional requirements, success criteria
    │   ├── plan.md           # Architecture decisions + build/buy (filtered to this feature)
    │   ├── tasks.md          # Phased tasks: Setup → Foundational → User Stories
    │   ├── data-model.md     # Entity definitions (from Layer 2 stories)
    │   └── contracts/
    │       └── api.md        # API contracts (from Layer 3 stories)
    ├── 002-core-features/
    │   ├── spec.md
    │   ├── plan.md
    │   └── tasks.md
    └── 003-social-features/
        ├── spec.md
        ├── plan.md
        └── tasks.md
```

`data-model.md` and `contracts/api.md` are only generated when the feature has Layer 2 (entity) or Layer 3 (API) stories, respectively.

---

## Using Exports with Coding Agents

### Setup

1. Run Haytham through all four phases
2. In the stories view, select **OpenSpec (zip)** or **Spec Kit (zip)** from the export dropdown
3. Download and unzip into your project root

### Claude Code

```bash
# Unzip into your project
unzip openspec.zip -d .

# Point Claude Code at the spec
claude "Implement the spec in openspec/specs/authentication/spec.md"
```

### Cursor / Copilot

Place the exported directory in your project root. Both tools automatically detect `.specify/` (Spec Kit) or can be pointed at `openspec/` via their configuration.

### Any Agent

The exports are plain markdown and YAML. Any tool that reads files can consume them. The structured format (SHALL statements, Gherkin scenarios, traced requirements) gives agents concrete, testable criteria rather than vague instructions.

---

## How It Works

The export pipeline is deterministic (no LLM calls). It transforms existing structured data from the session:

1. **Project Assembler** aggregates the full session context into an `ExportableProject` model: capabilities, architecture decisions, build/buy recommendations, system traits, stories, and scope items
2. **Spec Transforms** convert capabilities to SHALL statements, acceptance criteria to Gherkin format, and system traits to constitution articles
3. **Format-specific exporters** (`OpenSpecExporter`, `SpecKitExporter`) render the directory tree as `{path: content}` dictionaries
4. **Zip Utils** package the tree into a downloadable archive

The Execution Contract Schema ([ADR-028](adr/ADR-028-execution-contract-schema.md)) provides the structured data layer that makes this possible.

---

## Links

- [OpenSpec](https://github.com/Fission-AI/OpenSpec) (Fission AI)
- [Spec Kit](https://github.com/github/spec-kit) (GitHub)
- [ADR-028: Execution Contract Schema](adr/ADR-028-execution-contract-schema.md)
- [Spec Export Design](plans/2026-02-27-spec-export-design.md)
```

**Step 2: Add to mkdocs.yml nav**

In `mkdocs.yml`, after `- Example Session: example-session/index.md` (line 97), add:

```yaml
  - Exports: exports.md
```

**Step 3: Verify MkDocs builds**

Run: `uv run mkdocs build --strict 2>&1 | tail -5`
Expected: no errors. The broken link from Task 3 should now resolve.

**Step 4: Commit**

```bash
git add docs/exports.md mkdocs.yml
git commit -m "docs: add dedicated exports reference page"
```

---

### Task 9: Write blog post

**Files:**
- Create: `docs/blog/posts/2026-03-01-idea-to-agent-ready-spec.md`

**Step 1: Create the blog post**

Create `docs/blog/posts/2026-03-01-idea-to-agent-ready-spec.md`. Follow the CLAUDE.md blog writing style: conversational prose, active voice, concrete examples first, short paragraphs, no bullet decomposition of arguments.

The post should follow this structure:

1. **Front matter**: date, authors, categories (Multi-Agent Systems, Architecture), tags (openspec, spec-kit, coding-agents, exports), description for excerpt
2. **Hook**: You can go from a raw startup idea to a validated OpenSpec or Spec Kit export in under 20 minutes
3. **The problem**: Coding agents are garbage-in-garbage-out. Specs solve the format problem, but writing good specs is the hard part
4. **What Haytham does**: 19 agents validate the idea, scope the MVP, make architecture decisions, generate traced stories. Briefly walk through the four phases
5. **Show the output**: Include the directory tree of a real OpenSpec and Spec Kit export. Show what a generated `spec.md` looks like (SHALL statements + Gherkin)
6. **How to try it**: Quick start instructions (clone, uv sync, make run), link to the Exports docs page
7. **What's next**: Phase 5 coding agent integration, where the export feeds directly into implementation

Target length: 800-1200 words. End by pointing forward to the coding agent integration work.

**Step 2: Verify MkDocs builds**

Run: `uv run mkdocs build --strict 2>&1 | tail -5`
Expected: no errors. Blog post appears in the blog index.

**Step 3: Commit**

```bash
git add docs/blog/posts/2026-03-01-idea-to-agent-ready-spec.md
git commit -m "docs: add blog post on OpenSpec/Spec Kit export"
```

---

### Task 10: Final verification and squash commit

**Step 1: Run full MkDocs build**

Run: `uv run mkdocs build --strict 2>&1`
Expected: clean build, no warnings, no broken links.

**Step 2: Run ruff (in case any Python was touched)**

Run: `uv run ruff check haytham/ --fix && uv run ruff format haytham/`
Expected: no changes (this is docs-only, but verify).

**Step 3: Review all changes**

Run: `git diff --stat HEAD~9` (or however many commits from Tasks 1-9)
Expected: only markdown and YAML files changed/created.

**Step 4: Verify the key pages render correctly**

Run: `uv run mkdocs serve` and manually check:
- Landing page has the new export card
- How It Works has the export section
- Exports page renders with tables and tree diagrams
- Blog post appears and reads well
- Roadmap shows Item 5 as complete

---

## Task Dependency Order

Tasks 1-7 (existing page updates) are independent and can be done in any order or in parallel.

Task 8 (exports page) should be done before or alongside Task 3 (how-it-works), since Task 3 links to the exports page.

Task 9 (blog post) is independent of all other tasks.

Task 10 (final verification) must be last.

Recommended execution order for sequential work: 8, 3, 1, 2, 4, 5, 6, 7, 9, 10.
