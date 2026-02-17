"""Entry condition validator for Architecture Decisions workflow."""

from haytham.workflow.stage_registry import WorkflowType

from .base import MIN_STAGE_OUTPUT_LENGTH, EntryConditionResult, WorkflowEntryValidator


class ArchitectureDecisionsEntryValidator(WorkflowEntryValidator):
    """Validates entry conditions for Architecture Decisions workflow.

    Entry conditions:
    - Build vs Buy Analysis workflow completed
    - Build vs Buy Analysis document exists
    - Capability Model document exists
    """

    workflow_type = WorkflowType.ARCHITECTURE_DECISIONS

    def validate(self, force_override: bool = False) -> EntryConditionResult:
        """Validate entry conditions for Architecture Decisions.

        Returns:
            EntryConditionResult with pass/fail status and details
        """
        self._reset()

        # Check 1: Build vs Buy Analysis complete
        build_buy_complete = self._check_build_buy_complete()

        # Check 2: Build vs Buy Analysis document exists
        build_buy_exists = self._check_build_buy_analysis()

        # Check 3: Capability Model exists
        capability_model_exists = self._check_capability_model()

        # Compile result
        passed = len(self.errors) == 0

        if passed:
            message = "All entry conditions met. Ready to define architecture decisions."
        else:
            message = f"Entry conditions not met: {'; '.join(self.errors)}"

        return EntryConditionResult(
            passed=passed,
            message=message,
            details={
                "build_buy_complete": build_buy_complete,
                "build_buy_exists": build_buy_exists,
                "capability_model_exists": capability_model_exists,
                "errors": self.errors,
                "warnings": self.warnings,
            },
        )

    def _check_build_buy_complete(self) -> bool:
        """Check if Build vs Buy Analysis workflow is complete."""
        return self._check_workflow_complete("build-buy-analysis", "build-buy-analysis")

    def _check_build_buy_analysis(self) -> bool:
        """Check that Build vs Buy Analysis document exists."""
        build_buy = self.session_manager.load_stage_output("build-buy-analysis")

        if not build_buy:
            self.errors.append("Build vs Buy Analysis document not found")
            return False

        if len(build_buy.strip()) < MIN_STAGE_OUTPUT_LENGTH:
            self.warnings.append("Build vs Buy Analysis document seems too short")

        return True

    def _check_capability_model(self) -> bool:
        """Check that Capability Model document exists."""
        capability_model = self.session_manager.load_stage_output("capability-model")

        if not capability_model:
            self.errors.append("Capability Model document not found")
            return False

        return True
