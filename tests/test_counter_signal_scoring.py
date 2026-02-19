"""Tests for closed-loop scoring integrity (counter-signal consistency).

Covers:
- CounterSignal model validation
- GoNoGoScorecard with counter_signals (backward compat + rendering)
- evaluate_recommendation tool: backward compat, verdict logic
- Legacy formatter in burr_actions
"""

import importlib
import json

from haytham.agents.tools import recommendation as _recommendation_mod
from haytham.agents.worker_validation_summary.validation_summary_models import (
    CounterSignal,
    GoNoGoScorecard,
    KnockoutCriterion,
    KnockoutResult,
    ScorecardDimension,
    ValidationSummaryOutput,
)

# =============================================================================
# Helpers to import modules with heavy transitive deps
# =============================================================================


def _import_recommendation():
    """Return the recommendation module (reportlab mocked by conftest)."""
    return _recommendation_mod


def _call_evaluate_recommendation(**kwargs) -> dict:
    """Call the underlying function and parse the JSON result."""
    mod = _import_recommendation()
    result_str = mod.evaluate_recommendation(**kwargs)
    return json.loads(result_str)


def _import_burr_actions_formatter():
    """Import _format_validation_summary_output from output_utils."""
    mod = importlib.import_module("haytham.agents.output_utils")
    return mod._format_validation_summary_output


# =============================================================================
# CounterSignal model tests
# =============================================================================


class TestCounterSignalModel:
    def test_valid_counter_signal(self):
        cs = CounterSignal(
            signal="No independent evidence users want this",
            source="risk_assessment",
            affected_dimensions=["Market Opportunity", "Problem Severity"],
            reconciliation="Score lowered from 4 to 3 because market research is inconclusive",
        )
        assert cs.signal == "No independent evidence users want this"
        assert cs.source == "risk_assessment"
        assert len(cs.affected_dimensions) == 2
        assert "lowered" in cs.reconciliation

    def test_counter_signal_empty_dimensions(self):
        cs = CounterSignal(
            signal="High regulatory risk",
            source="market_context",
            affected_dimensions=[],
            reconciliation="Addressed by knockout criterion instead",
        )
        assert cs.affected_dimensions == []


# =============================================================================
# GoNoGoScorecard backward compatibility
# =============================================================================


class TestGoNoGoScorecardCounterSignals:
    """Verify counter_signals defaults to empty list (backward compat)."""

    def _make_scorecard(self, counter_signals=None):
        kwargs = {
            "knockout_criteria": [
                KnockoutCriterion(
                    criterion="Problem Reality",
                    result=KnockoutResult.PASS,
                    evidence="Confirmed",
                ),
            ],
            "scorecard": [
                ScorecardDimension(
                    dimension="Problem Severity", score=4, evidence="Users pay today"
                ),
            ],
            "composite_score": 4.0,
            "verdict": "GO",
            "critical_gaps": [],
            "guidance": "Proceed",
        }
        if counter_signals is not None:
            kwargs["counter_signals"] = counter_signals
        return GoNoGoScorecard(**kwargs)

    def test_default_empty_list(self):
        sc = self._make_scorecard()
        assert sc.counter_signals == []

    def test_with_counter_signals(self):
        cs = CounterSignal(
            signal="Unsupported claim",
            source="risk_assessment",
            affected_dimensions=["Market Opportunity"],
            reconciliation="Score reduced to 3",
        )
        sc = self._make_scorecard(counter_signals=[cs])
        assert len(sc.counter_signals) == 1
        assert sc.counter_signals[0].signal == "Unsupported claim"


# =============================================================================
# to_markdown() rendering
# =============================================================================


