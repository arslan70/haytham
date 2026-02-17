"""Tests for feedback cascade engine.

Tests cover:
- get_downstream_stages: finding stages after a given stage
- get_stages_to_revise: calculating full cascade scope
- is_cascade_needed: determining if cascading is required
- get_cascade_summary: generating human-readable summaries
"""

from haytham.feedback.cascade_engine import (
    get_downstream_stages,
    get_stages_to_revise,
    is_cascade_needed,
)

# Sample workflow stages for testing
IDEA_VALIDATION_STAGES = [
    "idea-analysis",
    "market-context",
    "risk-assessment",
    "validation-summary",
]

MVP_SPECIFICATION_STAGES = [
    "mvp-scope",
    "capability-model",
]


class TestGetDownstreamStages:
    """Tests for get_downstream_stages() function."""

    def test_first_stage_returns_all_remaining(self):
        """First stage should return all subsequent stages."""
        result = get_downstream_stages("idea-analysis", IDEA_VALIDATION_STAGES)
        assert result == ["market-context", "risk-assessment", "validation-summary"]

    def test_middle_stage_returns_subsequent(self):
        """Middle stage should return only stages after it."""
        result = get_downstream_stages("market-context", IDEA_VALIDATION_STAGES)
        assert result == ["risk-assessment", "validation-summary"]

    def test_last_stage_returns_empty(self):
        """Last stage should return empty list."""
        result = get_downstream_stages("validation-summary", IDEA_VALIDATION_STAGES)
        assert result == []

    def test_unknown_stage_returns_empty(self):
        """Unknown stage should return empty list."""
        result = get_downstream_stages("unknown-stage", IDEA_VALIDATION_STAGES)
        assert result == []

    def test_empty_stages_returns_empty(self):
        """Empty stage list should return empty list."""
        result = get_downstream_stages("idea-analysis", [])
        assert result == []

    def test_single_stage_workflow(self):
        """Single stage workflow should return empty for that stage."""
        result = get_downstream_stages("mvp-scope", ["mvp-scope"])
        assert result == []


class TestGetStagesToRevise:
    """Tests for get_stages_to_revise() function."""

    def test_single_affected_stage_includes_downstream(self):
        """Single affected stage should include all downstream stages."""
        result = get_stages_to_revise(["market-context"], IDEA_VALIDATION_STAGES)
        assert result == ["market-context", "risk-assessment", "validation-summary"]

    def test_earliest_stage_revises_all(self):
        """Affecting first stage should revise entire workflow."""
        result = get_stages_to_revise(["idea-analysis"], IDEA_VALIDATION_STAGES)
        assert result == IDEA_VALIDATION_STAGES

    def test_last_stage_only_revises_itself(self):
        """Affecting last stage should only revise that stage."""
        result = get_stages_to_revise(["validation-summary"], IDEA_VALIDATION_STAGES)
        assert result == ["validation-summary"]

    def test_multiple_affected_stages_uses_earliest(self):
        """Multiple affected stages should cascade from earliest."""
        result = get_stages_to_revise(
            ["risk-assessment", "market-context"],
            IDEA_VALIDATION_STAGES,
        )
        assert result == ["market-context", "risk-assessment", "validation-summary"]

    def test_empty_affected_returns_empty(self):
        """Empty affected stages should return empty list."""
        result = get_stages_to_revise([], IDEA_VALIDATION_STAGES)
        assert result == []

    def test_empty_workflow_returns_empty(self):
        """Empty workflow stages should return empty list."""
        result = get_stages_to_revise(["idea-analysis"], [])
        assert result == []

    def test_unknown_affected_stages_ignored(self):
        """Unknown affected stages should be ignored."""
        result = get_stages_to_revise(["unknown-stage"], IDEA_VALIDATION_STAGES)
        assert result == []

    def test_mixed_known_unknown_uses_known(self):
        """Mix of known and unknown should use earliest known."""
        result = get_stages_to_revise(
            ["unknown-stage", "risk-assessment"],
            IDEA_VALIDATION_STAGES,
        )
        assert result == ["risk-assessment", "validation-summary"]


class TestIsCascadeNeeded:
    """Tests for is_cascade_needed() function."""

    def test_first_stage_needs_cascade(self):
        """Affecting first stage should need cascade."""
        result = is_cascade_needed(["idea-analysis"], IDEA_VALIDATION_STAGES)
        assert result

    def test_middle_stage_needs_cascade(self):
        """Affecting middle stage should need cascade."""
        result = is_cascade_needed(["market-context"], IDEA_VALIDATION_STAGES)
        assert result

    def test_last_stage_no_cascade(self):
        """Affecting last stage should not need cascade."""
        result = is_cascade_needed(["validation-summary"], IDEA_VALIDATION_STAGES)
        assert not result

    def test_empty_affected_no_cascade(self):
        """Empty affected stages should not need cascade."""
        result = is_cascade_needed([], IDEA_VALIDATION_STAGES)
        assert not result

    def test_empty_workflow_no_cascade(self):
        """Empty workflow should not need cascade."""
        result = is_cascade_needed(["idea-analysis"], [])
        assert not result

    def test_single_stage_workflow_no_cascade(self):
        """Single stage workflow should not need cascade."""
        result = is_cascade_needed(["mvp-scope"], ["mvp-scope"])
        assert not result


# Note: get_cascade_summary tests are skipped because they require
# the full stage_registry which has complex dependencies.
# These would be tested in integration tests instead.
