"""Tests for claim origin taxonomy — internal vs. external classification.

Tests cover:
- External ratio extraction from risk assessment output
- Composite score extraction from validation summary JSON
- Claim origin post-validator logic
- Risk classification tool with external_unsupported_claims parameter
"""

import json
import sys
from unittest import mock

from haytham.workflow.validators.claim_origin import (
    _extract_composite_score,
    _extract_external_ratio,
    validate_claim_origin,
)


def _mock_reportlab():
    """Mock reportlab if absent (needed for package __init__ import chain)."""
    if "reportlab" not in sys.modules:
        rl_mock = mock.MagicMock()
        for sub in [
            "reportlab",
            "reportlab.lib",
            "reportlab.lib.colors",
            "reportlab.lib.pagesizes",
            "reportlab.lib.styles",
            "reportlab.lib.units",
            "reportlab.lib.enums",
            "reportlab.platypus",
            "reportlab.platypus.doctemplate",
            "reportlab.platypus.frames",
            "reportlab.platypus.paragraph",
            "reportlab.platypus.spacer",
            "reportlab.platypus.table",
            "reportlab.platypus.flowables",
            "reportlab.pdfgen",
        ]:
            sys.modules.setdefault(sub, rl_mock)


_mock_reportlab()
from haytham.agents.tools.risk_classification import classify_risk_level  # noqa: E402

# =============================================================================
# _extract_external_ratio
# =============================================================================


class TestExtractExternalRatio:
    """Test extraction of external claim support ratio from risk assessment."""

    def test_extracts_standard_format(self):
        text = "**External Validation:** 3/5 external claims supported (1 unsupported, 1 contradicted)."
        assert _extract_external_ratio(text) == (3, 5)

    def test_extracts_all_supported(self):
        text = "**External Validation:** 7/7 external claims supported (0 unsupported, 0 contradicted)."
        assert _extract_external_ratio(text) == (7, 7)

    def test_extracts_none_supported(self):
        text = "**External Validation:** 0/4 external claims supported (3 unsupported, 1 contradicted)."
        assert _extract_external_ratio(text) == (0, 4)

    def test_case_insensitive(self):
        text = "**external validation:** 2/6 External Claims Supported"
        assert _extract_external_ratio(text) == (2, 6)

    def test_embedded_in_larger_text(self):
        text = (
            "# Validation Results\n\n"
            "## Overall Risk Level: MEDIUM\n\n"
            "Some summary here.\n\n"
            "**Summary:** 12 claims analyzed: 8 supported, 2 partial, 1 unsupported, 1 contradicted.\n"
            "**External Validation:** 4/6 external claims supported (1 unsupported, 1 contradicted).\n\n"
            "## Identified Risks\n"
        )
        assert _extract_external_ratio(text) == (4, 6)

    def test_returns_none_when_missing(self):
        text = "**Summary:** 12 claims analyzed: 8 supported, 2 partial"
        assert _extract_external_ratio(text) is None

    def test_returns_none_for_empty_string(self):
        assert _extract_external_ratio("") is None

    def test_returns_none_for_malformed(self):
        text = "**External Validation:** many external claims supported"
        assert _extract_external_ratio(text) is None


# =============================================================================
# _extract_composite_score
# =============================================================================


class TestExtractCompositeScore:
    """Test extraction of composite score from validation summary JSON."""

    def test_extracts_score(self):
        data = {"go_no_go_assessment": {"composite_score": 3.8, "verdict": "GO"}}
        assert _extract_composite_score(json.dumps(data)) == 3.8

    def test_extracts_integer_score(self):
        data = {"go_no_go_assessment": {"composite_score": 4, "verdict": "GO"}}
        assert _extract_composite_score(json.dumps(data)) == 4

    def test_returns_none_for_missing_field(self):
        data = {"go_no_go_assessment": {"verdict": "GO"}}
        assert _extract_composite_score(json.dumps(data)) is None

    def test_returns_none_for_missing_assessment(self):
        data = {"executive_summary": "..."}
        assert _extract_composite_score(json.dumps(data)) is None

    def test_returns_none_for_invalid_json(self):
        assert _extract_composite_score("not json") is None

    def test_returns_none_for_empty_string(self):
        assert _extract_composite_score("") is None

    def test_returns_none_for_none_input(self):
        assert _extract_composite_score(None) is None