class TestToMarkdownCounterSignals:
    def _make_output(self, counter_signals=None):
        scorecard = GoNoGoScorecard(
            knockout_criteria=[
                KnockoutCriterion(
                    criterion="Problem Reality",
                    result=KnockoutResult.PASS,
                    evidence="Confirmed",
                ),
            ],
            counter_signals=counter_signals or [],
            scorecard=[
                ScorecardDimension(dimension="Problem Severity", score=4, evidence="Users pay"),
            ],
            composite_score=4.0,
            verdict="GO",
            critical_gaps=[],
            guidance="Proceed with MVP",
        )
        return ValidationSummaryOutput(
            executive_summary="Test summary",
            recommendation="GO",
            lean_canvas={
                "problems": ["Problem 1"],
                "customer_segments": ["Segment 1"],
                "unique_value_proposition": "UVP",
                "solution": ["Solution 1"],
                "revenue_model": "SaaS",
            },
            validation_findings={
                "market_opportunity": "Large",
                "competition": "Low",
                "critical_risks": ["Risk 1"],
            },
            go_no_go_assessment=scorecard,
            next_steps=["Step 1"],
        )

    def test_no_counter_signals_renders_without_section(self):
        md = self._make_output().to_markdown()
        assert "Counter-Signals Reconciliation" not in md

    def test_counter_signals_render_between_knockouts_and_dimensions(self):
        cs = CounterSignal(
            signal="Market size unverified",
            source="risk_assessment",
            affected_dimensions=["Market Opportunity"],
            reconciliation="Reduced score from 4 to 3 based on limited data",
        )
        md = self._make_output(counter_signals=[cs]).to_markdown()

        assert "### Counter-Signals Reconciliation" in md
        assert "Market size unverified" in md
        assert "risk_assessment" in md
        assert "Market Opportunity" in md
        assert "Reduced score from 4 to 3" in md

        # Verify ordering: knockouts → counter-signals → scored dimensions
        knockout_pos = md.index("### Knockout Criteria")
        counter_pos = md.index("### Counter-Signals Reconciliation")
        scored_pos = md.index("### Scored Dimensions")
        assert knockout_pos < counter_pos < scored_pos


# =============================================================================
# evaluate_recommendation tool tests
# =============================================================================


def _knockouts_pass():
    return json.dumps(
        [
            {"criterion": "Problem Reality", "result": "PASS", "evidence": "Confirmed"},
            {"criterion": "Channel Access", "result": "PASS", "evidence": "SEO viable"},
            {"criterion": "Regulatory", "result": "PASS", "evidence": "No blockers"},
        ]
    )


def _dimensions_high():
    return json.dumps(
        [
            {"dimension": "Problem Severity", "score": 4, "evidence": "..."},
            {"dimension": "Market Opportunity", "score": 4, "evidence": "..."},
            {"dimension": "Competitive Differentiation", "score": 4, "evidence": "..."},
            {"dimension": "Solution Feasibility", "score": 4, "evidence": "..."},
            {"dimension": "Revenue Viability", "score": 4, "evidence": "..."},
            {"dimension": "Founder-Market Fit", "score": 4, "evidence": "..."},
        ]
    )


