"""Verification result schemas for phase-boundary verifiers (ADR-022)."""

from typing import Literal

from pydantic import BaseModel, Field


class InvariantViolation(BaseModel):
    """A detected violation of a concept anchor invariant."""

    invariant: str = Field(description="The invariant property that was violated")
    violation: str = Field(description="Description of how it was violated")
    stage: str = Field(description="Which stage's output contains the violation")
    severity: Literal["blocking", "warning"] = Field(
        description="blocking = must fix before proceeding, warning = surface for review"
    )
    suggested_fix: str | None = Field(
        default=None, description="Suggested correction if applicable"
    )


class GenericizationFlag(BaseModel):
    """A detected genericization of a distinctive feature."""

    original_feature: str = Field(description="The distinctive feature from the anchor")
    generic_replacement: str = Field(description="What the feature was genericized into")
    stage: str = Field(description="Which stage's output contains the genericization")
    evidence: str = Field(description="Quote or reference showing the genericization")


class PhaseVerification(BaseModel):
    """Structured verification result for a phase.

    This is the output format for all phase-boundary verifiers.
    """

    phase: str = Field(description="Which phase was verified (WHY, WHAT, HOW, STORIES)")
    passed: bool = Field(description="True if no blocking violations, False if verification failed")

    # Confidence reporting (for swarm-based verification)
    confidence_score: int = Field(
        default=100,
        ge=0,
        le=100,
        description="Confidence in this verification result (0-100). "
        "Based on checker agreement and completeness.",
    )
    confidence_rationale: str = Field(
        default="",
        description="One-line explanation for the confidence score",
    )

    # Invariant tracking
    invariants_honored: list[str] = Field(
        default_factory=list,
        description="List of invariant property names that were properly preserved",
    )
    invariants_violated: list[InvariantViolation] = Field(
        default_factory=list, description="List of detected invariant violations"
    )

    # Identity tracking
    identity_preserved: list[str] = Field(
        default_factory=list,
        description="List of identity features that remain in the output",
    )
    identity_genericized: list[GenericizationFlag] = Field(
        default_factory=list, description="List of detected genericizations"
    )

    # Additional findings
    warnings: list[str] = Field(
        default_factory=list,
        description="Non-blocking issues to surface at the decision gate",
    )
    notes: str = Field(
        default="", description="Additional context or observations from the verifier"
    )

    @property
    def has_blocking_violations(self) -> bool:
        """Check if there are any blocking violations."""
        return any(v.severity == "blocking" for v in self.invariants_violated)

    @property
    def blocking_violations(self) -> list[InvariantViolation]:
        """Get only the blocking violations."""
        return [v for v in self.invariants_violated if v.severity == "blocking"]

    @property
    def warning_violations(self) -> list[InvariantViolation]:
        """Get only the warning-level violations."""
        return [v for v in self.invariants_violated if v.severity == "warning"]

    def to_summary(self) -> str:
        """Format verification result as a human-readable summary."""
        lines = [f"## Phase Verification: {self.phase}"]
        lines.append(f"**Status:** {'PASSED' if self.passed else 'FAILED'}")

        # Add confidence info if available
        if self.confidence_score < 100 or self.confidence_rationale:
            lines.append(f"**Confidence:** {self.confidence_score}%")
            if self.confidence_rationale:
                lines.append(f"**Rationale:** {self.confidence_rationale}")

        if self.invariants_honored:
            lines.append(f"\n**Invariants Honored ({len(self.invariants_honored)}):**")
            for inv in self.invariants_honored:
                lines.append(f"- {inv}")

        if self.invariants_violated:
            lines.append(f"\n**Invariants Violated ({len(self.invariants_violated)}):**")
            for v in self.invariants_violated:
                severity_marker = "[BLOCKING]" if v.severity == "blocking" else "[warning]"
                lines.append(f"- {severity_marker} **{v.invariant}**: {v.violation}")
                lines.append(f"  - Stage: {v.stage}")
                if v.suggested_fix:
                    lines.append(f"  - Fix: {v.suggested_fix}")

        if self.identity_preserved:
            lines.append(f"\n**Identity Features Preserved ({len(self.identity_preserved)}):**")
            for feat in self.identity_preserved:
                lines.append(f"- {feat}")

        if self.identity_genericized:
            lines.append(f"\n**Identity Features Genericized ({len(self.identity_genericized)}):**")
            for g in self.identity_genericized:
                lines.append(f"- **{g.original_feature}** → {g.generic_replacement}")
                lines.append(f"  - Stage: {g.stage}")
                lines.append(f'  - Evidence: "{g.evidence}"')

        if self.warnings:
            lines.append(f"\n**Warnings ({len(self.warnings)}):**")
            for w in self.warnings:
                lines.append(f"- {w}")

        if self.notes:
            lines.append(f"\n**Notes:** {self.notes}")

        return "\n".join(lines)
