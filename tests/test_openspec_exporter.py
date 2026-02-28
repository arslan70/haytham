"""Tests for the OpenSpec directory tree exporter."""

from haytham.exporters.openspec_exporter import OpenSpecExporter
from haytham.exporters.project_model import (
    ExportableCapability,
    ExportableDecision,
    ExportableProject,
    ExportableScopeItem,
)
from haytham.workflow.contracts.execution_contract import (
    AcceptanceCriterion,
    ContractStory,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_project(**overrides) -> ExportableProject:
    """Build a realistic ExportableProject for testing."""
    defaults = {
        "idea_summary": "A gym leaderboard app for CrossFit athletes",
        "appetite": "Small Batch",
        "generated_at": "2026-02-28T12:00:00Z",
        "system_traits": {"interface": "React SPA", "authentication": "OAuth2"},
        "scope_items": [
            ExportableScopeItem(
                name="User Authentication",
                description="Handle user identity and access control.",
                capabilities=["CAP-F-001"],
                stories=["STORY-001"],
            ),
        ],
        "capabilities": [
            ExportableCapability(
                id="CAP-F-001",
                name="Login",
                description="authenticate users via OAuth",
                serves_scope_item="User Authentication",
                priority="P1",
                is_functional=True,
                acceptance_criteria=["Users can log in with Google"],
            ),
        ],
        "decisions": [
            ExportableDecision(
                id="DEC-001",
                title="Use Supabase Auth",
                description="Managed auth with social login support.",
                rationale="Reduces custom auth code.",
                serves_capabilities=["CAP-F-001"],
                implements="build",
            ),
        ],
        "non_functional_capabilities": [
            ExportableCapability(
                id="CAP-NF-001",
                name="Response Time",
                description="API responses under 200ms at p95",
                serves_scope_item=None,
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
# Tree structure tests
# ===========================================================================


class TestTreeStructure:
    def test_tree_has_config_yaml(self):
        project = _make_project()
        tree = OpenSpecExporter().export_tree(project)
        assert "openspec/config.yaml" in tree

    def test_tree_has_project_md(self):
        project = _make_project()
        tree = OpenSpecExporter().export_tree(project)
        assert "openspec/project.md" in tree

    def test_tree_has_spec_per_scope_item(self):
        project = _make_project()
        tree = OpenSpecExporter().export_tree(project)
        assert "openspec/specs/user-authentication/spec.md" in tree

    def test_tree_has_cross_cutting_spec(self):
        project = _make_project()
        tree = OpenSpecExporter().export_tree(project)
        assert "openspec/specs/cross-cutting/spec.md" in tree

    def test_empty_nf_no_cross_cutting(self):
        project = _make_project(non_functional_capabilities=[])
        tree = OpenSpecExporter().export_tree(project)
        assert "openspec/specs/cross-cutting/spec.md" not in tree

    def test_infrastructure_scope_item_skipped(self):
        project = _make_project(
            scope_items=[
                ExportableScopeItem(
                    name="Infrastructure",
                    description="Infra stuff",
                    capabilities=[],
                    stories=[],
                ),
                ExportableScopeItem(
                    name="User Authentication",
                    description="Auth domain",
                    capabilities=["CAP-F-001"],
                    stories=["STORY-001"],
                ),
            ]
        )
        tree = OpenSpecExporter().export_tree(project)
        assert "openspec/specs/infrastructure/spec.md" not in tree
        assert "openspec/specs/user-authentication/spec.md" in tree


# ===========================================================================
# Spec content tests
# ===========================================================================


class TestSpecContent:
    def test_spec_contains_shall_statement(self):
        project = _make_project()
        tree = OpenSpecExporter().export_tree(project)
        spec = tree["openspec/specs/user-authentication/spec.md"]
        assert "SHALL" in spec

    def test_spec_contains_scenario(self):
        project = _make_project()
        tree = OpenSpecExporter().export_tree(project)
        spec = tree["openspec/specs/user-authentication/spec.md"]
        assert "#### Scenario:" in spec

    def test_spec_heading_hierarchy(self):
        project = _make_project()
        tree = OpenSpecExporter().export_tree(project)
        spec = tree["openspec/specs/user-authentication/spec.md"]
        assert "## Purpose" in spec
        assert "### Requirement:" in spec
        assert "#### Scenario:" in spec

    def test_spec_has_given_when_then(self):
        project = _make_project()
        tree = OpenSpecExporter().export_tree(project)
        spec = tree["openspec/specs/user-authentication/spec.md"]
        assert "- **Given**" in spec
        assert "- **When**" in spec
        assert "- **Then**" in spec

    def test_scenario_fallback_from_acceptance_criteria(self):
        """When no stories have acceptance criteria, use capability's acceptance_criteria."""
        project = _make_project(
            stories=[
                ContractStory(
                    id="STORY-001",
                    title="User login flow",
                    layer=1,
                    summary="Implement OAuth login",
                    implements=["CAP-F-001"],
                    acceptance_criteria=[],
                ),
            ],
        )
        tree = OpenSpecExporter().export_tree(project)
        spec = tree["openspec/specs/user-authentication/spec.md"]
        # Fallback should generate scenario from capability's acceptance_criteria
        assert "#### Scenario: Users can log in with Google" in spec


# ===========================================================================
# Cross-cutting spec tests
# ===========================================================================


class TestCrossCuttingSpec:
    def test_cross_cutting_contains_nf_capabilities(self):
        project = _make_project()
        tree = OpenSpecExporter().export_tree(project)
        spec = tree["openspec/specs/cross-cutting/spec.md"]
        assert "API responses under 200ms at p95" in spec

    def test_cross_cutting_has_shall(self):
        project = _make_project()
        tree = OpenSpecExporter().export_tree(project)
        spec = tree["openspec/specs/cross-cutting/spec.md"]
        assert "SHALL" in spec

    def test_cross_cutting_has_scenario(self):
        project = _make_project()
        tree = OpenSpecExporter().export_tree(project)
        spec = tree["openspec/specs/cross-cutting/spec.md"]
        assert "#### Scenario:" in spec


# ===========================================================================
# Config and project.md tests
# ===========================================================================


class TestConfigAndProject:
    def test_config_contains_project_name(self):
        project = _make_project()
        tree = OpenSpecExporter().export_tree(project)
        config = tree["openspec/config.yaml"]
        assert "gym leaderboard" in config

    def test_config_contains_traits(self):
        project = _make_project()
        tree = OpenSpecExporter().export_tree(project)
        config = tree["openspec/config.yaml"]
        assert "React SPA" in config

    def test_project_md_contains_decisions(self):
        project = _make_project()
        tree = OpenSpecExporter().export_tree(project)
        project_md = tree["openspec/project.md"]
        assert "Use Supabase Auth" in project_md

    def test_project_md_contains_tech_stack(self):
        project = _make_project()
        tree = OpenSpecExporter().export_tree(project)
        project_md = tree["openspec/project.md"]
        assert "React SPA" in project_md
