"""Tests for tool-level evidence validation in recommendation.py.

Covers:
- High-score evidence gate: source tag required, valid source, no rubric phrases
- Counter-signal source validation
"""

import importlib
import sys
from unittest import mock

import pytest


def _import_recommendation():
    """Import recommendation module, mocking reportlab if absent."""
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
    return importlib.import_module("haytham.agents.tools.recommendation")


@pytest.fixture(autouse=True)
def _clean_scorecard():
    """Clear the scorecard before and after each test."""
    mod = _import_recommendation()
    mod.clear_scorecard()
    yield
    mod.clear_scorecard()


class TestDimensionScoreValidation:
    """Test _validate_evidence gate on record_dimension_score."""

    def test_high_score_no_source_tag_rejected(self):
        """Score 4 without (source: ...) tag is REJECTED and not appended."""
        mod = _import_recommendation()
        result = mod.record_dimension_score(
            dimension="Problem Severity",
            score=4,
            evidence="Strong evidence of user pain from competitor reviews",
        )
        assert "REJECTED" in result
        assert "(source: stage_name)" in result
        assert len(mod.get_scorecard()["dimensions"]) == 0

    def test_high_score_invalid_source_rejected(self):
        """Score 4 with invalid source name is REJECTED."""
        mod = _import_recommendation()
        result = mod.record_dimension_score(
            dimension="Market Opportunity",
            score=4,
            evidence="TAM $50B verified (source: technical_assessment)",
        )
        assert "REJECTED" in result
        assert "technical_assessment" in result
        assert len(mod.get_scorecard()["dimensions"]) == 0

    def test_high_score_valid_source_accepted(self):
        """Score 4 with valid source and real evidence is accepted."""
        mod = _import_recommendation()
        result = mod.record_dimension_score(
            dimension="Problem Severity",
            score=4,
            evidence="Acme users report 'constant frustration' — paying $15/mo for workaround (source: market_context)",
        )
        assert "REJECTED" not in result
        assert "Recorded" in result
        assert len(mod.get_scorecard()["dimensions"]) == 1

    def test_low_score_real_evidence_accepted(self):
        """Score 3 with real evidence (no source tag) is accepted."""
        mod = _import_recommendation()
        result = mod.record_dimension_score(
            dimension="Market Opportunity",
            score=3,
            evidence="Competitor X has 10K users and $2M ARR in adjacent space",
        )
        assert "REJECTED" not in result
        assert "Recorded" in result
        assert len(mod.get_scorecard()["dimensions"]) == 1

    def test_low_score_rubric_phrase_rejected(self):
        """Score 3 with rubric phrase in evidence is REJECTED."""
        mod = _import_recommendation()
        result = mod.record_dimension_score(
            dimension="Market Opportunity",
            score=3,
            evidence="Moderate pain, users actively seek solutions in this space",
        )
        assert "REJECTED" in result
        assert "rubric text" in result
        assert len(mod.get_scorecard()["dimensions"]) == 0

    def test_high_score_rubric_phrase_rejected(self):
        """Score 4 with rubric phrase in evidence is REJECTED."""
        mod = _import_recommendation()
        result = mod.record_dimension_score(
            dimension="Execution Feasibility",
            score=4,
            evidence="Clearly feasible with known technology and reasonable effort (source: idea_analysis)",
        )
        assert "REJECTED" in result
        assert "rubric text" in result
        assert len(mod.get_scorecard()["dimensions"]) == 0

    def test_high_score_short_rubric_fragment_feasibility_rejected(self):
        """Score 4 with shorter rubric fragment (no 'clearly') is REJECTED."""
        mod = _import_recommendation()
        result = mod.record_dimension_score(
            dimension="Execution Feasibility",
            score=4,
            evidence="Feasible with known technology and reasonable effort (source: idea_analysis)",
        )
        assert "REJECTED" in result
        assert "rubric text" in result
        assert len(mod.get_scorecard()["dimensions"]) == 0

    def test_high_score_rubric_phrase_market_rejected(self):
        """Score 4 with 'large addressable market' rubric phrase is REJECTED."""
        mod = _import_recommendation()
        result = mod.record_dimension_score(
            dimension="Market Opportunity",
            score=4,
            evidence="Large addressable market with strong growth (source: market_context)",
        )
        assert "REJECTED" in result
        assert "rubric text" in result
        assert len(mod.get_scorecard()["dimensions"]) == 0


