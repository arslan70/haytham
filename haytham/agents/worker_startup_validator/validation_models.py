"""Pydantic models for structured validation output.

These models define the schema for the startup validator agent's output,
ensuring type-safe, validated responses with both structured data and
a human-readable summary.
"""

from pydantic import BaseModel, Field


class Claim(BaseModel):
    """A validated claim about the startup."""

    id: str = Field(description="Unique claim identifier (e.g., 'C1', 'C2')")
    text: str = Field(description="The claim text")
    type: str = Field(
        description="Claim type: market_claim, product_claim, financial_claim, or operational_claim"
    )
    origin: str = Field(
        description="Claim origin: 'internal' (verified from idea description) or 'external' (requires market evidence)",
        default="external",
    )
    source: str = Field(description="Source agent that made this claim")
    severity: str = Field(
        default="major",
        description=(
            "Claim severity: 'critical' (existential threat if wrong — e.g. safety, "
            "legal, core revenue), 'major' (significant impact on viability), "
            "'minor' (marginal impact, nice-to-validate)"
        ),
    )
    validation: str = Field(
        description="Validation result: supported, partial, unsupported, or contradicted"
    )
    reasoning: str = Field(description="Brief explanation of the validation result")


class Risk(BaseModel):
    """An identified risk based on validation results."""

    id: str = Field(description="Unique risk identifier (e.g., 'R1', 'R2')")
    level: str = Field(description="Risk level: high, medium, or low")
    claim_id: str = Field(description="ID of the related claim")
    description: str = Field(description="Description of the risk")
    mitigation: str = Field(description="Suggested mitigation strategy")


class ValidationSummary(BaseModel):
    """Summary statistics for the validation."""

    total_claims: int = Field(description="Total number of claims analyzed")
    supported: int = Field(description="Number of claims supported by evidence")
    partial: int = Field(description="Number of claims with partial support")
    unsupported: int = Field(description="Number of claims without support")
    contradicted: int = Field(default=0, description="Number of contradicted claims")
    high_risks: int = Field(description="Number of high-priority risks")
    medium_risks: int = Field(description="Number of medium-priority risks")


class ValidationOutput(BaseModel):
    """Complete validation output with structured data and human summary.

    This model is used with Strands structured_output_model to ensure
    the agent returns properly formatted, validated output.
    """

    claims: list[Claim] = Field(description="List of validated claims")
    risks: list[Risk] = Field(description="List of identified risks")
    summary: ValidationSummary = Field(description="Summary statistics")
    overall_risk_level: str = Field(
        description=(
            "The overall risk level for this startup: HIGH, MEDIUM, or LOW. "
            "HIGH: Multiple critical claims unsupported/contradicted, or 2+ high-severity risks. "
            "MEDIUM: Some concerns but core value proposition is supported, 1 high or multiple medium risks. "
            "LOW: Most claims supported with minor risks only."
        )
    )
    human_summary: str = Field(
        default="",
        deprecated="No longer rendered. Leave empty. Will be removed in a future release.",
        description="Legacy human-readable summary. No longer used.",
    )

    def to_markdown(self) -> str:
        """Convert the validation output to formatted markdown."""
        lines = [
            "# Validation Results",
            "",
            f"## Overall Risk Level: {self.overall_risk_level.upper()}",
            "",
            "## Validation Statistics",
            "",
            f"- **Total Claims Analyzed:** {self.summary.total_claims}",
            f"- **Supported:** {self.summary.supported}",
            f"- **Partial Support:** {self.summary.partial}",
            f"- **Unsupported:** {self.summary.unsupported}",
            f"- **High Risks:** {self.summary.high_risks}",
            f"- **Medium Risks:** {self.summary.medium_risks}",
            "",
        ]

        if self.claims:
            lines.append("## Validated Claims")
            lines.append("")
            validation_emoji = {
                "supported": "\u2705",
                "partial": "\u26a0\ufe0f",
                "unsupported": "\u274c",
                "contradicted": "\U0001f6ab",
            }
            for claim in self.claims:
                emoji = validation_emoji.get(claim.validation.lower(), "\u2753")
                lines.append(f"### {claim.id}: {claim.text[:100]}")
                lines.append(f"- **Type:** {claim.type}")
                lines.append(f"- **Origin:** {claim.origin}")
                lines.append(f"- **Severity:** {claim.severity}")
                lines.append(f"- **Source:** {claim.source}")
                lines.append(f"- **Validation:** {emoji} {claim.validation}")
                lines.append(f"- **Reasoning:** {claim.reasoning}")
                lines.append("")

        if self.risks:
            lines.append("## Identified Risks")
            lines.append("")
            risk_emoji = {"high": "\U0001f534", "medium": "\U0001f7e1", "low": "\U0001f7e2"}
            for risk in self.risks:
                emoji = risk_emoji.get(risk.level.lower(), "\u26aa")
                lines.append(f"### {risk.id}: {emoji} {risk.level.upper()} Risk")
                lines.append(f"- **Related Claim:** {risk.claim_id}")
                lines.append(f"- **Description:** {risk.description}")
                lines.append(f"- **Mitigation:** {risk.mitigation}")
                lines.append("")

        return "\n".join(lines)
