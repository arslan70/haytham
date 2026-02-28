"""Tests for ExportableProject and sub-models.

Follows project test patterns: module-level _make_*() helpers,
class-based test grouping.
"""

from haytham.exporters.project_model import (
    ExportableCapability,
    ExportableDecision,
    ExportableProject,
    ExportableScopeItem,
)
from haytham.workflow.contracts.execution_contract import ContractStory

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_capability(
    *,
    id: str = "CAP-F-001",
    name: str = "User Registration",
    description: str = "Allow users to create accounts",
    serves_scope_item: str | None = "User Management",
    priority: str = "P1",
    is_functional: bool = True,
    acceptance_criteria: list[str] | None = None,
) -> ExportableCapability:
    return ExportableCapability(
        id=id,
        name=name,
        description=description,
        serves_scope_item=serves_scope_item,
        priority=priority,
        is_functional=is_functional,
        acceptance_criteria=acceptance_criteria or [],
    )


def _make_decision(
    *,
    id: str = "DEC-001",
    title: str = "Use PostgreSQL",
    description: str = "Relational DB for structured data",
    rationale: str = "Strong ecosystem and JSON support",
    serves_capabilities: list[str] | None = None,
    implements: str = "build",
    alternatives_considered: list[str] | None = None,
) -> ExportableDecision:
    return ExportableDecision(
        id=id,
        title=title,
        description=description,
        rationale=rationale,
        serves_capabilities=serves_capabilities or ["CAP-F-001"],
        implements=implements,
        alternatives_considered=alternatives_considered or ["MySQL", "MongoDB"],
    )


def _make_scope_item(
    *,
    name: str = "User Management",
    description: str = "Core user features",
    capabilities: list[str] | None = None,
    stories: list[str] | None = None,
) -> ExportableScopeItem:
    return ExportableScopeItem(
        name=name,
        description=description,
        capabilities=capabilities or ["CAP-F-001", "CAP-F-002"],
        stories=stories or ["STORY-001", "STORY-002"],
    )


def _make_story(
    *,
    id: str = "STORY-001",
    title: str = "User registration",
    layer: int = 1,
    summary: str = "Implement user registration flow",
) -> ContractStory:
    return ContractStory(
        id=id,
        title=title,
        layer=layer,
        summary=summary,
        implements=["CAP-F-001"],
        depends_on=[],
    )


def _make_project(**overrides) -> ExportableProject:
    defaults = {
        "idea_summary": "A gym leaderboard app for CrossFit athletes",
        "appetite": "Small Batch",
        "generated_at": "2026-02-28T12:00:00Z",
        "system_traits": {"interface": "Web", "auth": "OAuth2"},
        "scope_items": [_make_scope_item()],
        "capabilities": [_make_capability()],
        "decisions": [_make_decision()],
        "non_functional_capabilities": [
            _make_capability(
                id="CAP-NF-001",
                name="Response Time",
                description="API responses under 200ms",
                serves_scope_item=None,
                is_functional=False,
            )
        ],
        "stories": [_make_story()],
    }
    defaults.update(overrides)
    return ExportableProject(**defaults)


# ===========================================================================
# ExportableCapability
# ===========================================================================


class TestExportableCapability:
    def test_functional_capability(self):
        cap = _make_capability()
        assert cap.id == "CAP-F-001"
        assert cap.is_functional is True
        assert cap.serves_scope_item == "User Management"
        assert cap.priority == "P1"

    def test_non_functional_capability_no_scope_item(self):
        cap = _make_capability(
            id="CAP-NF-001",
            name="Latency SLA",
            description="P99 under 200ms",
            serves_scope_item=None,
            is_functional=False,
        )
        assert cap.serves_scope_item is None
        assert cap.is_functional is False

    def test_acceptance_criteria_list(self):
        cap = _make_capability(
            acceptance_criteria=["Users can register with email", "Password must be 8+ chars"]
        )
        assert len(cap.acceptance_criteria) == 2

    def test_defaults(self):
        cap = ExportableCapability(id="CAP-F-099", name="Minimal", description="Bare minimum")
        assert cap.priority == "P1"
        assert cap.is_functional is True
        assert cap.serves_scope_item is None
        assert cap.acceptance_criteria == []


