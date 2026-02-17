"""Tests for haytham.workflow.entry_validators.

Covers validator registry, get_next_available_workflow ordering,
individual validator logic, and the 3-tier workflow completion check.
"""

import json
from pathlib import Path
from unittest import mock

import pytest

from haytham.workflow.entry_validators import (
    EntryConditionResult,
    get_available_workflows,
    get_entry_validator,
    get_next_available_workflow,
    validate_workflow_entry,
)
from haytham.workflow.entry_validators.base import (
    MIN_STAGE_OUTPUT_LENGTH,
    SessionStateAdapter,
    WorkflowEntryValidator,
)
from haytham.workflow.stage_registry import WorkflowType

# =============================================================================
# Helpers
# =============================================================================


def _make_session_manager(tmp_path: Path, **overrides):
    """Create a mock SessionManager with controllable state."""
    sm = mock.MagicMock()
    sm.session_dir = tmp_path
    sm.run_tracker = mock.MagicMock()
    sm.run_tracker.is_workflow_complete = mock.Mock(return_value=False)
    sm.load_session = mock.Mock(return_value=None)
    sm.load_stage_output = mock.Mock(return_value=None)

    # Apply overrides
    for key, value in overrides.items():
        setattr(sm, key, value)

    return sm


def _substantive_output() -> str:
    """Return a string that passes MIN_STAGE_OUTPUT_LENGTH check."""
    return "A" * (MIN_STAGE_OUTPUT_LENGTH + 10)


# =============================================================================
# Validator Registry
# =============================================================================


class TestValidatorRegistry:
    """Tests for the _VALIDATORS registry and factory function."""

    def test_all_workflow_types_have_validators(self):
        """Every WorkflowType has a registered validator."""
        for wf_type in WorkflowType:
            validator = get_entry_validator(wf_type, mock.MagicMock())
            assert isinstance(validator, WorkflowEntryValidator)

    def test_unknown_workflow_type_raises(self):
        with pytest.raises(ValueError, match="No validator registered"):
            get_entry_validator("nonexistent", mock.MagicMock())

    def test_validate_workflow_entry_convenience(self):
        """Convenience function delegates to validator.validate()."""
        sm = mock.MagicMock()
        sm.session_dir = Path("/fake")
        sm.run_tracker = mock.MagicMock()
        sm.run_tracker.is_workflow_complete = mock.Mock(return_value=False)
        sm.load_session = mock.Mock(return_value=None)
        sm.load_stage_output = mock.Mock(return_value=None)

        result = validate_workflow_entry(WorkflowType.IDEA_VALIDATION, sm)
        assert isinstance(result, EntryConditionResult)


# =============================================================================
# IdeaValidationEntryValidator
# =============================================================================


class TestIdeaValidationValidator:
    """Tests for the starting workflow validator."""

    def test_always_passes(self, tmp_path):
        """Idea validation is the starting workflow, always passes."""
        sm = _make_session_manager(tmp_path)
        result = validate_workflow_entry(WorkflowType.IDEA_VALIDATION, sm)
        assert result.passed is True

    def test_warns_when_no_system_goal(self, tmp_path):
        """Warns but still passes when system_goal is missing."""
        sm = _make_session_manager(tmp_path)
        sm.load_session.return_value = None
        result = validate_workflow_entry(WorkflowType.IDEA_VALIDATION, sm)
        assert result.passed is True


# =============================================================================
# MVPSpecificationEntryValidator
# =============================================================================


