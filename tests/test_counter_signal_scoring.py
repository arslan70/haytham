"""Tests for closed-loop scoring integrity (counter-signal consistency).

Covers:
- CounterSignal model validation
- GoNoGoScorecard with counter_signals (backward compat + rendering)
- evaluate_recommendation tool: backward compat, reconciliation, inconsistency detection, penalty
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
            confidence="HIGH",
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
    """Test the evaluate_recommendation tool with counter_signals parameter."""

    def test_backward_compat_no_counter_signals(self):
        """Tool works without counter_signals parameter (existing callers).

        With 0 counter-signals, the low-signal-count warning fires but
        no inconsistency penalty is applied (threshold is 2).
        """
        result = _call_evaluate_recommendation(
            knockout_results=_knockouts_pass(),
            dimension_scores=_dimensions_high(),
        )
        assert result["recommendation"] == "GO"
        assert result["composite_score"] == 4.0
        assert any("counter-signal(s) recorded" in w for w in result["warnings"])
        assert result["adjusted"] is False

    def test_reconciled_signals_no_penalty(self):
        """Properly reconciled counter-signals produce no inconsistency warnings.

        Low-signal-count warning still fires (only 1 signal) but no penalty applied.
        """
        signals = json.dumps(
            [
                {
                    "signal": "Market size claim unsupported",
                    "source": "risk_assessment",
                    "affected_dimensions": ["Market Opportunity"],
                    "reconciliation": "Score was lowered from 5 to 4 because the TAM figure lacks independent verification but adjacency data supports moderate opportunity",
                },
            ]
        )
        result = _call_evaluate_recommendation(
            knockout_results=_knockouts_pass(),
            dimension_scores=_dimensions_high(),
            counter_signals=signals,
        )
        # Only the low-signal-count warning, no inconsistency warning
        assert all("scored" not in w for w in result["warnings"])
        assert result["adjusted"] is False
        assert result["composite_score"] == 4.0

    def test_one_inconsistency_warns_but_no_penalty(self):
        """Single inconsistency + low-signal-count warning, but penalty triggers
        because total warnings (2) hit the inconsistency threshold."""
        signals = json.dumps(
            [
                {
                    "signal": "No evidence users want this",
                    "source": "risk_assessment",
                    "affected_dimensions": ["Problem Severity"],
                    "reconciliation": "",  # Empty = not reconciled
                },
            ]
        )
        result = _call_evaluate_recommendation(
            knockout_results=_knockouts_pass(),
            dimension_scores=_dimensions_high(),
            counter_signals=signals,
        )
        assert len(result["warnings"]) == 2
        assert any("Problem Severity" in w for w in result["warnings"])
        assert any("counter-signal(s) recorded" in w for w in result["warnings"])
        assert result["adjusted"] is True
        assert result["composite_score"] == 3.5

    def test_two_inconsistencies_trigger_penalty(self):
        """Two or more inconsistencies apply -0.5 composite penalty."""
        signals = json.dumps(
            [
                {
                    "signal": "No evidence users want this",
                    "source": "risk_assessment",
                    "affected_dimensions": ["Problem Severity"],
                    "reconciliation": "noted",  # Too short
                },
                {
                    "signal": "Market size unverified",
                    "source": "market_context",
                    "affected_dimensions": ["Market Opportunity"],
                    "reconciliation": "",  # Empty
                },
            ]
        )
        result = _call_evaluate_recommendation(
            knockout_results=_knockouts_pass(),
            dimension_scores=_dimensions_high(),
            counter_signals=signals,
        )
        assert len(result["warnings"]) >= 2
        assert result["adjusted"] is True
        assert result["composite_score"] == 3.5  # 4.0 - 0.5

    def test_penalty_can_shift_verdict_to_pivot(self):
        """Penalty can push a GO composite into PIVOT range."""
        signals = json.dumps(
            [
                {
                    "signal": "Signal A",
                    "source": "risk_assessment",
                    "affected_dimensions": ["Problem Severity"],
                    "reconciliation": "ok",  # Too short
                },
                {
                    "signal": "Signal B",
                    "source": "market_context",
                    "affected_dimensions": ["Market Opportunity"],
                    "reconciliation": "",
                },
            ]
        )
        result = _call_evaluate_recommendation(
            knockout_results=_knockouts_pass(),
            dimension_scores=_dimensions_high(),
            counter_signals=signals,
        )
        assert result["recommendation"] == "PIVOT"
        assert result["verdict"] == "CONDITIONAL GO"

    def test_penalty_clamped_to_zero(self):
        """Penalty doesn't produce negative composite scores."""
        low_dims = json.dumps(
            [
                {"dimension": "Problem Severity", "score": 1, "evidence": "..."},
            ]
        )
        # These signals don't affect any high-scored dim, so no warnings expected
        signals = json.dumps(
            [
                {
                    "signal": "A",
                    "source": "x",
                    "affected_dimensions": [],
                    "reconciliation": "",
                },
                {
                    "signal": "B",
                    "source": "x",
                    "affected_dimensions": [],
                    "reconciliation": "",
                },
            ]
        )
        result = _call_evaluate_recommendation(
            knockout_results=_knockouts_pass(),
            dimension_scores=low_dims,
            counter_signals=signals,
        )
        assert result["composite_score"] >= 0.0

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
        assert result["adjusted"] is False


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