class TestEvaluateRecommendationCounterSignals:
    """Test the evaluate_recommendation tool with counter_signals parameter.

    Counter-signals are now ignored by the verdict logic (displayed for
    transparency only). These tests verify backward compatibility.
    """

    def test_backward_compat_no_counter_signals(self):
        """Tool works without counter_signals parameter (existing callers)."""
        result = _call_evaluate_recommendation(
            knockout_results=_knockouts_pass(),
            dimension_scores=_dimensions_high(),
        )
        assert result["recommendation"] == "GO"
        assert result["composite_score"] == 4.0
        assert not result["adjusted"]

    def test_counter_signals_ignored_by_verdict(self):
        """Counter-signals param is accepted but does not affect the verdict."""
        signals = json.dumps(
            [
                {
                    "signal": "No evidence users want this",
                    "source": "risk_assessment",
                    "affected_dimensions": ["Problem Severity"],
                    "reconciliation": "Score lowered from 5 to 4",
                },
            ]
        )
        result = _call_evaluate_recommendation(
            knockout_results=_knockouts_pass(),
            dimension_scores=_dimensions_high(),
            counter_signals=signals,
        )
        # Counter-signals do not affect scoring
        assert result["recommendation"] == "GO"
        assert result["composite_score"] == 4.0
        assert not result["adjusted"]

    def test_multiple_counter_signals_no_penalty(self):
        """Multiple counter-signals produce no penalty (penalty logic removed)."""
        signals = json.dumps(
            [
                {
                    "signal": "No evidence users want this",
                    "source": "risk_assessment",
                    "affected_dimensions": ["Problem Severity"],
                    "reconciliation": "Score reflects limited evidence",
                },
                {
                    "signal": "Market size unverified",
                    "source": "market_context",
                    "affected_dimensions": ["Market Opportunity"],
                    "reconciliation": "Conservative scoring applied",
                },
            ]
        )
        result = _call_evaluate_recommendation(
            knockout_results=_knockouts_pass(),
            dimension_scores=_dimensions_high(),
            counter_signals=signals,
        )
        # No penalty applied, composite unchanged
        assert result["composite_score"] == 4.0
        assert not result["adjusted"]
        assert result["recommendation"] == "GO"

    def test_knockout_fail_ignores_counter_signals(self):
        """Knockout FAIL returns NO-GO regardless of counter-signals."""
        knockouts = json.dumps(
            [
                {"criterion": "Problem Reality", "result": "FAIL", "evidence": "Hypothetical"},
            ]
        )
        result = _call_evaluate_recommendation(
            knockout_results=knockouts,
            dimension_scores=_dimensions_high(),
            counter_signals="[]",
        )
        assert result["recommendation"] == "NO-GO"
        assert result["warnings"] == []
        assert not result["adjusted"]


# =============================================================================
# 6-dimension scoring tests (ADR-023 final: no Founder-Market Fit)
# =============================================================================


def _dimensions_six():
    """6 dimensions — ADR-023 final (no Founder-Market Fit)."""
    return json.dumps(
        [
            {"dimension": "Problem Severity", "score": 4, "evidence": "..."},
            {"dimension": "Market Opportunity", "score": 4, "evidence": "..."},
            {"dimension": "Competitive Differentiation", "score": 4, "evidence": "..."},
            {"dimension": "Execution Feasibility", "score": 4, "evidence": "..."},
            {"dimension": "Revenue Viability", "score": 4, "evidence": "..."},
            {"dimension": "Adoption & Engagement Risk", "score": 3, "evidence": "..."},
        ]
    )


class TestSixDimensionScoring:
    """Tests for the 6-dimension set (ADR-023 final: no Founder-Market Fit)."""

    def test_six_dimensions_composite(self):
        """6 dimensions produce correct composite score."""
        result = _call_evaluate_recommendation(
            knockout_results=_knockouts_pass(),
            dimension_scores=_dimensions_six(),
        )
        # (4+4+4+4+4+3) / 6 = 23/6 ≈ 3.8
        assert result["composite_score"] == 3.8
        assert result["recommendation"] == "GO"

    def test_low_execution_shifts_verdict(self):
        """Low execution feasibility score shifts composite into PIVOT range."""
        dims = json.dumps(
            [
                {"dimension": "Problem Severity", "score": 4, "evidence": "..."},
                {"dimension": "Market Opportunity", "score": 3, "evidence": "..."},
                {"dimension": "Competitive Differentiation", "score": 3, "evidence": "..."},
                {"dimension": "Execution Feasibility", "score": 1, "evidence": "..."},
                {"dimension": "Revenue Viability", "score": 3, "evidence": "..."},
                {"dimension": "Adoption & Engagement Risk", "score": 3, "evidence": "..."},
            ]
        )
        result = _call_evaluate_recommendation(
            knockout_results=_knockouts_pass(),
            dimension_scores=dims,
        )
        # (4+3+3+1+3+3) / 6 = 17/6 ≈ 2.8 → floor rule: dim ≤2 but 2.8 < 3.0 so no cap
        assert result["composite_score"] == 2.8
        assert result["recommendation"] == "PIVOT"

    def test_all_high_with_six_dims(self):
        """All high scores with 6-dim set → GO."""
        dims = json.dumps(
            [
                {"dimension": "Problem Severity", "score": 4, "evidence": "..."},
                {"dimension": "Market Opportunity", "score": 4, "evidence": "..."},
                {"dimension": "Competitive Differentiation", "score": 4, "evidence": "..."},
                {"dimension": "Execution Feasibility", "score": 4, "evidence": "..."},
                {"dimension": "Revenue Viability", "score": 4, "evidence": "..."},
                {"dimension": "Adoption & Engagement Risk", "score": 4, "evidence": "..."},
            ]
        )
        result = _call_evaluate_recommendation(
            knockout_results=_knockouts_pass(),
            dimension_scores=dims,
        )
        assert result["composite_score"] == 4.0
        assert result["recommendation"] == "GO"


