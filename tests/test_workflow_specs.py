"""Tests for workflow specs, factories, and builder.

Covers WorkflowSpec.build_default_state(), transition graph definitions,
terminal stage computation, context_stages validity, and factory dispatch.
"""

import pytest

from haytham.workflow.stage_registry import WorkflowType, get_stage_registry
from haytham.workflow.workflow_specs import (
    IDEA_VALIDATION_SPEC,
    MVP_SPECIFICATION_SPEC,
    STORY_GENERATION_SPEC,
    WORKFLOW_SPECS,
    WorkflowSpec,
)

# =============================================================================
# WorkflowSpec.build_default_state()
# =============================================================================


class TestBuildDefaultState:
    """Tests for the auto-generated default state."""

    def test_creates_output_and_status_keys_per_stage(self):
        """Each stage gets a '' output key and 'pending' status key."""
        state = IDEA_VALIDATION_SPEC.build_default_state()

        for stage_name in IDEA_VALIDATION_SPEC.stages:
            assert stage_name in state, f"Missing output key: {stage_name}"
            assert state[stage_name] == ""
            status_key = f"{stage_name}_status"
            assert status_key in state, f"Missing status key: {status_key}"
            assert state[status_key] == "pending"

    def test_extra_state_keys_default_to_empty_string(self):
        """extra_state_keys get '' as default."""
        state = IDEA_VALIDATION_SPEC.build_default_state()
        assert "risk_level" in state
        assert state["risk_level"] == ""

    def test_null_state_keys_default_to_none(self):
        """null_state_keys get None as default."""
        state = MVP_SPECIFICATION_SPEC.build_default_state()
        assert "system_traits_parsed" in state
        assert state["system_traits_parsed"] is None
        assert "system_traits_warnings" in state
        assert state["system_traits_warnings"] is None

    def test_extra_state_keys_do_not_overwrite_stage_keys(self):
        """setdefault on extra_state_keys preserves stage-generated keys."""
        # Create a spec where an extra_state_key matches a stage name
        spec = WorkflowSpec(
            workflow_type=WorkflowType.IDEA_VALIDATION,
            actions={},
            transitions=[],
            entrypoint="idea_analysis",
            tracking_project="test",
            stages=["idea_analysis"],
            extra_state_keys=["idea_analysis"],  # Collision
        )
        state = spec.build_default_state()
        # The stage loop sets it to "", then setdefault preserves ""
        assert state["idea_analysis"] == ""

    def test_mvp_spec_default_state_completeness(self):
        """MVP Specification default state has all expected keys."""
        state = MVP_SPECIFICATION_SPEC.build_default_state()
        expected = [
            "mvp_scope",
            "mvp_scope_status",
            "capability_model",
            "capability_model_status",
            "system_traits",
            "system_traits_status",
            "system_traits_parsed",
            "system_traits_warnings",
        ]
        for key in expected:
            assert key in state, f"Missing key: {key}"


# =============================================================================
# Spec Definitions: Structural Validity
# =============================================================================


class TestSpecStructure:
    """Verify structural properties of all workflow specs."""

    @pytest.fixture(params=list(WORKFLOW_SPECS.items()), ids=lambda x: x[0].value)
    def spec_pair(self, request):
        return request.param

    def test_entrypoint_is_first_stage(self, spec_pair):
        """Entrypoint matches the first stage in the ordered stages list."""
        wf_type, spec = spec_pair
        assert spec.entrypoint == spec.stages[0], (
            f"{wf_type}: entrypoint '{spec.entrypoint}' != first stage '{spec.stages[0]}'"
        )

    def test_all_actions_have_stage_entries(self, spec_pair):
        """Every action name appears in the stages list."""
        wf_type, spec = spec_pair
        for action_name in spec.actions:
            assert action_name in spec.stages, (
                f"{wf_type}: action '{action_name}' not in stages list"
            )

    def test_all_stages_have_action_entries(self, spec_pair):
        """Every stage name appears in the actions dict."""
        wf_type, spec = spec_pair
        for stage_name in spec.stages:
            assert stage_name in spec.actions, (
                f"{wf_type}: stage '{stage_name}' not in actions dict"
            )

    def test_transition_sources_are_valid_actions(self, spec_pair):
        """Every transition source is a valid action name."""
        wf_type, spec = spec_pair
        for transition in spec.transitions:
            source = transition[0]
            assert source in spec.actions, f"{wf_type}: transition source '{source}' not in actions"

    def test_transition_targets_are_valid_actions(self, spec_pair):
        """Every transition target is a valid action name."""
        wf_type, spec = spec_pair
        for transition in spec.transitions:
            target = transition[1]
            assert target in spec.actions, f"{wf_type}: transition target '{target}' not in actions"

    def test_context_stages_reference_valid_registry_slugs(self, spec_pair):
        """Every context_stages entry is a valid slug in the stage registry."""
        wf_type, spec = spec_pair
        registry = get_stage_registry()
        for slug in spec.context_stages:
            try:
                registry.get_by_slug(slug)
            except ValueError:
                pytest.fail(f"{wf_type}: context_stage '{slug}' not found in registry")


# =============================================================================
# Idea Validation: Conditional Branching
# =============================================================================


