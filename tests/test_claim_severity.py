"""Tests for claim severity field on validation models.

Covers:
- Claim model default severity
- Claim severity values
- ValidationSummary contradicted field
- Markdown rendering includes severity
"""

from haytham.agents.worker_startup_validator.validation_models import (
    Claim,
    ValidationOutput,
    ValidationSummary,
)


class TestClaimSeverityField:
    """Test the severity field on the Claim model."""

    def test_default_severity_is_major(self):
        claim = Claim(
            id="C1",
            text="Test claim",
            type="market_claim",
            origin="external",
            source="idea_analysis",
            validation="supported",
            reasoning="Evidence found",
        )
        assert claim.severity == "major"

    def test_critical_severity(self):
        claim = Claim(
            id="C1",
            text="Audio is unsafe for mental health",
            type="product_claim",
            origin="external",
            source="risk_assessment",
            severity="critical",
            validation="contradicted",
            reasoning="FDA guidelines prohibit this",
        )
        assert claim.severity == "critical"

    def test_minor_severity(self):
        claim = Claim(
            id="C1",
            text="Four themes may not cover all needs",
            type="product_claim",
            origin="internal",
            source="idea_analysis",
            severity="minor",
            validation="partial",
            reasoning="Most users only need 3",
        )
        assert claim.severity == "minor"

    def test_severity_in_markdown(self):
        claim = Claim(
            id="C1",
            text="Test claim",
            type="market_claim",
            origin="external",
            source="idea_analysis",
            severity="critical",
            validation="contradicted",
            reasoning="Evidence contradicts",
        )
        output = ValidationOutput(
            claims=[claim],
            risks=[],
            summary=ValidationSummary(
                total_claims=1,
                supported=0,
                partial=0,
                unsupported=0,
                contradicted=1,
                high_risks=0,
                medium_risks=0,
            ),
            overall_risk_level="HIGH",
            human_summary="Test summary",
        )
        md = output.to_markdown()
        assert "**Severity:** critical" in md


class TestValidationSummaryContradicted:
    """Test the contradicted field on ValidationSummary."""

    def test_default_contradicted_is_zero(self):
        summary = ValidationSummary(
            total_claims=10,
            supported=8,
            partial=1,
            unsupported=1,
            high_risks=0,
            medium_risks=1,
        )
        assert summary.contradicted == 0

    def test_explicit_contradicted(self):
        summary = ValidationSummary(
            total_claims=10,
            supported=7,
            partial=1,
            unsupported=1,
            contradicted=1,
            high_risks=1,
            medium_risks=0,
        )
        assert summary.contradicted == 1

    def test_backward_compat_no_contradicted(self):
        """Existing code creating ValidationSummary without contradicted still works."""
        summary = ValidationSummary(
            total_claims=5,
            supported=3,
            partial=1,
            unsupported=1,
            high_risks=0,
            medium_risks=0,
        )
        assert summary.contradicted == 0
