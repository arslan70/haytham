"""Tests for stage configuration system.

Tests cover:
- StageMetadata dataclass
- StageRegistry class with all 12 stages
- Helper functions for retrieving and formatting configurations
- Backward compatibility with stage_config.py
"""

import warnings

import pytest

from haytham.workflow.stage_registry import (
    StageMetadata,
    WorkflowType,
    format_query,
    get_all_stage_slugs,
    get_stage_by_slug,
    get_stage_registry,
)


class TestStageMetadata:
    """Test StageMetadata dataclass."""

    def test_stage_metadata_creation(self):
        """Test StageMetadata can be created with all required fields."""
        stage = StageMetadata(
            slug="test-stage",
            action_name="test_stage",
            display_name="Test Stage",
            display_index=1,
            description="A test stage",
            state_key="test_stage",
            status_key="test_stage_status",
            workflow_type=WorkflowType.IDEA_VALIDATION,
            query_template="Test query: {system_goal}",
            agent_names=["test_agent"],
            required_context=[],
        )

        assert stage.slug == "test-stage"
        assert stage.action_name == "test_stage"
        assert stage.display_name == "Test Stage"
        assert stage.display_index == 1
        assert stage.state_key == "test_stage"
        assert stage.status_key == "test_stage_status"
        assert stage.workflow_type == WorkflowType.IDEA_VALIDATION
        assert stage.query_template == "Test query: {system_goal}"
        assert stage.agent_names == ["test_agent"]
        assert not stage.is_optional
        assert stage.execution_mode == "single"

    def test_stage_metadata_immutable(self):
        """Test StageMetadata is immutable (frozen dataclass)."""
        stage = get_stage_by_slug("idea-analysis")
        with pytest.raises(AttributeError):  # FrozenInstanceError
            stage.slug = "new-slug"


class TestStageRegistry:
    """Test StageRegistry class with all stages."""

    def test_all_stages_present(self):
        """Test all 13 stages are defined."""
        registry = get_stage_registry()
        assert len(registry) == 13

    def test_stage_order(self):
        """Test stages are in correct order."""
        expected_slugs = [
            "idea-analysis",
            "market-context",
            "risk-assessment",
            "pivot-strategy",
            "validation-summary",
            "mvp-scope",
            "capability-model",
            "system-traits",
            "build-buy-analysis",
            "architecture-decisions",
            "story-generation",
            "story-validation",
            "dependency-ordering",
        ]
        actual_slugs = get_all_stage_slugs(include_optional=True)
        assert actual_slugs == expected_slugs

    def test_stage_order_without_optional(self):
        """Test stages order excludes optional stages."""
        slugs = get_all_stage_slugs(include_optional=False)
        assert "pivot-strategy" not in slugs
        assert len(slugs) == 12

    def test_get_by_slug(self):
        """Test get_by_slug returns correct stage."""
        stage = get_stage_by_slug("idea-analysis")
        assert stage.slug == "idea-analysis"
        assert stage.display_name == "Idea Analysis"

    def test_get_by_slug_invalid(self):
        """Test get_by_slug raises ValueError for invalid slug."""
        with pytest.raises(ValueError, match="Unknown stage slug"):
            get_stage_by_slug("invalid-slug")

    def test_get_by_action(self):
        """Test get_by_action returns correct stage."""
        registry = get_stage_registry()
        stage = registry.get_by_action("idea_analysis")
        assert stage.slug == "idea-analysis"
        assert stage.action_name == "idea_analysis"

    def test_workflow_filtering(self):
        """Test filtering stages by workflow type."""
        registry = get_stage_registry()

        idea_stages = registry.get_stages_for_workflow(WorkflowType.IDEA_VALIDATION)
        assert len(idea_stages) == 5  # Including optional pivot-strategy

        mvp_stages = registry.get_stages_for_workflow(WorkflowType.MVP_SPECIFICATION)
        assert len(mvp_stages) == 3

        build_buy_stages = registry.get_stages_for_workflow(WorkflowType.BUILD_BUY_ANALYSIS)
        assert len(build_buy_stages) == 1

        arch_stages = registry.get_stages_for_workflow(WorkflowType.ARCHITECTURE_DECISIONS)
        assert len(arch_stages) == 1

        story_stages = registry.get_stages_for_workflow(WorkflowType.STORY_GENERATION)
        assert len(story_stages) == 3