class TestCheckCounterSignalConsistency:
    def test_empty_signals(self):
        mod = _import_recommendation()
        warnings = mod._check_counter_signal_consistency([], [])
        assert warnings == []

    def test_reconciled_signal_no_warning(self):
        mod = _import_recommendation()
        signals = [
            {
                "signal": "test",
                "affected_dimensions": ["Problem Severity"],
                "reconciliation": "This is a substantive explanation of why the score stands",
            }
        ]
        dims = [{"dimension": "Problem Severity", "score": 4}]
        warnings = mod._check_counter_signal_consistency(signals, dims)
        assert warnings == []

    def test_unreconciled_low_score_no_warning(self):
        """Counter-signal on a low-scored dimension doesn't warn (already consistent)."""
        mod = _import_recommendation()
        signals = [
            {
                "signal": "test",
                "affected_dimensions": ["Problem Severity"],
                "reconciliation": "",
            }
        ]
        dims = [{"dimension": "Problem Severity", "score": 2}]
        warnings = mod._check_counter_signal_consistency(signals, dims)
        assert warnings == []


# =============================================================================
# Legacy formatter tests
# =============================================================================


class TestLegacyFormatterCounterSignals:
    def test_counter_signals_in_legacy_output(self):
        formatter = _import_burr_actions_formatter()
        data = {
            "executive_summary": "Test",
            "recommendation": "GO",
            "confidence": "HIGH",
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

    def test_structured_reconciliation_in_legacy_output(self):
        """Legacy formatter renders structured reconciliation fields."""
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
                        "evidence_cited": "Competitor analysis shows 3 funded players",
                        "why_score_holds": "Score is 3 not 4",
                        "what_would_change_score": "If market data showed < $10M TAM",
                    },
                ],
                "guidance": "Proceed",
            },
            "next_steps": ["Step 1"],
        }
        md = formatter(data)
        assert "Evidence cited:" in md
        assert "Why score holds:" in md
        assert "What would change score:" in md
        assert "Reconciliation:" not in md  # Should NOT fall back


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
        assert result["floor_capped"] is True
        assert "Revenue Viability" in result["floor_violations"]
        assert result["recommendation"] == "PIVOT"

    def test_no_floor_when_all_above_two(self):
        """All scores > 2 → no floor cap."""
        result = _call_evaluate_recommendation(
            knockout_results=_knockouts_pass(),
            dimension_scores=_dimensions_high(),
        )
        assert result["floor_capped"] is False
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
        assert result["floor_capped"] is False
        assert len(result["floor_violations"]) == 2  # Still lists violations

    def test_floor_and_counter_signal_penalty_interact(self):
        """Floor caps to 3.0, then counter-signal penalty brings it lower."""
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
                    "reconciliation": "ok",  # Too short
                },
                {
                    "signal": "Signal B",
                    "source": "market_context",
                    "affected_dimensions": ["Market Opportunity"],
                    "reconciliation": "",
                },
            ]
        )
        result = _call_evaluate_recommendation(
            knockout_results=_knockouts_pass(),
            dimension_scores=dims,
            counter_signals=signals,
        )
        # Floor caps to 3.0, then -0.5 penalty → 2.5 → PIVOT
        assert result["floor_capped"] is True
        assert result["adjusted"] is True
        assert result["composite_score"] == 2.5
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
        assert result["floor_capped"] is True
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
        assert result["risk_capped"] is True

    def test_high_risk_with_good_reconciliation_preserves_go(self):
        """HIGH risk with 2+ well-reconciled signals → GO preserved."""
        signals = json.dumps(
            [
                {
                    "signal": "Signal A",
                    "source": "risk_assessment",
                    "affected_dimensions": ["Problem Severity"],
                    "evidence_cited": "Competitor analysis shows 3 funded players in this space with $10M+ ARR",
                    "why_score_holds": "Score is justified because...",
                    "what_would_change_score": "If market dropped below $5M",
                },
                {
                    "signal": "Signal B",
                    "source": "market_context",
                    "affected_dimensions": ["Market Opportunity"],
                    "evidence_cited": "TAM validated by Gartner report showing $2B market size",
                    "why_score_holds": "Growth trajectory confirmed",
                    "what_would_change_score": "If growth stalls",
                },
            ]
        )
        result = _call_evaluate_recommendation(
            knockout_results=_knockouts_pass(),
            dimension_scores=_dimensions_high(),
            counter_signals=signals,
            risk_level="HIGH",
        )
        assert result["recommendation"] == "GO"
        assert result["risk_capped"] is False

    def test_medium_risk_no_veto(self):
        """MEDIUM risk does not trigger veto."""
        result = _call_evaluate_recommendation(
            knockout_results=_knockouts_pass(),
            dimension_scores=_dimensions_high(),
            risk_level="MEDIUM",
        )
        assert result["recommendation"] == "GO"
        assert result["risk_capped"] is False

    def test_empty_risk_level_backward_compat(self):
        """Empty string risk_level (default) → no veto."""
        result = _call_evaluate_recommendation(
            knockout_results=_knockouts_pass(),
            dimension_scores=_dimensions_high(),
        )
        assert result["recommendation"] == "GO"
        assert result["risk_capped"] is False

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
        assert result["risk_capped"] is False  # Was already PIVOT

    def test_high_risk_with_legacy_long_reconciliation(self):
        """Legacy reconciliation ≥ 50 chars counts as well-reconciled for veto override."""
        signals = json.dumps(
            [
                {
                    "signal": "Signal A",
                    "source": "risk_assessment",
                    "affected_dimensions": ["Problem Severity"],
                    "reconciliation": "A" * 50,  # Exactly 50 chars — meets threshold
                },
                {
                    "signal": "Signal B",
                    "source": "market_context",
                    "affected_dimensions": ["Market Opportunity"],
                    "reconciliation": "B" * 50,
                },
            ]
        )
        result = _call_evaluate_recommendation(
            knockout_results=_knockouts_pass(),
            dimension_scores=_dimensions_high(),
            counter_signals=signals,
            risk_level="HIGH",
        )
        assert result["recommendation"] == "GO"
        assert result["risk_capped"] is False


