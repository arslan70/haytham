"""Tests for revenue evidence extraction and validation."""

import json

from haytham.workflow.validators._scorecard_utils import extract_dimension_score
from haytham.workflow.validators.revenue_evidence import (
    _extract_assumed_price,
    _extract_price_range,
    _extract_revenue_tag,
    _extract_wtp,
    validate_revenue_evidence,
)

# =============================================================================
# _extract_revenue_tag (revenue_evidence.py)
# =============================================================================


class TestExtractRevenueEvidenceTag:
    """Test _extract_revenue_tag from competitor analysis output."""

    def test_extracts_priced(self):
        output = "**Revenue Evidence Tag:** [Priced]"
        assert _extract_revenue_tag(output) == "Priced"

    def test_extracts_freemium_dominant(self):
        output = "**Revenue Evidence Tag:** [Freemium-Dominant]"
        assert _extract_revenue_tag(output) == "Freemium-Dominant"

    def test_extracts_no_pricing_found(self):
        output = "**Revenue Evidence Tag:** [No-Pricing-Found]"
        assert _extract_revenue_tag(output) == "No-Pricing-Found"

    def test_extracts_without_brackets(self):
        output = "**Revenue Evidence Tag:** Priced"
        assert _extract_revenue_tag(output) == "Priced"

    def test_case_insensitive(self):
        output = "**Revenue Evidence Tag:** [priced]"
        assert _extract_revenue_tag(output).lower() == "priced"

    def test_returns_empty_string_when_missing(self):
        output = "### 3. Competitive Positioning\n\n- No tag here"
        assert _extract_revenue_tag(output) == ""

    def test_returns_empty_string_for_empty_input(self):
        assert _extract_revenue_tag("") == ""

    def test_extracts_from_full_section(self):
        output = """\
### 3. Competitive Positioning & Revenue Evidence

- **Market structure:** Fragmented
- **Leaders:** Slack dominates workspace chat
- **Pricing benchmarks:** Slack $7.25/user/mo, Teams included in M365
  - Pricing model type: subscription
  - Price range across competitors: $0-$12.50/user/mo
- **Revenue Evidence Tag:** [Priced]
"""
        assert _extract_revenue_tag(output) == "Priced"


# =============================================================================
# Helper extraction functions (revenue_evidence.py)
# =============================================================================


class TestExtractRevenueTag:
    """Test _extract_revenue_tag from market_context."""

    def test_extracts_from_competitor_section(self):
        mc = "## Competitor Analysis\n\n**Revenue Evidence Tag:** [No-Pricing-Found]"
        assert _extract_revenue_tag(mc) == "No-Pricing-Found"

    def test_returns_empty_when_missing(self):
        assert _extract_revenue_tag("no tag here") == ""


class TestExtractWtp:
    """Test _extract_wtp from concept anchor string."""

    def test_extracts_present(self):
        anchor = "- **Willingness to Pay:** Present"
        assert _extract_wtp(anchor) == "Present"

    def test_extracts_absent(self):
        anchor = "- **Willingness to Pay:** Absent"
        assert _extract_wtp(anchor) == "Absent"

    def test_extracts_unclear(self):
        anchor = "- **Willingness to Pay:** Unclear"
        assert _extract_wtp(anchor) == "Unclear"

    def test_returns_empty_when_missing(self):
        assert _extract_wtp("no wtp here") == ""


class TestExtractPriceRange:
    """Test _extract_price_range from market context."""

    def test_extracts_standard_format(self):
        mc = "  - Price range: $0-$12.50/user/mo"
        assert _extract_price_range(mc) == (0.0, 12.50)

    def test_extracts_with_commas(self):
        mc = "  - Price range: $1,000-$5,000/year"
        assert _extract_price_range(mc) == (1000.0, 5000.0)

    def test_extracts_with_en_dash(self):
        mc = "  - Price range: $10\u201350/month"
        assert _extract_price_range(mc) == (10.0, 50.0)

    def test_returns_none_when_missing(self):
        assert _extract_price_range("no price range here") is None

    def test_returns_none_for_empty_input(self):
        assert _extract_price_range("") is None

    def test_returns_none_for_pricing_not_found(self):
        mc = '  - Price range: "pricing not found"'
        assert _extract_price_range(mc) is None

    def test_extracts_from_full_section(self):
        mc = """\
### 3. Competitive Positioning & Revenue Evidence

- **Market structure:** Fragmented
- **Pricing benchmarks:** Slack $7.25/user/mo
  - Pricing model type: subscription
  - Price range: $0-$12.50/user/mo
- **Revenue Evidence Tag:** [Priced]
"""
        assert _extract_price_range(mc) == (0.0, 12.50)