class TestCounterSignalSourceValidation:
    """Test source validation on record_counter_signal."""

    def test_invalid_source_rejected(self):
        """Counter-signal with invalid source is REJECTED and not appended."""
        mod = _import_recommendation()
        result = mod.record_counter_signal(
            signal="Market size unverified",
            source="competitor_analysis",
            affected_dimensions="Market Opportunity",
            evidence_cited="Some evidence here",
            why_score_holds="Score is conservative",
            what_would_change_score="Direct market data",
        )
        assert "REJECTED" in result
        assert "competitor_analysis" in result
        assert len(mod.get_scorecard()["counter_signals"]) == 0

    def test_valid_source_accepted(self):
        """Counter-signal with valid source is accepted."""
        mod = _import_recommendation()
        result = mod.record_counter_signal(
            signal="Market size unverified",
            source="market_context",
            affected_dimensions="Market Opportunity",
            evidence_cited="Some evidence here",
            why_score_holds="Score is conservative",
            what_would_change_score="Direct market data",
        )
        assert "REJECTED" not in result
        assert "Recorded" in result
        assert len(mod.get_scorecard()["counter_signals"]) == 1

    def test_source_with_spaces_normalized(self):
        """Counter-signal source with spaces is normalized to underscores."""
        mod = _import_recommendation()
        result = mod.record_counter_signal(
            signal="Claims lack external validation",
            source="risk assessment",
            affected_dimensions="Market Opportunity",
            evidence_cited="Some evidence here",
            why_score_holds="Score is conservative",
            what_would_change_score="Direct market data",
        )
        assert "REJECTED" not in result
        assert "Recorded" in result
        sc = mod.get_scorecard()
        assert sc["counter_signals"][0]["source"] == "risk_assessment"


class TestSourceNormalizationInEvidence:
    """Test source name normalization in evidence validation."""

    def test_evidence_source_with_spaces_accepted(self):
        """Score 4 with source using spaces instead of underscores is accepted."""
        mod = _import_recommendation()
        result = mod.record_dimension_score(
            dimension="Problem Severity",
            score=4,
            evidence="Users report 'constant frustration' with 4.6★ rating (source: market context)",
        )
        assert "REJECTED" not in result
        assert "Recorded" in result

    def test_evidence_source_with_mixed_case_accepted(self):
        """Score 4 with source using mixed case is accepted."""
        mod = _import_recommendation()
        result = mod.record_dimension_score(
            dimension="Problem Severity",
            score=4,
            evidence="Competitor analysis shows 3 direct rivals (source: Market_Context)",
        )
        assert "REJECTED" not in result
        assert "Recorded" in result


# =============================================================================
# Evidence dedup tests (ADR-023)
# =============================================================================


class TestEvidenceDedup:
    """Test evidence dedup gate on record_dimension_score."""

    def test_identical_evidence_rejected(self):
        """Second dimension with identical evidence is REJECTED."""
        mod = _import_recommendation()
        # Record first dimension
        result1 = mod.record_dimension_score(
            dimension="Problem Severity",
            score=3,
            evidence="ShipFast has 12K users validating demand for logistics automation",
        )
        assert "Recorded" in result1
        # Attempt same evidence for different dimension
        result2 = mod.record_dimension_score(
            dimension="Market Opportunity",
            score=3,
            evidence="ShipFast has 12K users validating demand for logistics automation",
        )
        assert "REJECTED" in result2
        assert "word overlap" in result2
        assert len(mod.get_scorecard()["dimensions"]) == 1

    def test_high_overlap_rejected(self):
        """Evidence with >70% word overlap is REJECTED."""
        mod = _import_recommendation()
        result1 = mod.record_dimension_score(
            dimension="Problem Severity",
            score=3,
            evidence="ShipFast has 12K users and 4.2 star rating validating logistics pain",
        )
        assert "Recorded" in result1
        # Very similar evidence — most words overlap
        result2 = mod.record_dimension_score(
            dimension="Market Opportunity",
            score=3,
            evidence="ShipFast has 12K users and 4.2 star rating validating logistics demand",
        )
        assert "REJECTED" in result2
        assert len(mod.get_scorecard()["dimensions"]) == 1

    def test_distinct_evidence_accepted(self):
        """Dimensions with distinct evidence are both accepted."""
        mod = _import_recommendation()
        result1 = mod.record_dimension_score(
            dimension="Problem Severity",
            score=3,
            evidence="ShipFast users report hours wasted on manual routing daily",
        )
        assert "Recorded" in result1
        result2 = mod.record_dimension_score(
            dimension="Market Opportunity",
            score=3,
            evidence="TAM $8.1B freight tech verified by Gartner 2024 report",
        )
        assert "Recorded" in result2
        assert len(mod.get_scorecard()["dimensions"]) == 2

    def test_partial_overlap_below_threshold_accepted(self):
        """Evidence with moderate overlap (<70%) is accepted."""
        mod = _import_recommendation()
        result1 = mod.record_dimension_score(
            dimension="Problem Severity",
            score=3,
            evidence="Users report constant frustration with manual spreadsheet tracking",
        )
        assert "Recorded" in result1
        # Shares some words but well below 70% overlap
        result2 = mod.record_dimension_score(
            dimension="Revenue Viability",
            score=3,
            evidence="Competitor pricing shows $49-99/mo subscription for tracking solutions",
        )
        assert "Recorded" in result2
        assert len(mod.get_scorecard()["dimensions"]) == 2


