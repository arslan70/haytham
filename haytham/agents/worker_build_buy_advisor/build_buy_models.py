"""Pydantic models for structured Build vs Buy analysis output.

These models define the schema for the build_buy_analyzer agent's output,
ensuring type-safe, validated responses with clear structure for UI display.
"""

from __future__ import annotations

import json
from enum import Enum

from pydantic import BaseModel, Field, ValidationError


class RecommendationType(str, Enum):
    """Recommendation type for a capability or service."""

    BUILD = "BUILD"
    BUY = "BUY"
    HYBRID = "HYBRID"


class InfrastructureRequirement(BaseModel):
    """A high-level infrastructure requirement identified from capabilities."""

    category: str = Field(
        description="Category of infrastructure (e.g., 'Database', 'Authentication', 'Payments', 'Storage', 'Email')"
    )
    purpose: str = Field(
        description="What this infrastructure is needed for (e.g., 'Store user profiles and challenge progress')"
    )
    requirements: list[str] = Field(
        description="Specific requirements for this infrastructure (e.g., 'Real-time sync', 'ACID compliance')"
    )


class ServiceRecommendation(BaseModel):
    """A recommended service with rationale."""

    name: str = Field(description="Service name (e.g., 'Supabase', 'Stripe', 'Auth0')")
    category: str = Field(description="Category this service fulfills")
    recommendation: RecommendationType = Field(description="BUILD, BUY, or HYBRID")
    rationale: str = Field(description="Why this specific service was chosen over alternatives")
    capabilities_served: list[str] = Field(
        description="Which capabilities from the capability model this serves"
    )
    integration_effort: str = Field(
        description="Estimated integration effort (e.g., '2-4 hours', '1-2 days')"
    )
    pricing_notes: str = Field(description="Brief pricing information relevant to MVP stage")


class AlternativeService(BaseModel):
    """An alternative service option with pros/cons."""

    name: str = Field(description="Service name")
    pros: list[str] = Field(description="2-3 advantages of this alternative")
    cons: list[str] = Field(description="2-3 disadvantages of this alternative")
    best_for: str = Field(description="When this alternative would be the better choice")


class AlternativesSection(BaseModel):
    """Alternatives for a category of infrastructure."""

    category: str = Field(description="Category (e.g., 'Database', 'Authentication')")
    recommended: str = Field(description="The recommended service name")
    alternatives: list[AlternativeService] = Field(
        description="2-3 alternative options with pros/cons"
    )


class BuildBuyAnalysisOutput(BaseModel):
    """Complete Build vs Buy analysis output with structured data.

    This model is used with Strands structured_output_model to ensure
    the agent returns properly formatted, validated output.
    """

    # Section 1: Infrastructure Overview
    system_summary: str = Field(
        description=(
            "One paragraph summary of the system being built and its core technical needs. "
            "Example: 'This is a community-focused fitness app that needs real-time data sync, "
            "user authentication, and a challenge/leaderboard system.'"
        )
    )
    infrastructure_requirements: list[InfrastructureRequirement] = Field(
        description=(
            "High-level infrastructure requirements identified from the capability model. "
            "List 3-6 key infrastructure categories needed."
        )
    )

    # Section 2: Recommended Stack
    recommended_stack: list[ServiceRecommendation] = Field(
        description=(
            "The recommended combination of services/build decisions. "
            "Each entry should have clear rationale for why it was chosen."
        )
    )
    stack_rationale: str = Field(
        description=(
            "Overall rationale for this stack combination. Why do these services work well together? "
            "What are the key tradeoffs made?"
        )
    )

    # Section 3: Alternatives
    alternatives: list[AlternativesSection] = Field(
        description=(
            "Alternative options for key BUY recommendations. "
            "Include 2-3 alternatives per category with pros/cons."
        )
    )

    # Metadata
    total_integration_effort: str = Field(
        default="Not estimated",
        description="Estimated total integration effort for the recommended stack",
    )
    estimated_monthly_cost: str = Field(
        default="Not estimated",
        description="Estimated monthly cost at MVP scale (e.g., '$0-50/month for first 1000 users')",
    )

    def to_markdown(self) -> str:
        """Convert the analysis to formatted markdown."""
        lines = [
            "# Build vs Buy Analysis",
            "",
            "## System Overview",
            "",
            self.system_summary,
            "",
            "### Infrastructure Requirements",
            "",
        ]

        for req in self.infrastructure_requirements:
            lines.append(f"**{req.category}**: {req.purpose}")
            for r in req.requirements:
                lines.append(f"  - {r}")
            lines.append("")

        lines.extend(
            [
                "---",
                "",
                "## Recommended Stack",
                "",
                self.stack_rationale,
                "",
            ]
        )

        for svc in self.recommended_stack:
            emoji = (
                "🛒"
                if svc.recommendation == RecommendationType.BUY
                else ("🔧" if svc.recommendation == RecommendationType.BUILD else "🔀")
            )
            lines.append(f"### {emoji} {svc.name} ({svc.recommendation.value})")
            lines.append("")
            lines.append(f"**Category:** {svc.category}")
            lines.append(f"**Rationale:** {svc.rationale}")
            lines.append(f"**Serves:** {', '.join(svc.capabilities_served)}")
            lines.append(f"**Integration Effort:** {svc.integration_effort}")
            lines.append(f"**Pricing:** {svc.pricing_notes}")
            lines.append("")

        lines.extend(
            [
                "---",
                "",
                "## Alternatives",
                "",
            ]
        )

        for alt_section in self.alternatives:
            lines.append(f"### {alt_section.category}")
            lines.append(f"*Recommended: {alt_section.recommended}*")
            lines.append("")

            for alt in alt_section.alternatives:
                lines.append(f"**{alt.name}**")
                lines.append("- Pros: " + ", ".join(alt.pros))
                lines.append("- Cons: " + ", ".join(alt.cons))
                lines.append(f"- Best for: {alt.best_for}")
                lines.append("")

        lines.extend(
            [
                "---",
                "",
                "## Summary",
                "",
                f"**Total Integration Effort:** {self.total_integration_effort}",
                f"**Estimated Monthly Cost:** {self.estimated_monthly_cost}",
            ]
        )

        return "\n".join(lines)


def format_build_buy_analysis(data: dict | BuildBuyAnalysisOutput) -> str:
    """Format build buy analysis data as markdown.

    Args:
        data: Either a BuildBuyAnalysisOutput instance or a dict with the same structure

    Returns:
        Formatted markdown string
    """
    if isinstance(data, BuildBuyAnalysisOutput):
        return data.to_markdown()

    # Handle dict input (e.g., from JSON parsing)
    try:
        model = BuildBuyAnalysisOutput.model_validate(data)
        return model.to_markdown()
    except (ValidationError, TypeError, ValueError):
        # Fallback: return raw dict as formatted string
        return f"```json\n{json.dumps(data, indent=2)}\n```"
