"""Structured output envelope for pipeline stages (ADR-022 Part 6).

All agents produce output through this structured envelope that wraps their
freeform content. This enables programmatic validation while preserving the
flexibility of markdown output.

The envelope includes:
- tldr: Concise summary for context handoff (replaces first-line truncation)
- anchor_compliance: Self-reported compliance with concept anchor
- claims: Structured claims with source attribution
- content: The actual markdown output (freeform)
"""

import re
from typing import Literal

from pydantic import BaseModel, Field

from .anchor_schema import AnchorComplianceReport


class Claim(BaseModel):
    """A factual claim made by an agent with source attribution.

    Used for grounding enforcement (ADR-022 Part 3) to distinguish between
    validated facts, estimates, and unsourced assertions.
    """

    statement: str = Field(description="The factual claim being made")
    source: Literal["web_search", "estimate", "founder_input", "unsourced"] = Field(
        description="How this claim was sourced"
    )
    evidence: str | None = Field(
        default=None,
        description="URL, quote, or reasoning supporting the claim",
    )
    confidence: Literal["high", "medium", "low"] | None = Field(
        default=None,
        description="Agent's confidence in the claim accuracy",
    )


class StageOutput(BaseModel):
    """Structured envelope for all stage outputs.

    This schema enables programmatic validation while preserving the flexibility
    of freeform markdown output. Validators can inspect structured fields while
    the content field is saved as the stage's markdown output.

    Example:
    ```python
    output = StageOutput(
        tldr="The market for wellness apps is growing at 15% CAGR...",
        anchor_compliance=AnchorComplianceReport(
            invariants_preserved=["community_model", "group_structure"],
            invariants_overridden=[],
            identity_features_preserved=["spiritual practice aspect"],
            identity_features_genericized=[],
        ),
        claims=[
            Claim(
                statement="Market size is $4.3B",
                source="web_search",
                evidence="https://example.com/market-report",
            )
        ],
        content="## Market Analysis\\n\\nThe wellness app market...",
    )
    ```
    """

    tldr: str = Field(
        description="Concise summary (max 300 words) for context handoff to downstream stages"
    )
    anchor_compliance: AnchorComplianceReport | None = Field(
        default=None,
        description="Self-reported compliance with concept anchor. "
        "Phase-boundary verifiers independently validate these claims.",
    )
    claims: list[Claim] = Field(
        default_factory=list,
        description="Factual claims with source attribution. "
        "Only include for stages that cite statistics or make factual assertions.",
    )
    content: str = Field(
        description="The actual markdown output (freeform). "
        "This is what gets saved as the stage's markdown file.",
    )

    def to_markdown(self) -> str:
        """Format the full output as markdown with TL;DR header.

        Returns the content with TL;DR prepended for stages that
        produce markdown output.
        """
        lines = ["## TL;DR", "", self.tldr, "", "---", ""]

        # Add anchor compliance summary if present
        if self.anchor_compliance:
            preserved = self.anchor_compliance.invariants_preserved
            overridden = self.anchor_compliance.invariants_overridden
            if preserved or overridden:
                lines.append("### Anchor Compliance")
                if preserved:
                    lines.append(f"**Invariants Preserved:** {', '.join(preserved)}")
                if overridden:
                    lines.append("**Invariants Overridden:**")
                    for override in overridden:
                        lines.append(f"- {override.invariant}: {override.reason}")
                lines.append("")

        # Add the main content
        lines.append(self.content)

        return "\n".join(lines)

    def get_content_only(self) -> str:
        """Get just the content field for backward compatibility.

        Use this when you need the raw content without the TL;DR header.
        """
        return self.content

    @classmethod
    def from_markdown(cls, markdown: str, tldr: str | None = None) -> "StageOutput":
        """Create a StageOutput from existing markdown content.

        Useful for migrating existing agents to the structured output format.
        Extracts TL;DR from the content if present, or uses the provided tldr.

        Args:
            markdown: The markdown content
            tldr: Optional TL;DR summary (extracted from content if not provided)

        Returns:
            StageOutput with the content wrapped
        """
        extracted_tldr = tldr

        # Try to extract TL;DR from content
        if not extracted_tldr:
            tldr_pattern = r"##\s*TL;?DR\s*\n(.*?)(?=\n##|\n---|\Z)"
            match = re.search(tldr_pattern, markdown, re.IGNORECASE | re.DOTALL)
            if match:
                extracted_tldr = match.group(1).strip()
                # Limit to ~300 words
                words = extracted_tldr.split()
                if len(words) > 300:
                    extracted_tldr = " ".join(words[:300]) + "..."

        # Use first paragraph as fallback
        if not extracted_tldr:
            lines = [
                line.strip()
                for line in markdown.split("\n")
                if line.strip() and not line.startswith("#")
            ]
            extracted_tldr = lines[0][:500] if lines else "No summary available."

        return cls(
            tldr=extracted_tldr,
            anchor_compliance=None,
            claims=[],
            content=markdown,
        )


class StageOutputWithMetrics(StageOutput):
    """Extended stage output with execution metrics.

    Used internally by the stage executor to track additional metadata
    without exposing it in the agent's output schema.
    """

    execution_time_seconds: float | None = Field(
        default=None, description="Time taken to execute the stage"
    )
    token_count_estimate: int | None = Field(
        default=None, description="Estimated token count of output"
    )
    verifier_result: dict | None = Field(
        default=None, description="Phase-boundary verifier result if applicable"
    )
