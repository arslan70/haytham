"""Tests for competitor analysis recording tools and integration points."""

from unittest.mock import MagicMock

import pytest

from haytham.agents.tools.competitor_recording import (
    clear_competitor_accumulator,
    get_competitor_data,
    record_competitor,
    record_market_positioning,
    record_sentiment,
)
from haytham.workflow.stages.idea_validation import (
    extract_competitor_data_processor,
)


@pytest.fixture(autouse=True)
def _clean_accumulator():
    """Reset accumulator before each test."""
    clear_competitor_accumulator()
    yield
    clear_competitor_accumulator()


# ── record_competitor ────────────────────────────────────────────────────


class TestRecordCompetitor:
    def test_valid_direct(self):
        result = record_competitor(
            name="Acme",
            url="https://acme.com",
            traction="10k users",
            target_segment="SMBs",
            jtbd_match="Direct",
        )
        assert "Recorded competitor 'Acme'" in result
        data = get_competitor_data()
        assert len(data["competitors"]) == 1
        assert data["competitors"][0]["jtbd_match"] == "Direct"

    def test_valid_adjacent(self):
        result = record_competitor(
            name="Beta",
            url="https://beta.io",
            traction="5k downloads",
            target_segment="Consumers",
            jtbd_match="Adjacent",
        )
        assert "Adjacent" in result

    def test_valid_unrelated(self):
        result = record_competitor(
            name="Gamma",
            url="https://gamma.dev",
            traction="$2M funding",
            target_segment="Enterprise",
            jtbd_match="Unrelated",
        )
        assert "Unrelated" in result

    def test_invalid_jtbd_match(self):
        result = record_competitor(
            name="Bad",
            url="https://bad.com",
            traction="?",
            target_segment="?",
            jtbd_match="Somewhat",
        )
        assert "REJECTED" in result
        assert get_competitor_data()["competitors"] == []

    def test_multiple_competitors(self):
        for i in range(3):
            record_competitor(
                name=f"C{i}",
                url=f"https://c{i}.com",
                traction="",
                target_segment="All",
                jtbd_match="Direct",
            )
        assert len(get_competitor_data()["competitors"]) == 3


# ── record_sentiment ─────────────────────────────────────────────────────


class TestRecordSentiment:
    def test_basic(self):
        result = record_sentiment(
            competitor="Acme",
            love="Easy to use",
            hate="Expensive",
            wish="Better API",
            source="G2 reviews",
        )
        assert "Recorded sentiment for 'Acme'" in result
        data = get_competitor_data()
        assert len(data["sentiment"]) == 1
        assert data["sentiment"][0]["source"] == "G2 reviews"


# ── record_market_positioning ────────────────────────────────────────────


class TestRecordMarketPositioning:
    def test_valid(self):
        result = record_market_positioning(
            revenue_evidence_tag="Priced",
            switching_cost="Low",
            price_range_low="0",
            price_range_high="49.99",
            market_structure="Fragmented",
        )
        assert "Recorded market positioning" in result
        data = get_competitor_data()
        assert data["market_positioning"]["revenue_evidence_tag"] == "Priced"
        assert data["market_positioning"]["switching_cost"] == "Low"

    def test_invalid_revenue_tag(self):
        result = record_market_positioning(
            revenue_evidence_tag="Unknown",
            switching_cost="Low",
            price_range_low="",
            price_range_high="",
            market_structure="Fragmented",
        )
        assert "REJECTED" in result
        assert get_competitor_data()["market_positioning"] == {}

    def test_invalid_switching_cost(self):
        result = record_market_positioning(
            revenue_evidence_tag="Priced",
            switching_cost="Very High",
            price_range_low="",
            price_range_high="",
            market_structure="Fragmented",
        )
        assert "REJECTED" in result

    def test_all_valid_revenue_tags(self):
        for tag in ("Priced", "Freemium-Dominant", "No-Pricing-Found"):
            clear_competitor_accumulator()
            result = record_market_positioning(
                revenue_evidence_tag=tag,
                switching_cost="Medium",
                price_range_low="",
                price_range_high="",
                market_structure="Winner-take-all",
            )
            assert "REJECTED" not in result

    def test_all_valid_switching_costs(self):
        for cost in ("Low", "Medium", "High"):
            clear_competitor_accumulator()
            result = record_market_positioning(
                revenue_evidence_tag="Priced",
                switching_cost=cost,
                price_range_low="",
                price_range_high="",
                market_structure="Consolidating",
            )
            assert "REJECTED" not in result


# ── clear_competitor_accumulator ─────────────────────────────────────────


