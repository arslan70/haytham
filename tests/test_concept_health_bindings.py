"""Tests for concept health binding constraint validation."""

import json

from haytham.workflow.validators._scorecard_utils import extract_dimension_score
from haytham.workflow.validators.concept_health import (
    _extract_pain_clarity,
    validate_concept_health_bindings,
)

# =============================================================================
# _extract_pain_clarity
# =============================================================================


class TestExtractPainClarity:
    """Test _extract_pain_clarity from concept anchor string."""

    def test_extracts_clear(self):
        anchor = "- **Pain Clarity:** Clear"
        assert _extract_pain_clarity(anchor) == "Clear"

    def test_extracts_weak(self):
        anchor = "- **Pain Clarity:** Weak"
        assert _extract_pain_clarity(anchor) == "Weak"

    def test_extracts_ambiguous(self):
        anchor = "- **Pain Clarity:** Ambiguous"
        assert _extract_pain_clarity(anchor) == "Ambiguous"

    def test_returns_empty_when_missing(self):
        assert _extract_pain_clarity("no pain clarity here") == ""

    def test_returns_empty_for_empty_input(self):
        assert _extract_pain_clarity("") == ""

    def test_case_insensitive(self):
        anchor = "- **Pain Clarity:** weak"
        assert _extract_pain_clarity(anchor).lower() == "weak"


# =============================================================================
# _extract_problem_severity_score
# =============================================================================


class TestExtractProblemSeverityScore:
    """Test extract_dimension_score with 'problem severity' keyword."""

    def test_extracts_score(self):
        data = {
            "go_no_go_assessment": {
                "scorecard": [
                    {"dimension": "Problem Severity", "score": 4, "evidence": "..."},
                    {"dimension": "Market Opportunity", "score": 3, "evidence": "..."},
                ]
            }
        }
        assert extract_dimension_score(json.dumps(data), "problem severity") == 4

    def test_returns_none_for_missing_dimension(self):
        data = {
            "go_no_go_assessment": {
                "scorecard": [
                    {"dimension": "Market Opportunity", "score": 3, "evidence": "..."},
                ]
            }
        }
        assert extract_dimension_score(json.dumps(data), "problem severity") is None

    def test_returns_none_for_invalid_json(self):
        assert extract_dimension_score("not json", "problem severity") is None


# =============================================================================
# validate_concept_health_bindings (main validator)
# =============================================================================


class _MockState(dict):
    """Minimal dict-based mock for burr.core.State.get()."""

    def get(self, key, default=""):
        return super().get(key, default)


class TestValidateConceptHealthBindings:
    """Test the main validate_concept_health_bindings validator."""

    def _make_output(self, problem_severity_score: int) -> str:
        return json.dumps(
            {
                "go_no_go_assessment": {
                    "scorecard": [
                        {
                            "dimension": "Problem Severity",
                            "score": problem_severity_score,
                            "evidence": "...",
                        },
                        {"dimension": "Market Opportunity", "score": 3, "evidence": "..."},
                    ]
                }
            }
        )

    def test_weak_pain_high_score_warns(self):
        output = self._make_output(4)
        state = _MockState(
            {
                "concept_anchor_str": "- **Pain Clarity:** Weak",
            }
        )
        warnings = validate_concept_health_bindings(output, state)
        assert len(warnings) == 1
        assert "Pain Clarity is 'Weak'" in warnings[0]
        assert "must be ≤ 3" in warnings[0]

    def test_weak_pain_score_5_warns(self):
        output = self._make_output(5)
        state = _MockState(
            {
                "concept_anchor_str": "- **Pain Clarity:** Weak",
            }
        )
        warnings = validate_concept_health_bindings(output, state)
        assert len(warnings) == 1

    def test_clear_pain_high_score_no_warn(self):
        output = self._make_output(4)
        state = _MockState(
            {
                "concept_anchor_str": "- **Pain Clarity:** Clear",
            }
        )
        warnings = validate_concept_health_bindings(output, state)
        assert warnings == []

    def test_weak_pain_low_score_no_warn(self):
        output = self._make_output(3)
        state = _MockState(
            {
                "concept_anchor_str": "- **Pain Clarity:** Weak",
            }
        )
        warnings = validate_concept_health_bindings(output, state)
        assert warnings == []

    def test_ambiguous_pain_high_score_no_warn(self):
        """Ambiguous is not Weak — no binding constraint."""
        output = self._make_output(4)
        state = _MockState(
            {
                "concept_anchor_str": "- **Pain Clarity:** Ambiguous",
            }
        )
        warnings = validate_concept_health_bindings(output, state)
        assert warnings == []

    def test_missing_pain_clarity_no_warn(self):
        output = self._make_output(5)
        state = _MockState(
            {
                "concept_anchor_str": "No pain clarity here",
            }
        )
        warnings = validate_concept_health_bindings(output, state)
        assert warnings == []

    def test_missing_scorecard_no_warn(self):
        output = json.dumps({"go_no_go_assessment": {"scorecard": []}})
        state = _MockState(
            {
                "concept_anchor_str": "- **Pain Clarity:** Weak",
            }
        )
        warnings = validate_concept_health_bindings(output, state)
        assert warnings == []

    def test_invalid_output_returns_empty(self):
        state = _MockState(
            {
                "concept_anchor_str": "- **Pain Clarity:** Weak",
            }
        )
        warnings = validate_concept_health_bindings("not json", state)
        assert warnings == []