# =============================================================================
# Legacy 7-dimension scoring tests (old: separate Solution + Operational)
# =============================================================================


def _dimensions_seven():
    return json.dumps(
        [
            {"dimension": "Problem Severity", "score": 4, "evidence": "..."},
            {"dimension": "Market Opportunity", "score": 4, "evidence": "..."},
            {"dimension": "Competitive Differentiation", "score": 4, "evidence": "..."},
            {"dimension": "Solution Feasibility", "score": 4, "evidence": "..."},
            {"dimension": "Revenue Viability", "score": 4, "evidence": "..."},
            {"dimension": "Founder-Market Fit", "score": 4, "evidence": "..."},
            {"dimension": "Operational Feasibility", "score": 3, "evidence": "..."},
        ]
    )


class TestSevenDimensionScoring:
    def test_seven_dimensions_composite(self):
        """7 dimensions produce correct composite score."""
        result = _call_evaluate_recommendation(
            knockout_results=_knockouts_pass(),
            dimension_scores=_dimensions_seven(),
        )
        # (4+4+4+4+4+4+3) / 7 = 27/7 ≈ 3.9
        assert result["composite_score"] == 3.9
        assert result["recommendation"] == "GO"

    def test_low_operational_shifts_verdict(self):
        """Low operational feasibility score can shift composite into PIVOT range."""
        dims = json.dumps(
            [
                {"dimension": "Problem Severity", "score": 4, "evidence": "..."},
                {"dimension": "Market Opportunity", "score": 3, "evidence": "..."},
                {"dimension": "Competitive Differentiation", "score": 3, "evidence": "..."},
                {"dimension": "Solution Feasibility", "score": 4, "evidence": "..."},
                {"dimension": "Revenue Viability", "score": 3, "evidence": "..."},
                {"dimension": "Founder-Market Fit", "score": 3, "evidence": "..."},
                {"dimension": "Operational Feasibility", "score": 1, "evidence": "..."},
            ]
        )
        result = _call_evaluate_recommendation(
            knockout_results=_knockouts_pass(),
            dimension_scores=dims,
        )
        # (4+3+3+4+3+3+1) / 7 = 21/7 = 3.0 → PIVOT
        assert result["composite_score"] == 3.0
        assert result["recommendation"] == "PIVOT"


# =============================================================================
# Legacy 8-dimension scoring tests
# =============================================================================


def _dimensions_eight():
    return json.dumps(
        [
            {"dimension": "Problem Severity", "score": 4, "evidence": "..."},
            {"dimension": "Market Opportunity", "score": 4, "evidence": "..."},
            {"dimension": "Competitive Differentiation", "score": 4, "evidence": "..."},
            {"dimension": "Solution Feasibility", "score": 4, "evidence": "..."},
            {"dimension": "Revenue Viability", "score": 4, "evidence": "..."},
            {"dimension": "Founder-Market Fit", "score": 4, "evidence": "..."},
            {"dimension": "Operational Feasibility", "score": 3, "evidence": "..."},
            {"dimension": "Adoption & Engagement Risk", "score": 3, "evidence": "..."},
        ]
    )