# =============================================================================
# Dimension count guard tests (missing dimension rejection)
# =============================================================================


class TestDimensionCountGuard:
    """Test that compute_verdict rejects incomplete dimension sets."""

    def test_missing_dimensions_rejected(self):
        """compute_verdict with only 4 of 6 dimensions returns error listing missing ones."""
        mod = _import_recommendation()
        # Record knockouts
        mod.record_knockout(criterion="Problem Reality", result="PASS", evidence="Confirmed")
        mod.record_knockout(criterion="Channel Access", result="PASS", evidence="SEO viable")
        mod.record_knockout(criterion="Regulatory/Ethical", result="PASS", evidence="No blockers")
        # Record only 4 of 6 dimensions (skip Competitive Differentiation + Execution Feasibility)
        mod.record_dimension_score(
            dimension="Problem Severity", score=3, evidence="Users report pain in forums"
        )
        mod.record_dimension_score(
            dimension="Market Opportunity", score=3, evidence="TAM $10B in mental health"
        )
        mod.record_dimension_score(
            dimension="Revenue Viability", score=2, evidence="No pricing found for competitors"
        )
        mod.record_dimension_score(
            dimension="Adoption & Engagement Risk",
            score=3,
            evidence="Low switching cost from forums",
        )
        import json

        result = json.loads(mod.compute_verdict())
        assert "error" in result
        assert "Competitive Differentiation" in result["error"]
        assert "Execution Feasibility" in result["error"]
        assert "Missing 2" in result["error"]

    def test_all_six_dimensions_accepted(self):
        """compute_verdict with all 6 dimensions proceeds normally."""
        mod = _import_recommendation()
        mod.record_knockout(criterion="Problem Reality", result="PASS", evidence="Confirmed")
        mod.record_knockout(criterion="Channel Access", result="PASS", evidence="SEO viable")
        mod.record_knockout(criterion="Regulatory/Ethical", result="PASS", evidence="No blockers")
        mod.record_dimension_score(
            dimension="Problem Severity", score=3, evidence="Users report pain in forums"
        )
        mod.record_dimension_score(
            dimension="Market Opportunity", score=3, evidence="TAM $10B in mental health"
        )
        mod.record_dimension_score(
            dimension="Competitive Differentiation",
            score=3,
            evidence="Gaps in theme-based sessions",
        )
        mod.record_dimension_score(
            dimension="Execution Feasibility", score=3, evidence="Standard web tech stack"
        )
        mod.record_dimension_score(
            dimension="Revenue Viability", score=2, evidence="No pricing found for competitors"
        )
        mod.record_dimension_score(
            dimension="Adoption & Engagement Risk",
            score=3,
            evidence="Low switching cost from forums",
        )
        import json

        result = json.loads(mod.compute_verdict())
        assert "error" not in result
        assert "recommendation" in result


class TestWordOverlap:
    """Test _word_overlap helper directly."""

    def test_identical_strings(self):
        mod = _import_recommendation()
        assert mod._word_overlap("hello world", "hello world") == 1.0

    def test_no_overlap(self):
        mod = _import_recommendation()
        assert mod._word_overlap("hello world", "foo bar") == 0.0

    def test_partial_overlap(self):
        mod = _import_recommendation()
        overlap = mod._word_overlap("hello world foo", "hello world bar")
        # intersection={hello, world}, union={hello, world, foo, bar} → 2/4 = 0.5
        assert abs(overlap - 0.5) < 0.01

    def test_empty_string(self):
        mod = _import_recommendation()
        assert mod._word_overlap("", "hello") == 0.0
        assert mod._word_overlap("hello", "") == 0.0
