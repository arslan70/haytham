"""Tests for the ValidationReport model."""

import json

from haytham.agents.worker_report_synthesis.report_synthesis_models import (
    Recommendation,
    ValidationReport,
)


class TestRecommendationEnum:
    def test_go_value(self):
        assert Recommendation.GO == "GO"

    def test_pivot_value(self):
        assert Recommendation.PIVOT == "PIVOT"

    def test_no_go_value(self):
        assert Recommendation.NO_GO == "NO-GO"


class TestValidationReport:
    def test_round_trip(self):
        report = ValidationReport(
            recommendation=Recommendation.GO,
            report="# Test Report\n\nContent here",
        )
        data = json.loads(report.model_dump_json())
        restored = ValidationReport.model_validate(data)
        assert restored.recommendation == Recommendation.GO
        assert restored.report == "# Test Report\n\nContent here"

    def test_accepts_markdown(self):
        long_report = "## Section 1\n\n" * 100
        report = ValidationReport(
            recommendation=Recommendation.PIVOT,
            report=long_report,
        )
        assert len(report.report) > 1000
