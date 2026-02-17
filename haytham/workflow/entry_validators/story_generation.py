"""Entry condition validator for Story Generation workflow."""

import logging

from haytham.workflow.stage_registry import WorkflowType

from .base import EntryConditionResult, WorkflowEntryValidator

logger = logging.getLogger(__name__)


class StoryGenerationEntryValidator(WorkflowEntryValidator):
    """Validates entry conditions for Story Generation workflow.

    Entry conditions:
    - Architecture Decisions workflow completed
    - Build vs Buy Analysis document exists
    - Architecture Decisions document exists
    - ADR-022: HOW phase verification passes (trait consistency, architecture alignment)
    """

    workflow_type = WorkflowType.STORY_GENERATION
    phase_name = "HOW"

    def validate(self, force_override: bool = False) -> EntryConditionResult:
        """Validate entry conditions for Story Generation.

        Returns:
            EntryConditionResult with pass/fail status and details
        """
        self._reset()

        # Check 1: Architecture Decisions complete
        architecture_complete = self._check_architecture_decisions_complete()

        # Check 2: Build vs Buy Analysis exists
        build_buy_exists = self._check_build_buy_analysis()

        # Check 3: Architecture Decisions exists
        architecture_exists = self._check_architecture_decisions()

        # ADR-022: Gate 3 - Run HOW phase verification
        phase_verification = self._run_phase_verification()

        # Compile result
        passed = len(self.errors) == 0

        if passed:
            message = "All entry conditions met. Ready to generate stories."
        else:
            message = f"Entry conditions not met: {'; '.join(self.errors)}"

        return EntryConditionResult(
            passed=passed,
            message=message,
            details={
                "architecture_complete": architecture_complete,
                "build_buy_exists": build_buy_exists,
                "architecture_exists": architecture_exists,
                "phase_verification": phase_verification,
                "errors": self.errors,
                "warnings": self.warnings,
            },
        )

    def _check_architecture_decisions_complete(self) -> bool:
        """Check if Architecture Decisions workflow is complete."""
        return self._check_workflow_complete(
            "architecture-decisions",
            "architecture-decisions",
            legacy_slugs=("technical-design",),
        )

    def _check_build_buy_analysis(self) -> bool:
        """Check that Build vs Buy Analysis document exists."""
        build_buy = self.session_manager.load_stage_output("build-buy-analysis")

        if not build_buy:
            self.errors.append("Build vs Buy Analysis document not found")
            return False

        if len(build_buy.strip()) < 100:
            self.warnings.append("Build vs Buy Analysis document seems too short")

        return True

    def _check_architecture_decisions(self) -> bool:
        """Check that Architecture Decisions document exists."""
        architecture = self.session_manager.load_stage_output("architecture-decisions")

        if not architecture:
            self.errors.append("Architecture Decisions document not found")
            return False

        if len(architecture.strip()) < 100:
            self.warnings.append("Architecture Decisions document seems too short")

        return True