class TestExtractAssumedPrice:
    """Test _extract_assumed_price from validation summary JSON."""

    def test_extracts_from_revenue_model(self):
        data = {"lean_canvas": {"revenue_model": "Subscription at $29/month per user"}}
        assert _extract_assumed_price(json.dumps(data)) == 29.0

    def test_extracts_first_price(self):
        data = {"lean_canvas": {"revenue_model": "Freemium with $10/mo basic and $50/mo pro tiers"}}
        assert _extract_assumed_price(json.dumps(data)) == 10.0

    def test_returns_none_for_no_price(self):
        data = {"lean_canvas": {"revenue_model": "Advertising-based model"}}
        assert _extract_assumed_price(json.dumps(data)) is None

    def test_returns_none_for_missing_field(self):
        data = {"lean_canvas": {}}
        assert _extract_assumed_price(json.dumps(data)) is None

    def test_returns_none_for_invalid_json(self):
        assert _extract_assumed_price("not json") is None

    def test_returns_none_for_empty_string(self):
        assert _extract_assumed_price("") is None


class TestExtractRevenueScore:
    """Test extract_dimension_score with 'revenue' keyword."""

    def test_extracts_score(self):
        data = {
            "go_no_go_assessment": {
                "scorecard": [
                    {"dimension": "Problem Severity", "score": 4, "evidence": "..."},
                    {"dimension": "Revenue Viability", "score": 3, "evidence": "..."},
                ]
            }
        }
        assert extract_dimension_score(json.dumps(data), "revenue") == 3

    def test_returns_none_for_missing_dimension(self):
        data = {
            "go_no_go_assessment": {
                "scorecard": [
                    {"dimension": "Problem Severity", "score": 4, "evidence": "..."},
                ]
            }
        }
        assert extract_dimension_score(json.dumps(data), "revenue") is None

    def test_returns_none_for_invalid_json(self):
        assert extract_dimension_score("not json", "revenue") is None

    def test_returns_none_for_empty_string(self):
        assert extract_dimension_score("", "revenue") is None


# =============================================================================
# validate_revenue_evidence (main validator)
# =============================================================================


class _MockState(dict):
    """Minimal dict-based mock for burr.core.State.get()."""

    def get(self, key, default=""):
        return super().get(key, default)


