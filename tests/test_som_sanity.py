"""Tests for SOM sanity validator.

Covers:
- SOM >= $1M with small-scale indicators → warning
- SOM with enterprise-scale idea → no warning
- No SOM figure + Market Opportunity >= 4 → warning
- No SOM figure + Market Opportunity <= 3 → no warning
- SOM > 10x SAM → warning
"""

import json
from unittest.mock import MagicMock

from haytham.workflow.validators.som_sanity import validate_som_sanity


def _make_state(system_goal: str = "", market_context: str = "") -> MagicMock:
    """Create a mock Burr State with .get() support."""
    state = MagicMock()
    data = {
        "system_goal": system_goal,
        "market_context": market_context,
    }
    state.get = lambda key, default="": data.get(key, default)
    return state


def _make_output(market_opp_score: int = 3) -> str:
    """Create a minimal validation summary JSON with a Market Opportunity score."""
    return json.dumps(
        {
            "go_no_go_assessment": {
                "scorecard": [
                    {"dimension": "Market Opportunity", "score": market_opp_score},
                ],
            },
        }
    )


class TestSOMSmallScaleWarning:
    def test_som_with_existing_patients(self):
        """SOM $6.1M + 'existing patients' in system_goal → warning."""
        state = _make_state(
            system_goal="A platform for a solo psychologist to track existing patients and grow practice",
            market_context="**SOM:** $6.1 million based on addressable segment",
        )
        warnings = validate_som_sanity(_make_output(), state)
        assert len(warnings) >= 1
        assert any("implausible" in w for w in warnings)

    def test_som_with_enterprise_saas(self):
        """SOM $50M + 'enterprise SaaS platform' → no warning."""
        state = _make_state(
            system_goal="An enterprise SaaS platform for supply chain optimization",
            market_context="**SOM:** $50 million based on mid-market segment",
        )
        warnings = validate_som_sanity(_make_output(), state)
        assert not any("implausible" in w for w in warnings)

    def test_som_with_solo_practitioner(self):
        """SOM $2M + 'solo' practitioner → warning."""
        state = _make_state(
            system_goal="Solo practitioner wellness coaching app",
            market_context="**SOM:** $2M",
        )
        warnings = validate_som_sanity(_make_output(), state)
        assert any("implausible" in w for w in warnings)

    def test_som_with_single_location(self):
        """SOM $5M + 'single location' → warning."""
        state = _make_state(
            system_goal="A booking system for a single location dental clinic",
            market_context="**SOM:** $5 million",
        )
        warnings = validate_som_sanity(_make_output(), state)
        assert any("implausible" in w for w in warnings)


class TestSOMAbsentWarning:
    def test_no_som_high_market_opp(self):
        """No SOM figure + Market Opportunity >= 4 → warning."""
        state = _make_state(
            market_context="The mental health market is estimated to be large.",
        )
        warnings = validate_som_sanity(_make_output(market_opp_score=4), state)
        assert any("quantitative" in w for w in warnings)

    def test_no_som_low_market_opp(self):
        """No SOM figure + Market Opportunity <= 3 → no warning."""
        state = _make_state(
            market_context="The market opportunity is limited.",
        )
        warnings = validate_som_sanity(_make_output(market_opp_score=3), state)
        assert not any("quantitative" in w for w in warnings)

    def test_no_som_score_5_warns(self):
        """No SOM + Market Opportunity 5 → warning."""
        state = _make_state(
            market_context="Market is huge with explosive growth.",
        )
        warnings = validate_som_sanity(_make_output(market_opp_score=5), state)
        assert any("quantitative" in w for w in warnings)


class TestSOMExceedsSAM:
    def test_som_exceeds_sam(self):
        """SOM > 10x SAM → warning."""
        state = _make_state(
            system_goal="An AI tutoring platform",
            market_context="**SAM:** $5 million\n**SOM:** $60 million",
        )
        warnings = validate_som_sanity(_make_output(), state)
        assert any("exceeds SAM" in w for w in warnings)

    def test_som_within_sam(self):
        """SOM within SAM range → no warning."""
        state = _make_state(
            system_goal="An AI tutoring platform",
            market_context="**SAM:** $500 million\n**SOM:** $50 million",
        )
        warnings = validate_som_sanity(_make_output(), state)
        assert not any("exceeds SAM" in w for w in warnings)

    def test_som_exactly_10x_sam_no_warning(self):
        """SOM exactly 10x SAM → no warning (boundary)."""
        state = _make_state(
            system_goal="An AI tutoring platform",
            market_context="**SAM:** $5 million\n**SOM:** $50 million",
        )
        warnings = validate_som_sanity(_make_output(), state)
        assert not any("exceeds SAM" in w for w in warnings)


class TestSOMParsing:
    def test_billion_suffix(self):
        """SOM with 'billion' suffix parses correctly."""
        state = _make_state(
            system_goal="Enterprise cloud platform",
            market_context="**SOM:** $1.5 billion",
        )
        # No small-scale indicators, so no implausibility warning
        warnings = validate_som_sanity(_make_output(), state)
        assert not any("implausible" in w for w in warnings)

    def test_b_suffix(self):
        """SOM with 'B' suffix parses correctly."""
        state = _make_state(
            system_goal="Enterprise cloud platform",
            market_context="**SOM:** $2B",
        )
        warnings = validate_som_sanity(_make_output(), state)
        assert not any("implausible" in w for w in warnings)

    def test_comma_in_number(self):
        """SOM with comma formatting parses correctly."""
        state = _make_state(
            system_goal="Solo therapist with existing patients",
            market_context="**SOM:** $1,200 million",
        )
        warnings = validate_som_sanity(_make_output(), state)
        assert any("implausible" in w for w in warnings)
