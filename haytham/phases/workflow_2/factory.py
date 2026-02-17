"""Workflow 2 Factory: Create the Technical Translation workflow.

DEPRECATED: This module is deprecated as of ADR-016 (Four-Phase Workflow).
Use haytham.workflow.workflow_factories instead.

The four-phase architecture separates:
- Phase 3: Technical Design (build-buy-analysis, architecture-decisions)
- Phase 4: Story Generation (story-generation, story-validation, dependency-ordering)

This module is kept for backwards compatibility but will be removed in a future version.

Original description:
This module creates the Burr workflow for the Technical Translation phase
(Workflow 2) as defined in ADR-005. It handles:

1. Entry condition validation (capabilities, MVP scope, etc.)
2. Loading all required data from VectorDB and Backlog.md
3. Computing the architecture diff
4. Creating the Burr application with proper initial state

The workflow translates capabilities into implementable stories with
full traceability (implements:CAP-* labels).
"""

import json
import logging
import uuid
import warnings
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from burr.core import ApplicationBuilder

from .diff import ArchitectureDiff, compute_architecture_diff, get_diff_context_for_prompt

logger = logging.getLogger(__name__)


# =============================================================================
# Entry Condition Validation
# =============================================================================


@dataclass
class EntryConditionResult:
    """Result of entry condition validation."""

    passed: bool
    message: str
    details: dict[str, Any]


def validate_entry_conditions(session_manager) -> EntryConditionResult:
    """Validate entry conditions for Workflow 2 via the canonical validator.

    Delegates to BuildBuyAnalysisEntryValidator in entry_validators/build_buy.py,
    which is the single source of truth for Build/Buy entry validation.
    """
    from haytham.workflow.entry_validators import validate_workflow_entry
    from haytham.workflow.stage_registry import WorkflowType

    result = validate_workflow_entry(WorkflowType.BUILD_BUY_ANALYSIS, session_manager)
    return EntryConditionResult(
        passed=result.passed,
        message=result.message,
        details={"errors": [], "warnings": []},
    )


# =============================================================================
# Data Loading
# =============================================================================


@dataclass
class WorkflowContext:
    """All context needed for Workflow 2 execution.

    This is assembled from VectorDB, Backlog.md, and session state.
    """

    # From VectorDB
    capabilities: list[dict]
    decisions: list[dict]
    entities: list[dict]

    # From Backlog.md
    stories: list[dict]

    # From Session
    system_goal: str
    mvp_scope: str
    validation_summary: str

    # Computed
    diff: ArchitectureDiff

    # Audit
    run_id: str
    run_number: int


def load_workflow_context(session_manager, project_id: str = None) -> WorkflowContext:
    """Load all context needed for Workflow 2.

    Args:
        session_manager: SessionManager instance
        project_id: Optional project identifier

    Returns:
        WorkflowContext with all required data

    Raises:
        ValueError: If required data is missing
    """
    logger.info("Loading Workflow 2 context...")

    # 1. Load from VectorDB
    from haytham.state.vector_db import SystemStateDB

    db_path = session_manager.session_dir / "vector_db"
    db = SystemStateDB(str(db_path))

    capabilities = db.get_capabilities()
    decisions = db.get_decisions()
    entities = db.get_entities()

    logger.info(
        f"Loaded from VectorDB: {len(capabilities)} capabilities, "
        f"{len(decisions)} decisions, {len(entities)} entities"
    )

    # 2. Load from Backlog.md
    stories = []
    try:
        from haytham.backlog import BacklogCLI

        cli = BacklogCLI(session_manager.session_dir.parent)
        if cli.is_initialized():
            # Load all tasks and convert to dict format for diff computation
            tasks = cli.list_tasks()
            stories = [
                {
                    "id": task.id,
                    "title": task.title,
                    "status": task.status,
                    "labels": task.labels,
                    "priority": task.priority,
                }
                for task in tasks
            ]
            logger.info(f"Loaded {len(stories)} stories from Backlog.md")
        else:
            logger.info("Backlog.md not initialized - no stories to load")
    except ImportError:
        logger.warning("BacklogCLI not available")
    except Exception as e:
        logger.warning(f"Could not load stories from Backlog.md: {e}")

    # 3. Load from Session
    system_goal = session_manager.get_system_goal() or ""
    mvp_scope = session_manager.load_stage_output("mvp-scope") or ""
    validation_summary = session_manager.load_stage_output("validation-summary") or ""

    if not mvp_scope:
        raise ValueError("MVP Scope not found - cannot proceed with Workflow 2")

    # 4. Compute architecture diff
    diff = compute_architecture_diff(
        capabilities=capabilities,
        decisions=decisions,
        entities=entities,
        stories=stories,
    )

    logger.info(f"Architecture diff: {diff.summary()}")

    # 5. Create audit record
    run_id = str(uuid.uuid4())

    # Count existing architect workflow runs
    workflow_runs_file = session_manager.session_dir / "workflow_runs.json"
    if workflow_runs_file.exists():
        try:
            runs = json.loads(workflow_runs_file.read_text())
            architect_runs = [r for r in runs if r.get("workflow_type") == "architect"]
            run_number = len(architect_runs) + 1
        except json.JSONDecodeError:
            run_number = 1
    else:
        run_number = 1

    return WorkflowContext(
        capabilities=capabilities,
        decisions=decisions,
        entities=entities,
        stories=stories,
        system_goal=system_goal,
        mvp_scope=mvp_scope,
        validation_summary=validation_summary,
        diff=diff,
        run_id=run_id,
        run_number=run_number,
    )


