"""Workflow Factories for Separated Workflow Execution.

Thin dispatch layer that maps WorkflowType to WorkflowSpec and delegates
to build_workflow(). See workflow_specs.py for definitions and
workflow_builder.py for the shared builder.

Workflow types (ADR-016, Four-Phase Architecture):

1. Idea Validation (WHY): idea_analysis -> market_context -> risk_assessment -> validation_summary
2. MVP Specification (WHAT): mvp_scope -> capability_model -> system_traits
3. Build vs Buy Analysis (HOW 3a): build_buy_analysis
4. Architecture Decisions (HOW 3b): architecture_decisions
5. Story Generation (STORIES): story_generation -> story_validation -> dependency_ordering
"""

import logging
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from haytham.workflow.stage_registry import WorkflowType
from haytham.workflow.workflow_builder import WorkflowProgressHook, build_workflow
from haytham.workflow.workflow_specs import (
    ARCHITECTURE_DECISIONS_SPEC,
    BUILD_BUY_ANALYSIS_SPEC,
    IDEA_VALIDATION_SPEC,
    MVP_SPECIFICATION_SPEC,
    STORY_GENERATION_SPEC,
    WORKFLOW_SPECS,
)

if TYPE_CHECKING:
    from haytham.session.session_manager import SessionManager

logger = logging.getLogger(__name__)

# Re-export WorkflowProgressHook so existing imports keep working
__all__ = [
    "WorkflowProgressHook",
    "create_workflow_for_type",
    "create_idea_validation_workflow",
    "get_terminal_stage",
    "WORKFLOW_TERMINAL_STAGES",
    "IDEA_VALIDATION_STAGES",
    "MVP_SPECIFICATION_STAGES",
    "BUILD_BUY_ANALYSIS_STAGES",
    "ARCHITECTURE_DECISIONS_STAGES",
    "STORY_GENERATION_STAGES",
]


# ---------------------------------------------------------------------------
# Stage lists (backward-compatible re-exports from specs)
# ---------------------------------------------------------------------------

IDEA_VALIDATION_STAGES: list[str] = list(IDEA_VALIDATION_SPEC.stages)
MVP_SPECIFICATION_STAGES: list[str] = list(MVP_SPECIFICATION_SPEC.stages)
BUILD_BUY_ANALYSIS_STAGES: list[str] = list(BUILD_BUY_ANALYSIS_SPEC.stages)
ARCHITECTURE_DECISIONS_STAGES: list[str] = list(ARCHITECTURE_DECISIONS_SPEC.stages)
STORY_GENERATION_STAGES: list[str] = list(STORY_GENERATION_SPEC.stages)


# ---------------------------------------------------------------------------
# Backward-compatible factory for Idea Validation
# ---------------------------------------------------------------------------


def create_idea_validation_workflow(
    system_goal: str,
    session_manager: "SessionManager",
    app_id: str | None = None,
    on_stage_start: Callable | None = None,
    on_stage_complete: Callable | None = None,
    enable_tracking: bool = True,
    tracking_project: str = "haytham-validation",
    archetype: str | None = None,
) -> Any:
    """Create the Idea Validation workflow (Workflow 1).

    Backward-compatible wrapper around build_workflow(). New callers
    should prefer create_workflow_for_type().

    Args:
        system_goal: The startup idea to validate
        session_manager: SessionManager for persistence
        app_id: Optional custom app ID
        on_stage_start: Callback when stage starts
        on_stage_complete: Callback when stage completes
        enable_tracking: Enable Burr tracking UI
        tracking_project: Project name for tracking
        archetype: User-selected archetype (empty string = auto-detect)

    Returns:
        Burr Application instance
    """
    return build_workflow(
        spec=IDEA_VALIDATION_SPEC,
        session_manager=session_manager,
        system_goal=system_goal,
        app_id=app_id,
        on_stage_start=on_stage_start,
        on_stage_complete=on_stage_complete,
        enable_tracking=enable_tracking,
        tracking_project=tracking_project,
        archetype=archetype or "",
    )


# ---------------------------------------------------------------------------
# Unified Factory Function
# ---------------------------------------------------------------------------


def create_workflow_for_type(
    workflow_type: WorkflowType,
    session_manager: "SessionManager",
    system_goal: str | None = None,
    **kwargs: Any,
) -> Any:
    """Create a workflow of the specified type.

    This is the unified entry point for creating any workflow type.

    Args:
        workflow_type: The type of workflow to create
        session_manager: SessionManager for persistence
        system_goal: System goal (required for Idea Validation)
        **kwargs: Additional arguments passed to build_workflow

    Returns:
        Burr Application instance

    Raises:
        ValueError: If workflow_type is invalid or entry conditions not met
    """
    spec = WORKFLOW_SPECS.get(workflow_type)
    if spec is None:
        raise ValueError(f"Unknown workflow type: {workflow_type}")

    # Idea Validation requires system_goal
    if workflow_type == WorkflowType.IDEA_VALIDATION:
        if not system_goal:
            system_goal = session_manager.get_system_goal()
        if not system_goal:
            raise ValueError("System goal is required for Idea Validation workflow")

    return build_workflow(
        spec=spec,
        session_manager=session_manager,
        system_goal=system_goal,
        **kwargs,
    )


# ---------------------------------------------------------------------------
# Terminal Stages
# ---------------------------------------------------------------------------

WORKFLOW_TERMINAL_STAGES: dict[WorkflowType, str] = {
    wt: spec.stages[-1] for wt, spec in WORKFLOW_SPECS.items()
}


def get_terminal_stage(workflow_type: WorkflowType) -> str:
    """Get the terminal (final) stage for a workflow type.

    Args:
        workflow_type: The workflow type

    Returns:
        Name of the terminal stage action

    Raises:
        ValueError: If workflow_type is not recognised
    """
    try:
        return WORKFLOW_TERMINAL_STAGES[workflow_type]
    except KeyError:
        raise ValueError(f"Unknown workflow type: {workflow_type!r}") from None
