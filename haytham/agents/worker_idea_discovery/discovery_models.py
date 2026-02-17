"""Pydantic models for structured idea discovery output.

Flat schemas safe for LLM structured output. The model captures Lean Canvas
dimension assessments and targeted clarifying questions.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class DimensionAssessment(BaseModel):
    """Assessment of a single Lean Canvas dimension."""

    dimension: str = Field(
        description="Lean Canvas dimension: Problem, Customer Segments, UVP, or Solution"
    )
    coverage: str = Field(description="Coverage level: clear, partial, or missing")
    evidence: str = Field(
        description="Quote or summary from the idea that supports this assessment, or empty string if missing"
    )


class DiscoveryQuestion(BaseModel):
    """A targeted clarifying question for a gap in the idea."""

    dimension: str = Field(description="Which Lean Canvas dimension this question addresses")
    question: str = Field(description="The clarifying question to ask the founder")
    placeholder: str = Field(description="Example answer to guide the founder")


class IdeaDiscoveryOutput(BaseModel):
    """Structured output from the idea discovery agent.

    Contains assessments for all 4 Lean Canvas dimensions and 0-5 targeted
    questions for gaps found.
    """

    understood_context: str = Field(
        description="Brief summary of what the agent already understands about the idea"
    )
    assessments: list[DimensionAssessment] = Field(
        description="Exactly 4 assessments, one per Lean Canvas dimension"
    )
    questions: list[DiscoveryQuestion] = Field(
        description="0-5 targeted clarifying questions for gaps only"
    )