# =============================================================================
# Workflow Actions (imported from actions module)
# =============================================================================

from .actions import (
    architecture_decisions,
    component_boundaries,
    dependency_ordering,
    story_generation,
    story_validation,
)


def create_architect_workflow(
    session_manager,
    project_id: str = None,
    on_stage_start: Callable | None = None,
    on_stage_complete: Callable | None = None,
    enable_tracking: bool = True,
    tracking_project: str = "haytham-architect",
) -> tuple[Any, WorkflowContext]:
    """Create Workflow 2 (Technical Translation) with diff-based architecture awareness.

    DEPRECATED: Use workflow_factories.create_build_buy_analysis_workflow() / create_architecture_decisions_workflow() and
    workflow_factories.create_story_generation_workflow() instead.
    See ADR-016 for the four-phase workflow architecture.

    This factory function:
    1. Validates entry conditions
    2. Loads all required context from VectorDB, Backlog.md, and session
    3. Computes the architecture diff
    4. Creates the Burr workflow application

    Args:
        session_manager: SessionManager instance
        project_id: Optional project identifier (defaults to session-based ID)
        on_stage_start: Callback(stage_name, index, total) when stage starts
        on_stage_complete: Callback(stage_name, index, total, result) when stage completes
        enable_tracking: Enable Burr tracking UI (default: True)
        tracking_project: Project name for tracking

    Returns:
        Tuple of (Burr Application, WorkflowContext)

    Raises:
        ValueError: If entry conditions are not met
    """
    warnings.warn(
        "create_architect_workflow is deprecated. Use workflow_factories.create_build_buy_analysis_workflow() / create_architecture_decisions_workflow() "
        "and workflow_factories.create_story_generation_workflow() instead. See ADR-016.",
        DeprecationWarning,
        stacklevel=2,
    )
    logger.info("=" * 60)
    logger.info("CREATING WORKFLOW 2: TECHNICAL TRANSLATION")
    logger.info("=" * 60)

    # 1. Validate entry conditions
    validation = validate_entry_conditions(session_manager)

    if not validation.passed:
        logger.error(f"Entry condition validation failed: {validation.message}")
        raise ValueError(validation.message)

    logger.info(f"Entry conditions passed: {validation.message}")

    # 2. Load all context
    context = load_workflow_context(session_manager, project_id)

    # 3. Record workflow run for audit
    workflow_runs_file = session_manager.session_dir / "workflow_runs.json"
    if workflow_runs_file.exists():
        try:
            runs = json.loads(workflow_runs_file.read_text())
        except json.JSONDecodeError:
            runs = []
    else:
        runs = []

    run_record = {
        "run_id": context.run_id,
        "workflow_type": "architect",
        "run_number": context.run_number,
        "created_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "status": "running",
        "trigger": {
            "type": "user_initiated",
            "source_workflow": "discovery",
        },
        "diff_summary": context.diff.summary(),
    }
    runs.append(run_record)
    workflow_runs_file.write_text(json.dumps(runs, indent=2))

    # 4. Create tracker for observability
    tracker = None
    if enable_tracking:
        try:
            from burr.tracking import LocalTrackingClient

            tracker = LocalTrackingClient(project=tracking_project)
            logger.info(f"Burr tracking enabled for project: {tracking_project}")
        except ImportError:
            logger.warning("Burr tracking not available")

    # 5. Build initial state with full context
    app_id = f"haytham-architect-{project_id or 'default'}-run{context.run_number}"

    # Prepare diff context for prompts
    diff_context = get_diff_context_for_prompt(context.diff)

    # Build workflow
    builder = (
        ApplicationBuilder()
        # Define all actions (stages)
        .with_actions(
            architecture_decisions=architecture_decisions,
            component_boundaries=component_boundaries,
            story_generation=story_generation,
            story_validation=story_validation,
            dependency_ordering=dependency_ordering,
        )
        # Define transitions (linear for now)
        .with_transitions(
            ("architecture_decisions", "component_boundaries"),
            ("component_boundaries", "story_generation"),
            ("story_generation", "story_validation"),
            ("story_validation", "dependency_ordering"),
            # dependency_ordering is terminal
        )
        # Initial state with full context
        .with_state(
            # Project context
            project_id=project_id or "default",
            system_goal=context.system_goal,
            mvp_scope=context.mvp_scope,
            validation_summary=context.validation_summary,
            session_manager=session_manager,
            # VectorDB data
            capabilities=context.capabilities,
            existing_decisions=context.decisions,
            existing_entities=context.entities,
            # Backlog.md data
            existing_stories=context.stories,
            # The key context - what needs attention
            architecture_diff=context.diff,
            diff_context=diff_context,
            # Stage outputs (populated during execution)
            architecture_decisions_status="pending",
            architecture_decisions_output="",
            component_boundaries_status="pending",
            component_boundaries_output="",
            story_generation_status="pending",
            story_generation_output="",
            story_validation_status="pending",
            story_validation_output="",
            dependency_ordering_status="pending",
            dependency_ordering_output="",
            # Workflow audit
            workflow_run_id=context.run_id,
            workflow_run_number=context.run_number,
        )
        # Entry point
        .with_entrypoint("architecture_decisions")
        # Identity for persistence
        .with_identifiers(app_id=app_id)
    )

    # Add tracker if enabled
    if tracker:
        builder = builder.with_tracker(tracker)

    app = builder.build()

    logger.info(f"Created Workflow 2 with app_id: {app_id}")
    logger.info(f"Run ID: {context.run_id}, Run Number: {context.run_number}")
    logger.info(f"Diff: {context.diff.summary()}")

    return app, context


