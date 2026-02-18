"""Pydantic models for structured validation summary output.

These models define the schema for the validation summary agent's output,
ensuring type-safe, validated responses with explicit recommendations.

The Go/No-Go assessment uses a Stage-Gate inspired scorecard (Robert Cooper)
with knockout criteria and scored dimensions for transparent decision-making.
"""

from __future__ import annotations

import json
import re
from enum import Enum

from pydantic import BaseModel, Field, ValidationError


def _verdict_display(verdict: str) -> str:
    """Map internal verdict labels to user-facing display labels."""
    return {"CONDITIONAL GO": "PIVOT"}.get(verdict, verdict)


class LeanCanvas(BaseModel):
    """Condensed Lean Canvas summary."""

    problems: list[str] = Field(description="Top 2-3 problems the startup solves (one line each)")
    customer_segments: list[str] = Field(description="2 target customer segments")
    unique_value_proposition: str = Field(
        description="Single compelling sentence describing the unique value"
    )
    solution: list[str] = Field(description="Core solution capabilities (3 bullets max)")
    revenue_model: str = Field(description="How the startup makes money")


class ValidationFindings(BaseModel):
    """Key validation findings from prior stages."""

    market_opportunity: str = Field(description="Market size and growth potential summary")
    competition: str = Field(description="Key competitive gaps and positioning opportunities")
    critical_risks: list[str] = Field(description="Top 2 risks with severity level")


# =============================================================================
# Stage-Gate Scorecard Models
# =============================================================================


class KnockoutResult(str, Enum):
    """Result of a knockout criterion evaluation."""

    PASS = "PASS"
    FAIL = "FAIL"


class KnockoutCriterion(BaseModel):
    """A single knockout criterion — any FAIL triggers NO-GO."""

    criterion: str = Field(description="Name of the knockout criterion")
    result: KnockoutResult = Field(description="PASS or FAIL")
    evidence: str = Field(description="Brief evidence supporting the result")


class ScorecardDimension(BaseModel):
    """A scored dimension in the Go/No-Go scorecard (1-5 scale)."""

    dimension: str = Field(description="Name of the dimension being scored")
    score: int = Field(ge=1, le=5, description="Score from 1 (very weak) to 5 (very strong)")
    evidence: str = Field(description="Brief evidence justifying the score")


class CounterSignal(BaseModel):
    """A negative upstream signal displayed for transparency.

    Counter-signals are informational: they show risks the system identified
    but do not override the deterministic verdict rules.
    """

    signal: str = Field(
        description="The negative finding (e.g. 'No independent evidence users want this')"
    )
    source: str = Field(
        description="Which upstream stage surfaced this (e.g. 'risk_assessment', 'market_context')"
    )
    affected_dimensions: list[str] = Field(
        description="Which scored dimensions this signal should influence"
    )
    reconciliation: str = Field(
        default="",
        description="Why the dimension score is still appropriate despite this signal",
    )


class GoNoGoScorecard(BaseModel):
    """Stage-Gate inspired scorecard for transparent Go/No-Go decisions.

    Uses knockout criteria (any FAIL → NO-GO) plus scored dimensions
    with evidence citations for full transparency.
    """

    knockout_criteria: list[KnockoutCriterion] = Field(
        description="3 knockout criteria — any FAIL triggers NO-GO"
    )
    counter_signals: list[CounterSignal] = Field(
        default_factory=list,
        description="Negative upstream signals reconciled against dimension scores",
    )
    scorecard: list[ScorecardDimension] = Field(description="6 scored dimensions (1-5 scale)")
    composite_score: float = Field(
        ge=0.0, le=5.0, description="Average of all dimension scores (0.0 when knockout fails)"
    )
    verdict: str = Field(description="GO, CONDITIONAL GO, or NO-GO based on scoring rules")
    floor_capped: bool = Field(
        default=False,
        description="True if any dimension scored ≤2, capping composite at 3.0",
    )
    risk_capped: bool = Field(
        default=False,
        description="True if HIGH risk level overrode GO verdict to PIVOT",
    )
    critical_gaps: list[str] = Field(
        description="Dimensions scoring 2 or below that need attention"
    )
    guidance: str = Field(description="Clear guidance on recommended next steps")


