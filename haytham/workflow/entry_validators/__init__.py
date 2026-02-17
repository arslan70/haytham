"""Entry condition validators for workflow transitions.

Each workflow type has a dedicated validator that checks prerequisites
before the workflow can start. One file per validator for debuggability.
"""

import logging
from typing import TYPE_CHECKING

from haytham.workflow.stage_registry import WorkflowType

from .architecture import ArchitectureDecisionsEntryValidator
from .base import EntryConditionResult, SessionStateAdapter, WorkflowEntryValidator
from .build_buy import BuildBuyAnalysisEntryValidator
from .idea_validation import IdeaValidationEntryValidator
from .mvp_specification import MVPSpecificationEntryValidator
from .story_generation import StoryGenerationEntryValidator

if TYPE_CHECKING:
    from haytham.session.session_manager import SessionManager

logger = logging.getLogger(__name__)

# Registry of validators
_VALIDATORS: dict[WorkflowType, type[WorkflowEntryValidator]] = {
    WorkflowType.IDEA_VALIDATION: IdeaValidationEntryValidator,
    WorkflowType.MVP_SPECIFICATION: MVPSpecificationEntryValidator,
    WorkflowType.BUILD_BUY_ANALYSIS: BuildBuyAnalysisEntryValidator,
    WorkflowType.ARCHITECTURE_DECISIONS: ArchitectureDecisionsEntryValidator,
    WorkflowType.STORY_GENERATION: StoryGenerationEntryValidator,
}


def get_entry_validator(
    workflow_type: WorkflowType, session_manager: "SessionManager"
) -> WorkflowEntryValidator:
    """Get the appropriate entry validator for a workflow type.

    Args:
        workflow_type: The workflow to validate entry for
        session_manager: SessionManager instance for state access

    Returns:
        Configured WorkflowEntryValidator instance

    Raises:
        ValueError: If workflow_type is not recognized
    """
    validator_class = _VALIDATORS.get(workflow_type)
    if validator_class is None:
        raise ValueError(f"No validator registered for workflow type: {workflow_type}")
    return validator_class(session_manager)


def validate_workflow_entry(
    workflow_type: WorkflowType,
    session_manager: "SessionManager",
    force_override: bool = False,
) -> EntryConditionResult:
    """Convenience function to validate entry conditions for a workflow.

    Args:
        workflow_type: The workflow to validate entry for
        session_manager: SessionManager instance for state access
        force_override: If True, allow overriding soft blocks (like NO-GO)

    Returns:
        EntryConditionResult with validation outcome
    """
    validator = get_entry_validator(workflow_type, session_manager)
    return validator.validate(force_override=force_override)


# =============================================================================
# Workflow Availability Check
# =============================================================================


def get_available_workflows(session_manager: "SessionManager") -> list[WorkflowType]:
    """Get list of workflows that can be started based on current state.

    This is useful for determining what actions to show in the UI.

    Args:
        session_manager: SessionManager instance

    Returns:
        List of WorkflowType values that have all entry conditions met
    """
    available = []

    for workflow_type in WorkflowType:
        try:
            result = validate_workflow_entry(workflow_type, session_manager)
            if result.passed:
                available.append(workflow_type)
        except (ValueError, KeyError, TypeError) as e:
            logger.warning(f"Error checking availability for {workflow_type}: {e}")

    return available


def get_next_available_workflow(session_manager: "SessionManager") -> WorkflowType | None:
    """Get the next workflow in sequence that can be started.

    Checks workflows in order and returns the first one that:
    1. Has entry conditions met
    2. Is not yet completed

    Args:
        session_manager: SessionManager instance

    Returns:
        WorkflowType for next available workflow, or None if all complete/unavailable
    """
    workflow_order = [
        WorkflowType.IDEA_VALIDATION,
        WorkflowType.MVP_SPECIFICATION,
        WorkflowType.BUILD_BUY_ANALYSIS,
        WorkflowType.ARCHITECTURE_DECISIONS,
        WorkflowType.STORY_GENERATION,
    ]

    for workflow_type in workflow_order:
        # Skip if already complete
        if session_manager.is_workflow_complete(workflow_type.value):
            continue

        # Check if entry conditions are met
        result = validate_workflow_entry(workflow_type, session_manager)
        if result.passed:
            return workflow_type

    return None


__all__ = [
    "EntryConditionResult",
    "SessionStateAdapter",
    "WorkflowEntryValidator",
    "get_entry_validator",
    "validate_workflow_entry",
    "get_available_workflows",
    "get_next_available_workflow",
]
