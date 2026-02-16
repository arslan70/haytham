"""Entry condition validator for Idea Validation workflow."""

from typing import TYPE_CHECKING

from haytham.workflow.stage_registry import WorkflowType

from .base import EntryConditionResult, WorkflowEntryValidator

if TYPE_CHECKING:
    pass


class IdeaValidationEntryValidator(WorkflowEntryValidator):
    """Validates entry conditions for Idea Validation workflow.

    Entry conditions: None (this is the starting point).
    The only requirement is a system goal (startup idea) provided by the user.
    """

    workflow_type = WorkflowType.IDEA_VALIDATION

    def validate(self, force_override: bool = False) -> EntryConditionResult:
        """Validate entry conditions for Idea Validation.

        Since this is the starting workflow, the only check is that
        we have a system goal (startup idea) to analyze.

        Returns:
            EntryConditionResult (always passes if called correctly)
        """
        self._reset()

        # Check for system goal
        system_goal = self.session_manager.get_system_goal()
        has_goal = bool(system_goal and len(system_goal.strip()) > 10)

        if not has_goal:
            self.warnings.append("No system goal found - user should provide a startup idea")

        return EntryConditionResult(
            passed=True,  # Always passes - this is the starting point
            message="Ready to start Idea Validation workflow.",
            details={
                "has_system_goal": has_goal,
                "warnings": self.warnings,
            },
        )