class ValidationSummaryOutput(BaseModel):
    """Complete validation summary output with structured data.

    This model is used with Strands structured_output_model to ensure
    the agent returns properly formatted, validated output with an
    explicit recommendation for workflow gating.
    """

    executive_summary: str = Field(
        description=(
            "One-paragraph overview of the startup concept (60 words max). "
            "Include overall validation verdict."
        )
    )
    recommendation: str = Field(
        description=(
            "The workflow recommendation. Must be exactly one of: "
            "GO - Proceed with MVP development, core concept is validated. "
            "PIVOT - Concept has potential but needs significant changes before proceeding. "
            "NO-GO - Do not proceed, fundamental issues identified that cannot be easily resolved."
        )
    )
    lean_canvas: LeanCanvas = Field(description="Condensed Lean Canvas summary")
    validation_findings: ValidationFindings = Field(
        description="Key validation findings from prior analysis stages"
    )
    go_no_go_assessment: GoNoGoScorecard = Field(
        description="Stage-Gate scorecard with knockout criteria and scored dimensions"
    )
    next_steps: list[str] = Field(
        description=(
            "If GO/PIVOT: 3 immediate actions and key metrics to track. "
            "If NO-GO: Alternative approaches to consider."
        )
    )

    def to_markdown(self) -> str:
        """Convert the validation summary to formatted markdown."""
        lines = [
            "# Validation Summary",
            "",
            "## Executive Summary",
            "",
            self.executive_summary,
            "",
            "---",
            "",
            "## Validation Findings",
            "",
            "### Market Opportunity",
            "",
            self.validation_findings.market_opportunity,
            "",
            "### Competition",
            "",
            self.validation_findings.competition,
            "",
            "### Critical Risks",
            "",
        ]
        for risk in self.validation_findings.critical_risks:
            lines.append(f"- {risk}")

        # Stage-Gate Scorecard
        lines.extend(
            [
                "",
                "---",
                "",
                "## Go/No-Go Scorecard",
                "",
                "### Knockout Criteria",
                "",
                "| Criterion | Result | Evidence |",
                "|-----------|--------|----------|",
            ]
        )
        for kc in self.go_no_go_assessment.knockout_criteria:
            result_icon = "PASS" if kc.result == KnockoutResult.PASS else "FAIL"
            lines.append(f"| {kc.criterion} | {result_icon} | {kc.evidence} |")

        # Verdict drivers — explain what mechanisms shaped the verdict
        drivers: list[str] = []
        if self.go_no_go_assessment.floor_capped and self.go_no_go_assessment.critical_gaps:
            gaps = ", ".join(f"{g} (≤2)" for g in self.go_no_go_assessment.critical_gaps)
            drivers.append(f"Score floor triggered — {gaps} cap composite at 3.0")
        if self.go_no_go_assessment.risk_capped:
            drivers.append("HIGH risk level overrides GO verdict → PIVOT")
        if drivers:
            lines.extend(["", "### Verdict Drivers", ""])
            for d in drivers:
                lines.append(f"- {d}")

        # Counter-Signals Reconciliation (between knockouts and scored dimensions)
        if self.go_no_go_assessment.counter_signals:
            lines.extend(
                [
                    "",
                    "### Counter-Signals Reconciliation",
                    "",
                ]
            )
            for cs in self.go_no_go_assessment.counter_signals:
                dims = ", ".join(cs.affected_dimensions)
                lines.append(f"- **{cs.signal}** (source: {cs.source}, affects: {dims})")
                if cs.reconciliation:
                    lines.append(f"  - *Reconciliation:* {cs.reconciliation}")

        lines.extend(
            [
                "",
                "### Scored Dimensions",
                "",
                "| Dimension | Score | Evidence |",
                "|-----------|-------|----------|",
            ]
        )
        for dim in self.go_no_go_assessment.scorecard:
            score_bar = _score_bar(dim.score)
            lines.append(f"| {dim.dimension} | {score_bar} | {dim.evidence} |")

        lines.extend(
            [
                "",
                f"**Composite Score:** {self.go_no_go_assessment.composite_score:.1f} / 5.0",
                f"**Verdict:** {_verdict_display(self.go_no_go_assessment.verdict)}",
                "",
            ]
        )

        if self.go_no_go_assessment.critical_gaps:
            lines.append("### Critical Gaps")
            lines.append("")
            for gap in self.go_no_go_assessment.critical_gaps:
                lines.append(f"- {gap}")
            lines.append("")

        lines.extend(
            [
                "### Guidance",
                "",
                self.go_no_go_assessment.guidance,
                "",
                "---",
                "",
                "## Next Steps",
                "",
            ]
        )
        for step in self.next_steps:
            lines.append(f"1. {step}")

        return "\n".join(lines)


def _score_bar(score: int) -> str:
    """Render a score as a compact visual bar (e.g. '███░░ 3/5')."""
    filled = score
    empty = 5 - score
    return f"{'█' * filled}{'░' * empty} {score}/5"


