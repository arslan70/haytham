# AI-Ready Project Scaffold Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a new project-level export that produces a ready-to-code project directory with CLAUDE.md, AGENTS.md, .github/copilot-instructions.md, and .cursorrules, bundled with OpenSpec and Spec Kit exports. Each file follows the official best practices from the respective tool's documentation.

**Architecture:** New `ScaffoldExporter` inherits `ProjectExporter`, same pattern as OpenSpec/Spec Kit. The exporter composes existing exporters (delegates to `OpenSpecExporter` and `SpecKitExporter` for their subtrees) and adds AI coding tool context files. The `ExportableProject` model is extended with optional concept anchor and recommendation fields so the scaffold has richer context. All generation is deterministic (no LLM calls).

**Tech Stack:** Python, Pydantic, existing exporter infrastructure. No new dependencies.

**Issue:** https://github.com/arslan70/haytham/issues/46

## Best Practices Research (baked into this plan)

Sources:
- [Claude Code memory docs](https://code.claude.com/docs/en/memory)
- [AGENTS.md standard](https://agents.md) (adopted by 60,000+ repos, works with 20+ AI tools)
- [Codex AGENTS.md guide](https://developers.openai.com/codex/guides/agents-md/)
- [GitHub Copilot instructions docs](https://docs.github.com/copilot/customizing-copilot/adding-custom-instructions-for-github-copilot)
- [5 tips for Copilot instructions](https://github.blog/ai-and-ml/github-copilot/5-tips-for-writing-better-custom-instructions-for-copilot/)
- [ADR-022: Concept Anchor](docs/adr/ADR-022-concept-anchor.md) (identity risks, non-goals, constraints)

### CLAUDE.md best practices (from Claude Code docs)
- **Under 200 lines.** Longer files consume more context and reduce adherence.
- **Use `@path` imports** to reference spec files instead of inlining everything.
- **Specific, verifiable instructions.** "Use Supabase Auth for authentication" > "use appropriate auth."
- **Markdown headers + bullets.** Claude scans structure the same way readers do.
- **Sections only when content exists.** Omit empty sections entirely.
- **It's context, not enforcement.** More specific = more reliably followed.

### AGENTS.md best practices (from agents.md standard)
- **Universal format** adopted by 60,000+ repos, works across 20+ AI agents (Codex, Cursor, Copilot, Aider, etc.).
- **Standard sections:** Project Overview, Build & Test Commands, Code Style, Testing, Security, PR Instructions.
- **"A README for agents"** -- practical build steps, conventions, commands that would clutter a README.
- **32 KiB limit** by default. Keep it practical and focused.

### copilot-instructions.md best practices (from GitHub docs)
- **Under 2 pages / ~1000 lines.** Quality deteriorates beyond this.
- **Short imperative directives**, not narrative paragraphs.
- **5 required sections:** Project overview, tech stack, coding guidelines, project structure, available resources.
- **Separate from README:** Agent-specific context that would clutter human docs.

### .cursorrules best practices (from Cursor community)
- **Legacy format** (deprecated in favor of `.cursor/rules/`) but still widely supported.
- **Be specific and actionable.** "Use camelCase for variables" > "write clean code."
- **Concise.** Every word counts in the tokens economy.

## Output tree structure

```
project-name/
├── CLAUDE.md                          # Rich context for Claude Code (<200 lines, @imports)
├── AGENTS.md                          # Universal format for 20+ AI tools
├── .cursorrules                       # Concise rules for Cursor (legacy compat)
├── .github/
│   └── copilot-instructions.md        # Imperative directives for GitHub Copilot
├── README.md                          # Human-readable project overview
├── openspec/                          # OpenSpec export (delegated)
│   ├── config.yaml
│   ├── project.md
│   └── specs/...
└── .specify/                          # Spec Kit export (delegated)
    ├── memory/constitution.md
    └── specs/...
```

## Content mapping per file

| Section | CLAUDE.md | AGENTS.md | copilot-instructions.md | .cursorrules |
|---------|-----------|-----------|------------------------|-------------|
| Project one-liner | Yes (top) | Yes (overview) | Yes (overview) | Yes (top) |
| Hard constraints | Yes (bullets) | Folded into overview | Folded into guidelines | Yes (DO NOT) |
| Non-goals | Yes (DO NOT section) | Yes (anti-patterns) | Yes (guidelines) | Yes (DO NOT) |
| Identity risks | Yes (detailed) | No (too verbose) | No | No |
| System traits | Yes (architecture) | Yes (tech stack) | Yes (tech stack) | Yes (constraints) |
| Tech decisions | Yes (with rationale) | Yes (stack list) | Yes (stack list) | Yes (as rules) |
| Capabilities | Yes (table) | No (in spec files) | No (in spec files) | No |
| NF requirements | Yes (bullets) | Yes (quality) | No | No |
| Build commands | No (project not built yet) | Placeholder section | Placeholder section | No |
| Spec references | Yes (`@` imports) | Yes (file pointers) | Yes (file pointers) | Yes (pointers) |
| Generated-by | No | Yes (footer) | No | No |

---

### Task 1: Extend ExportableProject with concept anchor and recommendation fields

The scaffold exporter needs data that existing exporters don't: the concept anchor (non-goals, constraints, identity risks) and the recommendation summary (idea one-liner). Add optional fields to `ExportableProject` and update the assembler to populate them.

**Files:**
- Modify: `haytham/exporters/project_model.py:58-72`
- Modify: `haytham/exporters/project_assembler.py:23-26, 170-236`
- Test: `tests/test_project_assembler.py` (append new test classes to existing file)

**Step 1: Write failing tests for the new assembler fields**

Append the following test classes to the existing `tests/test_project_assembler.py` file (after the last test class, currently at line 395). The file already imports `json`, `Path`, `pytest`, and `assemble_exportable_project`. The new tests use a dedicated minimal helper to avoid coupling to the full `_write_session_files` fixture.

```python
# Append to tests/test_project_assembler.py


def _write_minimal_session(session_dir: Path) -> None:
    """Write only the execution contract (minimum required for assembly)."""
    contract = {
        "metadata": {
            "idea_summary": "A gym leaderboard app",
            "appetite": "Small Batch",
            "generated_at": "2026-03-01T00:00:00Z",
        },
        "system_traits": {"interface": "web"},
        "stories": [],
    }
    story_dir = session_dir / "story-generation"
    story_dir.mkdir(parents=True, exist_ok=True)
    (story_dir / "execution_contract.json").write_text(
        json.dumps(contract), encoding="utf-8"
    )


class TestConceptAnchorLoading:
    def test_concept_anchor_fields_populated(self, tmp_path):
        session_dir = tmp_path / "session"
        _write_minimal_session(session_dir)
        anchor = {
            "anchor": {
                "intent": {
                    "goal": "Build a gym app",
                    "explicit_constraints": ["invite-only", "anonymous"],
                    "non_goals": ["not a social media platform", "not public"],
                },
                "identity": [
                    {
                        "feature": "anonymous leaderboard",
                        "why_distinctive": "LLMs tend to add profiles",
                    }
                ],
            }
        }
        (session_dir / "concept_anchor.json").write_text(
            json.dumps(anchor), encoding="utf-8"
        )

        project = assemble_exportable_project(session_dir)
        assert project.explicit_constraints == ["invite-only", "anonymous"]
        assert project.non_goals == ["not a social media platform", "not public"]
        assert "anonymous leaderboard" in project.identity_risks[0]

    def test_missing_concept_anchor_leaves_defaults(self, tmp_path):
        session_dir = tmp_path / "session"
        _write_minimal_session(session_dir)
        project = assemble_exportable_project(session_dir)
        assert project.explicit_constraints == []
        assert project.non_goals == []
        assert project.identity_risks == []


class TestRecommendationLoading:
    def test_idea_one_liner_populated(self, tmp_path):
        session_dir = tmp_path / "session"
        _write_minimal_session(session_dir)
        rec = {
            "recommendation": "GO",
            "executive_summary": {
                "idea_in_one_line": "A gym leaderboard for CrossFit athletes",
                "strongest_point": "Clear market need",
                "recommendation_summary": "Build it",
                "recommendation_reasoning": "Strong concept",
                "competitive_snapshot": "No direct competitors",
                "closing_remark": "Interview 20 users",
            },
        }
        (session_dir / "recommendation.json").write_text(
            json.dumps(rec), encoding="utf-8"
        )

        project = assemble_exportable_project(session_dir)
        assert project.idea_one_liner == "A gym leaderboard for CrossFit athletes"

    def test_missing_recommendation_leaves_default(self, tmp_path):
        session_dir = tmp_path / "session"
        _write_minimal_session(session_dir)
        project = assemble_exportable_project(session_dir)
        assert project.idea_one_liner == ""
```

Run: `uv run pytest tests/test_project_assembler.py -v`
Expected: FAIL (fields don't exist on ExportableProject)

**Step 2: Add fields to ExportableProject**

In `haytham/exporters/project_model.py`, add after the `stories` field (line 72, last field in the class):

```python
    # Concept anchor (ADR-022) - populated for scaffold export
    idea_one_liner: str = ""
    explicit_constraints: list[str] = Field(default_factory=list)
    non_goals: list[str] = Field(default_factory=list)
    identity_risks: list[str] = Field(default_factory=list)
```

**Step 3: Update assembler to load concept anchor and recommendation**

In `haytham/exporters/project_assembler.py`, add path constants after `_BUILD_BUY_PATH` (line 26):

```python
_CONCEPT_ANCHOR_PATH = Path("concept_anchor.json")
_RECOMMENDATION_PATH = Path("recommendation.json")
```

In `assemble_exportable_project()`, after step 6 ("Extract short project name", ends at line 221) and before step 7 ("Assemble the project", line 223), add:

```python
    # 6b. Load concept anchor (optional, for scaffold export)
    anchor_data = _load_json(session_dir / _CONCEPT_ANCHOR_PATH)
    explicit_constraints: list[str] = []
    non_goals: list[str] = []
    identity_risks: list[str] = []
    if anchor_data is not None:
        anchor = anchor_data.get("anchor", {})
        intent = anchor.get("intent", {})
        explicit_constraints = intent.get("explicit_constraints", [])
        non_goals = intent.get("non_goals", [])
        identity_risks = [
            f"{item['feature']}: {item['why_distinctive']}"
            for item in anchor.get("identity", [])
            if "feature" in item and "why_distinctive" in item
        ]

    # 6c. Load recommendation summary (optional, for scaffold export)
    rec_data = _load_json(session_dir / _RECOMMENDATION_PATH)
    idea_one_liner = ""
    if rec_data is not None:
        exec_summary = rec_data.get("executive_summary", {})
        idea_one_liner = exec_summary.get("idea_in_one_line", "")
```

Then update the `ExportableProject(...)` constructor call (starts at line 224, ends at line 236) to include the new kwargs before the closing paren:

```python
        explicit_constraints=explicit_constraints,
        non_goals=non_goals,
        identity_risks=identity_risks,
        idea_one_liner=idea_one_liner,
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_project_assembler.py -v`
Expected: All PASS

**Step 5: Run existing tests to verify no regressions**

Run: `uv run pytest tests/test_project_assembler.py tests/test_openspec_exporter.py tests/test_speckit_exporter.py -v`
Expected: All PASS (new fields are optional with defaults, existing assembler tests unaffected)

**Step 6: Commit**

```bash
git add haytham/exporters/project_model.py haytham/exporters/project_assembler.py tests/test_project_assembler.py
git commit -m "feat: extend ExportableProject with concept anchor and recommendation fields"
```

---

### Task 2: Create ScaffoldExporter with all context files

The core of the feature. Produces CLAUDE.md, AGENTS.md, .cursorrules, .github/copilot-instructions.md, and README.md. Each file follows its tool's official best practices.

**Files:**
- Create: `haytham/exporters/scaffold_exporter.py`
- Test: `tests/test_scaffold_exporter.py` (create)

**Step 1: Write failing tests**

```python
# tests/test_scaffold_exporter.py
"""Tests for the AI-ready project scaffold exporter."""

from haytham.exporters.project_model import (
    ExportableCapability,
    ExportableDecision,
    ExportableProject,
    ExportableScopeItem,
)
from haytham.exporters.scaffold_exporter import ScaffoldExporter
from haytham.workflow.contracts.execution_contract import (
    AcceptanceCriterion,
    ContractStory,
)


def _make_project(**overrides) -> ExportableProject:
    """Build a realistic ExportableProject for scaffold testing."""
    defaults = {
        "project_name": "GymBoard",
        "idea_summary": "A gym leaderboard app for CrossFit athletes",
        "idea_one_liner": "A community leaderboard for CrossFit gyms",
        "appetite": "Small Batch",
        "generated_at": "2026-03-01T00:00:00Z",
        "system_traits": {
            "interface": "React SPA",
            "authentication": "OAuth2",
            "deployment": "Vercel",
            "data_layer": "Supabase",
        },
        "explicit_constraints": ["invite-only", "anonymous handles"],
        "non_goals": ["not a social media platform", "not open to public"],
        "identity_risks": [
            "anonymous leaderboard: LLMs tend to add user profiles and social features"
        ],
        "scope_items": [
            ExportableScopeItem(
                name="User Authentication",
                capabilities=["CAP-F-001"],
                stories=["STORY-001"],
            ),
        ],
        "capabilities": [
            ExportableCapability(
                id="CAP-F-001",
                name="Login",
                description="Authenticate users via OAuth",
                serves_scope_item="User Authentication",
            ),
        ],
        "decisions": [
            ExportableDecision(
                id="DEC-AUTH-001",
                title="Use Supabase Auth",
                description="Managed auth with social login.",
                rationale="Reduces custom auth code.",
                serves_capabilities=["CAP-F-001"],
                implements="BUY",
            ),
        ],
        "non_functional_capabilities": [
            ExportableCapability(
                id="CAP-NF-001",
                name="Response Time",
                description="API responses under 200ms at p95",
                is_functional=False,
            ),
        ],
        "stories": [
            ContractStory(
                id="STORY-001",
                title="User login flow",
                layer=1,
                summary="Implement OAuth login",
                implements=["CAP-F-001"],
                acceptance_criteria=[
                    AcceptanceCriterion(
                        id="AC-001",
                        scenario="Successful Google login",
                        given="a user with a Google account",
                        when="they click Sign in with Google",
                        then="they are redirected to the dashboard",
                    ),
                ],
            ),
        ],
    }
    defaults.update(overrides)
    return ExportableProject(**defaults)


# ===========================================================================
# Tree structure
# ===========================================================================


class TestTreeStructure:
    def test_tree_has_claude_md(self):
        tree = ScaffoldExporter().export_tree(_make_project())
        assert "CLAUDE.md" in tree

    def test_tree_has_agents_md(self):
        tree = ScaffoldExporter().export_tree(_make_project())
        assert "AGENTS.md" in tree

    def test_tree_has_cursorrules(self):
        tree = ScaffoldExporter().export_tree(_make_project())
        assert ".cursorrules" in tree

    def test_tree_has_copilot_instructions(self):
        tree = ScaffoldExporter().export_tree(_make_project())
        assert ".github/copilot-instructions.md" in tree

    def test_tree_has_readme(self):
        tree = ScaffoldExporter().export_tree(_make_project())
        assert "README.md" in tree

    def test_tree_includes_openspec_subtree(self):
        tree = ScaffoldExporter().export_tree(_make_project())
        assert "openspec/config.yaml" in tree

    def test_tree_includes_speckit_subtree(self):
        tree = ScaffoldExporter().export_tree(_make_project())
        assert ".specify/memory/constitution.md" in tree


# ===========================================================================
# CLAUDE.md content (best practice: <200 lines, @imports, specific rules)
# ===========================================================================


class TestClaudeMdContent:
    def test_contains_project_name(self):
        tree = ScaffoldExporter().export_tree(_make_project())
        assert "# GymBoard" in tree["CLAUDE.md"]

    def test_contains_idea_one_liner(self):
        tree = ScaffoldExporter().export_tree(_make_project())
        assert "A community leaderboard for CrossFit gyms" in tree["CLAUDE.md"]

    def test_contains_constraints_as_verifiable_rules(self):
        """Best practice: instructions should be specific enough to verify."""
        tree = ScaffoldExporter().export_tree(_make_project())
        claude_md = tree["CLAUDE.md"]
        assert "invite-only" in claude_md
        assert "anonymous handles" in claude_md

    def test_contains_non_goals_as_do_not(self):
        """Best practice: explicit DO NOT instructions for non-goals."""
        tree = ScaffoldExporter().export_tree(_make_project())
        claude_md = tree["CLAUDE.md"]
        assert "not a social media platform" in claude_md
        assert "DO NOT" in claude_md

    def test_contains_system_traits(self):
        tree = ScaffoldExporter().export_tree(_make_project())
        claude_md = tree["CLAUDE.md"]
        assert "React SPA" in claude_md
        assert "Supabase" in claude_md

    def test_contains_architecture_decisions_with_rationale(self):
        """Best practice: include rationale so Claude understands why, not just what."""
        tree = ScaffoldExporter().export_tree(_make_project())
        claude_md = tree["CLAUDE.md"]
        assert "Use Supabase Auth" in claude_md
        assert "Reduces custom auth code" in claude_md

    def test_contains_capabilities_table(self):
        tree = ScaffoldExporter().export_tree(_make_project())
        claude_md = tree["CLAUDE.md"]
        assert "CAP-F-001" in claude_md
        assert "Login" in claude_md

    def test_contains_non_functional_requirements(self):
        tree = ScaffoldExporter().export_tree(_make_project())
        assert "200ms" in tree["CLAUDE.md"]

    def test_contains_identity_risks(self):
        """Anti-genericization warnings from concept anchor."""
        tree = ScaffoldExporter().export_tree(_make_project())
        assert "LLMs tend to add user profiles" in tree["CLAUDE.md"]

    def test_uses_at_imports_for_spec_references(self):
        """Best practice: use @path imports to reference spec files."""
        tree = ScaffoldExporter().export_tree(_make_project())
        claude_md = tree["CLAUDE.md"]
        assert "@openspec/project.md" in claude_md

    def test_under_200_lines(self):
        """Best practice: CLAUDE.md should be under 200 lines for best adherence."""
        tree = ScaffoldExporter().export_tree(_make_project())
        line_count = tree["CLAUDE.md"].count("\n")
        assert line_count < 200, f"CLAUDE.md is {line_count} lines, should be under 200"

    def test_empty_non_goals_omits_section(self):
        """Best practice: omit empty sections entirely."""
        tree = ScaffoldExporter().export_tree(_make_project(non_goals=[]))
        assert "What This Project Is NOT" not in tree["CLAUDE.md"]

    def test_empty_constraints_omits_section(self):
        tree = ScaffoldExporter().export_tree(
            _make_project(explicit_constraints=[])
        )
        assert "Hard Constraints" not in tree["CLAUDE.md"]


# ===========================================================================
# AGENTS.md content (universal format, 20+ AI tools)
# ===========================================================================


class TestAgentsMdContent:
    def test_contains_project_overview(self):
        """Required section per agents.md spec."""
        tree = ScaffoldExporter().export_tree(_make_project())
        agents_md = tree["AGENTS.md"]
        assert "GymBoard" in agents_md
        assert "A community leaderboard for CrossFit gyms" in agents_md

    def test_contains_tech_stack(self):
        tree = ScaffoldExporter().export_tree(_make_project())
        assert "Supabase Auth" in tree["AGENTS.md"]

    def test_contains_code_style_section(self):
        """Required section per agents.md spec."""
        tree = ScaffoldExporter().export_tree(_make_project())
        assert "Code Style & Guidelines" in tree["AGENTS.md"]

    def test_contains_non_goals(self):
        tree = ScaffoldExporter().export_tree(_make_project())
        assert "not a social media platform" in tree["AGENTS.md"]

    def test_contains_quality_requirements(self):
        tree = ScaffoldExporter().export_tree(_make_project())
        assert "200ms" in tree["AGENTS.md"]

    def test_contains_spec_references(self):
        tree = ScaffoldExporter().export_tree(_make_project())
        agents_md = tree["AGENTS.md"]
        assert "openspec/" in agents_md
        assert ".specify/" in agents_md

    def test_contains_generated_by_footer(self):
        tree = ScaffoldExporter().export_tree(_make_project())
        assert "Haytham" in tree["AGENTS.md"]


# ===========================================================================
# .github/copilot-instructions.md (imperative, under 2 pages)
# ===========================================================================


class TestCopilotInstructionsContent:
    def test_contains_project_overview(self):
        """Copilot tip #1: start with an elevator pitch."""
        tree = ScaffoldExporter().export_tree(_make_project())
        assert "GymBoard" in tree[".github/copilot-instructions.md"]

    def test_contains_tech_stack(self):
        """Copilot tip #2: list backend frameworks and tools."""
        tree = ScaffoldExporter().export_tree(_make_project())
        assert "Supabase Auth" in tree[".github/copilot-instructions.md"]

    def test_contains_non_goals(self):
        tree = ScaffoldExporter().export_tree(_make_project())
        assert "not a social media platform" in tree[".github/copilot-instructions.md"]

    def test_uses_imperative_directives(self):
        """Best practice: short imperative directives, not narrative."""
        tree = ScaffoldExporter().export_tree(_make_project())
        copilot = tree[".github/copilot-instructions.md"]
        # Should use imperative style ("Use X for Y", "Do not X")
        assert "Do not" in copilot or "Use " in copilot

    def test_contains_project_structure(self):
        """Copilot tip #4: map folder organization."""
        tree = ScaffoldExporter().export_tree(_make_project())
        copilot = tree[".github/copilot-instructions.md"]
        assert "openspec/" in copilot
        assert ".specify/" in copilot


# ===========================================================================
# .cursorrules (concise, actionable rules)
# ===========================================================================


class TestCursorRulesContent:
    def test_contains_project_identity(self):
        tree = ScaffoldExporter().export_tree(_make_project())
        assert "GymBoard" in tree[".cursorrules"]

    def test_contains_tech_stack_rules(self):
        """Best practice: specific, actionable rules."""
        tree = ScaffoldExporter().export_tree(_make_project())
        assert "Supabase Auth" in tree[".cursorrules"]

    def test_contains_non_goals_as_rules(self):
        tree = ScaffoldExporter().export_tree(_make_project())
        assert "not a social media platform" in tree[".cursorrules"]

    def test_concise(self):
        """Best practice: every word counts in the tokens economy."""
        tree = ScaffoldExporter().export_tree(_make_project())
        line_count = tree[".cursorrules"].count("\n")
        assert line_count < 80, f".cursorrules is {line_count} lines, should be concise"


# ===========================================================================
# README.md
# ===========================================================================


class TestReadmeContent:
    def test_contains_project_name(self):
        tree = ScaffoldExporter().export_tree(_make_project())
        assert "GymBoard" in tree["README.md"]

    def test_contains_idea_summary(self):
        tree = ScaffoldExporter().export_tree(_make_project())
        assert "gym leaderboard" in tree["README.md"]

    def test_contains_capabilities_list(self):
        tree = ScaffoldExporter().export_tree(_make_project())
        assert "Login" in tree["README.md"]

    def test_contains_haytham_attribution(self):
        tree = ScaffoldExporter().export_tree(_make_project())
        assert "Haytham" in tree["README.md"]


# ===========================================================================
# Edge cases
# ===========================================================================


class TestEdgeCases:
    def test_minimal_project_no_crash(self):
        """Scaffold export works with minimal data (no anchor, no decisions)."""
        minimal = ExportableProject(idea_summary="A simple app")
        tree = ScaffoldExporter().export_tree(minimal)
        assert "CLAUDE.md" in tree
        assert "AGENTS.md" in tree
        assert ".cursorrules" in tree

    def test_empty_traits_handled(self):
        tree = ScaffoldExporter().export_tree(_make_project(system_traits={}))
        assert "CLAUDE.md" in tree

    def test_all_files_have_content(self):
        """No file should be empty."""
        tree = ScaffoldExporter().export_tree(_make_project())
        for path, content in tree.items():
            assert len(content.strip()) > 0, f"{path} is empty"
```

Run: `uv run pytest tests/test_scaffold_exporter.py -v`
Expected: FAIL (module doesn't exist)

**Step 2: Implement ScaffoldExporter**

```python
# haytham/exporters/scaffold_exporter.py
"""AI-ready project scaffold exporter.

Produces a project directory with context files for AI coding tools,
bundled with OpenSpec and Spec Kit exports.

File format choices follow each tool's official best practices:
- CLAUDE.md: <200 lines, @path imports, specific verifiable rules
  (https://code.claude.com/docs/en/memory)
- AGENTS.md: Universal format for 20+ AI tools, standard sections
  (https://agents.md)
- copilot-instructions.md: Short imperative directives, <2 pages
  (https://docs.github.com/copilot/customizing-copilot/adding-custom-instructions-for-github-copilot)
- .cursorrules: Concise actionable rules (legacy Cursor format)

Tree layout:

    CLAUDE.md
    AGENTS.md
    .cursorrules
    .github/
        copilot-instructions.md
    README.md
    openspec/...              (delegated to OpenSpecExporter)
    .specify/...              (delegated to SpecKitExporter)
"""

from haytham.exporters.openspec_exporter import OpenSpecExporter
from haytham.exporters.project_exporter_base import ProjectExporter
from haytham.exporters.project_model import ExportableProject
from haytham.exporters.speckit_exporter import SpecKitExporter


class ScaffoldExporter(ProjectExporter):
    """Export project data as an AI-ready project scaffold."""

    format_name = "AI Scaffold"

    def export_tree(self, project: ExportableProject) -> dict[str, str]:
        """Produce the scaffold directory tree as {relative_path: content}."""
        tree: dict[str, str] = {}

        # AI coding tool context files
        tree["CLAUDE.md"] = self._render_claude_md(project)
        tree["AGENTS.md"] = self._render_agents_md(project)
        tree[".cursorrules"] = self._render_cursorrules(project)
        tree[".github/copilot-instructions.md"] = self._render_copilot_instructions(
            project
        )
        tree["README.md"] = self._render_readme(project)

        # Delegate to existing exporters for spec subtrees
        tree.update(OpenSpecExporter().export_tree(project))
        tree.update(SpecKitExporter().export_tree(project))

        return tree

    # ------------------------------------------------------------------
    # CLAUDE.md -- rich context, <200 lines, @imports for spec references
    # ------------------------------------------------------------------

    def _render_claude_md(self, project: ExportableProject) -> str:
        """Render CLAUDE.md following Claude Code best practices.

        Best practices applied:
        - Under 200 lines for optimal adherence
        - Use @path imports to reference spec files instead of inlining
        - Specific, verifiable instructions (not vague guidance)
        - Markdown headers + bullets for scannable structure
        - Omit empty sections entirely
        """
        lines: list[str] = []
        name = project.project_name or "Project"

        lines.append(f"# {name}")
        lines.append("")

        one_liner = project.idea_one_liner or project.idea_summary
        if one_liner:
            lines.append(one_liner)
            lines.append("")

        # Hard constraints as verifiable rules
        if project.explicit_constraints:
            lines.append("## Hard Constraints")
            lines.append("")
            for constraint in project.explicit_constraints:
                lines.append(f"- {constraint}")
            lines.append("")

        # Explicit DO NOT list from concept anchor non-goals
        if project.non_goals:
            lines.append("## What This Project Is NOT")
            lines.append("")
            lines.append("DO NOT build or suggest any of the following:")
            lines.append("")
            for non_goal in project.non_goals:
                lines.append(f"- {non_goal}")
            lines.append("")

        # Identity risks (genericization warnings from ADR-022)
        if project.identity_risks:
            lines.append("## Identity Risks")
            lines.append("")
            lines.append(
                "These features are distinctive. Do NOT genericize them:"
            )
            lines.append("")
            for risk in project.identity_risks:
                lines.append(f"- {risk}")
            lines.append("")

        # System architecture from traits
        if project.system_traits:
            lines.append("## System Architecture")
            lines.append("")
            for key, value in project.system_traits.items():
                label = key.replace("_", " ").title()
                lines.append(f"- **{label}:** {value}")
            lines.append("")

        # Tech stack decisions with rationale
        if project.decisions:
            lines.append("## Tech Stack")
            lines.append("")
            for dec in project.decisions:
                rec = f" ({dec.implements})" if dec.implements else ""
                lines.append(f"### {dec.id}: {dec.title}{rec}")
                lines.append("")
                lines.append(dec.description)
                if dec.rationale:
                    lines.append(f"**Rationale:** {dec.rationale}")
                lines.append("")

        # Capabilities as compact table
        if project.capabilities:
            lines.append("## Capabilities")
            lines.append("")
            lines.append("| ID | Name | Scope Item |")
            lines.append("|---|---|---|")
            for cap in project.capabilities:
                scope = cap.serves_scope_item or "-"
                lines.append(f"| {cap.id} | {cap.name} | {scope} |")
            lines.append("")

        # Non-functional requirements
        if project.non_functional_capabilities:
            lines.append("## Non-Functional Requirements")
            lines.append("")
            for cap in project.non_functional_capabilities:
                lines.append(f"- **{cap.name}:** {cap.description}")
            lines.append("")

        # @imports for spec files (Claude Code best practice)
        lines.append("## Detailed Specifications")
        lines.append("")
        lines.append("@openspec/project.md")
        lines.append("")
        lines.append(
            "For full feature specifications, see `openspec/specs/` and `.specify/specs/`."
        )
        lines.append("")

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # AGENTS.md -- universal format for 20+ AI agents
    # ------------------------------------------------------------------

    def _render_agents_md(self, project: ExportableProject) -> str:
        """Render AGENTS.md following the agents.md standard.

        Standard sections: Project Overview, Build & Test, Code Style,
        Testing, Project Structure, Security. Works with Codex, Cursor,
        Copilot, Aider, and 20+ other AI coding tools.
        """
        lines: list[str] = []
        name = project.project_name or "Project"

        # Project Overview (required by agents.md)
        lines.append(f"# {name}")
        lines.append("")
        one_liner = project.idea_one_liner or project.idea_summary
        if one_liner:
            lines.append(one_liner)
            lines.append("")

        if project.non_goals:
            lines.append("**This project is NOT:**")
            for non_goal in project.non_goals:
                lines.append(f"- {non_goal}")
            lines.append("")

        # Tech Stack (agents.md recommended section)
        if project.decisions or project.system_traits:
            lines.append("## Tech Stack")
            lines.append("")
            if project.system_traits:
                for key, value in project.system_traits.items():
                    label = key.replace("_", " ").title()
                    lines.append(f"- **{label}:** {value}")
                lines.append("")
            if project.decisions:
                for dec in project.decisions:
                    lines.append(f"- **{dec.title}:** {dec.description}")
                lines.append("")

        # Build & Test Commands (agents.md recommended section)
        lines.append("## Build & Test Commands")
        lines.append("")
        lines.append(
            "<!-- TODO: Add build and test commands after project setup -->"
        )
        lines.append("")

        # Code Style & Guidelines (agents.md recommended section)
        lines.append("## Code Style & Guidelines")
        lines.append("")
        if project.explicit_constraints:
            for constraint in project.explicit_constraints:
                lines.append(f"- {constraint}")
            lines.append("")

        # Quality Requirements
        if project.non_functional_capabilities:
            lines.append("## Quality Requirements")
            lines.append("")
            for cap in project.non_functional_capabilities:
                lines.append(f"- **{cap.name}:** {cap.description}")
            lines.append("")

        # Project Structure (agents.md recommended section)
        lines.append("## Project Structure")
        lines.append("")
        lines.append("- `openspec/` - Feature specifications with acceptance criteria")
        lines.append("- `openspec/config.yaml` - Project metadata and system traits")
        lines.append("- `openspec/specs/` - Per-domain requirement specs")
        lines.append("- `.specify/` - Implementation tasks organized by domain")
        lines.append("- `.specify/memory/constitution.md` - System principles")
        lines.append("- `.specify/specs/` - Per-feature spec, plan, and tasks")
        lines.append("")

        # Footer
        generated = project.generated_at or "unknown"
        lines.append("---")
        lines.append("")
        lines.append(
            f"Generated by [Haytham](https://github.com/arslan70/haytham) on {generated}"
        )
        lines.append("")

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # .github/copilot-instructions.md -- imperative, <2 pages
    # ------------------------------------------------------------------

    def _render_copilot_instructions(self, project: ExportableProject) -> str:
        """Render copilot-instructions.md following GitHub's 5 tips.

        Tips applied:
        1. Project overview (elevator pitch)
        2. Tech stack (frameworks and tools)
        3. Coding guidelines (constraints, non-goals)
        4. Project structure (folder map)
        5. Available resources (spec file pointers)
        """
        lines: list[str] = []
        name = project.project_name or "Project"

        # Tip 1: Project overview
        lines.append(f"# {name}")
        lines.append("")
        one_liner = project.idea_one_liner or project.idea_summary
        if one_liner:
            lines.append(one_liner)
            lines.append("")

        # Tip 2: Tech stack
        if project.decisions:
            lines.append("## Tech Stack")
            lines.append("")
            for dec in project.decisions:
                target = (
                    ", ".join(dec.serves_capabilities)
                    if dec.serves_capabilities
                    else "this project"
                )
                lines.append(f"- Use {dec.title} for {target}.")
            lines.append("")

        # Tip 3: Coding guidelines
        guidelines: list[str] = []
        if project.explicit_constraints:
            guidelines.extend(project.explicit_constraints)
        if project.non_goals:
            for ng in project.non_goals:
                guidelines.append(f"Do not build: {ng}")
        if project.system_traits:
            for key, value in project.system_traits.items():
                label = key.replace("_", " ")
                guidelines.append(f"Use {value} for {label}")

        if guidelines:
            lines.append("## Guidelines")
            lines.append("")
            for g in guidelines:
                lines.append(f"- {g}")
            lines.append("")

        # Tip 4: Project structure
        lines.append("## Project Structure")
        lines.append("")
        lines.append("- `openspec/` - Feature specifications with acceptance criteria")
        lines.append("- `.specify/` - Implementation tasks organized by domain")
        lines.append("")

        # Tip 5: Available resources
        lines.append("## Resources")
        lines.append("")
        lines.append("- `openspec/project.md` - Architecture decisions and tech stack")
        lines.append("- `openspec/specs/` - Per-domain requirement specifications")
        lines.append("- `.specify/specs/` - Per-feature implementation plans and tasks")
        lines.append("")

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # .cursorrules -- concise actionable rules (legacy Cursor format)
    # ------------------------------------------------------------------

    def _render_cursorrules(self, project: ExportableProject) -> str:
        """Render .cursorrules with concise, actionable rules.

        Best practices: specific over vague, every word counts,
        keep it under 80 lines.
        """
        lines: list[str] = []
        name = project.project_name or "Project"

        lines.append(f"# {name}")
        lines.append("")

        one_liner = project.idea_one_liner or project.idea_summary
        if one_liner:
            lines.append(one_liner)
            lines.append("")

        # Non-goals as DO NOT rules
        if project.non_goals:
            lines.append("## DO NOT")
            lines.append("")
            for non_goal in project.non_goals:
                lines.append(f"- {non_goal}")
            lines.append("")

        # Tech stack as rules
        if project.decisions:
            lines.append("## Tech Stack (do not suggest alternatives)")
            lines.append("")
            for dec in project.decisions:
                lines.append(f"- **{dec.title}**: {dec.description}")
            lines.append("")

        # System constraints
        if project.system_traits:
            lines.append("## System Constraints")
            lines.append("")
            for key, value in project.system_traits.items():
                label = key.replace("_", " ").title()
                lines.append(f"- {label}: {value}")
            lines.append("")

        # Reference
        lines.append("## Reference")
        lines.append("")
        lines.append("- `openspec/` - Feature specifications with acceptance criteria")
        lines.append("- `.specify/` - Implementation tasks organized by domain")
        lines.append("")

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # README.md -- human-readable overview
    # ------------------------------------------------------------------

    def _render_readme(self, project: ExportableProject) -> str:
        """Render README.md with human-readable project overview."""
        lines: list[str] = []
        name = project.project_name or "Project"

        lines.append(f"# {name}")
        lines.append("")
        if project.idea_summary:
            lines.append(project.idea_summary)
            lines.append("")

        if project.appetite:
            lines.append(f"**Appetite:** {project.appetite}")
            lines.append("")

        # Features
        if project.capabilities:
            lines.append("## Features")
            lines.append("")
            for cap in project.capabilities:
                lines.append(f"- **{cap.name}**: {cap.description}")
            lines.append("")

        # Tech stack
        if project.decisions:
            lines.append("## Tech Stack")
            lines.append("")
            for dec in project.decisions:
                lines.append(f"- **{dec.title}**: {dec.description}")
            lines.append("")

        # Generated by
        generated = project.generated_at or "unknown"
        lines.append("---")
        lines.append("")
        lines.append(
            f"Generated by [Haytham](https://github.com/arslan70/haytham) on {generated}"
        )
        lines.append("")

        return "\n".join(lines)
```

**Step 3: Run tests to verify they pass**

Run: `uv run pytest tests/test_scaffold_exporter.py -v`
Expected: All PASS

**Step 4: Commit**

```bash
git add haytham/exporters/scaffold_exporter.py tests/test_scaffold_exporter.py
git commit -m "feat: add ScaffoldExporter with CLAUDE.md, AGENTS.md, cursorrules, copilot, and README"
```

---

### Task 3: Register exporter and wire up Streamlit UI

Add the scaffold exporter to the registry and make it available from the export dropdown.

**Files:**
- Modify: `haytham/exporters/__init__.py:1-48` (import, __all__, PROJECT_EXPORTERS)
- Modify: `frontend_streamlit/views/stories.py:587-670` (dropdown options, format detection, captions)

**Step 1: Register in __init__.py**

Add import after line 11:

```python
from .scaffold_exporter import ScaffoldExporter
```

Add to `__all__` list:

```python
    "ScaffoldExporter",
```

Add to `PROJECT_EXPORTERS` dict:

```python
    "scaffold": ScaffoldExporter,
```

**Step 2: Add to Streamlit selectbox**

In `frontend_streamlit/views/stories.py`, add `"AI Scaffold (zip)"` to the options list (after `"Spec Kit (zip)"` at line 594):

```python
            "AI Scaffold (zip)",
```

Update the project-level exporter condition (line 645):

```python
    if export_format in ("OpenSpec (zip)", "Spec Kit (zip)", "AI Scaffold (zip)"):
```

Replace the format_key ternary (line 646) with a dict lookup (Open/Closed: adding a new format is a one-line dict entry, not another elif):

```python
        _FORMAT_KEYS = {
            "OpenSpec (zip)": "openspec",
            "Spec Kit (zip)": "speckit",
            "AI Scaffold (zip)": "scaffold",
        }
        format_key = _FORMAT_KEYS[export_format]
```

Add a caption for the scaffold format. After the existing `if/else` captions (lines 668-670), replace the `else` with an `elif/else` chain:

```python
            elif format_key == "scaffold":
                st.caption(
                    "Ready-to-code project with CLAUDE.md, AGENTS.md, "
                    "and Copilot instructions for 20+ AI coding tools"
                )
```

**Step 3: Run lint and format**

Run: `uv run ruff check haytham/ --fix && uv run ruff format haytham/`
Expected: Clean

**Step 4: Run all exporter tests**

Run: `uv run pytest tests/test_openspec_exporter.py tests/test_speckit_exporter.py tests/test_scaffold_exporter.py tests/test_project_assembler.py -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add haytham/exporters/__init__.py frontend_streamlit/views/stories.py
git commit -m "feat: register ScaffoldExporter and add AI Scaffold option to export UI"
```

---

### Task 4: Run full test suite and lint

Final verification that nothing is broken.

**Step 1: Run ruff**

Run: `uv run ruff check haytham/ --fix && uv run ruff format haytham/`

**Step 2: Run all unit tests**

Run: `uv run pytest tests/ -v -m "not integration" -x`
Expected: All PASS

**Step 3: Fix any issues found and commit**

If any tests fail or lint issues are found, fix and commit:

```bash
git commit -m "fix: address lint and test issues from scaffold export"
```
