"""Tests for IdeaArchetype enum and ConceptAnchor archetype integration."""

import json

from haytham.workflow.anchor_schema import ConceptAnchor, IdeaArchetype, Intent


class TestIdeaArchetypeEnum:
    """Tests for IdeaArchetype enum values and display_name."""

    def test_archetype_enum_values(self):
        """Enum has exactly 6 members with expected values."""
        assert len(IdeaArchetype) == 6
        assert IdeaArchetype.consumer_app == "consumer_app"
        assert IdeaArchetype.b2b_saas == "b2b_saas"
        assert IdeaArchetype.marketplace == "marketplace"
        assert IdeaArchetype.developer_tool == "developer_tool"
        assert IdeaArchetype.internal_tool == "internal_tool"
        assert IdeaArchetype.other == "other"

    def test_display_name(self):
        """display_name returns human-readable names."""
        assert IdeaArchetype.consumer_app.display_name == "Consumer App"
        assert IdeaArchetype.b2b_saas.display_name == "B2B SaaS"
        assert IdeaArchetype.marketplace.display_name == "Marketplace"
        assert IdeaArchetype.developer_tool.display_name == "Developer Tool"
        assert IdeaArchetype.internal_tool.display_name == "Internal Tool"
        assert IdeaArchetype.other.display_name == "Other"

    def test_archetype_is_str(self):
        """IdeaArchetype is a StrEnum, usable as string."""
        assert isinstance(IdeaArchetype.marketplace, str)
        assert f"type is {IdeaArchetype.marketplace}" == "type is marketplace"


class TestConceptAnchorWithArchetype:
    """Tests for ConceptAnchor archetype field integration."""

    def _make_anchor(self, archetype=None):
        """Helper to create a minimal ConceptAnchor."""
        return ConceptAnchor(
            intent=Intent(
                goal="Build a dog walking marketplace",
                explicit_constraints=["Must support real-time tracking"],
                non_goals=["No cat walking"],
            ),
            invariants=[],
            identity=[],
            archetype=archetype,
        )

    def test_anchor_with_archetype_serialization(self):
        """Archetype round-trips through JSON serialization."""
        anchor = self._make_anchor(archetype=IdeaArchetype.marketplace)
        data = json.loads(anchor.model_dump_json())
        restored = ConceptAnchor.model_validate(data)
        assert restored.archetype == IdeaArchetype.marketplace
        assert restored.archetype.display_name == "Marketplace"

    def test_anchor_without_archetype_backward_compat(self):
        """Old JSON without archetype key deserializes with None."""
        data = {
            "intent": {
                "goal": "Build something",
                "explicit_constraints": [],
                "non_goals": [],
            },
            "invariants": [],
            "identity": [],
        }
        anchor = ConceptAnchor.model_validate(data)
        assert anchor.archetype is None

    def test_to_context_string_includes_archetype(self):
        """Rendered context includes Product Archetype section when set."""
        anchor = self._make_anchor(archetype=IdeaArchetype.b2b_saas)
        ctx = anchor.to_context_string()
        assert "### Product Archetype" in ctx
        assert "**Type:** B2B SaaS" in ctx

    def test_to_context_string_omits_when_none(self):
        """No archetype section when archetype is None."""
        anchor = self._make_anchor(archetype=None)
        ctx = anchor.to_context_string()
        assert "Product Archetype" not in ctx


class TestArchetypeOverrideLogic:
    """Tests for user archetype override logic (extracted from post-processor).

    The post-processor imports burr.core.State which may not be installed in
    the test env, so we test the override logic directly on ConceptAnchor.
    """

    def _apply_archetype_override(self, anchor: ConceptAnchor, user_archetype: str) -> None:
        """Replicate the override logic from extract_anchor_post_processor."""
        if user_archetype:
            try:
                anchor.archetype = IdeaArchetype(user_archetype)
            except ValueError:
                pass

    def test_user_selection_overrides_llm(self):
        """User-selected archetype overrides the LLM classification."""
        anchor = ConceptAnchor(
            intent=Intent(goal="Test idea", explicit_constraints=[], non_goals=[]),
            invariants=[],
            identity=[],
            archetype=IdeaArchetype.consumer_app,  # LLM classified
        )
        self._apply_archetype_override(anchor, "marketplace")
        assert anchor.archetype == IdeaArchetype.marketplace

    def test_auto_detect_preserves_llm_classification(self):
        """When user chose auto-detect (empty string), LLM classification stands."""
        anchor = ConceptAnchor(
            intent=Intent(goal="Test idea", explicit_constraints=[], non_goals=[]),
            invariants=[],
            identity=[],
            archetype=IdeaArchetype.developer_tool,  # LLM classified
        )
        self._apply_archetype_override(anchor, "")
        assert anchor.archetype == IdeaArchetype.developer_tool

    def test_invalid_archetype_preserves_llm(self):
        """Invalid user archetype string preserves LLM classification."""
        anchor = ConceptAnchor(
            intent=Intent(goal="Test idea", explicit_constraints=[], non_goals=[]),
            invariants=[],
            identity=[],
            archetype=IdeaArchetype.b2b_saas,
        )
        self._apply_archetype_override(anchor, "not_a_real_archetype")
        assert anchor.archetype == IdeaArchetype.b2b_saas
