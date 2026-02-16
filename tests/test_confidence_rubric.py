"""Tests for deterministic confidence rubric.

Covers:
- _compute_confidence_hint in recommendation tool
- _apply_confidence_rubric in idea_validation post-processor
- _count_contradicted_critical parser
- Edge cases: borderlines, empty inputs, zero external claims
"""

import importlib
import json
import sys
from unittest import mock

# =============================================================================
# Helpers to import modules with heavy transitive deps
# =============================================================================


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


def _import_idea_validation():
    """Import idea_validation module, mocking burr if absent."""
    if "burr" not in sys.modules and "burr.core" not in sys.modules:
        burr_mock = mock.MagicMock()
        sys.modules.setdefault("burr", burr_mock)
        sys.modules.setdefault("burr.core", burr_mock)
    return importlib.import_module("haytham.workflow.stages.idea_validation")


# =============================================================================
# _compute_confidence_hint (tool-level)
# =============================================================================


class TestComputeConfidenceHint:
    """Test the confidence hint function in the recommendation tool."""

    def setup_method(self):
        self.mod = _import_recommendation()
        self.compute = self.mod._compute_confidence_hint

    def test_empty_dict_returns_none(self):
        assert self.compute({}) is None

    def test_contradicted_critical_returns_low(self):
        result = self.compute(
            {
                "external_supported": 5,
                "external_total": 6,
                "contradicted_critical": 1,
                "risk_level": "LOW",
            }
        )
        assert result == "LOW"

    def test_high_risk_weak_external_returns_low(self):
        result = self.compute(
            {
                "external_supported": 2,
                "external_total": 6,
                "contradicted_critical": 0,
                "risk_level": "HIGH",
            }
        )
        assert result == "LOW"

    def test_high_risk_strong_external_returns_medium(self):
        result = self.compute(
            {
                "external_supported": 4,
                "external_total": 6,
                "contradicted_critical": 0,
                "risk_level": "HIGH",
            }
        )
        assert result == "MEDIUM"

    def test_low_external_pct_returns_low(self):
        """< 40% external supported → LOW."""
        result = self.compute(
            {
                "external_supported": 1,
                "external_total": 5,
                "contradicted_critical": 0,
                "risk_level": "MEDIUM",
            }
        )
        assert result == "LOW"

    def test_medium_external_pct_returns_medium(self):
        """40–69% external supported → MEDIUM."""
        result = self.compute(
            {
                "external_supported": 3,
                "external_total": 6,
                "contradicted_critical": 0,
                "risk_level": "MEDIUM",
            }
        )
        assert result == "MEDIUM"

    def test_high_external_pct_returns_high(self):
        """≥ 70% external supported → HIGH."""
        result = self.compute(
            {
                "external_supported": 5,
                "external_total": 6,
                "contradicted_critical": 0,
                "risk_level": "LOW",
            }
        )
        assert result == "HIGH"

    def test_zero_external_returns_none(self):
        result = self.compute(
            {
                "external_supported": 0,
                "external_total": 0,
                "contradicted_critical": 0,
                "risk_level": "LOW",
            }
        )
        assert result is None

    def test_borderline_40_pct(self):
        """Exactly 40% → MEDIUM (not LOW)."""
        result = self.compute(
            {
                "external_supported": 2,
                "external_total": 5,
                "contradicted_critical": 0,
                "risk_level": "LOW",
            }
        )
        assert result == "MEDIUM"

    def test_borderline_70_pct(self):
        """Exactly 70% → HIGH."""
        result = self.compute(
            {
                "external_supported": 7,
                "external_total": 10,
                "contradicted_critical": 0,
                "risk_level": "LOW",
            }
        )
        assert result == "HIGH"

    def test_borderline_50_pct_high_risk(self):
        """Exactly 50% with HIGH risk → MEDIUM."""
        result = self.compute(
            {
                "external_supported": 3,
                "external_total": 6,
                "contradicted_critical": 0,
                "risk_level": "HIGH",
            }
        )
        assert result == "MEDIUM"

    def test_contradicted_critical_overrides_good_external(self):
        """Contradicted critical → LOW even with 100% external support."""
        result = self.compute(
            {
                "external_supported": 6,
                "external_total": 6,
                "contradicted_critical": 1,
                "risk_level": "LOW",
            }
        )
        assert result == "LOW"


# =============================================================================
# _apply_confidence_rubric (post-processor level)
# =============================================================================