class TestMVPSpecificationValidator:
    """Tests for MVP Specification entry conditions."""

    def test_passes_when_all_conditions_met(self, tmp_path):
        """Passes when idea-validation is complete with GO recommendation."""
        sm = _make_session_manager(tmp_path)
        sm.run_tracker.is_workflow_complete = mock.Mock(
            side_effect=lambda slug: slug == "idea-validation"
        )
        sm.load_stage_output = mock.Mock(
            side_effect=lambda slug: _substantive_output()
            if slug in ("validation-summary", "risk-assessment")
            else None
        )

        # Create recommendation.json
        rec_path = tmp_path / "recommendation.json"
        rec_path.write_text(json.dumps({"recommendation": "GO"}))

        result = validate_workflow_entry(WorkflowType.MVP_SPECIFICATION, sm)
        assert result.passed is True
        assert result.recommendation == "GO"

    def test_fails_when_idea_validation_incomplete(self, tmp_path):
        """Fails when idea-validation workflow is not complete."""
        sm = _make_session_manager(tmp_path)
        sm.run_tracker.is_workflow_complete = mock.Mock(return_value=False)
        sm.load_session.return_value = None

        result = validate_workflow_entry(WorkflowType.MVP_SPECIFICATION, sm)
        assert result.passed is False

    def test_fails_on_no_go_recommendation(self, tmp_path):
        """Fails when recommendation is NO-GO (but can be overridden)."""
        sm = _make_session_manager(tmp_path)
        sm.run_tracker.is_workflow_complete = mock.Mock(
            side_effect=lambda slug: slug == "idea-validation"
        )
        sm.load_stage_output = mock.Mock(return_value=_substantive_output())

        rec_path = tmp_path / "recommendation.json"
        rec_path.write_text(json.dumps({"recommendation": "NO-GO"}))

        result = validate_workflow_entry(WorkflowType.MVP_SPECIFICATION, sm)
        assert result.passed is False
        assert result.can_override is True
        assert result.recommendation == "NO-GO"

    def test_no_go_with_force_override_passes(self, tmp_path):
        """NO-GO recommendation passes when force_override=True."""
        sm = _make_session_manager(tmp_path)
        sm.run_tracker.is_workflow_complete = mock.Mock(
            side_effect=lambda slug: slug == "idea-validation"
        )
        sm.load_stage_output = mock.Mock(return_value=_substantive_output())

        rec_path = tmp_path / "recommendation.json"
        rec_path.write_text(json.dumps({"recommendation": "NO-GO"}))

        result = validate_workflow_entry(WorkflowType.MVP_SPECIFICATION, sm, force_override=True)
        assert result.passed is True

    def test_pivot_recommendation_passes(self, tmp_path):
        """PIVOT recommendation is treated as passing."""
        sm = _make_session_manager(tmp_path)
        sm.run_tracker.is_workflow_complete = mock.Mock(
            side_effect=lambda slug: slug == "idea-validation"
        )
        sm.load_stage_output = mock.Mock(return_value=_substantive_output())

        rec_path = tmp_path / "recommendation.json"
        rec_path.write_text(json.dumps({"recommendation": "PIVOT"}))

        result = validate_workflow_entry(WorkflowType.MVP_SPECIFICATION, sm)
        assert result.passed is True
        assert result.recommendation == "PIVOT"


# =============================================================================
# 3-Tier Workflow Completion Check
# =============================================================================


class TestWorkflowCompletionCheck:
    """Tests for the _check_workflow_complete 3-tier fallback."""

    def test_tier1_run_tracker(self, tmp_path):
        """Tier 1: run_tracker.is_workflow_complete returns True."""
        sm = _make_session_manager(tmp_path)
        sm.run_tracker.is_workflow_complete = mock.Mock(
            side_effect=lambda slug: slug == "idea-validation"
        )

        validator = get_entry_validator(WorkflowType.MVP_SPECIFICATION, sm)
        assert validator._check_workflow_complete("idea-validation", "validation-summary")

    def test_tier2_stage_status_fallback(self, tmp_path):
        """Tier 2: stage_statuses in session show completed."""
        sm = _make_session_manager(tmp_path)
        sm.run_tracker.is_workflow_complete = mock.Mock(return_value=False)
        sm.load_session.return_value = {"stage_statuses": {"validation-summary": "completed"}}

        validator = get_entry_validator(WorkflowType.MVP_SPECIFICATION, sm)
        result = validator._check_workflow_complete("idea-validation", "validation-summary")
        assert result is True
        assert any("stage is complete" in w for w in validator.warnings)

    def test_tier3_lock_file_fallback(self, tmp_path):
        """Tier 3: lock file exists."""
        sm = _make_session_manager(tmp_path)
        sm.run_tracker.is_workflow_complete = mock.Mock(return_value=False)
        sm.load_session.return_value = None

        # Create lock file
        lock_file = tmp_path / ".idea-validation.locked"
        lock_file.write_text("{}")

        validator = get_entry_validator(WorkflowType.MVP_SPECIFICATION, sm)
        result = validator._check_workflow_complete("idea-validation", "validation-summary")
        assert result is True
        assert any("accepted by user" in w for w in validator.warnings)

    def test_all_tiers_fail(self, tmp_path):
        """All 3 tiers fail: workflow is not complete."""
        sm = _make_session_manager(tmp_path)
        sm.run_tracker.is_workflow_complete = mock.Mock(return_value=False)
        sm.load_session.return_value = None

        validator = get_entry_validator(WorkflowType.MVP_SPECIFICATION, sm)
        result = validator._check_workflow_complete("idea-validation", "validation-summary")
        assert result is False
        assert any("not complete" in e for e in validator.errors)

    def test_legacy_slug_check(self, tmp_path):
        """Legacy slugs are checked as fallback."""
        sm = _make_session_manager(tmp_path)
        sm.run_tracker.is_workflow_complete = mock.Mock(
            side_effect=lambda slug: slug == "legacy-slug"
        )

        validator = get_entry_validator(WorkflowType.MVP_SPECIFICATION, sm)
        result = validator._check_workflow_complete(
            "idea-validation", "validation-summary", legacy_slugs=("legacy-slug",)
        )
        assert result is True


