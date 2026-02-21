"""Tests for post-synthesis guardrails."""

import json
from unittest.mock import MagicMock

from haytham.workflow.validators.report_guardrails import (
    validate_regulated_domain_safety,
    validate_som_arithmetic,
)


def _make_output(recommendation="GO", report=""):
    return json.dumps({"recommendation": recommendation, "report": report})


class TestSomArithmetic:
    def test_no_som_no_warning(self):
        output = _make_output(report="No market sizing here")
        warnings = validate_som_arithmetic(output, MagicMock())
        assert warnings == []

    def test_single_som_no_warning(self):
        output = _make_output(report="SOM $500K based on local market")
        warnings = validate_som_arithmetic(output, MagicMock())
        assert warnings == []

    def test_matching_som_no_warning(self):
        output = _make_output(report="SOM $500K ... our SOM of $500K")
        warnings = validate_som_arithmetic(output, MagicMock())
        assert warnings == []

    def test_mismatched_som_warns(self):
        output = _make_output(report="SOM $320K in summary ... SOM $3.2M in breakdown")
        warnings = validate_som_arithmetic(output, MagicMock())
        assert len(warnings) == 1
        assert "mismatch" in warnings[0].lower() or "SOM" in warnings[0]


class TestRegulatedDomainSafety:
    def test_no_keywords_no_warning(self):
        output = _make_output(recommendation="GO", report="A simple web app")
        warnings = validate_regulated_domain_safety(output, MagicMock())
        assert warnings == []

    def test_hipaa_with_go_warns(self):
        output = _make_output(recommendation="GO", report="Must comply with HIPAA regulations")
        warnings = validate_regulated_domain_safety(output, MagicMock())
        assert len(warnings) == 1
        assert "HIPAA" in warnings[0]

    def test_hipaa_with_pivot_no_warning(self):
        output = _make_output(recommendation="PIVOT", report="Must comply with HIPAA regulations")
        warnings = validate_regulated_domain_safety(output, MagicMock())
        assert warnings == []

    def test_multiple_keywords_listed(self):
        output = _make_output(recommendation="GO", report="HIPAA and GDPR compliance needed")
        warnings = validate_regulated_domain_safety(output, MagicMock())
        assert len(warnings) == 1
        assert "HIPAA" in warnings[0]
        assert "GDPR" in warnings[0]