# ===========================================================================
# ExportableDecision
# ===========================================================================


class TestExportableDecision:
    def test_decision_with_capabilities(self):
        dec = _make_decision(serves_capabilities=["CAP-F-001", "CAP-F-002", "CAP-NF-001"])
        assert len(dec.serves_capabilities) == 3
        assert "CAP-NF-001" in dec.serves_capabilities

    def test_decision_alternatives(self):
        dec = _make_decision(alternatives_considered=["DynamoDB", "Firestore"])
        assert dec.alternatives_considered == ["DynamoDB", "Firestore"]

    def test_defaults(self):
        dec = ExportableDecision(
            id="DEC-099", title="Minimal", description="Bare", rationale="Because"
        )
        assert dec.serves_capabilities == []
        assert dec.implements == ""
        assert dec.alternatives_considered == []


# ===========================================================================
# ExportableScopeItem
# ===========================================================================


class TestExportableScopeItem:
    def test_scope_item_links(self):
        item = _make_scope_item(
            capabilities=["CAP-F-001", "CAP-F-002"],
            stories=["STORY-001", "STORY-003"],
        )
        assert item.capabilities == ["CAP-F-001", "CAP-F-002"]
        assert item.stories == ["STORY-001", "STORY-003"]

    def test_defaults(self):
        item = ExportableScopeItem(name="Bare Item")
        assert item.description == ""
        assert item.capabilities == []
        assert item.stories == []


# ===========================================================================
# ExportableProject
# ===========================================================================


class TestExportableProject:
    def test_full_construction(self):
        project = _make_project()
        assert project.idea_summary == "A gym leaderboard app for CrossFit athletes"
        assert project.appetite == "Small Batch"
        assert project.generated_at == "2026-02-28T12:00:00Z"
        assert project.system_traits["interface"] == "Web"
        assert len(project.scope_items) == 1
        assert len(project.capabilities) == 1
        assert len(project.decisions) == 1
        assert len(project.non_functional_capabilities) == 1
        assert len(project.stories) == 1

    def test_stories_are_contract_stories(self):
        project = _make_project()
        story = project.stories[0]
        assert isinstance(story, ContractStory)
        assert story.id == "STORY-001"
        assert story.implements == ["CAP-F-001"]

    def test_defaults_all_empty(self):
        project = ExportableProject(idea_summary="Minimal idea")
        assert project.appetite == ""
        assert project.generated_at == ""
        assert project.system_traits == {}
        assert project.scope_items == []
        assert project.capabilities == []
        assert project.decisions == []
        assert project.non_functional_capabilities == []
        assert project.build_buy is None
        assert project.stories == []

    def test_build_buy_accepts_arbitrary_data(self):
        project = _make_project(build_buy={"strategy": "build", "rationale": "Custom requirements"})
        assert project.build_buy["strategy"] == "build"

    def test_json_roundtrip(self):
        project = _make_project()
        json_str = project.model_dump_json()
        restored = ExportableProject.model_validate_json(json_str)
        assert restored.idea_summary == project.idea_summary
        assert len(restored.stories) == len(project.stories)
        assert restored.stories[0].id == project.stories[0].id
        assert restored.capabilities[0].id == project.capabilities[0].id
        assert restored.decisions[0].id == project.decisions[0].id

    def test_scope_item_links_capabilities_to_stories(self):
        """Scope items bridge capabilities and stories by ID reference."""
        scope = _make_scope_item(
            name="Leaderboard",
            capabilities=["CAP-F-010", "CAP-F-011"],
            stories=["STORY-005", "STORY-006", "STORY-007"],
        )
        project = _make_project(scope_items=[scope])
        item = project.scope_items[0]
        assert item.name == "Leaderboard"
        assert len(item.capabilities) == 2
        assert len(item.stories) == 3
