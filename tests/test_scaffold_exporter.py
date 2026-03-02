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