class TestEightDimensionScoring:
    def test_eight_dimensions_composite(self):
        """8 dimensions produce correct composite score."""
        result = _call_evaluate_recommendation(
            knockout_results=_knockouts_pass(),
            dimension_scores=_dimensions_eight(),
        )
        # (4+4+4+4+4+4+3+3) / 8 = 30/8 = 3.75 → rounds to 3.8
        assert result["composite_score"] == 3.8
        assert result["recommendation"] == "GO"

    def test_low_adoption_shifts_verdict(self):
        """Low adoption & engagement risk score can shift composite into PIVOT range."""
        dims = json.dumps(
            [
                {"dimension": "Problem Severity", "score": 4, "evidence": "..."},
                {"dimension": "Market Opportunity", "score": 3, "evidence": "..."},
                {"dimension": "Competitive Differentiation", "score": 3, "evidence": "..."},
                {"dimension": "Solution Feasibility", "score": 4, "evidence": "..."},
                {"dimension": "Revenue Viability", "score": 3, "evidence": "..."},
                {"dimension": "Founder-Market Fit", "score": 3, "evidence": "..."},
                {"dimension": "Operational Feasibility", "score": 3, "evidence": "..."},
                {"dimension": "Adoption & Engagement Risk", "score": 1, "evidence": "..."},
            ]
        )
        result = _call_evaluate_recommendation(
            knockout_results=_knockouts_pass(),
            dimension_scores=dims,
        )
        # (4+3+3+4+3+3+3+1) / 8 = 24/8 = 3.0 → PIVOT
        assert result["composite_score"] == 3.0
        assert result["recommendation"] == "PIVOT"

    def test_high_adoption_boosts_composite(self):
        """High adoption score (low behavioral deviation) contributes positively."""
        dims = json.dumps(
            [
                {"dimension": "Problem Severity", "score": 4, "evidence": "..."},
                {"dimension": "Market Opportunity", "score": 4, "evidence": "..."},
                {"dimension": "Competitive Differentiation", "score": 4, "evidence": "..."},
                {"dimension": "Solution Feasibility", "score": 4, "evidence": "..."},
                {"dimension": "Revenue Viability", "score": 4, "evidence": "..."},
                {"dimension": "Founder-Market Fit", "score": 4, "evidence": "..."},
                {"dimension": "Operational Feasibility", "score": 3, "evidence": "..."},
                {"dimension": "Adoption & Engagement Risk", "score": 5, "evidence": "..."},
            ]
        )
        result = _call_evaluate_recommendation(
            knockout_results=_knockouts_pass(),
            dimension_scores=dims,
        )
        # (4+4+4+4+4+4+3+5) / 8 = 32/8 = 4.0 → GO
        assert result["composite_score"] == 4.0
        assert result["recommendation"] == "GO"


# =============================================================================
# Legacy formatter tests
# =============================================================================