class TestClearAccumulator:
    def test_clears_all(self):
        record_competitor(
            name="A",
            url="",
            traction="",
            target_segment="",
            jtbd_match="Direct",
        )
        record_sentiment(
            competitor="A",
            love="",
            hate="",
            wish="",
            source="",
        )
        record_market_positioning(
            revenue_evidence_tag="Priced",
            switching_cost="Low",
            price_range_low="",
            price_range_high="",
            market_structure="",
        )
        clear_competitor_accumulator()
        data = get_competitor_data()
        assert data["competitors"] == []
        assert data["sentiment"] == []
        assert data["market_positioning"] == {}


# ── extract_competitor_data_processor ────────────────────────────────────


class TestExtractCompetitorDataProcessor:
    def test_extracts_all_fields(self):
        record_competitor(
            name="A",
            url="",
            traction="",
            target_segment="",
            jtbd_match="Direct",
        )
        record_competitor(
            name="B",
            url="",
            traction="",
            target_segment="",
            jtbd_match="Adjacent",
        )
        record_market_positioning(
            revenue_evidence_tag="Priced",
            switching_cost="High",
            price_range_low="10",
            price_range_high="50",
            market_structure="Fragmented",
        )
        state = MagicMock()
        result = extract_competitor_data_processor("some output", state)
        assert result["revenue_evidence_tag"] == "Priced"
        assert result["switching_cost"] == "High"
        assert result["competitor_jtbd_matches"] == ["Direct", "Adjacent"]

    def test_empty_accumulator_returns_defaults(self):
        state = MagicMock()
        result = extract_competitor_data_processor("some output", state)
        assert result == {
            "revenue_evidence_tag": "",
            "switching_cost": "",
            "competitor_jtbd_matches": [],
        }

    def test_partial_data(self):
        record_competitor(
            name="A",
            url="",
            traction="",
            target_segment="",
            jtbd_match="Unrelated",
        )
        state = MagicMock()
        result = extract_competitor_data_processor("some output", state)
        assert result["revenue_evidence_tag"] == ""
        assert result["competitor_jtbd_matches"] == ["Unrelated"]


# ── Validator state-field fallback ───────────────────────────────────────


class TestValidatorStateFallback:
    """Verify validators prefer state fields over regex extraction."""

    def test_revenue_evidence_uses_state_field(self):
        from haytham.workflow.validators.revenue_evidence import validate_revenue_evidence

        state = MagicMock()
        state.get = lambda key, default="": {
            "market_context": "",
            "concept_anchor_str": "",
            "revenue_evidence_tag": "No-Pricing-Found",
        }.get(key, default)

        output = '{"go_no_go_assessment": {"scorecard": [{"dimension": "Revenue Viability", "score": 4}]}}'
        warnings = validate_revenue_evidence(output, state)
        assert any("not found" in w.lower() or "not found" in w for w in warnings)

    def test_revenue_evidence_regex_fallback(self):
        from haytham.workflow.validators.revenue_evidence import validate_revenue_evidence

        state = MagicMock()
        state.get = lambda key, default="": {
            "market_context": "**Revenue Evidence Tag:** [No-Pricing-Found]",
            "concept_anchor_str": "",
            "revenue_evidence_tag": "",
        }.get(key, default)

        output = '{"go_no_go_assessment": {"scorecard": [{"dimension": "Revenue Viability", "score": 4}]}}'
        warnings = validate_revenue_evidence(output, state)
        assert any("not found" in w.lower() or "pricing" in w.lower() for w in warnings)

    def test_jtbd_match_uses_state_field(self):
        from haytham.workflow.validators.jtbd_match import validate_jtbd_match

        state = MagicMock()
        state.get = lambda key, default="": {
            "market_context": "",
            "competitor_jtbd_matches": ["Adjacent", "Unrelated", "Adjacent"],
        }.get(key, default)

        output = '{"go_no_go_assessment": {"scorecard": [{"dimension": "Market Opportunity", "score": 4}]}}'
        warnings = validate_jtbd_match(output, state)
        assert any("JTBD" in w or "jtbd" in w.lower() for w in warnings)

    def test_dim8_uses_state_field(self):
        from haytham.workflow.validators.dim8_inputs import validate_dim8_inputs

        state = MagicMock()
        state.get = lambda key, default="": {
            "market_context": "",
            "switching_cost": "High",
        }.get(key, default)

        output = '{"go_no_go_assessment": {"scorecard": [{"dimension": "Adoption & Engagement Risk", "score": 4}]}}'
        warnings = validate_dim8_inputs(output, state)
        assert any("switching" in w.lower() for w in warnings)