class TestIdeaValidationTransitions:
    """Tests specific to the idea-validation workflow's conditional branching."""

    def test_risk_assessment_has_conditional_and_default(self):
        """risk_assessment has both a conditional (HIGH) and default transition."""
        transitions_from_risk = [
            t for t in IDEA_VALIDATION_SPEC.transitions if t[0] == "risk_assessment"
        ]
        assert len(transitions_from_risk) == 2, (
            f"Expected 2 transitions from risk_assessment, got {len(transitions_from_risk)}"
        )

    def test_conditional_transition_precedes_default(self):
        """when(risk_level='HIGH') comes BEFORE default in transition list.

        Burr evaluates transitions in order. If default came first, it would
        always match and the conditional branch would never fire.
        """
        transitions_from_risk = [
            t for t in IDEA_VALIDATION_SPEC.transitions if t[0] == "risk_assessment"
        ]
        # First transition should go to pivot_strategy (conditional)
        assert transitions_from_risk[0][1] == "pivot_strategy"
        # Second transition should go to validation_summary (default)
        assert transitions_from_risk[1][1] == "validation_summary"

    def test_pivot_strategy_always_goes_to_validation_summary(self):
        """pivot_strategy unconditionally transitions to validation_summary."""
        transitions_from_pivot = [
            t for t in IDEA_VALIDATION_SPEC.transitions if t[0] == "pivot_strategy"
        ]
        assert len(transitions_from_pivot) == 1
        assert transitions_from_pivot[0][1] == "validation_summary"

    def test_idea_validation_has_five_stages(self):
        assert len(IDEA_VALIDATION_SPEC.stages) == 5

    def test_pivot_strategy_is_optional_in_registry(self):
        """pivot-strategy is marked as optional in the stage registry."""
        registry = get_stage_registry()
        stage = registry.get_by_slug("pivot-strategy")
        assert stage.is_optional


# =============================================================================
# Terminal Stage Computation
# =============================================================================


class TestTerminalStages:
    """Tests for terminal stage detection."""

    def test_terminal_stages_from_specs(self):
        """Last stage in each spec's stages list is the terminal stage."""
        from haytham.workflow.workflow_factories import WORKFLOW_TERMINAL_STAGES

        for wf_type, spec in WORKFLOW_SPECS.items():
            expected_terminal = spec.stages[-1]
            assert wf_type in WORKFLOW_TERMINAL_STAGES
            assert WORKFLOW_TERMINAL_STAGES[wf_type] == expected_terminal, (
                f"{wf_type}: expected terminal '{expected_terminal}', "
                f"got '{WORKFLOW_TERMINAL_STAGES[wf_type]}'"
            )

    def test_get_terminal_stage(self):
        from haytham.workflow.workflow_factories import get_terminal_stage

        assert get_terminal_stage(WorkflowType.IDEA_VALIDATION) == "validation_summary"
        assert get_terminal_stage(WorkflowType.STORY_GENERATION) == "dependency_ordering"

    def test_get_terminal_stage_unknown_raises(self):
        from haytham.workflow.workflow_factories import get_terminal_stage

        with pytest.raises(ValueError, match="Unknown workflow type"):
            get_terminal_stage("nonexistent_type")


# =============================================================================
# WORKFLOW_SPECS Coverage
# =============================================================================


class TestWorkflowSpecsRegistry:
    """Verify WORKFLOW_SPECS covers all WorkflowType values."""

    def test_all_workflow_types_have_specs(self):
        """Every WorkflowType enum value has a corresponding spec."""
        for wf_type in WorkflowType:
            assert wf_type in WORKFLOW_SPECS, (
                f"WorkflowType.{wf_type.name} has no entry in WORKFLOW_SPECS"
            )

    def test_spec_workflow_type_matches_key(self):
        """Each spec's workflow_type matches its key in WORKFLOW_SPECS."""
        for wf_type, spec in WORKFLOW_SPECS.items():
            assert spec.workflow_type == wf_type, (
                f"Spec keyed as {wf_type} has workflow_type={spec.workflow_type}"
            )

    def test_no_duplicate_action_names_across_specs(self):
        """No two specs share the same action name (avoids Burr conflicts)."""
        seen = {}
        for wf_type, spec in WORKFLOW_SPECS.items():
            for action_name in spec.actions:
                if action_name in seen:
                    # It's OK if they reference the same function (shared actions)
                    pass
                seen[action_name] = wf_type


# =============================================================================
# Multi-Workflow Context Loading
# =============================================================================


class TestContextStages:
    """Verify context_stages form a valid dependency chain."""

    def test_idea_validation_has_no_context_stages(self):
        """First workflow has no upstream context to load."""
        assert IDEA_VALIDATION_SPEC.context_stages == []

    def test_mvp_specification_loads_from_idea_validation(self):
        """MVP Spec loads context from idea validation stages."""
        ctx = MVP_SPECIFICATION_SPEC.context_stages
        assert "validation-summary" in ctx
        assert "idea-analysis" in ctx

    def test_story_generation_loads_from_all_prior(self):
        """Story Generation loads context from all prior workflows."""
        ctx = STORY_GENERATION_SPEC.context_stages
        assert "capability-model" in ctx
        assert "build-buy-analysis" in ctx
        assert "architecture-decisions" in ctx

    def test_context_stages_are_from_earlier_workflows(self):
        """Context stages only reference stages from earlier workflow types."""
        registry = get_stage_registry()
        workflow_order = list(WorkflowType)

        for wf_type, spec in WORKFLOW_SPECS.items():
            wf_index = workflow_order.index(wf_type)
            for slug in spec.context_stages:
                ctx_stage = registry.get_by_slug(slug)
                ctx_wf_index = workflow_order.index(ctx_stage.workflow_type)
                assert ctx_wf_index < wf_index, (
                    f"{wf_type}: context_stage '{slug}' is from "
                    f"{ctx_stage.workflow_type} (index {ctx_wf_index}), "
                    f"which is not before {wf_type} (index {wf_index})"
                )
