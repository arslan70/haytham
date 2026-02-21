"""Pydantic models for the report synthesis stage."""

from enum import Enum

from pydantic import BaseModel, Field


class Recommendation(str, Enum):
    """Go/No-Go/Pivot recommendation for the startup idea."""

    GO = "GO"
    PIVOT = "PIVOT"
    NO_GO = "NO-GO"


class ValidationReport(BaseModel):
    """Structured output from the report synthesis agent.

    Contains the GO/PIVOT/NO-GO recommendation as a typed field for
    downstream consumption (Gate 1, UI), and the full validation report
    as markdown for human review.
    """

    recommendation: Recommendation = Field(
        description="GO, PIVOT, or NO-GO recommendation for the startup idea"
    )
    report: str = Field(
        description="Complete validation report in markdown covering all 11 sections"
    )
