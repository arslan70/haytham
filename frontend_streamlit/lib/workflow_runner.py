"""Streamlit Workflow Runner.

Wraps the Burr workflow execution for synchronous Streamlit usage.
Uses callbacks for progress updates instead of Chainlit messages.
"""

import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from lib.session_utils import load_environment, setup_paths

setup_paths()
load_environment()

from haytham.agents.utils.web_search import reset_session_counter
from haytham.session.session_manager import SessionManager
from haytham.workflow.stage_registry import WorkflowType, get_stage_registry
from haytham.workflow.workflow_factories import (
    WORKFLOW_TERMINAL_STAGES,
    create_idea_validation_workflow,
    create_workflow_for_type,
)

logger = logging.getLogger(__name__)


@dataclass
class StageProgress:
    """Progress update for a stage."""

    stage_slug: str
    display_name: str
    display_index: int | str
    status: str  # "pending", "running", "completed", "failed"
    current_stage: int  # 1-indexed for display
    total_stages: int
    output: str | None = None
    error: str | None = None


@dataclass
class WorkflowResult:
    """Result of workflow execution."""

    workflow_type: str
    status: str  # "completed", "failed", "cancelled"
    stages: list[StageProgress] = field(default_factory=list)
    execution_time: float = 0.0
    error: str | None = None
    recommendation: str | None = None  # GO/NO-GO/PIVOT for idea validation


@dataclass
class WorkflowConfig:
    """Configuration for running a workflow."""

    workflow_type: WorkflowType
    workflow_slug: str  # e.g., "idea-validation"
    factory_fn: Callable  # e.g., create_idea_validation_workflow
    factory_kwargs: dict = field(default_factory=dict)
    pre_run: Callable | None = None  # Called with (session_manager, session_dir)
    post_run: Callable | None = None  # Called with (state, session_dir) -> recommendation


def _get_stage_display_info(action_name: str) -> tuple[str, str, int | str]:
    """Get display info for a stage from the registry.

    Returns:
        Tuple of (slug, display_name, display_index)
    """
    registry = get_stage_registry()
    try:
        metadata = registry.get_by_action(action_name)
        return metadata.slug, metadata.display_name, metadata.display_index
    except KeyError:
        # Fallback for unknown stages
        return action_name, action_name.replace("_", " ").title(), 0


def run_workflow(
    config: WorkflowConfig,
    session_dir: Path,
    on_stage_start: Callable[[StageProgress], None] | None = None,
    on_stage_complete: Callable[[StageProgress], None] | None = None,
) -> WorkflowResult:
    """Run a workflow synchronously using the provided config.

    Creates session manager, runs workflow, returns result.
    Calls back on_stage_start/on_stage_complete for UI updates.

    Args:
        config: Workflow configuration
        session_dir: Path to session directory
        on_stage_start: Callback when a stage starts
        on_stage_complete: Callback when a stage completes

    Returns:
        WorkflowResult with status and stage progress
    """
    start_time = time.time()

    # Reset web search session counter for cost protection
    reset_session_counter(session_id=str(session_dir))

    # Create session manager
    base_dir = session_dir.parent
    session_manager = SessionManager(str(base_dir))

    # Run pre-run hook (e.g., clear session, set system goal)
    if config.pre_run:
        config.pre_run(session_manager, session_dir)

    # Stage progress tracking
    stages_progress: list[StageProgress] = []

    def handle_stage_start(stage_name: str, index: int, total: int):
        """Handle stage start callback from workflow."""
        slug, display_name, display_index = _get_stage_display_info(stage_name)

        progress = StageProgress(
            stage_slug=slug,
            display_name=display_name,
            display_index=display_index,
            status="running",
            current_stage=index + 1,
            total_stages=total,
        )

        logger.info(f"Stage started: {display_name} ({index + 1}/{total})")

        if on_stage_start:
            try:
                on_stage_start(progress)
            except Exception as e:
                logger.error(f"on_stage_start callback error: {e}")

    def handle_stage_complete(stage_name: str, index: int, total: int, result: dict):
        """Handle stage complete callback from workflow."""
        slug, display_name, display_index = _get_stage_display_info(stage_name)

        progress = StageProgress(
            stage_slug=slug,
            display_name=display_name,
            display_index=display_index,
            status="completed" if result.get("status") == "completed" else "failed",
            current_stage=index + 1,
            total_stages=total,
            output=result.get("output", "")[:500] if result.get("output") else None,
        )

        stages_progress.append(progress)
        logger.info(f"Stage completed: {display_name} (status={result.get('status')})")

        if on_stage_complete:
            try:
                on_stage_complete(progress)
            except Exception as e:
                logger.error(f"on_stage_complete callback error: {e}")

    # Create and run workflow
    try:
        app = config.factory_fn(
            session_manager=session_manager,
            on_stage_start=handle_stage_start,
            on_stage_complete=handle_stage_complete,
            enable_tracking=False,
            **config.factory_kwargs,
        )

        # Run to completion
        terminal_stage = WORKFLOW_TERMINAL_STAGES[config.workflow_type]
        logger.info(f"Running {config.workflow_slug} workflow to terminal stage: {terminal_stage}")

        action, result, state = app.run(halt_after=[terminal_stage])

        final_status = state.get(f"{terminal_stage}_status", "completed")
        execution_time = time.time() - start_time

        # Run post-run hook (e.g., extract recommendation, count stories)
        recommendation = None
        if config.post_run:
            recommendation = config.post_run(state, session_dir)

        logger.info(
            f"{config.workflow_slug} workflow completed in {execution_time:.1f}s "
            f"(status={final_status})"
        )

        if final_status == "completed":
            session_manager.run_tracker.record_workflow_complete(config.workflow_slug)

        return WorkflowResult(
            workflow_type=config.workflow_slug,
            status="completed" if final_status == "completed" else "failed",
            stages=stages_progress,
            execution_time=execution_time,
            recommendation=recommendation,
        )

    except Exception as e:
        logger.error(f"{config.workflow_slug} workflow failed: {e}", exc_info=True)
        execution_time = time.time() - start_time

        return WorkflowResult(
            workflow_type=config.workflow_slug,
            status="failed",
            stages=stages_progress,
            execution_time=execution_time,
            error=str(e),
        )