class TestValidateRevenueEvidence:
    """Test the main validate_revenue_evidence validator."""

    def _make_output(self, revenue_score: int) -> str:
        return json.dumps(
            {
                "go_no_go_assessment": {
                    "scorecard": [
                        {"dimension": "Problem Severity", "score": 4, "evidence": "..."},
                        {
                            "dimension": "Revenue Viability",
                            "score": revenue_score,
                            "evidence": "...",
                        },
                        {"dimension": "Market Opportunity", "score": 3, "evidence": "..."},
                    ]
                }
            }
        )

    def test_high_score_no_pricing_warns(self):
        output = self._make_output(4)
        state = _MockState(
            {
                "market_context": "**Revenue Evidence Tag:** [No-Pricing-Found]",
                "concept_anchor_str": "- **Willingness to Pay:** Present",
            }
        )
        warnings = validate_revenue_evidence(output, state)
        assert len(warnings) == 1
        assert "competitor pricing was not found" in warnings[0]

    def test_high_score_absent_wtp_warns(self):
        output = self._make_output(4)
        state = _MockState(
            {
                "market_context": "**Revenue Evidence Tag:** [Priced]",
                "concept_anchor_str": "- **Willingness to Pay:** Absent",
            }
        )
        warnings = validate_revenue_evidence(output, state)
        assert len(warnings) == 1
        assert "WTP signal is 'Absent'" in warnings[0]

    def test_high_score_no_pricing_and_absent_wtp_warns_twice(self):
        output = self._make_output(5)
        state = _MockState(
            {
                "market_context": "**Revenue Evidence Tag:** [No-Pricing-Found]",
                "concept_anchor_str": "- **Willingness to Pay:** Absent",
            }
        )
        warnings = validate_revenue_evidence(output, state)
        assert len(warnings) == 2

    def test_low_score_with_strong_evidence_warns(self):
        output = self._make_output(2)
        state = _MockState(
            {
                "market_context": "**Revenue Evidence Tag:** [Priced]",
                "concept_anchor_str": "- **Willingness to Pay:** Present",
            }
        )
        warnings = validate_revenue_evidence(output, state)
        assert len(warnings) == 1
        assert "may be too low" in warnings[0]

    def test_consistent_high_score_no_warnings(self):
        output = self._make_output(4)
        state = _MockState(
            {
                "market_context": "**Revenue Evidence Tag:** [Priced]",
                "concept_anchor_str": "- **Willingness to Pay:** Present",
            }
        )
        warnings = validate_revenue_evidence(output, state)
        assert warnings == []

    def test_consistent_low_score_no_warnings(self):
        output = self._make_output(2)
        state = _MockState(
            {
                "market_context": "**Revenue Evidence Tag:** [No-Pricing-Found]",
                "concept_anchor_str": "- **Willingness to Pay:** Absent",
            }
        )
        warnings = validate_revenue_evidence(output, state)
        assert warnings == []

    def test_mid_score_no_warnings(self):
        output = self._make_output(3)
        state = _MockState(
            {
                "market_context": "**Revenue Evidence Tag:** [No-Pricing-Found]",
                "concept_anchor_str": "- **Willingness to Pay:** Present",
            }
        )
        warnings = validate_revenue_evidence(output, state)
        assert warnings == []

    def test_missing_upstream_signals_no_warnings(self):
        """No warnings when upstream signals are absent (can't validate)."""
        output = self._make_output(4)
        state = _MockState(
            {
                "market_context": "No tag here",
                "concept_anchor_str": "",
            }
        )
        warnings = validate_revenue_evidence(output, state)
        assert warnings == []

    def test_no_revenue_score_returns_empty(self):
        """No warnings when revenue score can't be extracted."""
        output = json.dumps({"go_no_go_assessment": {"scorecard": []}})
        state = _MockState(
            {
                "market_context": "**Revenue Evidence Tag:** [No-Pricing-Found]",
                "concept_anchor_str": "- **Willingness to Pay:** Absent",
            }
        )
        warnings = validate_revenue_evidence(output, state)
        assert warnings == []

    def test_assumed_price_above_2x_ceiling_warns(self):
        output = json.dumps(
            {
                "go_no_go_assessment": {
                    "scorecard": [
                        {"dimension": "Revenue Viability", "score": 3, "evidence": "..."},
                    ]
                },
                "lean_canvas": {"revenue_model": "Subscription at $100/month"},
            }
        )
        state = _MockState(
            {
                "market_context": (
                    "  - Price range: $10-$30/user/mo\n**Revenue Evidence Tag:** [Priced]"
                ),
                "concept_anchor_str": "- **Willingness to Pay:** Present",
            }
        )
        warnings = validate_revenue_evidence(output, state)
        assert any(">2x competitor ceiling" in w for w in warnings)

    def test_assumed_price_within_range_no_price_warn(self):
        output = json.dumps(
            {
                "go_no_go_assessment": {
                    "scorecard": [
                        {"dimension": "Revenue Viability", "score": 3, "evidence": "..."},
                    ]
                },
                "lean_canvas": {"revenue_model": "Subscription at $25/month"},
            }
        )
        state = _MockState(
            {
                "market_context": (
                    "  - Price range: $10-$30/user/mo\n**Revenue Evidence Tag:** [Priced]"
                ),
                "concept_anchor_str": "- **Willingness to Pay:** Present",
            }
        )
        warnings = validate_revenue_evidence(output, state)
        assert not any(">2x competitor ceiling" in w for w in warnings)

    def test_missing_price_range_no_price_warn(self):
        output = self._make_output(3)
        state = _MockState(
            {
                "market_context": "**Revenue Evidence Tag:** [Priced]",
                "concept_anchor_str": "- **Willingness to Pay:** Present",
            }
        )
        warnings = validate_revenue_evidence(output, state)
        assert not any(">2x competitor ceiling" in w for w in warnings)

    def test_invalid_output_returns_empty(self):
        state = _MockState({})
        warnings = validate_revenue_evidence("not json", state)
        assert warnings == []
