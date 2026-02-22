"""Tests for post-synthesis guardrails."""

import json
from unittest.mock import MagicMock

from haytham.workflow.validators.report_guardrails import (
    validate_regulated_domain_safety,
    validate_som_arithmetic,
)


def _make_output(recommendation="GO", report=""):
    return json.dumps({"recommendation": recommendation, "report": report})


def _make_state(system_goal=""):
    """Create a mock state with a proper system_goal string."""
    state = MagicMock()
    state.get.side_effect = lambda key, default="": system_goal if key == "system_goal" else default
    return state


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
        warnings = validate_regulated_domain_safety(output, _make_state("A todo list app"))
        assert warnings == []

    def test_hipaa_with_go_warns(self):
        output = _make_output(recommendation="GO", report="Must comply with HIPAA regulations")
        warnings = validate_regulated_domain_safety(output, _make_state("A todo list app"))
        assert len(warnings) == 1
        assert "HIPAA" in warnings[0]

    def test_hipaa_with_pivot_no_warning(self):
        """PIVOT recommendations don't trigger the GO+compliance warning."""
        output = _make_output(recommendation="PIVOT", report="Must comply with HIPAA regulations")
        warnings = validate_regulated_domain_safety(output, _make_state("A todo list app"))
        assert warnings == []

    def test_multiple_keywords_listed(self):
        output = _make_output(recommendation="GO", report="HIPAA and GDPR compliance needed")
        warnings = validate_regulated_domain_safety(output, _make_state("A todo list app"))
        assert len(warnings) == 1
        assert "HIPAA" in warnings[0]
        assert "GDPR" in warnings[0]

    # --- New: domain-signal detection tests ---

    def test_health_idea_missing_hipaa_warns(self):
        """A health/therapy idea that doesn't mention HIPAA gets flagged."""
        output = _make_output(
            recommendation="PIVOT",
            report="Regulatory barriers for patient data anonymity.",
        )
        state = _make_state("A psychologist wants to develop a therapy app for patients")
        warnings = validate_regulated_domain_safety(output, state)
        assert any("HIPAA" in w for w in warnings)
        assert any("health" in w.lower() or "therapy" in w.lower() for w in warnings)

    def test_health_idea_with_hipaa_no_domain_warning(self):
        """A health idea that DOES mention HIPAA gets no domain-missing warning."""
        output = _make_output(
            recommendation="PIVOT",
            report="HIPAA compliance required. Estimated cost $10K-$30K for BAAs.",
        )
        state = _make_state("A psychologist wants to develop a therapy app for patients")
        warnings = validate_regulated_domain_safety(output, state)
        # No "missing HIPAA" warning (HIPAA is present in report)
        assert not any("does not mention HIPAA" in w for w in warnings)

    def test_fintech_idea_missing_pci_warns(self):
        """A fintech idea that doesn't mention PCI-DSS gets flagged."""
        output = _make_output(recommendation="GO", report="Simple payment processing app.")
        state = _make_state("A payment processing tool for small businesses")
        warnings = validate_regulated_domain_safety(output, state)
        assert any("PCI-DSS" in w for w in warnings)

    def test_children_idea_missing_coppa_warns(self):
        """A children's app that doesn't mention COPPA gets flagged."""
        output = _make_output(recommendation="GO", report="Educational game for young learners.")
        state = _make_state("An educational app for children under 13")
        warnings = validate_regulated_domain_safety(output, state)
        assert any("COPPA" in w for w in warnings)

    def test_non_regulated_idea_no_domain_warning(self):
        """A non-regulated idea doesn't trigger domain warnings."""
        output = _make_output(recommendation="GO", report="Simple task management tool.")
        state = _make_state("A project management tool for remote teams")
        warnings = validate_regulated_domain_safety(output, state)
        assert warnings == []

    def test_mock_state_without_system_goal_is_safe(self):
        """Passing a MagicMock without configured system_goal doesn't crash."""
        output = _make_output(recommendation="GO", report="A simple web app")
        warnings = validate_regulated_domain_safety(output, MagicMock())
        assert isinstance(warnings, list)
