"""Pydantic models for structured Architecture Decisions output.

These models define the schema for the architecture_decisions agent's output,
ensuring type-safe, validated responses that map each technical decision back
to the capabilities it serves.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class ArchitectureDecision(BaseModel):
    """A single architecture decision with rationale and traceability."""

    id: str = Field(description="Decision identifier (e.g., 'DEC-AUTH-001')")
    name: str = Field(description="Short name for the decision")
    description: str = Field(description="What this decision entails")
    rationale: str = Field(description="Why this is the right choice")
    serves_capabilities: list[str] = Field(
        description="Capability IDs this decision serves (e.g., 'CAP-F-001')"
    )
    implements_recommendation: str = Field(
        description="Which build/buy recommendation this implements"
    )
    alternatives_considered: list[str] = Field(
        default_factory=list,
        description="Alternatives and why they were rejected",
    )


class CoverageCheck(BaseModel):
    """Coverage summary showing which capabilities are addressed by decisions."""

    functional_capabilities_covered: list[str] = Field(
        default_factory=list,
        description="Functional capability IDs covered by decisions",
    )
    non_functional_capabilities_covered: list[str] = Field(
        default_factory=list,
        description="Non-functional capability IDs covered by decisions",
    )
    uncovered_capabilities: list[str] = Field(
        default_factory=list,
        description="Capability IDs not addressed by any decision",
    )


class ArchitectureDecisionsOutput(BaseModel):
    """Complete architecture decisions output with coverage traceability.

    This model is used with Strands structured_output_model to ensure
    the agent returns properly formatted, validated output.
    """

    decisions: list[ArchitectureDecision] = Field(
        description="Architecture decisions with rationale and capability traceability"
    )
    coverage_check: CoverageCheck = Field(
        default_factory=CoverageCheck,
        description="Coverage summary for functional and non-functional capabilities",
    )
    summary: str = Field(
        default="",
        description="Brief summary of the overall architecture approach",
    )

    def to_markdown(self) -> str:
        """Convert the architecture decisions to formatted markdown."""
        lines = [
            "# Architecture Decisions",
            "",
            self.summary,
            "",
            f"**Total decisions:** {len(self.decisions)}",
            "",
        ]

        # Coverage summary
        all_covered = (
            self.coverage_check.functional_capabilities_covered
            + self.coverage_check.non_functional_capabilities_covered
        )
        if all_covered:
            lines.extend(
                [
                    "## Coverage Summary",
                    "",
                    f"**Functional capabilities covered:** {', '.join(self.coverage_check.functional_capabilities_covered) or 'None'}",
                    f"**Non-functional capabilities covered:** {', '.join(self.coverage_check.non_functional_capabilities_covered) or 'None'}",
                ]
            )
            if self.coverage_check.uncovered_capabilities:
                lines.append(
                    f"**Uncovered capabilities:** {', '.join(self.coverage_check.uncovered_capabilities)}"
                )
            lines.append("")

        for i, decision in enumerate(self.decisions, start=1):
            if i > 1:
                lines.extend(["---", ""])

            lines.append(f"## {i}. {decision.id}: {decision.name}")
            lines.append("")
            lines.append(f"**Description:** {decision.description}")
            lines.append("")
            lines.append(f"**Rationale:** {decision.rationale}")
            lines.append("")
            lines.append(
                f"**Serves Capabilities:** {', '.join(decision.serves_capabilities)}"
            )
            lines.append("")
            lines.append(
                f"**Implements:** {decision.implements_recommendation}"
            )
            lines.append("")

            if decision.alternatives_considered:
                lines.append("**Alternatives Considered:**")
                for alt in decision.alternatives_considered:
                    lines.append(f"  - {alt}")
            lines.append("")

        return "\n".join(lines)