# =============================================================================
# get_next_available_workflow
# =============================================================================


class TestGetNextAvailableWorkflow:
    """Tests for workflow sequencing."""

    def test_returns_idea_validation_first(self, tmp_path):
        """First available workflow is always IDEA_VALIDATION."""
        sm = _make_session_manager(tmp_path)
        sm.run_tracker.is_workflow_complete = mock.Mock(return_value=False)

        result = get_next_available_workflow(sm)
        assert result == WorkflowType.IDEA_VALIDATION

    def test_skips_completed_workflows(self, tmp_path):
        """Completed workflows are skipped."""
        sm = _make_session_manager(tmp_path)

        def is_complete(slug):
            return slug == "idea-validation"

        sm.run_tracker.is_workflow_complete = mock.Mock(side_effect=is_complete)
        sm.load_stage_output = mock.Mock(return_value=_substantive_output())

        # Create recommendation.json so MVP can pass
        rec_path = tmp_path / "recommendation.json"
        rec_path.write_text(json.dumps({"recommendation": "GO"}))

        result = get_next_available_workflow(sm)
        assert result == WorkflowType.MVP_SPECIFICATION

    def test_returns_none_when_all_complete(self, tmp_path):
        """Returns None when all workflows are complete."""
        sm = _make_session_manager(tmp_path)
        sm.run_tracker.is_workflow_complete = mock.Mock(return_value=True)

        result = get_next_available_workflow(sm)
        assert result is None


# =============================================================================
# get_available_workflows
# =============================================================================


class TestGetAvailableWorkflows:
    """Tests for listing available workflows."""

    def test_idea_validation_always_available(self, tmp_path):
        """IDEA_VALIDATION is always available (no prerequisites)."""
        sm = _make_session_manager(tmp_path)
        available = get_available_workflows(sm)
        assert WorkflowType.IDEA_VALIDATION in available

    def test_mvp_spec_not_available_without_idea_validation(self, tmp_path):
        """MVP_SPECIFICATION is not available when idea-validation is incomplete."""
        sm = _make_session_manager(tmp_path)
        sm.run_tracker.is_workflow_complete = mock.Mock(return_value=False)
        sm.load_session.return_value = None

        available = get_available_workflows(sm)
        assert WorkflowType.MVP_SPECIFICATION not in available


# =============================================================================
# SessionStateAdapter
# =============================================================================


class TestSessionStateAdapter:
    """Tests for the State-like adapter used by phase verifiers."""

    def test_maps_state_keys_to_stage_slugs(self, tmp_path):
        """State keys are correctly mapped to stage output slugs."""
        sm = _make_session_manager(tmp_path)
        sm.load_stage_output = mock.Mock(return_value="Loaded output")

        adapter = SessionStateAdapter(sm)
        result = adapter.get("idea_analysis")

        sm.load_stage_output.assert_called_with("idea-analysis")
        assert result == "Loaded output"

    def test_caches_loaded_values(self, tmp_path):
        """Repeated get() calls use cache, not re-loading."""
        sm = _make_session_manager(tmp_path)
        sm.load_stage_output = mock.Mock(return_value="Cached output")

        adapter = SessionStateAdapter(sm)
        adapter.get("idea_analysis")
        adapter.get("idea_analysis")

        # Only called once due to caching
        sm.load_stage_output.assert_called_once()

    def test_returns_default_for_unknown_key(self, tmp_path):
        """Unknown keys return the provided default."""
        sm = _make_session_manager(tmp_path)
        adapter = SessionStateAdapter(sm)

        result = adapter.get("unknown_key", "fallback")
        assert result == "fallback"

    def test_returns_default_for_empty_stage_output(self, tmp_path):
        """Empty stage output returns the default value."""
        sm = _make_session_manager(tmp_path)
        sm.load_stage_output = mock.Mock(return_value=None)

        adapter = SessionStateAdapter(sm)
        result = adapter.get("idea_analysis", "default_val")
        assert result == "default_val"

    def test_loads_concept_anchor(self, tmp_path):
        """Concept anchor is loaded from the separate JSON file."""
        sm = _make_session_manager(tmp_path)

        anchor_file = tmp_path / "concept_anchor.json"
        anchor_file.write_text(
            json.dumps(
                {
                    "anchor": {"intent": "scheduling"},
                    "anchor_str": "Core: scheduling app",
                }
            )
        )

        adapter = SessionStateAdapter(sm)
        assert adapter.get("concept_anchor_str") == "Core: scheduling app"
        assert adapter.get("concept_anchor") == {"intent": "scheduling"}

    def test_system_goal_from_session(self, tmp_path):
        """system_goal is loaded from the session."""
        sm = _make_session_manager(tmp_path)
        sm.load_session.return_value = {"system_goal": "My SaaS idea"}

        adapter = SessionStateAdapter(sm)
        assert adapter.get("system_goal") == "My SaaS idea"