# =============================================================================
# Pre/Post-run hooks
# =============================================================================


def _idea_validation_pre_run(
    session_manager: SessionManager, session_dir: Path, system_goal: str, clear_existing: bool
) -> None:
    """Pre-run hook for idea validation: clear session and set system goal."""
    if clear_existing and session_dir.exists():
        import shutil

        shutil.rmtree(session_dir)
        session_dir.mkdir(parents=True, exist_ok=True)

    session_manager.set_system_goal(system_goal)
    session_manager.create_session()


def _extract_recommendation(state: Any, session_dir: Path) -> str | None:
    """Post-run hook: extract GO/NO-GO/PIVOT from validation summary state."""
    import json

    terminal_stage = WORKFLOW_TERMINAL_STAGES[WorkflowType.IDEA_VALIDATION]
    validation_output = state.get(terminal_stage, "")
    if not validation_output:
        return None

    # Try JSON first (output_model stores structured JSON in Burr state)
    try:
        data = json.loads(validation_output)
        rec = data.get("recommendation", "").upper()
        if rec in ("NO-GO", "NO_GO"):
            return "NO-GO"
        elif rec == "PIVOT":
            return "PIVOT"
        elif rec == "GO":
            return "GO"
    except (json.JSONDecodeError, TypeError, AttributeError):
        pass

    # Fallback: substring search for legacy markdown
    upper_output = validation_output.upper()
    if "NO-GO" in upper_output or "NO GO" in upper_output:
        return "NO-GO"
    elif "PIVOT" in upper_output:
        return "PIVOT"
    elif "GO" in upper_output:
        return "GO"
    return None


def _count_stories(state: Any, session_dir: Path) -> str | None:
    """Post-run hook: count generated stories."""
    stories_file = session_dir / "generated_stories.json"
    story_count = 0
    if stories_file.exists():
        try:
            stories = json.loads(stories_file.read_text())
            story_count = len(stories) if isinstance(stories, list) else 0
        except Exception:
            pass
    return f"{story_count} stories generated" if story_count > 0 else None


# =============================================================================
# Thin wrappers (backward-compatible public API)
# =============================================================================


def run_idea_validation(
    system_goal: str,
    session_dir: Path,
    on_stage_start: Callable[[StageProgress], None] | None = None,
    on_stage_complete: Callable[[StageProgress], None] | None = None,
    clear_existing: bool = True,
    archetype: str | None = None,
) -> WorkflowResult:
    """Run Idea Validation workflow synchronously."""
    config = WorkflowConfig(
        workflow_type=WorkflowType.IDEA_VALIDATION,
        workflow_slug="idea-validation",
        factory_fn=create_idea_validation_workflow,
        factory_kwargs={"system_goal": system_goal, "archetype": archetype},
        pre_run=lambda sm, sd: _idea_validation_pre_run(sm, sd, system_goal, clear_existing),
        post_run=_extract_recommendation,
    )
    return run_workflow(config, session_dir, on_stage_start, on_stage_complete)


def _factory_for_type(workflow_type: WorkflowType) -> Callable:
    """Return a factory callable that delegates to create_workflow_for_type."""

    def _factory(**kwargs):
        return create_workflow_for_type(workflow_type, **kwargs)

    return _factory


def run_mvp_specification(
    session_dir: Path,
    on_stage_start: Callable[[StageProgress], None] | None = None,
    on_stage_complete: Callable[[StageProgress], None] | None = None,
    force_override: bool = False,
) -> WorkflowResult:
    """Run MVP Specification workflow synchronously."""
    config = WorkflowConfig(
        workflow_type=WorkflowType.MVP_SPECIFICATION,
        workflow_slug="mvp-specification",
        factory_fn=_factory_for_type(WorkflowType.MVP_SPECIFICATION),
        factory_kwargs={"force_override": force_override},
    )
    return run_workflow(config, session_dir, on_stage_start, on_stage_complete)


