"""Tests for the Spec Kit directory tree exporter."""

from haytham.exporters.project_model import (
    ExportableCapability,
    ExportableDecision,
    ExportableProject,
    ExportableScopeItem,
)
from haytham.exporters.speckit_exporter import SpecKitExporter
from haytham.workflow.contracts.execution_contract import (
    AcceptanceCriterion,
    ContractStory,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_project(**overrides) -> ExportableProject:
    """Build a realistic ExportableProject for Spec Kit testing.

    Includes stories at layers 0, 2, and 3 to exercise data-model.md
    and contracts/api.md generation paths.
    """
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
                stories=["STORY-001", "STORY-002", "STORY-003"],
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
        "build_buy": {
            "recommended_stack": [
                {
                    "name": "Supabase",
                    "category": "Authentication",
                    "recommendation": "BUY",
                    "rationale": "Managed auth reduces custom code.",
                    "capabilities_served": ["CAP-F-001"],
                    "integration_effort": "2-4 hours",
                    "pricing_notes": "Free tier for MVP",
                },
            ],
        },
        "stories": [
            ContractStory(
                id="STORY-001",
                title="Project scaffolding",
                layer=0,
                summary="Set up the initial project structure",
                implements=["CAP-F-001"],
            ),
            ContractStory(
                id="STORY-002",
                title="User table schema",
                layer=2,
                summary="Define the user data model",
                content="## Users Table\n\n| Column | Type |\n|---|---|\n| id | UUID |",
                implements=["CAP-F-001"],
                depends_on=["STORY-001"],
            ),
            ContractStory(
                id="STORY-003",
                title="Login endpoint",
                layer=3,
                summary="Implement the OAuth login API",
                content="## POST /auth/login\n\nAccepts OAuth token and returns session.",
                implements=["CAP-F-001"],
                depends_on=["STORY-002"],
                acceptance_criteria=[
                    AcceptanceCriterion(
                        id="AC-001",
                        scenario="Successful Google login",
                        given="a user with a Google account",
                        when="they submit a valid OAuth token",
                        then="a session token is returned",
                    ),
                ],
            ),
        ],
    }
    defaults.update(overrides)
    return ExportableProject(**defaults)


# ===========================================================================
# Constitution tests
# ===========================================================================


class TestConstitution:
    def test_tree_has_constitution(self):
        project = _make_project()
        tree = SpecKitExporter().export_tree(project)
        assert ".specify/memory/constitution.md" in tree

    def test_constitution_has_versioning_footer(self):
        project = _make_project()
        tree = SpecKitExporter().export_tree(project)
        content = tree[".specify/memory/constitution.md"]
        assert "**Version**: 1.0" in content
        assert "**Ratified**:" in content

    def test_constitution_has_nf_capabilities(self):
        project = _make_project()
        tree = SpecKitExporter().export_tree(project)
        content = tree[".specify/memory/constitution.md"]
        assert "API responses under 200ms at p95" in content


# ===========================================================================
# Spec tests
# ===========================================================================


class TestSpec:
    def test_tree_has_spec_md(self):
        project = _make_project()
        tree = SpecKitExporter().export_tree(project)
        assert ".specify/specs/001-user-authentication/spec.md" in tree

    def test_spec_has_fr_ids(self):
        project = _make_project()
        tree = SpecKitExporter().export_tree(project)
        content = tree[".specify/specs/001-user-authentication/spec.md"]
        assert "FR-001" in content


# ===========================================================================
# Plan tests
# ===========================================================================


class TestPlan:
    def test_tree_has_plan_md(self):
        project = _make_project()
        tree = SpecKitExporter().export_tree(project)
        assert ".specify/specs/001-user-authentication/plan.md" in tree


# ===========================================================================
# Tasks tests
# ===========================================================================


class TestTasks:
    def test_tree_has_tasks_md(self):
        project = _make_project()
        tree = SpecKitExporter().export_tree(project)
        assert ".specify/specs/001-user-authentication/tasks.md" in tree

    def test_tasks_has_t_ids(self):
        project = _make_project()
        tree = SpecKitExporter().export_tree(project)
        content = tree[".specify/specs/001-user-authentication/tasks.md"]
        assert "T001" in content

    def test_tasks_has_phase_grouping(self):
        project = _make_project()
        tree = SpecKitExporter().export_tree(project)
        content = tree[".specify/specs/001-user-authentication/tasks.md"]
        assert "## Phase" in content


# ===========================================================================
# Conditional file tests
# ===========================================================================


class TestConditionalFiles:
    def test_data_model_for_layer_2(self):
        project = _make_project()
        tree = SpecKitExporter().export_tree(project)
        assert ".specify/specs/001-user-authentication/data-model.md" in tree

    def test_contracts_for_layer_3(self):
        project = _make_project()
        tree = SpecKitExporter().export_tree(project)
        assert ".specify/specs/001-user-authentication/contracts/api.md" in tree

    def test_no_data_model_without_layer_2(self):
        """data-model.md should not exist when there are no layer 2 stories."""
        project = _make_project(
            scope_items=[
                ExportableScopeItem(
                    name="User Authentication",
                    description="Handle user identity and access control.",
                    capabilities=["CAP-F-001"],
                    stories=["STORY-001", "STORY-003"],
                ),
            ],
            stories=[
                ContractStory(
                    id="STORY-001",
                    title="Project scaffolding",
                    layer=0,
                    summary="Set up the initial project structure",
                    implements=["CAP-F-001"],
                ),
                ContractStory(
                    id="STORY-003",
                    title="Login endpoint",
                    layer=3,
                    summary="Implement the OAuth login API",
                    content="## POST /auth/login\n\nAccepts OAuth token.",
                    implements=["CAP-F-001"],
                    acceptance_criteria=[
                        AcceptanceCriterion(
                            id="AC-001",
                            scenario="Successful Google login",
                            given="a user with a Google account",
                            when="they submit a valid OAuth token",
                            then="a session token is returned",
                        ),
                    ],
                ),
            ],
        )
        tree = SpecKitExporter().export_tree(project)
        data_model_keys = [k for k in tree if "data-model.md" in k]
        assert data_model_keys == []