# =============================================================================
# validate_claim_origin (main validator)
# =============================================================================


class _MockState(dict):
    """Minimal dict-based mock for burr.core.State.get()."""

    def get(self, key, default=""):
        return super().get(key, default)


class TestValidateClaimOrigin:
    """Test the main validate_claim_origin validator."""

    def _make_output(self, composite_score: float) -> str:
        return json.dumps(
            {
                "go_no_go_assessment": {
                    "composite_score": composite_score,
                    "verdict": "GO" if composite_score > 3.0 else "NO-GO",
                }
            }
        )

    def _make_risk_assessment(self, supported: int, total: int) -> str:
        unsupported = total - supported
        return (
            f"**Summary:** {total + 5} claims analyzed.\n"
            f"**External Validation:** {supported}/{total} external claims supported "
            f"({unsupported} unsupported, 0 contradicted)."
        )

    def test_high_composite_weak_external_warns(self):
        """Composite > 3.5 with < 50% external support triggers warning."""
        output = self._make_output(4.0)
        state = _MockState(
            {
                "risk_assessment": self._make_risk_assessment(1, 5),
            }
        )
        warnings = validate_claim_origin(output, state)
        assert len(warnings) == 1
        assert "inflated by internal claims" in warnings[0]
        assert "1/5" in warnings[0]

    def test_high_composite_no_external_support_warns_thrice(self):
        """Composite > 3.5 with 0/4 external support triggers all three warnings."""
        output = self._make_output(4.0)
        state = _MockState(
            {
                "risk_assessment": self._make_risk_assessment(0, 4),
            }
        )
        warnings = validate_claim_origin(output, state)
        assert len(warnings) == 3
        assert "inflated by internal claims" in warnings[0]
        assert "no market evidence" in warnings[1]
        assert "Only 4 external claims" in warnings[2]

    def test_high_composite_strong_external_no_warning(self):
        """Composite > 3.5 with strong external support — no warnings."""
        output = self._make_output(4.2)
        state = _MockState(
            {
                "risk_assessment": self._make_risk_assessment(5, 6),
            }
        )
        warnings = validate_claim_origin(output, state)
        assert warnings == []

    def test_low_composite_weak_external_no_warning(self):
        """Low composite score — no warning even with weak external support."""
        output = self._make_output(2.5)
        state = _MockState(
            {
                "risk_assessment": self._make_risk_assessment(0, 5),
            }
        )
        warnings = validate_claim_origin(output, state)
        assert warnings == []

    def test_moderate_composite_no_external_warns(self):
        """Composite > 3.0 with 0/4 external support triggers both warnings."""
        output = self._make_output(3.2)
        state = _MockState(
            {
                "risk_assessment": self._make_risk_assessment(0, 4),
            }
        )
        warnings = validate_claim_origin(output, state)
        assert len(warnings) == 2
        assert "no market evidence" in warnings[0]
        assert "Only 4 external claims" in warnings[1]

    def test_moderate_composite_no_external_few_claims_low_count_only(self):
        """Composite > 3.0 with 0/2 external — only low-count warning (< 3 total skips no-evidence check)."""
        output = self._make_output(3.2)
        state = _MockState(
            {
                "risk_assessment": self._make_risk_assessment(0, 2),
            }
        )
        warnings = validate_claim_origin(output, state)
        assert len(warnings) == 1
        assert "Only 2 external claims" in warnings[0]

    def test_missing_risk_assessment_no_warning(self):
        """No warning when risk_assessment is missing from state."""
        output = self._make_output(4.5)
        state = _MockState({})
        warnings = validate_claim_origin(output, state)
        assert warnings == []

    def test_missing_composite_score_no_warning(self):
        """No warning when composite score can't be extracted."""
        output = json.dumps({"executive_summary": "..."})
        state = _MockState(
            {
                "risk_assessment": self._make_risk_assessment(1, 5),
            }
        )
        warnings = validate_claim_origin(output, state)
        assert warnings == []

    def test_zero_total_external_no_warning(self):
        """No warning when there are zero external claims (can't compute ratio)."""
        output = self._make_output(4.5)
        state = _MockState(
            {
                "risk_assessment": (
                    "**External Validation:** 0/0 external claims supported "
                    "(0 unsupported, 0 contradicted)."
                ),
            }
        )
        warnings = validate_claim_origin(output, state)
        assert warnings == []

    def test_invalid_output_no_warning(self):
        state = _MockState(
            {
                "risk_assessment": self._make_risk_assessment(1, 5),
            }
        )
        warnings = validate_claim_origin("not json", state)
        assert warnings == []

    def test_borderline_composite_3_5_no_inflation_warning(self):
        """Composite exactly 3.5 should NOT trigger the > 3.5 inflation check."""
        output = self._make_output(3.5)
        state = _MockState(
            {
                "risk_assessment": self._make_risk_assessment(1, 5),
            }
        )
        warnings = validate_claim_origin(output, state)
        assert warnings == []

    def test_borderline_external_50_pct_no_inflation_warning(self):
        """Exactly 50% external support should NOT trigger the < 0.5 check."""
        output = self._make_output(4.0)
        state = _MockState(
            {
                "risk_assessment": self._make_risk_assessment(3, 6),
            }
        )
        warnings = validate_claim_origin(output, state)
        assert warnings == []

    def test_low_external_count_warns(self):
        """Fewer than 5 external claims triggers insufficient-external warning."""
        output = self._make_output(3.0)
        state = _MockState(
            {
                "risk_assessment": self._make_risk_assessment(3, 4),
            }
        )
        warnings = validate_claim_origin(output, state)
        assert len(warnings) == 1
        assert "Only 4 external claims" in warnings[0]
        assert "at least 5 expected" in warnings[0]

    def test_exactly_five_external_no_low_count_warning(self):
        """Exactly 5 external claims should NOT trigger the < 5 check."""
        output = self._make_output(3.0)
        state = _MockState(
            {
                "risk_assessment": self._make_risk_assessment(4, 5),
            }
        )
        warnings = validate_claim_origin(output, state)
        assert warnings == []

    def test_low_external_count_combined_with_inflation(self):
        """Low external count warning can stack with inflation warning."""
        output = self._make_output(4.0)
        state = _MockState(
            {
                "risk_assessment": self._make_risk_assessment(1, 4),
            }
        )
        warnings = validate_claim_origin(output, state)
        assert any("inflated by internal claims" in w for w in warnings)
        assert any("Only 4 external claims" in w for w in warnings)


