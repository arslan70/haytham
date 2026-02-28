# Spec Export Design: OpenSpec + Spec Kit + Unified Export Layer

**Date:** 2026-02-27
**Updated:** 2026-02-28 (upstream simplification review)
**Status:** Phase 0 Complete, design reviewed (see [findings](./phase-0-findings.md))
**Issues:** #10 (Spec Kit), #8 (OpenSpec, not yet created)
**Dependencies:** Execution Contract Schema (ADR-028, complete), upstream structured output changes (Phase 1a)

## Problem

Haytham produces rich specification data across four phases (WHY, WHAT, HOW, STORIES), but exports only story-level data. The existing exporters (Linear, Jira, Markdown, CSV) transform `list[ExportableStory]` into flat files for project management tools. They discard capabilities, architecture decisions, system traits, MVP scope, and validation context.

Two emerging spec-driven formats, OpenSpec and Spec Kit, can consume the full session output and feed it directly to coding agents (Claude Code, Copilot, Cursor). Supporting these formats closes the loop from "idea validated" to "spec ready for implementation."

The question is not just "how to add two more exporters" but "how to restructure the export layer so it can serve story-level exports AND project-level exports without duplicating session loading, data aggregation, or transformation logic."

## Format Analysis

### What Haytham Currently Exports

```
list[ExportableStory] -> BaseExporter.export() -> str (single file)
```

Stories only. No project context. Single-file output.

### What OpenSpec Needs

```
openspec/
├── specs/
│   ├── auth-login/
│   │   └── spec.md          # Requirements as SHALL statements + Gherkin scenarios
│   ├── auth-session/
│   │   └── spec.md
│   └── checkout-payment/
│       └── spec.md
├── changes/                  # Empty on initial export (no prior spec exists)
└── config.yaml               # Project metadata
```

**Key characteristics:**
- Directory tree output (not a single file)
- Organized by **capability domain** (grouping related capabilities)
- Requirements use SHALL language: "The system SHALL authenticate users via OAuth 2.0"
- Each requirement has Gherkin scenarios (GIVEN/WHEN/THEN)
- Specs represent current system behavior, not change deltas
- `config.yaml` holds project-level metadata

**Data sources needed:**
- Capabilities (capability-model) -> domain-grouped spec.md files
- Stories (story-generation) -> acceptance criteria become Gherkin scenarios
- System Traits (system-traits) -> config.yaml
- MVP Scope (mvp-scope) -> purpose sections in spec.md files
- Execution Contract -> traceability (which stories implement which capabilities)

### What Spec Kit Needs

```
.specify/
├── memory/
│   └── constitution.md                    # Project principles from system traits
├── specs/
│   ├── 001-user-authentication/
│   │   ├── spec.md                        # Feature overview, user stories, requirements
│   │   ├── plan.md                        # Technical approach, architecture decisions
│   │   ├── data-model.md                  # Entity definitions (from Layer 2 stories)
│   │   ├── tasks.md                       # Implementation tasks (from stories)
│   │   └── contracts/                     # API contracts (from Layer 3 stories)
│   │       └── api.md
│   └── 002-leaderboard-management/
│       ├── spec.md
│       ├── plan.md
│       ├── data-model.md
│       ├── tasks.md
│       └── contracts/
└── templates/                             # Empty or minimal (not needed for export)
```

**Key characteristics:**
- Directory tree output
- Organized by **numbered feature** (scope items from MVP)
- Each feature gets a full spec/plan/tasks/data-model/contracts directory
- Constitution file encodes project principles
- Richer per-feature artifacts than OpenSpec
- Tasks are implementation-ready with file paths and dependencies

**Data sources needed:**
- System Traits -> constitution.md (mapped to "articles" / principles)
- MVP Scope -> feature grouping (scope items become numbered feature directories)
- Capabilities -> spec.md requirements within feature directories
- Architecture Decisions -> plan.md per feature
- Stories -> tasks.md (layer 4 features), data-model.md (layer 2 entities), contracts/ (layer 3 API)
- Build/Buy Analysis -> plan.md rationale sections
- Execution Contract -> traceability + structured acceptance criteria
- Validation Summary -> project context metadata

### Side-by-Side Comparison

| Dimension | User Stories (existing) | OpenSpec | Spec Kit |
|-----------|------------------------|----------|----------|
| Output shape | Single file | Directory tree | Directory tree |
| Input data scope | Stories only | Stories + capabilities + traits | Everything |
| Grouping key | Flat (by layer) | Capability domain | MVP scope item |
| Requirements format | Checkbox acceptance criteria | SHALL + Gherkin | User stories + func/non-func reqs |
| Unique artifacts | None | config.yaml, delta format | constitution.md, plan.md, data-model.md, contracts/ |
| Primary consumer | PM tools (Linear, Jira) | AI coding agents | AI coding agents (GitHub ecosystem) |

## Upstream Prerequisites

The export layer depends on structured data from upstream stages. Today, several stages produce structured output internally (Pydantic models, LLM JSON) but only persist markdown to disk, forcing downstream consumers to reconstruct structure from prose. This section defines upstream changes that eliminate fragile parsing from the export path.

### Principle: JSON Is Canonical, Markdown Is a View

Stage outputs follow a single pattern:

```
LLM → structured output (Pydantic) → save as .json (canonical, machine-readable)
                                    → render to .md (derived view, human review)
```

The `.json` file is the source of truth. The `.md` file is derived from it via `to_markdown()`. Downstream consumers (export assembler, coding agents) read `.json`. Humans (gate reviewers, Streamlit UI) read `.md`. Neither is reconstructed from the other. Drift is impossible by construction: re-running a stage regenerates both from the same LLM call.

### Upstream Change 1: Persist JSON for Stages with `output_model` (Generic)

Modify `stage_executor.py` to auto-save a `.json` file when `StageExecutionConfig.output_model` is set. The executor already calls `output_model.model_validate_json(output).to_markdown()` for disk rendering. Add a parallel write of the validated JSON.

**Stages affected:** `system-traits` (has `SystemTraitsOutput`), `build-buy-analysis` (has `BuildBuyAnalysisOutput`), `story-generation` (has `StoryGenerationHybridOutput`).