class TestLegacyFormatterCounterSignals:
    def test_counter_signals_in_legacy_output(self):
        formatter = _import_burr_actions_formatter()
        data = {
            "executive_summary": "Test",
            "recommendation": "GO",
            "go_no_go_assessment": {
                "counter_signals": [
                    {
                        "signal": "Unverified market size",
                        "source": "risk_assessment",
                        "affected_dimensions": ["Market Opportunity"],
                        "reconciliation": "Score adjusted down to 3",
                    },
                ],
                "guidance": "Proceed with caution",
            },
            "next_steps": ["Step 1"],
        }
        md = formatter(data)
        assert "Counter-Signals Reconciliation" in md
        assert "Unverified market size" in md
        assert "Score adjusted down to 3" in md

    def test_no_counter_signals_in_legacy_output(self):
        formatter = _import_burr_actions_formatter()
        data = {
            "executive_summary": "Test",
            "recommendation": "GO",
            "go_no_go_assessment": {
                "guidance": "Proceed",
            },
            "next_steps": ["Step 1"],
        }
        md = formatter(data)
        assert "Counter-Signals Reconciliation" not in md

    def test_empty_counter_signals_in_legacy_output(self):
        formatter = _import_burr_actions_formatter()
        data = {
            "executive_summary": "Test",
            "recommendation": "GO",
            "go_no_go_assessment": {
                "counter_signals": [],
                "guidance": "Proceed",
            },
            "next_steps": ["Step 1"],
        }
        md = formatter(data)
        assert "Counter-Signals Reconciliation" not in md

    def test_reconciliation_in_legacy_output(self):
        """Legacy formatter renders reconciliation field."""
        formatter = _import_burr_actions_formatter()
        data = {
            "executive_summary": "Test",
            "recommendation": "GO",
            "go_no_go_assessment": {
                "counter_signals": [
                    {
                        "signal": "Market size unverified",
                        "source": "risk_assessment",
                        "affected_dimensions": ["Market Opportunity"],
                        "reconciliation": "Score is 3 not 4, already conservative",
                    },
                ],
                "guidance": "Proceed",
            },
            "next_steps": ["Step 1"],
        }
        md = formatter(data)
        assert "Market size unverified" in md
        assert "Reconciliation:" in md
        assert "Score is 3 not 4" in md


# =============================================================================
# Floor Rule tests (Item 3)
# =============================================================================


class TestFloorRule:
    """Test that any dimension ≤ 2 caps composite at 3.0."""

    def test_floor_caps_high_composite(self):
        """One dimension at 2 with high others → composite capped to 3.0 → PIVOT."""
        dims = json.dumps(
            [
                {"dimension": "Problem Severity", "score": 4, "evidence": "..."},
                {"dimension": "Market Opportunity", "score": 4, "evidence": "..."},
                {"dimension": "Competitive Differentiation", "score": 4, "evidence": "..."},
                {"dimension": "Solution Feasibility", "score": 4, "evidence": "..."},
                {"dimension": "Revenue Viability", "score": 2, "evidence": "..."},
                {"dimension": "Founder-Market Fit", "score": 4, "evidence": "..."},
                {"dimension": "Operational Feasibility", "score": 4, "evidence": "..."},
                {"dimension": "Adoption & Engagement Risk", "score": 4, "evidence": "..."},
            ]
        )
        result = _call_evaluate_recommendation(
            knockout_results=_knockouts_pass(),
            dimension_scores=dims,
        )
        assert result["composite_score"] == 3.0
        assert result["floor_capped"]
        assert "Revenue Viability" in result["floor_violations"]
        assert result["recommendation"] == "PIVOT"

    def test_no_floor_when_all_above_two(self):
        """All scores > 2 → no floor cap."""
        result = _call_evaluate_recommendation(
            knockout_results=_knockouts_pass(),
            dimension_scores=_dimensions_high(),
        )
        assert not result["floor_capped"]
        assert result["floor_violations"] == []

    def test_no_floor_when_composite_already_low(self):
        """Floor violation but composite already ≤ 3.0 → no cap needed."""
        dims = json.dumps(
            [
                {"dimension": "Problem Severity", "score": 2, "evidence": "..."},
                {"dimension": "Market Opportunity", "score": 2, "evidence": "..."},
                {"dimension": "Solution Feasibility", "score": 3, "evidence": "..."},
            ]
        )
        result = _call_evaluate_recommendation(
            knockout_results=_knockouts_pass(),
            dimension_scores=dims,
        )
        # (2+2+3)/3 = 2.33 — already below 3.0
        assert not result["floor_capped"]
        assert len(result["floor_violations"]) == 2  # Still lists violations

    def test_floor_with_counter_signals_no_penalty(self):
        """Floor caps to 3.0; counter-signals do not apply additional penalty."""
        dims = json.dumps(
            [
                {"dimension": "Problem Severity", "score": 4, "evidence": "..."},
                {"dimension": "Market Opportunity", "score": 4, "evidence": "..."},
                {"dimension": "Revenue Viability", "score": 2, "evidence": "..."},
            ]
        )
        signals = json.dumps(
            [
                {
                    "signal": "Signal A",
                    "source": "risk_assessment",
                    "affected_dimensions": ["Problem Severity"],
                    "reconciliation": "Score reflects limited data",
                },
                {
                    "signal": "Signal B",
                    "source": "market_context",
                    "affected_dimensions": ["Market Opportunity"],
                    "reconciliation": "Conservative scoring applied",
                },
            ]
        )
        result = _call_evaluate_recommendation(
            knockout_results=_knockouts_pass(),
            dimension_scores=dims,
            counter_signals=signals,
        )
        # Floor caps to 3.0, no additional penalty from counter-signals
        assert result["floor_capped"]
        assert not result["adjusted"]
        assert result["composite_score"] == 3.0
        assert result["recommendation"] == "PIVOT"

    def test_dimension_at_one_triggers_floor(self):
        """Score of 1 also triggers floor rule."""
        dims = json.dumps(
            [
                {"dimension": "Problem Severity", "score": 5, "evidence": "..."},
                {"dimension": "Market Opportunity", "score": 5, "evidence": "..."},
                {"dimension": "Solution Feasibility", "score": 1, "evidence": "..."},
            ]
        )
        result = _call_evaluate_recommendation(
            knockout_results=_knockouts_pass(),
            dimension_scores=dims,
        )
        assert result["floor_capped"]
        assert result["composite_score"] == 3.0


