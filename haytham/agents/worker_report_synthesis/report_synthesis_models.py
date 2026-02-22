"""Pydantic models for the report synthesis stage."""

from enum import Enum

from pydantic import BaseModel, Field


class Recommendation(str, Enum):
    """Go/No-Go/Pivot recommendation for the startup idea."""

    GO = "GO"
    PIVOT = "PIVOT"
    NO_GO = "NO-GO"


class ExecutiveSummary(BaseModel):
    """Structured 6-field executive summary for the report cover page.

    Each field maps to a label in the "AT A GLANCE" box on the PDF cover.
    """

    idea_in_one_line: str = Field(
        description="One plain-language sentence summarising what the idea does."
    )
    strongest_point: str = Field(
        description="The single strongest reason this idea is worth considering."
    )
    recommendation_summary: str = Field(
        description="The recommendation in plain language "
        "(e.g. 'Go ahead, but validate pricing first')."
    )
    recommendation_reasoning: str = Field(
        description="The decisive factor driving the recommendation."
    )
    competitive_snapshot: str = Field(
        description="Who else is in this space and what gap this idea exploits."
    )
    closing_remark: str = Field(
        description="The single most important action the founder should take next."
    )


class ValidationReport(BaseModel):
    """Structured output from the report synthesis agent.

    Contains the GO/PIVOT/NO-GO recommendation as a typed field for
    downstream consumption (Gate 1, UI), and the full validation report
    as markdown for human review.
    """

    recommendation: Recommendation = Field(
        description="GO, PIVOT, or NO-GO recommendation for the startup idea"
    )
    executive_summary: ExecutiveSummary = Field(
        description="Structured 6-field summary for the report cover page."
    )
    report: str = Field(
        description="Complete validation report in markdown covering all 8 sections"
    )

    def to_markdown(self) -> str:
        """Render the validation report as markdown for disk saves.

        The executive summary is NOT included here; it lives exclusively
        in the AT A GLANCE box on the PDF cover (sourced from
        recommendation.json, not the markdown file).
        """
        return f"## Recommendation: {self.recommendation.value}\n\n{self.report}"