class TestApplyConfidenceRubric:
    """Test the post-processor confidence rubric."""

    def setup_method(self):
        self.mod = _import_idea_validation()
        self.rubric = self.mod._apply_confidence_rubric

    def test_contradicted_critical_returns_low(self):
        assert self.rubric(5, 6, 1, "LOW") == "LOW"

    def test_high_risk_weak_returns_low(self):
        assert self.rubric(2, 6, 0, "HIGH") == "LOW"

    def test_high_risk_strong_returns_medium(self):
        assert self.rubric(4, 6, 0, "HIGH") == "MEDIUM"

    def test_low_pct_returns_low(self):
        assert self.rubric(1, 5, 0, "MEDIUM") == "LOW"

    def test_medium_pct_returns_medium(self):
        assert self.rubric(3, 6, 0, "MEDIUM") == "MEDIUM"

    def test_high_pct_returns_high(self):
        assert self.rubric(5, 6, 0, "LOW") == "HIGH"

    def test_zero_total_returns_medium(self):
        """No external claims → default MEDIUM."""
        assert self.rubric(0, 0, 0, "LOW") == "MEDIUM"


# =============================================================================
# _count_contradicted_critical (parser)
# =============================================================================


class TestCountContradictedCritical:
    """Test extraction of contradicted critical claims from markdown."""

    def setup_method(self):
        self.mod = _import_idea_validation()
        self.count = self.mod._count_contradicted_critical

    def test_one_contradicted_critical(self):
        text = (
            "| C1 | Audio is unsafe | product_claim | external | critical | contradicted | FDA prohibits |\n"
            "| C2 | Market is large | market_claim | external | major | supported | Data confirms |\n"
        )
        assert self.count(text) == 1

    def test_no_contradicted_critical(self):
        text = (
            "| C1 | Market is large | market_claim | external | major | supported | Data confirms |\n"
            "| C2 | Revenue viable | financial_claim | external | major | partial | Some evidence |\n"
        )
        assert self.count(text) == 0

    def test_contradicted_but_not_critical(self):
        text = "| C1 | Minor thing | product_claim | internal | minor | contradicted | Evidence says no |\n"
        assert self.count(text) == 0

    def test_critical_but_not_contradicted(self):
        text = (
            "| C1 | Safety claim | product_claim | external | critical | supported | Confirmed |\n"
        )
        assert self.count(text) == 0

    def test_multiple_contradicted_critical(self):
        text = (
            "| C1 | Safety | product_claim | external | critical | contradicted | No |\n"
            "| C2 | Legal | product_claim | external | critical | contradicted | Blocked |\n"
            "| C3 | Market | market_claim | external | major | supported | Yes |\n"
        )
        assert self.count(text) == 2

    def test_empty_text(self):
        assert self.count("") == 0


# =============================================================================
# Confidence hint via tool integration
# =============================================================================


class TestConfidenceHintInTool:
    """Test that the tool returns confidence_hint when evidence_quality is provided."""

    def _call(self, **kwargs):
        mod = _import_recommendation()
        return json.loads(mod.evaluate_recommendation(**kwargs))

    def _knockouts_pass(self):
        return json.dumps(
            [
                {"criterion": "Problem Reality", "result": "PASS", "evidence": "Confirmed"},
            ]
        )

    def _dimensions_high(self):
        return json.dumps(
            [
                {"dimension": "Problem Severity", "score": 4, "evidence": "..."},
                {"dimension": "Market Opportunity", "score": 4, "evidence": "..."},
                {"dimension": "Solution Feasibility", "score": 4, "evidence": "..."},
                {"dimension": "Revenue Viability", "score": 4, "evidence": "..."},
            ]
        )

    def test_with_evidence_quality(self):
        eq = json.dumps(
            {
                "external_supported": 5,
                "external_total": 6,
                "contradicted_critical": 0,
                "risk_level": "LOW",
            }
        )
        result = self._call(
            knockout_results=self._knockouts_pass(),
            dimension_scores=self._dimensions_high(),
            evidence_quality=eq,
        )
        assert result["confidence_hint"] == "HIGH"

    def test_without_evidence_quality(self):
        result = self._call(
            knockout_results=self._knockouts_pass(),
            dimension_scores=self._dimensions_high(),
        )
        assert result["confidence_hint"] is None

    def test_empty_evidence_quality(self):
        result = self._call(
            knockout_results=self._knockouts_pass(),
            dimension_scores=self._dimensions_high(),
            evidence_quality="{}",
        )
        assert result["confidence_hint"] is None