# =============================================================================
# Risk Level Veto tests (Item 1)
# =============================================================================


class TestRiskLevelVeto:
    """Test that HIGH risk caps GO → PIVOT unless well-reconciled."""

    def test_high_risk_caps_go_to_pivot(self):
        """HIGH risk with no reconciled signals → GO capped to PIVOT."""
        result = _call_evaluate_recommendation(
            knockout_results=_knockouts_pass(),
            dimension_scores=_dimensions_high(),
            risk_level="HIGH",
        )
        assert result["recommendation"] == "PIVOT"
        assert result["risk_capped"]

    def test_medium_risk_no_veto(self):
        """MEDIUM risk does not trigger veto."""
        result = _call_evaluate_recommendation(
            knockout_results=_knockouts_pass(),
            dimension_scores=_dimensions_high(),
            risk_level="MEDIUM",
        )
        assert result["recommendation"] == "GO"
        assert not result["risk_capped"]

    def test_empty_risk_level_backward_compat(self):
        """Empty string risk_level (default) → no veto."""
        result = _call_evaluate_recommendation(
            knockout_results=_knockouts_pass(),
            dimension_scores=_dimensions_high(),
        )
        assert result["recommendation"] == "GO"
        assert not result["risk_capped"]

    def test_already_pivot_not_double_penalized(self):
        """Already-PIVOT verdict not affected by risk veto."""
        dims = json.dumps(
            [
                {"dimension": "Problem Severity", "score": 3, "evidence": "..."},
                {"dimension": "Market Opportunity", "score": 3, "evidence": "..."},
                {"dimension": "Solution Feasibility", "score": 3, "evidence": "..."},
            ]
        )
        result = _call_evaluate_recommendation(
            knockout_results=_knockouts_pass(),
            dimension_scores=dims,
            risk_level="HIGH",
        )
        assert result["recommendation"] == "PIVOT"
        assert not result["risk_capped"]  # Was already PIVOT

