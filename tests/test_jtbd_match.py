"""Tests for JTBD match extraction and validation."""

import json

from haytham.workflow.validators._scorecard_utils import extract_dimension_score
from haytham.workflow.validators.jtbd_match import (
    _extract_jtbd_matches,
    validate_jtbd_match,
)

# =============================================================================
# _extract_jtbd_matches (jtbd_match.py)
# =============================================================================


class TestExtractJtbdMatches:
    """Test _extract_jtbd_matches from competitor analysis output."""

    def test_extracts_standard_format(self):
        output = (
            "- **JTBD Match:** [Direct]\n"
            "- **JTBD Match:** [Adjacent]\n"
            "- **JTBD Match:** [Unrelated]\n"
        )
        assert _extract_jtbd_matches(output) == ["Direct", "Adjacent", "Unrelated"]

    def test_extracts_without_brackets(self):
        output = "- **JTBD Match:** Direct\n- **JTBD Match:** Adjacent\n"
        assert _extract_jtbd_matches(output) == ["Direct", "Adjacent"]

    def test_case_insensitive(self):
        output = "- **JTBD Match:** [direct]\n- **JTBD Match:** [ADJACENT]\n"
        result = _extract_jtbd_matches(output)
        assert len(result) == 2
        assert result[0].lower() == "direct"
        assert result[1].lower() == "adjacent"

    def test_returns_empty_when_missing(self):
        output = "### 1. Competitor Identification\n\nNo JTBD tags here"
        assert _extract_jtbd_matches(output) == []

    def test_returns_empty_for_empty_input(self):
        assert _extract_jtbd_matches("") == []

    def test_extracts_from_full_competitor_block(self):
        output = """\
**Competitor A** https://example.com
- **What they offer:** A thing
- **Traction:** 10K users [estimate]
- **Target segment:** Developers
- **JTBD Match:** [Direct]

**Competitor B** https://example2.com
- **What they offer:** Another thing
- **Target segment:** Enterprises
- **JTBD Match:** [Adjacent]
"""
        assert _extract_jtbd_matches(output) == ["Direct", "Adjacent"]


# =============================================================================
# _extract_market_opportunity_score (jtbd_match.py)
# =============================================================================


class TestExtractMarketOpportunityScore:
    """Test extract_dimension_score with 'market opportunity' keyword."""

    def test_extracts_score(self):
        data = {
            "go_no_go_assessment": {
                "scorecard": [
                    {"dimension": "Problem Severity", "score": 4, "evidence": "..."},
                    {"dimension": "Market Opportunity", "score": 3, "evidence": "..."},
                ]
            }
        }
        assert extract_dimension_score(json.dumps(data), "market opportunity") == 3

    def test_returns_none_for_missing_dimension(self):
        data = {
            "go_no_go_assessment": {
                "scorecard": [
                    {"dimension": "Problem Severity", "score": 4, "evidence": "..."},
                ]
            }
        }
        assert extract_dimension_score(json.dumps(data), "market opportunity") is None

    def test_returns_none_for_invalid_json(self):
        assert extract_dimension_score("not json", "market opportunity") is None

    def test_returns_none_for_empty_string(self):
        assert extract_dimension_score("", "market opportunity") is None


# =============================================================================
# validate_jtbd_match (main validator)
# =============================================================================


class _MockState(dict):
    """Minimal dict-based mock for burr.core.State.get()."""

    def get(self, key, default=""):
        return super().get(key, default)


class TestValidateJtbdMatch:
    """Test the main validate_jtbd_match validator."""

    def _make_output(self, market_opportunity_score: int) -> str:
        return json.dumps(
            {
                "go_no_go_assessment": {
                    "scorecard": [
                        {"dimension": "Problem Severity", "score": 4, "evidence": "..."},
                        {
                            "dimension": "Market Opportunity",
                            "score": market_opportunity_score,
                            "evidence": "...",
                        },
                    ]
                }
            }
        )

    def test_all_adjacent_high_score_warns(self):
        output = self._make_output(4)
        state = _MockState(
            {
                "market_context": (
                    "- **JTBD Match:** [Adjacent]\n"
                    "- **JTBD Match:** [Adjacent]\n"
                    "- **JTBD Match:** [Unrelated]\n"
                ),
            }
        )
        warnings = validate_jtbd_match(output, state)
        assert len(warnings) == 1
        assert "no competitors solve the same core JTBD" in warnings[0]

    def test_all_direct_high_score_no_warn(self):
        output = self._make_output(5)
        state = _MockState(
            {
                "market_context": (
                    "- **JTBD Match:** [Direct]\n"
                    "- **JTBD Match:** [Direct]\n"
                    "- **JTBD Match:** [Adjacent]\n"
                ),
            }
        )
        warnings = validate_jtbd_match(output, state)
        assert warnings == []

    def test_no_matches_no_warn(self):
        output = self._make_output(5)
        state = _MockState(
            {
                "market_context": "No JTBD tags here",
            }
        )
        warnings = validate_jtbd_match(output, state)
        assert warnings == []

    def test_mixed_with_one_direct_no_warn(self):
        output = self._make_output(4)
        state = _MockState(
            {
                "market_context": (
                    "- **JTBD Match:** [Direct]\n"
                    "- **JTBD Match:** [Adjacent]\n"
                    "- **JTBD Match:** [Unrelated]\n"
                ),
            }
        )
        warnings = validate_jtbd_match(output, state)
        assert warnings == []

    def test_all_adjacent_low_score_no_warn(self):
        output = self._make_output(3)
        state = _MockState(
            {
                "market_context": ("- **JTBD Match:** [Adjacent]\n- **JTBD Match:** [Unrelated]\n"),
            }
        )
        warnings = validate_jtbd_match(output, state)
        assert warnings == []

    def test_single_competitor_no_warn(self):
        """Not enough competitors to be meaningful."""
        output = self._make_output(5)
        state = _MockState(
            {
                "market_context": "- **JTBD Match:** [Adjacent]\n",
            }
        )
        warnings = validate_jtbd_match(output, state)
        assert warnings == []
