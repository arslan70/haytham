"""Tests for the ValidationReport model."""

import json

from haytham.agents.worker_report_synthesis.report_synthesis_models import (
    ExecutiveSummary,
    Recommendation,
    ValidationReport,
)

_SAMPLE_SUMMARY = ExecutiveSummary(
    idea_in_one_line="A platform connecting gym owners with freelance trainers.",
    strongest_point="Clear pain point validated by 3 competitor exits in this space.",
    recommendation_summary="Go ahead, but validate pricing with gym owners first.",
    recommendation_reasoning="Strong demand signal, but unit economics are unproven.",
    competitive_snapshot="GymNet and FitMatch dominate, but neither serves small gyms.",
    closing_remark="Interview 10 independent gym owners about trainer scheduling pain.",
)


class TestRecommendationEnum:
    def test_go_value(self):
        assert Recommendation.GO == "GO"

    def test_pivot_value(self):
        assert Recommendation.PIVOT == "PIVOT"

    def test_no_go_value(self):
        assert Recommendation.NO_GO == "NO-GO"


class TestExecutiveSummary:
    def test_all_fields_present(self):
        s = _SAMPLE_SUMMARY
        assert s.idea_in_one_line.startswith("A platform")
        assert s.strongest_point
        assert s.recommendation_summary
        assert s.recommendation_reasoning
        assert s.competitive_snapshot
        assert s.closing_remark

    def test_round_trip(self):
        data = json.loads(_SAMPLE_SUMMARY.model_dump_json())
        restored = ExecutiveSummary.model_validate(data)
        assert restored.idea_in_one_line == _SAMPLE_SUMMARY.idea_in_one_line
        assert restored.closing_remark == _SAMPLE_SUMMARY.closing_remark


class TestValidationReport:
    def test_round_trip(self):
        report = ValidationReport(
            recommendation=Recommendation.GO,
            executive_summary=_SAMPLE_SUMMARY,
            report="# Test Report\n\nContent here",
        )
        data = json.loads(report.model_dump_json())
        restored = ValidationReport.model_validate(data)
        assert restored.recommendation == Recommendation.GO
        assert restored.executive_summary.idea_in_one_line == _SAMPLE_SUMMARY.idea_in_one_line
        assert restored.report == "# Test Report\n\nContent here"

    def test_accepts_markdown(self):
        long_report = "## Section 1\n\n" * 100
        report = ValidationReport(
            recommendation=Recommendation.PIVOT,
            executive_summary=_SAMPLE_SUMMARY,
            report=long_report,
        )
        assert len(report.report) > 1000

    def test_to_markdown_excludes_executive_summary(self):
        """Executive summary lives only in AT A GLANCE (PDF cover), not in markdown."""
        report = ValidationReport(
            recommendation=Recommendation.GO,
            executive_summary=_SAMPLE_SUMMARY,
            report="# Validation Report\n\nBody here.",
        )
        md = report.to_markdown()
        assert "## Recommendation: GO" in md
        assert "# Validation Report" in md
        assert "Body here." in md
        # Executive summary must NOT appear in markdown (it's in recommendation.json only)
        assert "Executive Summary" not in md
        assert "In a nutshell" not in md
