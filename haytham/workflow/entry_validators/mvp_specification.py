"""Entry condition validator for MVP Specification workflow."""

import json
import logging

from haytham.workflow.stage_registry import WorkflowType

from .base import MIN_STAGE_OUTPUT_LENGTH, EntryConditionResult, WorkflowEntryValidator

logger = logging.getLogger(__name__)


class MVPSpecificationEntryValidator(WorkflowEntryValidator):
    """Validates entry conditions for MVP Specification workflow.

    Entry conditions:
    - Idea Validation workflow completed
    - Recommendation is GO or PIVOT (not NO-GO)
    - Report synthesis document exists
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

        # Check 2: Report synthesis exists
        report_synthesis_exists = self._check_report_synthesis()

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
        passed = len(self.errors) == 0 and idea_validation_complete and report_synthesis_exists

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
                "report_synthesis_exists": report_synthesis_exists,
                "recommendation": recommendation,
                "recommendation_ok": recommendation_ok,
                "phase_verification": phase_verification,
                "errors": self.errors,
                "warnings": self.warnings,
            },
        )

    def _check_idea_validation_complete(self) -> bool:
        """Check if Idea Validation workflow is complete."""
        return self._check_workflow_complete("idea-validation", "report-synthesis")

    def _check_report_synthesis(self) -> bool:
        """Check that report synthesis document exists."""
        report = self.session_manager.load_stage_output("report-synthesis")

        if report and len(report.strip()) >= MIN_STAGE_OUTPUT_LENGTH:
            return True

        self.errors.append("Report synthesis document not found")
        return False

    def _extract_recommendation(self) -> str:
        """Extract GO/NO-GO/PIVOT recommendation from recommendation.json.

        The recommendation is written by the extract_recommendation_processor
        post-processor during the report-synthesis stage.

        Returns:
            Recommendation string or empty if not found
        """
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

        self.warnings.append("Could not extract recommendation from recommendation.json")
        return ""