class ScorerOutput(BaseModel):
    """Intermediate output from validation_scorer agent.

    Contains all analytical fields: knockouts, dimension scores,
    counter-signals, and the deterministic verdict.
    """

    knockout_criteria: list[KnockoutCriterion]
    counter_signals: list[CounterSignal] = Field(default_factory=list)
    scorecard: list[ScorecardDimension]
    composite_score: float = Field(ge=0.0, le=5.0)
    verdict: str
    recommendation: str
    floor_capped: bool = False
    risk_capped: bool = False
    critical_gaps: list[str] = Field(default_factory=list)
    guidance: str
    risk_level: str = Field(default="MEDIUM")


class NarrativeFields(BaseModel):
    """Narrative output from validation_narrator agent.

    Contains human-readable prose fields: executive summary,
    lean canvas, validation findings, and next steps.
    """

    executive_summary: str
    lean_canvas: LeanCanvas
    validation_findings: ValidationFindings
    next_steps: list[str]


def _fix_exec_summary_verdict(exec_summary: str, recommendation: str) -> str:
    """Ensure the executive summary contains the correct recommendation.

    Weaker models sometimes hallucinate a different verdict in the prose
    (e.g. writing "NO-GO" when the scorer said "PIVOT").  This function
    detects the mismatch and patches the text deterministically.
    """
    rec_upper = recommendation.upper()
    # All possible verdict/recommendation terms the narrator might use
    verdict_terms = ["NO-GO", "NOGO", "NO GO", "PIVOT", "CONDITIONAL GO", "GO"]
    # Sort longest-first so "NO-GO" matches before "GO"
    verdict_terms.sort(key=len, reverse=True)

    pattern = re.compile(
        r"\b(" + "|".join(re.escape(t) for t in verdict_terms) + r")\b",
        re.IGNORECASE,
    )

    matches = list(pattern.finditer(exec_summary))
    if not matches:
        # No verdict found — append it
        return f"{exec_summary.rstrip()} {rec_upper} recommendation."

    # Check if any match already equals the correct recommendation
    for m in matches:
        matched = m.group(0).upper()
        # "CONDITIONAL GO" maps to "PIVOT" in recommendation vocabulary
        if matched == "CONDITIONAL GO":
            normalised = "PIVOT"
        # Normalise "NOGO" / "NO GO" → "NO-GO"
        elif matched in ("NOGO", "NO GO"):
            normalised = "NO-GO"
        else:
            normalised = matched
        if normalised == rec_upper:
            return exec_summary  # Already correct

    # All matches are wrong — replace the first occurrence
    first = matches[0]
    return exec_summary[: first.start()] + rec_upper + exec_summary[first.end() :]


def merge_scorer_narrator(scorer: dict, narrator: dict) -> dict:
    """Build ValidationSummaryOutput dict from scorer + narrator outputs.

    This is a deterministic, testable function that combines analytical
    fields from the scorer with narrative fields from the narrator into
    the unchanged ValidationSummaryOutput schema.

    Includes a post-hoc consistency check: if the narrator's executive
    summary contains a verdict that contradicts the scorer's authoritative
    recommendation, the text is patched deterministically.

    Args:
        scorer: Dict of ScorerOutput fields
        narrator: Dict of NarrativeFields fields

    Returns:
        Dict that validates as ValidationSummaryOutput
    """
    exec_summary = _fix_exec_summary_verdict(
        narrator["executive_summary"],
        scorer["recommendation"],
    )
    return {
        "executive_summary": exec_summary,
        "recommendation": scorer["recommendation"],
        "lean_canvas": narrator["lean_canvas"],
        "validation_findings": narrator["validation_findings"],
        "go_no_go_assessment": {
            "knockout_criteria": scorer["knockout_criteria"],
            "counter_signals": scorer.get("counter_signals", []),
            "scorecard": scorer["scorecard"],
            "composite_score": scorer["composite_score"],
            "verdict": scorer["verdict"],
            "floor_capped": scorer.get("floor_capped", False),
            "risk_capped": scorer.get("risk_capped", False),
            "critical_gaps": scorer.get("critical_gaps", []),
            "guidance": scorer["guidance"],
        },
        "next_steps": narrator["next_steps"],
    }


def format_validation_summary(data: dict | ValidationSummaryOutput) -> str:
    """Format validation summary data as markdown.

    Args:
        data: Either a ValidationSummaryOutput instance or a dict with the same structure

    Returns:
        Formatted markdown string
    """
    if isinstance(data, ValidationSummaryOutput):
        return data.to_markdown()

    # Handle dict input (e.g., from JSON parsing)
    try:
        model = ValidationSummaryOutput.model_validate(data)
        return model.to_markdown()
    except (ValidationError, TypeError, ValueError):
        # Fallback: return raw dict as formatted string
        return f"```json\n{json.dumps(data, indent=2)}\n```"
