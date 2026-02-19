"""Tests for verdict driver rendering in ValidationSummaryOutput.to_markdown()."""

from haytham.agents.worker_validation_summary.validation_summary_models import (
    GoNoGoScorecard,
    KnockoutCriterion,
    KnockoutResult,
    LeanCanvas,
    ScorecardDimension,
    ValidationFindings,
    ValidationSummaryOutput,
)


def _make_scorecard(**overrides) -> GoNoGoScorecard:
    """Build a minimal GoNoGoScorecard with optional overrides."""
    defaults = {
        "knockout_criteria": [
            KnockoutCriterion(
                criterion="Problem Reality", result=KnockoutResult.PASS, evidence="e"
            ),
        ],
        "scorecard": [
            ScorecardDimension(dimension="Problem Severity", score=3, evidence="e"),
        ],
        "composite_score": 3.0,
        "verdict": "PIVOT",
        "critical_gaps": [],
        "guidance": "Next steps here.",
    }
    defaults.update(overrides)
    return GoNoGoScorecard(**defaults)


def _make_summary(scorecard: GoNoGoScorecard) -> ValidationSummaryOutput:
    """Build a minimal ValidationSummaryOutput wrapping the given scorecard."""
    return ValidationSummaryOutput(
        executive_summary="Test summary.",
        recommendation="PIVOT",
        lean_canvas=LeanCanvas(
            problems=["p1"],
            customer_segments=["s1"],
            unique_value_proposition="uvp",
            solution=["sol"],
            revenue_model="rev",
        ),
        validation_findings=ValidationFindings(
            market_opportunity="mo",
            competition="comp",
            critical_risks=["r1"],
        ),
        go_no_go_assessment=scorecard,
        next_steps=["step1"],
    )


def test_verdict_drivers_floor_capped():
    """When floor_capped=True + critical_gaps present, renders floor driver."""
    sc = _make_scorecard(
        floor_capped=True,
        critical_gaps=["Revenue Viability"],
    )
    md = _make_summary(sc).to_markdown()
    assert "### Verdict Drivers" in md
    assert "Score floor triggered" in md
    assert "Revenue Viability (≤2)" in md
    assert "cap composite at 3.0" in md


def test_verdict_drivers_risk_capped():
    """When risk_capped=True, renders risk override driver."""
    sc = _make_scorecard(risk_capped=True)
    md = _make_summary(sc).to_markdown()
    assert "### Verdict Drivers" in md
    assert "HIGH risk level overrides GO verdict → PIVOT" in md


def test_verdict_drivers_both():
    """Both flags → both drivers rendered."""
    sc = _make_scorecard(
        floor_capped=True,
        risk_capped=True,
        critical_gaps=["Problem Severity", "Revenue Viability"],
    )
    md = _make_summary(sc).to_markdown()
    assert "### Verdict Drivers" in md
    assert "Score floor triggered" in md
    assert "Problem Severity (≤2)" in md
    assert "Revenue Viability (≤2)" in md
    assert "HIGH risk level overrides GO verdict → PIVOT" in md


def test_no_verdict_drivers_when_go():
    """When floor_capped=False and risk_capped=False, no Verdict Drivers section."""
    sc = _make_scorecard(
        floor_capped=False,
        risk_capped=False,
        verdict="GO",
    )
    md = _make_summary(sc).to_markdown()
    assert "### Verdict Drivers" not in md


def test_floor_capped_without_critical_gaps_no_floor_driver():
    """floor_capped=True but no critical_gaps → no floor driver line."""
    sc = _make_scorecard(floor_capped=True, critical_gaps=[])
    md = _make_summary(sc).to_markdown()
    assert "Score floor triggered" not in md