def run_build_buy_analysis(
    session_dir: Path,
    on_stage_start: Callable[[StageProgress], None] | None = None,
    on_stage_complete: Callable[[StageProgress], None] | None = None,
) -> WorkflowResult:
    """Run Build vs Buy Analysis workflow synchronously."""
    config = WorkflowConfig(
        workflow_type=WorkflowType.BUILD_BUY_ANALYSIS,
        workflow_slug="build-buy-analysis",
        factory_fn=_factory_for_type(WorkflowType.BUILD_BUY_ANALYSIS),
    )
    return run_workflow(config, session_dir, on_stage_start, on_stage_complete)


def run_architecture_decisions(
    session_dir: Path,
    on_stage_start: Callable[[StageProgress], None] | None = None,
    on_stage_complete: Callable[[StageProgress], None] | None = None,
) -> WorkflowResult:
    """Run Architecture Decisions workflow synchronously."""
    config = WorkflowConfig(
        workflow_type=WorkflowType.ARCHITECTURE_DECISIONS,
        workflow_slug="architecture-decisions",
        factory_fn=_factory_for_type(WorkflowType.ARCHITECTURE_DECISIONS),
    )
    return run_workflow(config, session_dir, on_stage_start, on_stage_complete)


def run_story_generation(
    session_dir: Path,
    on_stage_start: Callable[[StageProgress], None] | None = None,
    on_stage_complete: Callable[[StageProgress], None] | None = None,
) -> WorkflowResult:
    """Run Story Generation workflow synchronously."""
    config = WorkflowConfig(
        workflow_type=WorkflowType.STORY_GENERATION,
        workflow_slug="story-generation",
        factory_fn=_factory_for_type(WorkflowType.STORY_GENERATION),
        post_run=_count_stories,
    )
    return run_workflow(config, session_dir, on_stage_start, on_stage_complete)


def get_workflow_status(session_dir: Path) -> dict[str, Any]:
    """Get the current workflow status from session.

    Returns:
        Dict with workflow completion status
    """
    return {
        "idea_validation_complete": (session_dir / "validation-summary").exists(),
        "mvp_specification_complete": (session_dir / "system-traits").exists()
        or (session_dir / "capability-model").exists(),
        "build_buy_analysis_complete": (session_dir / "build-buy-analysis").exists(),
        "architecture_decisions_complete": (session_dir / "architecture-decisions").exists(),
        "technical_design_complete": (
            session_dir / "architecture-decisions"
        ).exists(),  # Backward compat
        "story_generation_complete": (session_dir / "dependency-ordering").exists(),
        "has_project": (session_dir / "project.yaml").exists(),
    }


# =============================================================================
# Feedback Processing Helper
# =============================================================================


def process_workflow_feedback(
    feedback: str,
    workflow_type: str,
    session_dir: Path,
    on_stage_start: Callable[[str], None] | None = None,
    on_stage_complete: Callable[[str], None] | None = None,
):
    """Process user feedback for a completed workflow.

    Args:
        feedback: User's feedback text
        workflow_type: Type of workflow (idea-validation, mvp-specification, etc.)
        session_dir: Path to session directory
        on_stage_start: Callback when a stage revision starts
        on_stage_complete: Callback when a stage revision completes

    Returns:
        FeedbackResult with affected stages, revised stages, and status
    """
    from haytham.feedback.feedback_processor import FeedbackProcessor, FeedbackResult

    # Workflow stage configurations
    workflow_stages = {
        "idea-validation": [
            "idea-analysis",
            "market-context",
            "risk-assessment",
            "validation-summary",
        ],
        "mvp-specification": [
            "mvp-scope",
            "capability-model",
            "system-traits",
        ],
        "build-buy-analysis": [
            "build-buy-analysis",
        ],
        "architecture-decisions": [
            "architecture-decisions",
        ],
        "story-generation": [
            "story-generation",
            "story-validation",
            "dependency-ordering",
        ],
    }

    stages = workflow_stages.get(workflow_type, [])
    if not stages:
        return FeedbackResult(
            affected_stages=[],
            revised_stages=[],
            reasoning=f"Unknown workflow type: {workflow_type}",
            status="failed",
            error=f"Unknown workflow type: {workflow_type}",
        )

    # Get system goal
    from lib.session_utils import get_system_goal

    system_goal = get_system_goal() or ""

    # Create session manager
    base_dir = session_dir.parent
    session_manager = SessionManager(str(base_dir))

    # Create and run processor
    processor = FeedbackProcessor(
        session_manager=session_manager,
        workflow_type=workflow_type,
        workflow_stages=stages,
        system_goal=system_goal,
    )

    result = processor.process_feedback(
        feedback=feedback,
        on_stage_start=on_stage_start,
        on_stage_complete=on_stage_complete,
    )

    return result


def lock_workflow(workflow_type: str, session_dir: Path) -> None:
    """Lock a workflow after user accepts.

    Args:
        workflow_type: Type of workflow to lock
        session_dir: Path to session directory
    """
    base_dir = session_dir.parent
    session_manager = SessionManager(str(base_dir))
    session_manager.run_tracker.lock_workflow(workflow_type)
