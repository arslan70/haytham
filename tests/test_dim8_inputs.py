"""Tests for Dim 8 (Adoption & Engagement Risk) input consistency validation."""

import json

from haytham.workflow.stages.idea_validation import (
    _extract_switching_cost as extract_switching_cost_iv,
)
from haytham.workflow.validators._scorecard_utils import extract_dimension_score
from haytham.workflow.validators.dim8_inputs import (
    _extract_switching_cost,
    validate_dim8_inputs,
)

# =============================================================================
# _extract_switching_cost (dim8_inputs.py + idea_validation.py)
# =============================================================================


class TestExtractSwitchingCost:
    """Test _extract_switching_cost from competitor analysis output."""

    def test_extracts_high(self):
        output = "- **Switching Cost:** [High] — data migration is complex"
        assert _extract_switching_cost(output) == "High"

    def test_extracts_low(self):
        output = "- **Switching Cost:** [Low] — no data lock-in"
        assert _extract_switching_cost(output) == "Low"

    def test_extracts_medium(self):
        output = "- **Switching Cost:** [Medium] — some integrations"
        assert _extract_switching_cost(output) == "Medium"

    def test_extracts_without_brackets(self):
        output = "- **Switching Cost:** High — data migration"
        assert _extract_switching_cost(output) == "High"

    def test_case_insensitive(self):
        output = "- **Switching cost:** [high] — locked in"
        result = _extract_switching_cost(output)
        assert result.lower() == "high"

    def test_returns_empty_when_missing(self):
        assert _extract_switching_cost("no switching cost here") == ""

    def test_returns_empty_for_empty_input(self):
        assert _extract_switching_cost("") == ""

    def test_idea_validation_extractor_matches(self):
        """Verify idea_validation.py extractor produces same results."""
        output = "- **Switching Cost:** [High] — data migration"
        assert extract_switching_cost_iv(output) == "High"


# =============================================================================
# _extract_dim8_score
# =============================================================================


class TestExtractDim8Score:
    """Test extract_dimension_score with 'adoption' keyword."""

    def test_extracts_score(self):
        data = {
            "go_no_go_assessment": {
                "scorecard": [
                    {"dimension": "Problem Severity", "score": 4, "evidence": "..."},
                    {"dimension": "Adoption & Engagement Risk", "score": 3, "evidence": "..."},
                ]
            }
        }
        assert extract_dimension_score(json.dumps(data), "adoption") == 3

    def test_matches_partial_name(self):
        """Should match any dimension containing 'adoption'."""
        data = {
            "go_no_go_assessment": {
                "scorecard": [
                    {"dimension": "Adoption Risk", "score": 2, "evidence": "..."},
                ]
            }
        }
        assert extract_dimension_score(json.dumps(data), "adoption") == 2

    def test_returns_none_for_missing_dimension(self):
        data = {
            "go_no_go_assessment": {
                "scorecard": [
                    {"dimension": "Problem Severity", "score": 4, "evidence": "..."},
                ]
            }
        }
        assert extract_dimension_score(json.dumps(data), "adoption") is None

    def test_returns_none_for_invalid_json(self):
        assert extract_dimension_score("not json", "adoption") is None


# =============================================================================
# validate_dim8_inputs (main validator)
# =============================================================================


class _MockState(dict):
    """Minimal dict-based mock for burr.core.State.get()."""

    def get(self, key, default=""):
        return super().get(key, default)


class TestValidateDim8Inputs:
    """Test the main validate_dim8_inputs validator."""

    def _make_output(self, dim8_score: int) -> str:
        return json.dumps(
            {
                "go_no_go_assessment": {
                    "scorecard": [
                        {"dimension": "Problem Severity", "score": 4, "evidence": "..."},
                        {
                            "dimension": "Adoption & Engagement Risk",
                            "score": dim8_score,
                            "evidence": "...",
                        },
                    ]
                }
            }
        )

    def test_high_switching_cost_high_dim8_warns(self):
        output = self._make_output(4)
        state = _MockState(
            {
                "market_context": "- **Switching Cost:** [High] — deep integrations",
            }
        )
        warnings = validate_dim8_inputs(output, state)
        assert len(warnings) == 1
        assert "Switching Cost is 'High'" in warnings[0]

    def test_high_switching_cost_dim8_5_warns(self):
        output = self._make_output(5)
        state = _MockState(
            {
                "market_context": "- **Switching Cost:** [High] — data lock-in",
            }
        )
        warnings = validate_dim8_inputs(output, state)
        assert len(warnings) == 1

    def test_low_switching_cost_high_dim8_no_warn(self):
        output = self._make_output(5)
        state = _MockState(
            {
                "market_context": "- **Switching Cost:** [Low] — no lock-in",
            }
        )
        warnings = validate_dim8_inputs(output, state)
        assert warnings == []

    def test_high_switching_cost_low_dim8_no_warn(self):
        output = self._make_output(3)
        state = _MockState(
            {
                "market_context": "- **Switching Cost:** [High] — deep integrations",
            }
        )
        warnings = validate_dim8_inputs(output, state)
        assert warnings == []

    def test_medium_switching_cost_high_dim8_no_warn(self):
        output = self._make_output(4)
        state = _MockState(
            {
                "market_context": "- **Switching Cost:** [Medium] — some effort",
            }
        )
        warnings = validate_dim8_inputs(output, state)
        assert warnings == []

    def test_missing_switching_cost_no_warn(self):
        output = self._make_output(5)
        state = _MockState(
            {
                "market_context": "No switching cost tag",
            }
        )
        warnings = validate_dim8_inputs(output, state)
        assert warnings == []

    def test_missing_scorecard_no_warn(self):
        output = json.dumps({"go_no_go_assessment": {"scorecard": []}})
        state = _MockState(
            {
                "market_context": "- **Switching Cost:** [High] — locked in",
            }
        )
        warnings = validate_dim8_inputs(output, state)
        assert warnings == []

    def test_invalid_output_returns_empty(self):
        state = _MockState(
            {
                "market_context": "- **Switching Cost:** [High] — locked",
            }
        )
        warnings = validate_dim8_inputs("not json", state)
        assert warnings == []