# =============================================================================
# Structured Reconciliation tests (Item 4)
# =============================================================================


class TestStructuredReconciliation:
    """Test structured reconciliation fields on counter-signals."""

    def test_all_three_fields_no_warning(self):
        """All 3 structured fields populated with substantive evidence → reconciled.

        Only the low-signal-count warning fires (1 signal < 2 minimum).
        """
        signals = json.dumps(
            [
                {
                    "signal": "No evidence users want this",
                    "source": "risk_assessment",
                    "affected_dimensions": ["Problem Severity"],
                    "evidence_cited": "3 competitors funded in 2024 validates market demand",
                    "why_score_holds": "Score is 4 based on competitor validation",
                    "what_would_change_score": "If all competitors pivoted away",
                },
            ]
        )
        result = _call_evaluate_recommendation(
            knockout_results=_knockouts_pass(),
            dimension_scores=_dimensions_high(),
            counter_signals=signals,
        )
        # No inconsistency warnings, only the low-signal-count warning
        assert all("scored" not in w for w in result["warnings"])
        assert result["adjusted"] is False

    def test_partial_fields_warning(self):
        """Only 2 of 3 structured fields → not reconciled, warning on high-scored dim.

        Plus low-signal-count warning (1 signal < 2 minimum) → penalty triggers.
        """
        signals = json.dumps(
            [
                {
                    "signal": "No evidence",
                    "source": "risk_assessment",
                    "affected_dimensions": ["Problem Severity"],
                    "evidence_cited": "Some evidence",
                    "why_score_holds": "Score justified",
                    # Missing what_would_change_score
                },
            ]
        )
        result = _call_evaluate_recommendation(
            knockout_results=_knockouts_pass(),
            dimension_scores=_dimensions_high(),
            counter_signals=signals,
        )
        assert len(result["warnings"]) == 2
        assert any("Problem Severity" in w for w in result["warnings"])
        assert any("counter-signal(s) recorded" in w for w in result["warnings"])

    def test_legacy_reconciliation_still_works(self):
        """Legacy reconciliation text ≥ 20 chars still counts as reconciled.

        Only the low-signal-count warning fires (1 signal < 2 minimum).
        """
        signals = json.dumps(
            [
                {
                    "signal": "Market size unverified",
                    "source": "risk_assessment",
                    "affected_dimensions": ["Problem Severity"],
                    "reconciliation": "Score was lowered from 5 to 4 because market data is limited but adjacency supports it",
                },
            ]
        )
        result = _call_evaluate_recommendation(
            knockout_results=_knockouts_pass(),
            dimension_scores=_dimensions_high(),
            counter_signals=signals,
        )
        # No inconsistency warnings, only the low-signal-count warning
        assert all("scored" not in w for w in result["warnings"])

    def test_model_backward_compat(self):
        """CounterSignal model accepts old format (reconciliation only)."""
        cs = CounterSignal(
            signal="Test signal",
            source="risk_assessment",
            affected_dimensions=["Market Opportunity"],
            reconciliation="This is the old-style reconciliation text",
        )
        assert cs.evidence_cited == ""
        assert cs.why_score_holds == ""
        assert cs.what_would_change_score == ""

    def test_structured_fields_in_to_markdown(self):
        """Structured fields render in markdown output."""
        cs = CounterSignal(
            signal="Market size unverified",
            source="risk_assessment",
            affected_dimensions=["Market Opportunity"],
            evidence_cited="Competitor analysis shows 3 funded players",
            why_score_holds="Score is 3 not 4, already conservative",
            what_would_change_score="If market data showed < $10M TAM",
        )
        scorecard = GoNoGoScorecard(
            knockout_criteria=[
                KnockoutCriterion(
                    criterion="Problem Reality",
                    result=KnockoutResult.PASS,
                    evidence="Confirmed",
                ),
            ],
            counter_signals=[cs],
            scorecard=[
                ScorecardDimension(dimension="Problem Severity", score=4, evidence="Users pay"),
            ],
            composite_score=4.0,
            verdict="GO",
            critical_gaps=[],
            guidance="Proceed",
        )
        output = ValidationSummaryOutput(
            executive_summary="Test",
            recommendation="GO",
            confidence="HIGH",
            lean_canvas={
                "problems": ["P1"],
                "customer_segments": ["S1"],
                "unique_value_proposition": "UVP",
                "solution": ["S1"],
                "revenue_model": "SaaS",
            },
            validation_findings={
                "market_opportunity": "Large",
                "competition": "Low",
                "critical_risks": ["R1"],
            },
            go_no_go_assessment=scorecard,
            next_steps=["Step 1"],
        )
        md = output.to_markdown()
        assert "Evidence cited:" in md
        assert "Why score holds:" in md
        assert "What would change score:" in md
        assert "Reconciliation:" not in md