# =============================================================================
# classify_risk_level with external_unsupported_claims
# =============================================================================


class TestRiskClassificationExternalClaims:
    """Test the risk classification tool's external_unsupported_claims parameter."""

    def test_three_external_unsupported_returns_high(self):
        result = classify_risk_level(
            high_risk_count=0,
            medium_risk_count=0,
            unsupported_claims=3,
            contradicted_claims=0,
            external_unsupported_claims=3,
        )
        assert result == "HIGH"

    def test_four_external_unsupported_returns_high(self):
        result = classify_risk_level(
            high_risk_count=0,
            medium_risk_count=0,
            unsupported_claims=4,
            contradicted_claims=0,
            external_unsupported_claims=4,
        )
        assert result == "HIGH"

    def test_two_external_unsupported_returns_medium(self):
        result = classify_risk_level(
            high_risk_count=0,
            medium_risk_count=0,
            unsupported_claims=2,
            contradicted_claims=0,
            external_unsupported_claims=2,
        )
        assert result == "MEDIUM"

    def test_one_external_unsupported_falls_through(self):
        """1 external unsupported with no other risk factors → LOW."""
        result = classify_risk_level(
            high_risk_count=0,
            medium_risk_count=0,
            unsupported_claims=1,
            contradicted_claims=0,
            external_unsupported_claims=1,
        )
        assert result == "LOW"

    def test_zero_external_unsupported_backward_compat(self):
        """Default value (0) should not change existing behavior."""
        result = classify_risk_level(
            high_risk_count=0,
            medium_risk_count=0,
            unsupported_claims=2,
            contradicted_claims=0,
            external_unsupported_claims=0,
        )
        assert result == "LOW"

    def test_default_parameter_backward_compat(self):
        """Calling without external_unsupported_claims should work."""
        result = classify_risk_level(
            high_risk_count=0,
            medium_risk_count=0,
            unsupported_claims=2,
            contradicted_claims=0,
        )
        assert result == "LOW"

    def test_external_high_takes_precedence_over_medium_rules(self):
        """3 external unsupported → HIGH even if other factors say MEDIUM."""
        result = classify_risk_level(
            high_risk_count=0,
            medium_risk_count=2,
            unsupported_claims=3,
            contradicted_claims=0,
            external_unsupported_claims=3,
        )
        assert result == "HIGH"

    def test_existing_high_rules_still_work(self):
        """Existing HIGH rules remain functional."""
        assert classify_risk_level(2, 0, 0, 0, 0) == "HIGH"
        assert classify_risk_level(0, 0, 0, 2, 0) == "HIGH"
        assert classify_risk_level(1, 0, 2, 0, 0) == "HIGH"

    def test_existing_medium_rules_still_work(self):
        """Existing MEDIUM rules remain functional."""
        assert classify_risk_level(1, 0, 0, 0, 0) == "MEDIUM"
        assert classify_risk_level(0, 3, 0, 0, 0) == "MEDIUM"
        assert classify_risk_level(0, 0, 3, 0, 0) == "MEDIUM"

    def test_existing_low_rule_still_works(self):
        """LOW for no significant risks."""
        assert classify_risk_level(0, 0, 0, 0, 0) == "LOW"
        assert classify_risk_level(0, 2, 2, 0, 0) == "LOW"