class TestStageConfigs:
    """Test individual stage configurations."""

    def test_idea_analysis_stage(self):
        """Test idea-analysis stage configuration."""
        stage = get_stage_by_slug("idea-analysis")
        assert stage.display_name == "Idea Analysis"
        assert stage.display_index == 1
        assert stage.agent_names == ["concept_expansion"]
        assert stage.execution_mode == "single"
        assert stage.workflow_type == WorkflowType.IDEA_VALIDATION
        assert "{system_goal}" in stage.query_template
        assert stage.required_context == []

    def test_market_context_stage(self):
        """Test market-context stage configuration."""
        stage = get_stage_by_slug("market-context")
        assert stage.display_name == "Market Context"
        assert stage.display_index == 2
        assert set(stage.agent_names) == {"market_intelligence", "competitor_analysis"}
        assert stage.execution_mode == "sequential"
        assert stage.required_context == ["idea-analysis"]

    def test_pivot_strategy_is_optional(self):
        """Test pivot-strategy stage is marked as optional."""
        stage = get_stage_by_slug("pivot-strategy")
        assert stage.is_optional
        assert stage.display_index == "3b"

    def test_build_buy_analysis_stage(self):
        """Test build-buy-analysis stage configuration."""
        stage = get_stage_by_slug("build-buy-analysis")
        assert stage.display_name == "Build vs Buy Analysis"
        assert stage.agent_names == ["build_buy_analyzer"]
        assert stage.workflow_type == WorkflowType.BUILD_BUY_ANALYSIS


class TestQueryFormatting:
    """Test query template formatting."""

    def test_format_query_with_system_goal(self):
        """Test format_query formats template with system_goal."""
        query = format_query("idea-analysis", system_goal="AI startup validator")
        assert "AI startup validator" in query
        assert "Analyze this startup idea" in query

    def test_format_query_missing_variable(self):
        """Test format_query raises KeyError for missing variables."""
        with pytest.raises(KeyError, match="Missing required template variable"):
            format_query("idea-analysis")  # Missing system_goal

    def test_format_query_without_variables(self):
        """Test format_query works for stages without template variables."""
        # risk-assessment doesn't have {system_goal} in template
        query = format_query("risk-assessment")
        assert "Identify and assess risks" in query


class TestStageConsistency:
    """Test consistency of stage configurations."""

    def test_all_stages_have_query_templates(self):
        """Test all stages have query_template field."""
        for stage in get_stage_registry():
            assert stage.query_template, f"{stage.slug} missing query_template"
            assert len(stage.query_template) > 0

    def test_all_stages_have_state_keys(self):
        """Test all stages have state_key and status_key."""
        for stage in get_stage_registry():
            assert stage.state_key, f"{stage.slug} missing state_key"
            assert stage.status_key, f"{stage.slug} missing status_key"
            assert stage.status_key == f"{stage.state_key}_status"

    def test_all_stages_have_agents(self):
        """Test all stages have at least one agent."""
        for stage in get_stage_registry():
            assert len(stage.agent_names) > 0, f"{stage.slug} has no agents"

    def test_slugs_are_kebab_case(self):
        """Test all slugs are kebab-case."""
        for stage in get_stage_registry():
            assert "-" in stage.slug or stage.slug.islower()
            assert " " not in stage.slug
            assert "_" not in stage.slug

    def test_action_names_are_snake_case(self):
        """Test all action names are snake_case."""
        for stage in get_stage_registry():
            assert "_" in stage.action_name or stage.action_name.islower()
            assert "-" not in stage.action_name
            assert " " not in stage.action_name


class TestBackwardCompatibility:
    """Test backward compatibility with stage_config.py."""

    def test_import_from_stage_config(self):
        """Test importing from stage_config.py still works."""
        import importlib

        import haytham.phases.stage_config as sc_module

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            # Force re-import to trigger deprecation warning even if already cached
            importlib.reload(sc_module)

            # Should have deprecation warning
            assert len(w) >= 1
            assert "deprecated" in str(w[0].message).lower()

        # Backward compat aliases should work
        from haytham.phases.stage_config import (
            STAGES,
            StageConfig,
        )
        from haytham.phases.stage_config import (
            WorkflowType as WF,
        )
        from haytham.phases.stage_config import (
            get_stage_by_slug as gsbs,
        )

        assert len(STAGES) == 13
        assert StageConfig.__name__ == "StageMetadata"
        assert WF == WorkflowType

        stage = gsbs("idea-analysis")
        assert stage.slug == "idea-analysis"

    def test_stage_config_has_query_template(self):
        """Test StageConfig alias has query_template field."""
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            from haytham.phases.stage_config import STAGES

            for stage in STAGES:
                assert hasattr(stage, "query_template")
                assert stage.query_template