# =============================================================================
# Reconciliation quality gate tests (Fix 3)
# =============================================================================


class TestReconciliationQualityGate:
    """Test that circular/vacuous evidence is rejected by _is_signal_reconciled."""

    def test_circular_evidence_not_reconciled(self):
        """Circular phrase in evidence_cited → not reconciled.

        Plus low-signal-count warning (1 signal < 2 minimum) → penalty triggers.
        """
        signals = json.dumps(
            [
                {
                    "signal": "No evidence users want this",
                    "source": "risk_assessment",
                    "affected_dimensions": ["Problem Severity"],
                    "evidence_cited": "Score is conservative based on potential benefits of the concept",
                    "why_score_holds": "Score reflects current understanding",
                    "what_would_change_score": "Direct user feedback",
                },
            ]
        )
        result = _call_evaluate_recommendation(
            knockout_results=_knockouts_pass(),
            dimension_scores=_dimensions_high(),
            counter_signals=signals,
        )
        assert len(result["warnings"]) == 2
        assert any("Problem Severity" in w for w in result["warnings"])
        assert any("counter-signal(s) recorded" in w for w in result["warnings"])

    def test_short_evidence_not_reconciled(self):
        """evidence_cited < 30 chars → not reconciled.

        Plus low-signal-count warning (1 signal < 2 minimum) → penalty triggers.
        """
        signals = json.dumps(
            [
                {
                    "signal": "Market size unverified",
                    "source": "risk_assessment",
                    "affected_dimensions": ["Market Opportunity"],
                    "evidence_cited": "Some data exists",
                    "why_score_holds": "Score is reasonable",
                    "what_would_change_score": "More data",
                },
            ]
        )
        result = _call_evaluate_recommendation(
            knockout_results=_knockouts_pass(),
            dimension_scores=_dimensions_high(),
            counter_signals=signals,
        )
        assert len(result["warnings"]) == 2
        assert any("Market Opportunity" in w for w in result["warnings"])
        assert any("counter-signal(s) recorded" in w for w in result["warnings"])

    def test_substantive_evidence_reconciled(self):
        """Substantive evidence (>= 30 chars, no circular phrases) → reconciled.

        Only the low-signal-count warning fires (1 signal < 2 minimum).
        """
        signals = json.dumps(
            [
                {
                    "signal": "High regulatory risk",
                    "source": "risk_assessment",
                    "affected_dimensions": ["Problem Severity"],
                    "evidence_cited": "Competitor analysis confirms 3 funded startups operating in this regulated space with FDA approval",
                    "why_score_holds": "Market exists despite regulation",
                    "what_would_change_score": "If FDA changes rules to block new entrants",
                },
            ]
        )
        result = _call_evaluate_recommendation(
            knockout_results=_knockouts_pass(),
            dimension_scores=_dimensions_high(),
            counter_signals=signals,
        )
        # No inconsistency warnings, only the low-signal-count warning
        assert all("scored" not in w for w in result["warnings"])
        assert result["adjusted"] is False

    def test_circular_evidence_blocks_risk_veto_override(self):
        """Circular evidence should not count as well-reconciled for risk veto override.

        With circular evidence on 2 high-scored dims, unreconciled counter-signals
        trigger the -0.5 penalty (4.0 → 3.5 → PIVOT). The risk veto doesn't fire
        because the verdict is already PIVOT. We verify the well-reconciled count
        directly to confirm circular evidence is rejected.
        """
        mod = _import_recommendation()
        signals = [
            {
                "signal": "Signal A",
                "source": "risk_assessment",
                "affected_dimensions": ["Problem Severity"],
                "evidence_cited": "Score is conservative based on potential market opportunity",
                "why_score_holds": "Score reflects reality",
                "what_would_change_score": "Direct feedback",
            },
            {
                "signal": "Signal B",
                "source": "market_context",
                "affected_dimensions": ["Market Opportunity"],
                "evidence_cited": "Already accounted for in the scoring methodology",
                "why_score_holds": "Score is appropriate",
                "what_would_change_score": "New data",
            },
        ]
        # Circular evidence → 0 well-reconciled signals (below the 2 threshold)
        assert mod._count_well_reconciled_signals(signals) == 0

        # And the overall result is PIVOT (due to penalty from unreconciled signals)
        result = _call_evaluate_recommendation(
            knockout_results=_knockouts_pass(),
            dimension_scores=_dimensions_high(),
            counter_signals=json.dumps(signals),
            risk_level="HIGH",
        )
        assert result["recommendation"] == "PIVOT"