# =============================================================================
# Workflow Runner
# =============================================================================


@dataclass
class Workflow2Result:
    """Result of Workflow 2 execution."""

    status: str  # COMPLETED, FAILED, IN_PROGRESS
    message: str
    diff_summary: str
    run_id: str
    run_number: int
    stage_results: dict = None


def run_architect_workflow(session_manager, execute: bool = True) -> Workflow2Result:
    """Run Workflow 2 (Technical Translation).

    DEPRECATED: Use workflow_runner.run_build_buy_analysis() / run_architecture_decisions() and
    workflow_runner.run_story_generation() instead.
    See ADR-016 for the four-phase workflow architecture.

    Args:
        session_manager: SessionManager instance
        execute: If True, actually run the workflow. If False, just validate and create.

    Returns:
        Workflow2Result with execution status
    """
    warnings.warn(
        "run_architect_workflow is deprecated. Use workflow_runner.run_build_buy_analysis() / run_architecture_decisions() "
        "and workflow_runner.run_story_generation() instead. See ADR-016.",
        DeprecationWarning,
        stacklevel=2,
    )
    import time

    try:
        # Create the workflow
        app, context = create_architect_workflow(session_manager)

        if not execute:
            # Just validate and create, don't run
            return Workflow2Result(
                status="READY",
                message="Workflow 2 created and ready to execute.",
                diff_summary=context.diff.summary(),
                run_id=context.run_id,
                run_number=context.run_number,
            )

        # Run the workflow to completion
        logger.info("=" * 60)
        logger.info("EXECUTING WORKFLOW 2")
        logger.info("=" * 60)

        start_time = time.time()

        try:
            # Run until dependency_ordering completes (terminal state)
            final_action, final_result, final_state = app.run(
                halt_after=["dependency_ordering"],
                inputs={},
            )

            execution_time = time.time() - start_time

            # Extract stage results
            stage_results = {
                "architecture_decisions": {
                    "status": final_state.get("architecture_decisions_status"),
                    "output": final_state.get("architecture_decisions_output", "")[:500],
                },
                "component_boundaries": {
                    "status": final_state.get("component_boundaries_status"),
                    "output": final_state.get("component_boundaries_output", "")[:500],
                },
                "story_generation": {
                    "status": final_state.get("story_generation_status"),
                    "output": final_state.get("story_generation_output", "")[:500],
                },
                "story_validation": {
                    "status": final_state.get("story_validation_status"),
                    "output": final_state.get("story_validation_output", "")[:500],
                },
                "dependency_ordering": {
                    "status": final_state.get("dependency_ordering_status"),
                    "output": final_state.get("dependency_ordering_output", "")[:500],
                },
            }

            # Check for failures
            failed_stages = [
                name for name, result in stage_results.items() if result.get("status") == "failed"
            ]

            if failed_stages:
                logger.warning(f"Workflow completed with failures: {failed_stages}")
                return Workflow2Result(
                    status="COMPLETED_WITH_ERRORS",
                    message=f"Workflow completed in {execution_time:.1f}s with {len(failed_stages)} failed stages: {', '.join(failed_stages)}",
                    diff_summary=context.diff.summary(),
                    run_id=context.run_id,
                    run_number=context.run_number,
                    stage_results=stage_results,
                )

            logger.info(f"Workflow 2 completed successfully in {execution_time:.1f}s")

            # Update workflow run status
            _update_workflow_run_status(session_manager, context.run_id, "completed")

            return Workflow2Result(
                status="COMPLETED",
                message=f"Workflow 2 completed successfully in {execution_time:.1f}s",
                diff_summary=context.diff.summary(),
                run_id=context.run_id,
                run_number=context.run_number,
                stage_results=stage_results,
            )

        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Workflow execution failed: {e}", exc_info=True)

            _update_workflow_run_status(session_manager, context.run_id, "failed")

            return Workflow2Result(
                status="FAILED",
                message=f"Workflow execution failed after {execution_time:.1f}s: {str(e)}",
                diff_summary=context.diff.summary(),
                run_id=context.run_id,
                run_number=context.run_number,
            )

    except ValueError as e:
        return Workflow2Result(
            status="FAILED",
            message=str(e),
            diff_summary="N/A",
            run_id="",
            run_number=0,
        )
    except Exception as e:
        logger.error(f"Failed to run Workflow 2: {e}", exc_info=True)
        return Workflow2Result(
            status="FAILED",
            message=f"Unexpected error: {str(e)}",
            diff_summary="N/A",
            run_id="",
            run_number=0,
        )


def _update_workflow_run_status(session_manager, run_id: str, status: str):
    """Update the status of a workflow run in workflow_runs.json."""
    workflow_runs_file = session_manager.session_dir / "workflow_runs.json"

    if not workflow_runs_file.exists():
        return

    try:
        runs = json.loads(workflow_runs_file.read_text())
        for run in runs:
            if run.get("run_id") == run_id:
                run["status"] = status
                run["completed_at"] = datetime.now(UTC).isoformat().replace("+00:00", "Z")
                break
        workflow_runs_file.write_text(json.dumps(runs, indent=2))
    except Exception as e:
        logger.warning(f"Failed to update workflow run status: {e}")