**Effort:** ~10 lines in `stage_executor.py`. Non-breaking (markdown output unchanged). Fixes the system-traits round-trip issue (#36) as a side effect.

### Upstream Change 2: Add `structured_output_model` to Architecture Decisions

The architecture-decisions agent currently relies on prompt instructions ("output ONLY JSON") with a multi-fallback extraction chain (`_extract_json_from_response` with backtick fixers, trailing comma handlers, object scanners). JSON parsing failures silently produce raw prose output with status `"completed"`.

**Change:** Define an `ArchitectureDecisionsOutput` Pydantic model. Add `structured_output_model_path` to `AGENT_CONFIGS["architecture_decisions"]`. The Strands SDK enforces valid JSON via tool-calling.

**Additional fixes required:**
- Replace `str(result)` with `extract_text_from_result(result, output_as_json=True)` in `_run_architect_agent()`. The current `str(result)` on a Strands `AgentResult` is a latent bug.
- Delete `_extract_json_from_response()` and its backtick-fixer chain (~70 lines of dead code).
- Update the markdown rendering loop in `run_architecture_decisions()` from `.get("id")` dict access to `.id` attribute access.

**Schema complexity:** Depth 2, one `list[BaseModel]`, no enums. Simpler than `BuildBuyAnalysisOutput` (depth 3, three `list[BaseModel]`, one enum) which already works in production. Token budget is 8000 (generous).

**Feasibility: HIGH.** Schema is within demonstrated Strands SDK limits. The hardest change (`str(result)` fix) is already a bug fix.

### Upstream Change 3: Add Pydantic Validation to Capability Model

The capability-model agent uses `ToolProfile.THINKING` and prompt-based JSON ("output ONLY JSON"). It has no `structured_output_model`. Adding full SDK enforcement is feasible (schema complexity comparable to `BuildBuyAnalysisOutput`, `THINKING` coexists with `structured_output_model`) but requires token budget tuning and `additional_save` handoff changes.

**Phased approach:**
1. **Now:** Define `CapabilityModelOutput` Pydantic model matching the prompt schema. Validate after `extract_json_from_text()`:
   ```python
   raw = extract_json_from_text(output)
   validated = CapabilityModelOutput.model_validate(raw)  # loud failure if malformed
   ```
   This turns silent degradation into explicit failure. The Pydantic model also documents the schema (currently only in the prompt file).

2. **Later:** Upgrade to full `structured_output_model` once architecture-decisions proves the pattern. Requires: bump `TOKENS_LARGE` from 4000 to ~6000 (think tool overhead), update `store_capabilities_in_state` to receive JSON from the `output_as_json=True` extraction path, implement `to_markdown()` on the model.

**Why not full SDK enforcement now:** The `THINKING` tool + `structured_output_model` interaction is supported but untested in this codebase. The token budget is tight. These are solvable but need testing with a real session. Pydantic validation after extraction gives 90% of the benefit (loud failures, documented schema) with minimal risk.

### Upstream Change Summary

| # | Change | Priority | Effort | Eliminates |
|---|--------|----------|--------|------------|
| 1 | Persist `.json` for stages with `output_model` | High | ~10 lines | System traits markdown re-parsing, build-buy prose parsing |
| 2 | `structured_output_model` for architecture-decisions | High | Small | Regex parsing, `_extract_json_from_response()`, `str(result)` bug |
| 3 | Pydantic validation for capability-model | High | Small | Silent degradation on malformed JSON |
| 4 | Full `structured_output_model` for capability-model | Medium | Medium | `extract_json_from_text()` heuristics (deferred) |

**After these changes, the export assembler reads structured JSON from every source. No regex parsing, no markdown re-parsing, no `extract_json_from_text()` heuristics.**

### JSON Output Reliability by Stage

| Stage | Mechanism | Reliability | Notes |
|---|---|---|---|
| system-traits | SDK-enforced (`SystemTraitsOutput`) | HIGH | Existing, works in production |
| build-buy-analysis | SDK-enforced (`BuildBuyAnalysisOutput`) | HIGH | Existing, works in production |
| architecture-decisions | SDK-enforced (after Upstream Change 2) | HIGH | New `ArchitectureDecisionsOutput` model |
| capability-model | Prompt-based + Pydantic validation (Upstream Change 3) | MEDIUM | Loud failure on malformed JSON; full SDK enforcement deferred |
| story-generation | SDK-enforced skeleton + Pydantic assembly | HIGH | `stories.json` is deterministic `model_dump()` |

---

## Proposed Design

### 1. ExportableProject Model

A new Pydantic model that aggregates the full session context. Both OpenSpec and Spec Kit exporters consume this. Story-level exporters continue using `list[ExportableStory]`.

**Location:** `haytham/exporters/project_model.py`

```python
class ExportableCapability(BaseModel):
    id: str                          # CAP-F-001, CAP-NF-001
    name: str
    description: str
    serves_scope_item: str | None    # Links to MVP scope item (None for non-functional)
    priority: str
    is_functional: bool
    acceptance_criteria: list[str]   # For scenario fallback when no stories linked

class ExportableDecision(BaseModel):
    id: str                          # DEC-AUTH-001
    title: str
    description: str
    rationale: str
    serves_capabilities: list[str]   # CAP-F-* IDs (direct linkage)
    implements: str                  # Technology name, e.g., "REST API", "PostgreSQL"
    alternatives_considered: list[str]

class ExportableScopeItem(BaseModel):
    name: str                        # "User Authentication", "Leaderboard"
    description: str
    capabilities: list[str]          # CAP-F-* IDs that serve this item
    stories: list[str]               # Story IDs implementing these capabilities

class ExportableProject(BaseModel):
    # Metadata
    idea_summary: str
    appetite: str
    generated_at: str

    # Phase outputs (all from structured JSON sources, see Upstream Prerequisites)
    system_traits: dict[str, str | list[str]]   # From ExecutionContract
    scope_items: list[ExportableScopeItem]
    capabilities: list[ExportableCapability]
    decisions: list[ExportableDecision]
    non_functional_capabilities: list[ExportableCapability]  # Cross-cutting, no scope item
    build_buy: BuildBuyAnalysisOutput            # Structured model (persisted JSON)

    # Stories (already structured via ExecutionContract)
    stories: list[ContractStory]     # From execution_contract.py
```

**Design notes on the model:**

- **`system_traits` comes from the ExecutionContract.** The contract already contains parsed traits. The project assembler passes them through, not re-parses from markdown.
- **`decisions` come from structured JSON.** After Upstream Change 2, the architecture-decisions agent produces `ArchitectureDecisionsOutput` via SDK-enforced structured output. The persisted `.json` file is read directly. No regex parsing needed. `ExportableDecision` carries the full field set including `serves_capabilities` (direct capability linkage) and `alternatives_considered`.
- **`build_buy` is a structured model.** After Upstream Change 1, the `BuildBuyAnalysisOutput` Pydantic model is persisted as `.json`. The Spec Kit `plan.md` renderer can filter `ServiceRecommendation` entries by `capabilities_served` to show per-feature technology choices, instead of dumping the full raw markdown.
- **No `validation_summary_raw`.** This field was in the original model but had no consumer in any exporter or mapping. Removed.
- **No `mvp_scope_raw`:** Scope item names come from the capability model JSON's `traceability.scope_items_covered` array (structured data, no prose parsing needed). Descriptions come from `serves_scope_item` matches on capabilities. Fallback: if `traceability.scope_items_covered` is missing, derive scope items from the unique set of `serves_scope_item` values across all functional capabilities.
- **`non_functional_capabilities`:** Non-functional capabilities (CAP-NF-*) don't have `serves_scope_item` and are cross-cutting. They're separated from functional capabilities so exporters can place them appropriately (see Non-Functional Capability Placement below).
- **Capability ID normalization:** Real agent output uses `CAP-F-*` / `CAP-NF-*` (confirmed in Phase 0). Test fixtures in conftest.py use bare `CAP-001` / `NFR-001` and should be fixed. The assembler still normalizes bare IDs as a safety net: `CAP-\d+` -> `CAP-F-*` with a logged warning.
- **Orphan stories:** Stories with no `implements` (typically L0 infrastructure, L2 deployment, L4 UI shell) are collected in a synthetic "Infrastructure" scope item. No secondary linkage via `uses` (DEC-*) is attempted for placement. The DEC → capability → scope item chain is too indirect and produces counter-intuitive groupings (e.g., "Project Initialization" appearing under "User Authentication" because it sets up infrastructure that auth uses). The `uses` → DEC linkage is used for decisions-to-scope-items mapping in `plan.md`, not for story placement.
- **Multi-scope stories:** Stories implementing multiple capabilities (e.g., STORY-018 implements all 5 functional caps) appear under each scope item they serve. No deduplication. Each feature directory gets the full story in its tasks.

**Assembly:** `assemble_exportable_project()` reads the saved `execution_contract.json` from disk via `ExecutionContract.model_validate_json()` (not re-assembled), then loads the remaining structured JSON files: capability model, architecture decisions, and build-buy analysis. The contract provides stories, traits, and metadata. The additional JSON files provide capabilities, decisions, and build-buy data.

**Loading the ExecutionContract in the UI:** The Streamlit export view loads the contract from `session/story-generation/execution_contract.json`. A `load_execution_contract()` convenience method should be added to `SessionManager` to centralize file path knowledge.

### 2. Separate Exporter Interfaces

The existing `BaseExporter` takes `list[ExportableStory]` and returns a single string. The new exporters take `ExportableProject` and return a directory tree. These are fundamentally different interfaces. Putting both methods on one base class would mean every exporter has a method that raises `NotImplementedError`, and callers must know the concrete type to pick the right method (a Liskov Substitution violation).

Instead, introduce a separate `ProjectExporter` ABC:

```python
# haytham/exporters/base.py (existing, unchanged)
class BaseExporter(ABC):
    # ... all existing methods unchanged ...
    @abstractmethod
    def export(self, stories: list[ExportableStory]) -> str: ...


# haytham/exporters/project_exporter_base.py (new)
class ProjectExporter(ABC):
    format_name: str
    file_extension: str = "zip"
    mime_type: str = "application/zip"

    @abstractmethod
    def export_tree(self, project: ExportableProject) -> dict[str, str]:
        """Produce a directory tree as {relative_path: content}.

        Returns a dict mapping relative file paths to their string content.
        The caller is responsible for writing to disk or zipping.
        """
        ...

    def get_filename(self) -> str:
        return f"{self.format_name.lower().replace(' ', '-')}.{self.file_extension}"
```

Existing exporters (Linear, Jira, etc.) are untouched. They keep using `BaseExporter.export(stories)`. The registry holds both types (see Registry Update below).

### 3. OpenSpecExporter

**Location:** `haytham/exporters/openspec_exporter.py`

Produces the `openspec/` directory tree:

```python
class OpenSpecExporter(ProjectExporter):
    format_name = "OpenSpec"

    def export_tree(self, project: ExportableProject) -> dict[str, str]:
        tree = {}
        tree["openspec/config.yaml"] = self._render_config(project)

        # Group capabilities by domain (derived from scope item name)
        for scope_item in project.scope_items:
            domain_slug = slugify(scope_item.name)
            caps = [c for c in project.capabilities if c.id in scope_item.capabilities]
            stories = [s for s in project.stories if s.id in scope_item.stories]
            tree[f"openspec/specs/{domain_slug}/spec.md"] = self._render_spec(
                scope_item, caps, stories
            )

        # Non-functional capabilities in a cross-cutting spec
        if project.non_functional_capabilities:
            tree["openspec/specs/cross-cutting/spec.md"] = (
                self._render_non_functional_spec(project.non_functional_capabilities)
            )

        return tree
```

**Additional file: `openspec/project.md`** (tech stack and conventions, discovered in Phase 0):
```python
tree["openspec/project.md"] = self._render_project(project)
```
Rendered from system traits (tech classification) and architecture decisions summary (technology choices). This file is consumed by AI agents as project context.

**Spec.md rendering** (template-based, no LLM):
- Heading: `# {scope_item.name} Specification`
- `## Purpose`: from scope item description
- One `### Requirement: {capability.name}` block per capability (heading hierarchy enforced by `openspec validate`)
  - SHALL statement derived from capability description: `"The system SHALL {description}"`
  - `#### Scenario:` blocks derived from story acceptance criteria (using existing `gherkin_parser.py`)
  - **Scenario fallback:** If a capability has no linked stories, use the capability's own `acceptance_criteria` field to generate scenarios. Every requirement must have at least one scenario (enforced by `openspec validate`).

### 4. SpecKitExporter

**Location:** `haytham/exporters/speckit_exporter.py`

Produces the `.specify/` directory tree:

```python
class SpecKitExporter(ProjectExporter):
    format_name = "Spec Kit"

    def export_tree(self, project: ExportableProject) -> dict[str, str]:
        tree = {}
        tree[".specify/memory/constitution.md"] = self._render_constitution(project)

        for i, scope_item in enumerate(project.scope_items, 1):
            prefix = f".specify/specs/{i:03d}-{slugify(scope_item.name)}"
            caps = [c for c in project.capabilities if c.id in scope_item.capabilities]
            stories = [s for s in project.stories if s.id in scope_item.stories]

            tree[f"{prefix}/spec.md"] = self._render_spec(scope_item, caps, stories)
            tree[f"{prefix}/plan.md"] = self._render_plan(scope_item, project)
            tree[f"{prefix}/tasks.md"] = self._render_tasks(stories)

            layer_2 = [s for s in stories if s.layer == 2]
            if layer_2:
                tree[f"{prefix}/data-model.md"] = self._render_data_model(layer_2)

            api_stories = [s for s in stories if s.layer == 3]
            if api_stories:
                tree[f"{prefix}/contracts/api.md"] = self._render_contracts(api_stories)

        return tree
```

**Empty file policy:** Only emit a file if it has content. If a scope item has no layer 2 stories, skip `data-model.md`. If no layer 3 stories, skip `contracts/api.md`. The `spec.md`, `plan.md`, and `tasks.md` files are always emitted (they can be populated from capabilities and decisions even without stories). If a scope item has capabilities but zero stories, `tasks.md` includes a note: "No implementation stories generated for this feature."

**File format details (validated in Phase 0):**

**spec.md** uses Spec Kit's required sections:
```markdown
# Feature Specification: {scope_item.name}

## User Scenarios & Testing

### User Story 1 - {story.title} (Priority: {priority})
{story.summary}
**Acceptance Scenarios**:
1. **Given** {ac.given}, **When** {ac.when}, **Then** {ac.then}

## Requirements

### Functional Requirements
- **FR-001**: System MUST {capability.description}

## Success Criteria

### Measurable Outcomes
- **SC-001**: {derived from capability acceptance_criteria}
```

**tasks.md** uses Spec Kit's strict task format:
```markdown
# Implementation Tasks: {scope_item.name}

## Phase 1: Setup
- [ ] T001 {story.title} - {summary}

## Phase 2: Foundational
- [ ] T002 {story.title} - {summary}

## Phase 3+: User Stories
- [ ] T003 [US1] {story.title} - {summary}
```
Task IDs are sequential (T001, T002...). Layer 0-1 stories -> Setup, Layer 2 -> Foundational, Layer 3-4 -> User Stories grouped by scope item. `[P]` marker added for parallelizable tasks (no `depends_on`). `[USn]` marker links tasks to user stories from spec.md.

**constitution.md** includes versioning footer:
```markdown
**Version**: 1.0 | **Ratified**: {generated_at} | **Last Amended**: {generated_at}
```

**Skipped for v1:** `research.md`, `quickstart.md`, `checklists/requirements.md` (these are agent-generated artifacts from `/speckit.plan` and `/speckit.specify`, not spec content).

### 5. Shared Transformation Logic

Both exporters need similar transformations. These go in a shared module.

**Location:** `haytham/exporters/spec_transforms.py`

```python
def capability_to_shall_statement(cap: ExportableCapability) -> str:
    """Convert capability description to SHALL requirement."""

def stories_to_gherkin(stories: list[ContractStory]) -> list[dict]:
    """Extract Gherkin scenarios from story acceptance criteria.
    Reuses gherkin_parser.py from the contracts module."""

def traits_to_constitution_articles(traits: dict) -> str:
    """Map system traits to constitution-style principles."""

def slugify(name: str) -> str:
    """Convert 'User Authentication' to 'user-authentication'.

    Implementation: re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')
    No external dependency (python-slugify is not needed for this).
    Collision handling: if two scope items slugify to the same string,
    append a numeric suffix (-2, -3). The assembler detects this and warns.
    Non-ASCII characters are stripped (MVP scope items are English).
    """

def group_stories_by_layer(stories: list[ContractStory]) -> dict[int, list[ContractStory]]:
    """Separate stories into layer buckets for data-model vs API vs feature rendering."""
```

### 6. UI Integration

Add OpenSpec and Spec Kit to the export format dropdown in `frontend_streamlit/views/stories.py`. Since these are directory trees, the download produces a zip file.

```python
# New options in the selectbox
options=["Linear (CSV)", "Jira (CSV)", "Markdown", "Generic CSV", "JSON",
         "OpenSpec (Directory)", "Spec Kit (Directory)"]

# For tree exporters:
elif export_format == "OpenSpec (Directory)":
    project = load_exportable_project(session_manager, execution_contract)
    exporter = OpenSpecExporter()
    tree = exporter.export_tree(project)
    zip_bytes = tree_to_zip(tree)
    st.download_button("Download OpenSpec (.zip)", zip_bytes, "openspec.zip", "application/zip")
```

A small `tree_to_zip(tree: dict[str, str]) -> bytes` utility converts the path-to-content dict into a zip archive. This lives in the exporters package as a shared utility.

### 7. Registry Update

Two registries, one per interface:

```python
# haytham/exporters/__init__.py

# Story-level exporters (single-file output)
STORY_EXPORTERS: dict[str, type[BaseExporter]] = {
    "linear": LinearExporter,
    "jira": JiraExporter,
    "markdown": MarkdownExporter,
    "csv": CSVExporter,
}

# Project-level exporters (directory tree output)
PROJECT_EXPORTERS: dict[str, type[ProjectExporter]] = {
    "openspec": OpenSpecExporter,
    "speckit": SpecKitExporter,
}
```

The UI dispatches based on which registry the selected format belongs to. `get_exporter()` can remain as a convenience that searches both registries and returns a union type, or the UI can use the registries directly.

## Data Flow Summary

```
  Session Directory (structured JSON files, canonical sources)
  ┌────────────────────────────────────────────────────────────┐
  │ execution_contract.json  (stories, traits, metadata)       │
  │ capability-model/*.json  (capabilities, scope items)       │
  │ architecture-decisions/*.json  (decisions)                 │
  │ build-buy-analysis/*.json  (service recommendations)       │
  └──────────────────────────┬─────────────────────────────────┘
                             │
              ┌──────────────┴──────────────────┐
              │                                 │
    ┌─────────▼──────────┐          ┌───────────▼──────────┐
    │  load_stories_*()  │          │ assemble_exportable_  │
    │  (existing)        │          │ project()             │
    └─────────┬──────────┘          │ reads .json files     │
              │                     │ no parsing/regex      │
    list[ExportableStory]           └───────────┬──────────┘
              │                                 │
              │                       ExportableProject
              │                                 │
   ┌──────────┼──────────┐         ┌────────────┼──────────┐
   │          │          │         │                       │
 Linear    Jira     Markdown    OpenSpec              Spec Kit
 (.export)                     (.export_tree)       (.export_tree)
   │          │          │         │                       │
  str        str        str   dict[str,str]         dict[str,str]
   |          |          |         │                       │
 STORY_EXPORTERS registry     tree_to_zip()         tree_to_zip()
                                   │                       │
                              PROJECT_EXPORTERS registry
```

## Open Questions and Risks

### 1. Scope Item Parsing (DE-RISKED in Phase 0)

~~HIGH RISK~~ **RESOLVED.** Phase 0 discovered that the capability model JSON contains `traceability.scope_items_covered`, a structured array of scope item names that exactly match `serves_scope_item` values on capabilities. No MVP scope prose parsing needed.

**Validated algorithm:**
1. Load capability model JSON from session
2. Read `traceability.scope_items_covered` array for scope item names
3. Group functional capabilities by `serves_scope_item` (exact match, confirmed in Phase 0)
4. For each scope item, find stories via `ContractStory.implements` matching the scope item's capability IDs

**Fallback (if `traceability` field missing):** Derive scope items from unique `serves_scope_item` values across all functional capabilities.

**Phase 0 evidence:** 100% of functional capabilities have `serves_scope_item`. Values are exact text matches to scope item names. All 5 scope items produce 2-4 stories each with no empty groups.

### 2. Story-to-Capability Linkage Quality (DE-RISKED in Phase 0)

~~HIGH RISK~~ **RESOLVED.** Phase 0 validated strong linkage: 72% of stories have `implements`, and 100% of capabilities are covered by at least one story.

**Remaining consideration:** 7 orphan stories (no `implements`) are infrastructure/setup (L0 project init, L2 deployment, L4 UI shell). These go into a synthetic "Infrastructure" scope item. No secondary linkage via `uses` (DEC-*) is attempted for story placement (the chain is too indirect, see design notes on orphan stories).

**Multi-scope stories:** STORY-018 implements all 5 functional capabilities. It appears under each scope item. No deduplication.

### 3. Architecture Decisions Parsing (ELIMINATED by Upstream Change 2)

~~MEDIUM RISK~~ **ELIMINATED.** Phase 0 confirmed the markdown format is regex-parseable. But Upstream Change 2 makes parsing unnecessary: the architecture-decisions agent will produce `ArchitectureDecisionsOutput` via SDK-enforced structured output. The persisted `.json` file gives the assembler `list[ExportableDecision]` directly via `model_validate_json()`. No regex, no fallbacks.

- **Direct capability linkage:** Each decision has `serves_capabilities: list[str]` (e.g., `["CAP-F-003", "CAP-F-005"]`). This provides a direct path to scope items (decision -> capabilities -> scope items).
- **Fallback (if Upstream Change 2 is not yet deployed):** Regex `## \d+\. (DEC-[A-Z]+-\d+): (.+)` on the markdown output. Phase 0 validated this format. If no DEC headers are parseable, include all content as a single `DEC-UNSTRUCTURED` decision.

### 4. SHALL Statement Quality (DE-RISKED in Phase 0)

~~MEDIUM RISK~~ **RESOLVED.** Phase 0 confirmed all capability descriptions are action-oriented ("Facilitate real-time video/audio sessions...", "Allow only existing patients to join...", "Enable manual entry of good wishes..."). The simple template `"The system SHALL {description}"` reads naturally.

Non-functional capabilities use the `requirement` field instead of `description` for SHALL statements (e.g., "The system SHALL ensure all video/audio streams and good wishes data are encrypted in transit and at rest").

### 5. OpenSpec Format Fidelity (LOW RISK after Phase 0)

~~MEDIUM RISK~~ **Reduced.** Phase 0 documented the exact validation rules enforced by `openspec validate`:
- Every requirement must contain SHALL or MUST keyword (our template does this)
- Every requirement must have at least one `#### Scenario:` block (need fallback for capabilities without stories)
- Heading hierarchy must be exact: `##` sections, `###` requirements, `####` scenarios
- Files must be named `spec.md` (hardcoded in validator)

**Remaining risk:** Scenario coverage. If a capability has no linked stories, the capability's own `acceptance_criteria` field serves as fallback for generating scenarios.

### 6. Spec Kit Format Fidelity (LOW RISK after Phase 0)

~~MEDIUM RISK~~ **Reduced.** Phase 0 documented the actual template structures from the `github/spec-kit` repository. No machine validator exists (validation is agent-level), so our output needs only structural compatibility with `/speckit.implement` consumption.

**Key format corrections identified:** spec.md uses FR-NNN requirement IDs, tasks.md uses strict T001 task format with phase grouping, constitution.md needs versioning footer. These are incorporated into the exporter sections above.

### 7. Capability ID Format Inconsistency (MEDIUM RISK)

The capability model agent prompt specifies `CAP-F-001` and `CAP-NF-001` (with F/NF prefix), but test fixtures in `conftest.py` use bare `CAP-001`. The ExecutionContract assembler splits on `CAP-F-*` / `CAP-NF-*` prefixes. If the agent sometimes outputs `CAP-001` without the prefix, linkage through `ContractStory.implements` breaks silently.

- **Risk:** Stories referencing `CAP-F-001` won't match a capability with id `CAP-001`, so the story won't appear under any scope item.
- **Mitigation:** The `assemble_exportable_project()` function normalizes IDs: bare `CAP-\d+` is treated as `CAP-F-*` with a logged warning. Long-term, fix the test fixtures to use the correct prefix format and add a quality check to the capability model agent tests.

### 8. ExportableProject Assembly Complexity (LOW RISK, reduced by upstream changes)

~~LOW RISK~~ **REDUCED FURTHER.** With the upstream prerequisites in place, `assemble_exportable_project()` reads 4 structured JSON files with Pydantic `model_validate_json()`. No markdown parsing, no regex, no `extract_json_from_text()` heuristics.

- **Sources:** `execution_contract.json` (stories, traits, metadata), capability model `.json` (capabilities, scope items), architecture decisions `.json` (decisions), build-buy `.json` (service recommendations).
- **Duplication risk eliminated:** The contract assembler and the project assembler share no parsing logic. The contract assembler produces `execution_contract.json` during the pipeline. The project assembler reads it at export time.

### 9. Zip Download UX (LOW RISK)

Streamlit's `st.download_button` works with bytes. Producing a zip in-memory is straightforward (`io.BytesIO` + `zipfile`). The risk is minor: users might expect to browse the directory structure before downloading.

- **Mitigation:** Show a tree preview (list of files and sizes) above the download button using `st.code()`. Edge cases: `tree_to_zip()` should handle empty dicts (return an empty zip, not crash) and all values are `str` (no binary content in v1).

### 10. Capability Model JSON Reliability (MEDIUM RISK, mitigated by Upstream Change 3)

The capability-model agent uses prompt-based JSON output with no SDK enforcement. If the LLM produces malformed JSON, `store_capabilities_in_state` silently skips (no error, no capabilities stored). This is an existing pipeline problem, not new to the export design.

- **Current state:** `extract_json_from_text()` uses a 3-strategy heuristic chain (direct `json.loads`, regex code-block extraction, character-scan for `{...}`). Failures are silent.
- **After Upstream Change 3:** Pydantic validation after extraction turns silent degradation into explicit failure. The `CapabilityModelOutput` model also documents the schema (currently only in the prompt file).
- **Remaining risk:** The agent can still produce malformed JSON. The mitigation makes failures loud, not impossible. Full elimination requires Upstream Change 4 (`structured_output_model`), deferred until architecture-decisions proves the pattern.

### 11. Layer Numbering in Spec Kit tasks.md (LOW RISK)

The Spec Kit exporter groups stories by phase: `L0-1 -> Setup, L2 -> Foundational, L3-4 -> User Stories`. This uses `ContractStory.layer` which ranges 0-5 (correct). Note: `ExportableStory.LAYER_NAMES` in `haytham/exporters/models.py` assumes layers 1-4 (a separate, older mapping). The Spec Kit exporter must use `ContractStory.layer`, not `ExportableStory` layer constants.

## Non-Functional Capability Placement

Non-functional capabilities (CAP-NF-*) are cross-cutting. They don't have `serves_scope_item` and can't be grouped under a single feature. Each format handles them differently:

**OpenSpec:** A dedicated `openspec/specs/cross-cutting/spec.md` containing all non-functional requirements as SHALL statements. This keeps the per-domain specs focused on functional requirements while making non-functional requirements discoverable.

**Spec Kit:** Non-functional requirements are included in `.specify/memory/constitution.md` alongside system traits. They're a natural fit here because constitution principles and non-functional requirements both describe system-wide constraints. Each non-functional capability becomes a numbered principle article.

## What We're NOT Building

- **LLM-enhanced transformations:** All rendering is template-based. No LLM calls in the export path. We may revisit this later if template quality is insufficient, but starting deterministic is correct.
- **OpenSpec change/delta workflow:** We export the initial spec state only. The delta/proposal workflow is an OpenSpec feature for ongoing spec evolution, not initial export.
- **Spec Kit CLI integration:** We produce the directory structure. We don't run `specify` commands or generate agent-specific config files (`.claude/commands/`, etc.).
- **Round-trip import:** Exporting is one-way. We don't import OpenSpec or Spec Kit back into Haytham.
- **OpenSpec config.yaml schema validation:** We produce a minimal config.yaml. Full schema compliance is a stretch goal.

## Implementation Sequence

This is the suggested order for implementation, with natural review points.

### Phase 0: Data Validation Spike (COMPLETE)

**Status:** Done. See [Phase 0 Findings](./phase-0-findings.md).

**Key outcomes:** Scope item parsing de-risked (use `traceability.scope_items_covered` instead of MVP scope prose). Story linkage strong (72% with `implements`, 100% capability coverage). Architecture decisions regex-parseable with direct capability linkage. SHALL template works. Both target formats documented with exact validation rules and template structures.

### Phase 1a: Upstream Prerequisites (parallel with Phase 1b)

These changes are independent of the export layer and can be developed/reviewed separately.

1. **Generic JSON persistence:** Modify `stage_executor.py` to auto-save `.json` when `output_model` is set (~10 lines). Verify system-traits, build-buy, and story-generation stages produce valid `.json` files alongside `.md`.
2. **Architecture decisions structured output:** Define `ArchitectureDecisionsOutput` Pydantic model. Add `structured_output_model_path` to `AGENT_CONFIGS`. Fix `str(result)` bug in `_run_architect_agent()`. Delete `_extract_json_from_response()`. Update markdown rendering to use Pydantic attribute access. Add `output_model` to `StageExecutionConfig` for `.json` persistence.
3. **Capability model validation:** Define `CapabilityModelOutput` Pydantic model. Add validation after `extract_json_from_text()` in `store_capabilities_in_state`. Persist validated JSON to disk via `additional_save`.
4. **Add `load_execution_contract()`** convenience method to `SessionManager`.
5. Unit tests for each upstream change. Run a full pipeline with the Good Wishes Exchange App idea to validate JSON files are correct.

### Phase 1b: Foundation (ExportableProject + assembly)
1. Create `haytham/exporters/project_model.py` with `ExportableProject` and sub-models
2. Create `haytham/exporters/project_exporter_base.py` with `ProjectExporter` ABC
3. Create `haytham/exporters/project_assembler.py` with `assemble_exportable_project()` (reads `.json` files, no parsing)
4. Add shared transforms in `haytham/exporters/spec_transforms.py`
5. Unit tests for assembly and transforms using synthetic fixtures
6. **Validate against real data:** Run `assemble_exportable_project()` against session data. Verify scope item grouping, capability linkage, and decision loading work from persisted JSON files.

### Phase 2: OpenSpec Exporter
1. Create `haytham/exporters/openspec_exporter.py`
2. Template rendering for config.yaml, project.md, spec.md, and cross-cutting/spec.md files
3. Ensure heading hierarchy compliance (`##`/`###`/`####`), SHALL keywords, scenario blocks
4. Unit tests with synthetic project data
5. Integration test: validate output against `openspec validate`

### Phase 3: Spec Kit Exporter
1. Create `haytham/exporters/speckit_exporter.py`
2. Template rendering for constitution.md (with versioning footer), spec.md (FR-NNN format), plan.md, tasks.md (T001 task IDs, phase grouping), data-model.md, contracts/
3. Unit tests with synthetic project data
4. Integration test: verify output structure matches `specify init` conventions

### Phase 4: UI Integration + Zip
1. Create `haytham/exporters/zip_utils.py` with `tree_to_zip()`
2. Update `haytham/exporters/__init__.py` with `STORY_EXPORTERS` and `PROJECT_EXPORTERS` registries
3. Add OpenSpec and Spec Kit options to the Streamlit export UI
4. Wire up `assemble_exportable_project()` in the UI (needs session_manager access)
5. Add tree preview before download
6. End-to-end test with gym leaderboard session data through the full UI flow

## File Inventory

### New Files (Upstream Prerequisites)
| File | Purpose |
|------|---------|
| `haytham/agents/worker_architecture_decisions/architecture_decisions_models.py` | `ArchitectureDecisionsOutput` Pydantic model |
| `haytham/agents/worker_capability_model/capability_model_models.py` | `CapabilityModelOutput` Pydantic model (validation + schema docs) |

### New Files (Export Layer)
| File | Purpose |
|------|---------|
| `haytham/exporters/project_model.py` | ExportableProject Pydantic model and sub-models |
| `haytham/exporters/project_exporter_base.py` | ProjectExporter ABC (separate from BaseExporter) |
| `haytham/exporters/project_assembler.py` | JSON file reading + ExportableProject composition (no parsing) |
| `haytham/exporters/spec_transforms.py` | Shared template transforms (SHALL, Gherkin, slugify, etc.) |
| `haytham/exporters/openspec_exporter.py` | OpenSpec directory tree exporter |
| `haytham/exporters/speckit_exporter.py` | Spec Kit directory tree exporter |
| `haytham/exporters/zip_utils.py` | tree_to_zip() utility |
| `tests/test_project_model.py` | ExportableProject tests |
| `tests/test_project_assembler.py` | Assembly + scope item grouping tests |
| `tests/test_openspec_exporter.py` | OpenSpec exporter tests |
| `tests/test_speckit_exporter.py` | Spec Kit exporter tests |
| `tests/test_spec_transforms.py` | Shared transform tests |

### Modified Files (Upstream Prerequisites)
| File | Change |
|------|--------|
| `haytham/workflow/stage_executor.py` | Auto-save `.json` when `output_model` is set |
| `haytham/workflow/stages/technical_design.py` | Use `ArchitectureDecisionsOutput` structured output, fix `str(result)` bug, delete `_extract_json_from_response()` |
| `haytham/workflow/stages/mvp_specification.py` | Add Pydantic validation to `store_capabilities_in_state`, persist validated JSON |
| `haytham/config.py` | Add `structured_output_model_path` to `architecture_decisions` agent config |
| `haytham/session/session_manager.py` | Add `load_execution_contract()` convenience method |

### Modified Files (Export Layer)
| File | Change |
|------|--------|
| `haytham/exporters/__init__.py` | Split into STORY_EXPORTERS and PROJECT_EXPORTERS registries |
| `frontend_streamlit/views/stories.py` | Add OpenSpec/Spec Kit to format selector, zip download logic |

## Appendix A: Haytham Data -> OpenSpec Mapping (Detailed)

```
openspec/config.yaml
  <- system_traits (project classification)
  <- idea_summary (from metadata)

openspec/project.md
  <- system_traits -> tech stack classification
  <- architecture_decisions -> technology choices summary (DEC-* implements fields)

openspec/specs/{domain-slug}/spec.md
  <- scope_item.name -> # heading
  <- scope_item.description -> ## Purpose section
  <- capabilities[serves_scope_item == scope_item] -> ### Requirement: blocks
     <- capability.description -> "The system SHALL {description}"
     <- stories[implements contains capability.id] -> #### Scenario: blocks
        <- acceptance_criteria -> GIVEN/WHEN/THEN (via gherkin_parser)
     <- FALLBACK: capability.acceptance_criteria -> #### Scenario: blocks (if no stories)

openspec/specs/cross-cutting/spec.md
  <- non_functional_capabilities -> ### Requirement: blocks
     <- capability.requirement -> "The system SHALL {requirement}"
```

## Appendix B: Haytham Data -> Spec Kit Mapping (Detailed)

```
.specify/memory/constitution.md
  <- system_traits -> mapped to principle articles
     interface_type -> "Interface Principle"
     authentication_model -> "Security Principle"
     deployment_target -> "Infrastructure Principle"
     data_persistence -> "Data Principle"
  <- non_functional_capabilities -> additional principle articles
     CAP-NF-* -> numbered principles (system-wide constraints)
  <- footer: "Version: 1.0 | Ratified: {generated_at} | Last Amended: {generated_at}"

.specify/specs/{NNN}-{feature-slug}/spec.md
  <- scope_item.name -> # Feature Specification heading
  <- ## User Scenarios & Testing
     <- stories[layer == 3-4, implements these caps] -> ### User Story N blocks
        <- acceptance_criteria -> Given/When/Then scenarios
  <- ## Requirements
     <- capabilities -> - **FR-NNN**: System MUST {description}
  <- ## Success Criteria
     <- capability.acceptance_criteria -> - **SC-NNN**: measurable criteria

.specify/specs/{NNN}-{feature-slug}/plan.md
  <- architecture_decisions (filtered via decision.serves_capabilities) -> Tech decisions
  <- build_buy.recommended_stack (filtered via service.capabilities_served) -> Per-feature tech choices

.specify/specs/{NNN}-{feature-slug}/tasks.md
  <- stories (all layers for this scope item) -> Strict task format
     <- - [ ] T001 [P] [USn] {story.title} - {summary}
     <- Grouped by phase: Setup (L0-1), Foundational (L2), User Stories (L3-4)
     <- [P] marker for parallelizable (no depends_on)

.specify/specs/{NNN}-{feature-slug}/data-model.md
  <- stories[layer == 2] -> Entity definitions extracted from story content

.specify/specs/{NNN}-{feature-slug}/contracts/api.md
  <- stories[layer == 3] -> API endpoint definitions extracted from story content
```

## Appendix C: Pre-Implementation Research Tasks

**All completed in Phase 0.** See [Phase 0 Findings](./phase-0-findings.md) for full results.

## Appendix D: Review History

**2026-02-27 (initial review):** Nine recommendations incorporated:

1. **Split exporter interfaces** (High): Replaced single `BaseExporter` with `BaseExporter` (story) + `ProjectExporter` (tree) to avoid Liskov Substitution violation. Two registries: `STORY_EXPORTERS`, `PROJECT_EXPORTERS`.
2. **Concrete scope item parsing algorithm** (High): Added parsing strategy (IN SCOPE bullets, exact/fuzzy matching, fallback to deriving from `serves_scope_item` values).
3. **Phase 0 data validation spike** (High): Added Phase 0 to validate scope item parsing, capability linkage, and ID format against real data before writing production code. Phase 1 also ends with real-data validation.
4. **Clarify structured vs raw fields** (Medium): Removed `architecture_raw` and `mvp_scope_raw` from `ExportableProject`. Decisions are parsed into `list[ExportableDecision]` during assembly. Scope items are parsed during assembly.
5. **Non-functional capability placement** (Medium): Added `non_functional_capabilities` field, cross-cutting spec for OpenSpec, constitution integration for Spec Kit.
6. **Validate early** (Medium): Phase 1 now ends with real-data validation instead of deferring to Phase 5.
7. **Capability ID normalization** (Medium): Added Risk #7 and normalization strategy in model design notes.
8. **Empty feature directory behavior** (Low): Added empty file policy to SpecKitExporter section.
9. **slugify() specification** (Low): Added implementation details, collision handling, non-ASCII behavior.

**2026-02-27 (Phase 0 findings):** Plan updated with validated data:

1. **Scope item source changed:** `traceability.scope_items_covered` from capability model replaces MVP scope prose parsing. De-risks the #1 concern entirely.
2. **Decision linkage improved:** `Serves Capabilities` field on decisions provides direct capability linkage, replacing indirect `story.uses` path.
3. **Orphan story placement:** 7 stories without `implements` go to synthetic "Infrastructure" scope item. Secondary DEC linkage considered but rejected (see 2026-02-28 review, item 8).
4. **Multi-scope story policy:** Stories implementing multiple capabilities appear under each scope item (no dedup).
5. **OpenSpec: added project.md** to exporter output (tech stack + conventions).
6. **OpenSpec: scenario fallback** from capability `acceptance_criteria` when no stories linked.
7. **Spec Kit: corrected file formats.** spec.md uses FR-NNN IDs and User Story blocks. tasks.md uses T001 IDs with phase grouping. constitution.md gets versioning footer.
8. **Risks 1-4 de-risked.** Scope item parsing, story linkage, architecture decisions, and SHALL quality all validated against real session data. Risks 5-6 reduced from MEDIUM to LOW.
9. **Phase 0 marked complete.** Status updated, findings report written.

**2026-02-28 (upstream simplification review):** Thirteen changes from design review and upstream feasibility analysis:

1. **Added Upstream Prerequisites section** (High): Established "JSON is canonical, markdown is a view" principle. Three upstream changes eliminate all fragile parsing from the export path: generic JSON persistence for stages with `output_model`, `structured_output_model` for architecture-decisions, Pydantic validation for capability-model.
2. **Architecture decisions: structured output** (High): `ArchitectureDecisionsOutput` Pydantic model with SDK-enforced tool-calling. Eliminates `_extract_json_from_response()` (~70 lines), fixes latent `str(result)` bug in `_run_architect_agent()`. Schema feasibility confirmed (depth 2, simpler than `BuildBuyAnalysisOutput` which works in production).
3. **Capability model: phased approach** (High): Define `CapabilityModelOutput` Pydantic model for validation now; defer full `structured_output_model` until architecture-decisions proves the pattern. Turns silent degradation into explicit failure. Full SDK enforcement feasible (schema comparable to `BuildBuyAnalysisOutput`, `THINKING` tool coexists with `structured_output_model`) but needs token budget tuning (4000 -> ~6000) and `additional_save` handoff changes.
4. **Removed `validation_summary_raw`** (Medium): No consumer in any exporter or mapping. Dead field.
5. **`build_buy` changed from raw markdown to structured model** (Medium): `BuildBuyAnalysisOutput` persisted as `.json`. Spec Kit `plan.md` renderer can filter `ServiceRecommendation` by `capabilities_served` for per-feature tech choices instead of dumping full markdown.
6. **`system_traits` sourced from ExecutionContract** (Low): Avoids re-parsing markdown. Contract already contains parsed traits.
7. **`ExportableDecision` enriched** (Medium): Now carries `description`, `serves_capabilities`, `implements`, `alternatives_considered` (full field set from structured output) instead of just `id`, `title`, `rationale`, `pattern`.
8. **Orphan story policy sharpened** (Medium): Always placed in synthetic "Infrastructure" scope item. No secondary linkage via `uses` -> DEC -> capability -> scope item attempted. The chain is too indirect and produces counter-intuitive groupings.
9. **Assembly reads saved contract from disk** (Medium): `assemble_exportable_project()` reads `execution_contract.json` via `ExecutionContract.model_validate_json()`, not re-assembled. Eliminates duplication with the contract assembler.
10. **UI contract loading specified** (Medium): Added `load_execution_contract()` convenience method to `SessionManager`. Centralizes file path knowledge.
11. **Layer numbering note** (Low): Added Risk #11. Spec Kit tasks.md must use `ContractStory.layer` (0-5 range), not `ExportableStory.LAYER_NAMES` (1-4 range).
12. **Implementation sequence restructured** (Medium): Phase 1 split into Phase 1a (upstream prerequisites, parallelizable) and Phase 1b (export foundation). File inventory updated with upstream files.
13. **JSON output reliability documented** (Medium): Added per-stage reliability table (system-traits HIGH, build-buy HIGH, architecture-decisions HIGH after change, capability-model MEDIUM with validation, story-generation HIGH).
