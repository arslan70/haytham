"""Tests for shared spec transformation utilities."""

from haytham.exporters.project_model import ExportableCapability
from haytham.exporters.spec_transforms import (
    capability_to_shall_statement,
    group_stories_by_layer,
    slugify,
    traits_to_constitution_articles,
)
from haytham.workflow.contracts.execution_contract import ContractStory

# ---------------------------------------------------------------------------
# slugify
# ---------------------------------------------------------------------------


class TestSlugify:
    def test_basic(self):
        assert slugify("User Authentication") == "user-authentication"

    def test_special_characters(self):
        assert slugify("Join session via invite link!") == "join-session-via-invite-link"

    def test_multiple_spaces(self):
        assert slugify("Real  Time  Sync") == "real-time-sync"

    def test_leading_trailing(self):
        assert slugify("  Hello World  ") == "hello-world"

    def test_empty(self):
        assert slugify("") == ""

    def test_numeric(self):
        assert slugify("8 participants max") == "8-participants-max"


# ---------------------------------------------------------------------------
# capability_to_shall_statement
# ---------------------------------------------------------------------------


class TestCapabilityToShallStatement:
    def test_functional(self):
        cap = ExportableCapability(
            id="C1",
            name="Auth",
            description="Authenticate users via OAuth",
            is_functional=True,
        )
        result = capability_to_shall_statement(cap)
        assert result == "The system SHALL authenticate users via OAuth"

    def test_already_lowercase(self):
        cap = ExportableCapability(
            id="C2",
            name="Cache",
            description="cache frequently accessed data",
            is_functional=True,
        )
        result = capability_to_shall_statement(cap)
        assert result == "The system SHALL cache frequently accessed data"

    def test_non_functional(self):
        cap = ExportableCapability(
            id="NF1",
            name="Latency",
            description="Respond within 200ms for 95th percentile",
            is_functional=False,
        )
        result = capability_to_shall_statement(cap)
        assert result == "The system SHALL respond within 200ms for 95th percentile"


# ---------------------------------------------------------------------------
# group_stories_by_layer
# ---------------------------------------------------------------------------


def _story(story_id: str, layer: int) -> ContractStory:
    return ContractStory(id=story_id, title=f"Story {story_id}", layer=layer, summary="")


class TestGroupStoriesByLayer:
    def test_groups_correctly(self):
        stories = [
            _story("S1", 0),
            _story("S2", 2),
            _story("S3", 3),
            _story("S4", 4),
            _story("S5", 2),
        ]
        grouped = group_stories_by_layer(stories)

        assert set(grouped.keys()) == {0, 2, 3, 4}
        assert len(grouped[0]) == 1
        assert len(grouped[2]) == 2
        assert len(grouped[3]) == 1
        assert len(grouped[4]) == 1
        assert grouped[0][0].id == "S1"
        assert [s.id for s in grouped[2]] == ["S2", "S5"]

    def test_empty_list(self):
        assert group_stories_by_layer([]) == {}


# ---------------------------------------------------------------------------
# traits_to_constitution_articles
# ---------------------------------------------------------------------------


class TestTraitsToConstitution:
    def test_maps_traits(self):
        traits = {
            "interface": "React SPA",
            "interface_explanation": "Modern frontend framework",
            "authentication": "JWT-based",
        }
        result = traits_to_constitution_articles(traits)

        assert "Article 1: Interface Principle" in result
        assert "Article 2: Security Principle" in result
        assert "**Interface:** React SPA" in result
        assert "Modern frontend framework" in result
        assert "**Authentication:** JWT-based" in result

    def test_skips_explanations(self):
        traits = {
            "interface": "CLI",
            "interface_explanation": "Command-line interface",
        }
        result = traits_to_constitution_articles(traits)

        # Only one article should be generated (interface), not a separate
        # one for the _explanation key.
        assert result.count("### Article") == 1