# =============================================================================
# Critical claim escalation (Item 5)
# =============================================================================


class TestCriticalClaimEscalation:
    """Test contradicted_critical_claims parameter on classify_risk_level."""

    def test_one_contradicted_critical_returns_high(self):
        """One contradicted critical claim → HIGH regardless of other factors."""
        result = classify_risk_level(
            high_risk_count=0,
            medium_risk_count=0,
            unsupported_claims=0,
            contradicted_claims=0,
            external_unsupported_claims=0,
            contradicted_critical_claims=1,
        )
        assert result == "HIGH"

    def test_zero_contradicted_critical_no_effect(self):
        """Zero contradicted critical claims → falls through to other rules."""
        result = classify_risk_level(
            high_risk_count=0,
            medium_risk_count=0,
            unsupported_claims=0,
            contradicted_claims=0,
            external_unsupported_claims=0,
            contradicted_critical_claims=0,
        )
        assert result == "LOW"

    def test_critical_takes_precedence_over_low(self):
        """Contradicted critical overrides what would otherwise be LOW."""
        result = classify_risk_level(
            high_risk_count=0,
            medium_risk_count=1,
            unsupported_claims=0,
            contradicted_claims=0,
            external_unsupported_claims=0,
            contradicted_critical_claims=1,
        )
        assert result == "HIGH"

    def test_default_param_backward_compat(self):
        """Calling without contradicted_critical_claims works."""
        result = classify_risk_level(
            high_risk_count=0,
            medium_risk_count=0,
            unsupported_claims=0,
            contradicted_claims=0,
            external_unsupported_claims=0,
        )
        assert result == "LOW"

    def test_multiple_contradicted_critical_still_high(self):
        result = classify_risk_level(
            high_risk_count=0,
            medium_risk_count=0,
            unsupported_claims=0,
            contradicted_claims=0,
            external_unsupported_claims=0,
            contradicted_critical_claims=3,
        )
        assert result == "HIGH"
