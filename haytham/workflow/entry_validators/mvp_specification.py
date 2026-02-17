"""Entry condition validator for MVP Specification workflow."""

import json
import logging
import re

from haytham.workflow.stage_registry import WorkflowType

_RECOMMENDATION_RE = re.compile(r"RECOMMENDATION:\s*(GO|NO-GO|PIVOT)")

from .base import EntryConditionResult, WorkflowEntryValidator

logger = logging.getLogger(__name__)


class MVPSpecificationEntryValidator(WorkflowEntryValidator):
    """Validates entry conditions for MVP Specification workflow.

    Entry conditions:
    - Idea Validation workflow completed
    - Recommendation is GO or PIVOT (not NO-GO)
    - Validation Summary document exists
    - ADR-022: WHY phase verification passes (concept preserved, no fabrication)
    """

    workflow_type = WorkflowType.MVP_SPECIFICATION
    phase_name = "WHY"

    def validate(self, force_override: bool = False) -> EntryConditionResult:
        """Validate entry conditions for MVP Specification.

        Args:
            force_override: If True, allow proceeding despite NO-GO recommendation

        Returns:
            EntryConditionResult with pass/fail status and details
        """
        self._reset()

        # Check 1: Idea Validation complete
        idea_validation_complete = self._check_idea_validation_complete()

        # Check 2: Validation Summary exists
        validation_summary_exists = self._check_validation_summary()

        # Check 3: Recommendation is GO or PIVOT
        recommendation = self._extract_recommendation()
        recommendation_ok = recommendation in ("GO", "PIVOT", "PROCEED")

        # ADR-022: Gate 1 - Run WHY phase verification
        phase_verification = self._run_phase_verification()

        # NO-GO is overridable - user can proceed at their own risk
        can_override = False
        override_warning = ""

        if not recommendation_ok and recommendation:
            if force_override:
                # User chose to override - add warning but don't block
                self.warnings.append(
                    f"Proceeding despite {recommendation} recommendation (user override)."
                )
                recommendation_ok = True  # Allow proceeding
            else:
                # Not overriding - this is an overridable block
                can_override = True
                override_warning = (
                    f"The validation returned {recommendation}. You can still proceed, but consider:\n"
                    "• Refining the idea based on validation feedback\n"
                    "• Exploring pivot opportunities identified in the report\n"
                    "• Proceeding anyway if you believe the validation is too conservative"
                )
                self.errors.append(
                    f"Validation recommendation is {recommendation}. "
                    "Override available if you want to proceed anyway."
                )

        # Compile result
        passed = len(self.errors) == 0 and idea_validation_complete and validation_summary_exists

        if passed:
            message = f"All entry conditions met. Recommendation: {recommendation}"
        else:
            if can_override:
                message = f"Recommendation is {recommendation}. You can override and proceed, or refine your idea."
            else:
                message = f"Entry conditions not met: {'; '.join(self.errors)}"

        return EntryConditionResult(
            passed=passed,
            message=message,
            recommendation=recommendation,
            can_override=can_override,
            override_warning=override_warning,
            details={
                "idea_validation_complete": idea_validation_complete,
                "validation_summary_exists": validation_summary_exists,
                "recommendation": recommendation,
                "recommendation_ok": recommendation_ok,
                "phase_verification": phase_verification,
                "errors": self.errors,
                "warnings": self.warnings,
            },
        )

    def _check_idea_validation_complete(self) -> bool:
        """Check if Idea Validation workflow is complete."""
        return self._check_workflow_complete("idea-validation", "validation-summary")

    def _check_validation_summary(self) -> bool:
        """Check that Validation Summary document exists."""
        validation_summary = self.session_manager.load_stage_output("validation-summary")

        if validation_summary and len(validation_summary.strip()) >= 100:
            return True

        # Fallback: Check risk-assessment output (last stage before summary)
        # This covers cases where the validation summary save failed but the
        # risk assessment completed successfully
        risk_assessment = self.session_manager.load_stage_output("risk-assessment")
        if risk_assessment and len(risk_assessment.strip()) >= 100:
            self.warnings.append(
                "Validation Summary not found, but risk-assessment output exists (used as fallback)"
            )
            return True

        self.errors.append("Validation Summary document not found")
        return False

    def _extract_recommendation(self) -> str:
        """Extract GO/NO-GO/PIVOT recommendation from validation summary.

        Short-circuit: checks recommendation.json metadata file first (written
        by save_final_output post_processor). Falls back to regex on markdown
        for backward compat with older sessions.

        Returns:
            Recommendation string or empty if not found
        """
        # Short-circuit: check metadata file from post_processor
        try:
            meta_path = self.session_manager.session_dir / "recommendation.json"
            if meta_path.exists():
                data = json.loads(meta_path.read_text())
                rec = data.get("recommendation", "")
                if rec in ("GO", "NO-GO", "PIVOT"):
                    logger.info(f"Recommendation from metadata: {rec}")
                    return rec
        except (json.JSONDecodeError, OSError, AttributeError):
            pass

        # Fallback: regex from rendered markdown on disk
        validation_summary = self.session_manager.load_stage_output("validation-summary")

        # Fallback to risk-assessment if validation-summary is empty
        if not validation_summary or len(validation_summary.strip()) < 50:
            validation_summary = self.session_manager.load_stage_output("risk-assessment")

        if not validation_summary:
            return ""

        summary_upper = validation_summary.upper()

        # Look for explicit "Recommendation:" line from ValidationSummaryOutput
        match = _RECOMMENDATION_RE.search(summary_upper)
        if match:
            recommendation = match.group(1)
            logger.info(f"Recommendation from markdown regex: {recommendation}")
            return recommendation

        # Fallback: Check for legacy patterns (for backward compatibility)
        if "VERDICT: GO" in summary_upper:
            return "GO"
        if "VERDICT: NO-GO" in summary_upper:
            return "NO-GO"
        if "VERDICT: PIVOT" in summary_upper:
            return "PIVOT"
        if "PROCEED WITH" in summary_upper or "READY TO PROCEED" in summary_upper:
            return "PROCEED"

        # Default to allowing progress if we can't determine
        self.warnings.append("Could not extract explicit recommendation from validation summary")
        return "PROCEED"
