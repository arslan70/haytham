"""Burr Workflow Definition for Haytham Validation.

This module defines the workflow graph with conditional transitions
and provides the BurrWorkflowRunner for workflow execution.

The workflow supports:
- Linear stage execution (4 validation stages + capability model)
- Conditional branching (HIGH risk -> pivot strategy)
- State persistence and resume
- Human-in-the-loop approvals via callbacks
- OpenTelemetry tracing via workflow_span
"""

import logging
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from burr.core import Application, ApplicationBuilder, State, default, when
from burr.lifecycle import PostRunStepHook, PreRunStepHook
from burr.tracking import LocalTrackingClient

from .burr_actions import (
    idea_analysis,
    market_context,
    pivot_strategy,
    risk_assessment,
    validation_summary,
)
from .workflow_factories import _load_anchor_from_disk

logger = logging.getLogger(__name__)


# =============================================================================
# Lifecycle Hooks
# =============================================================================


@dataclass
class StageProgressHook(PostRunStepHook, PreRunStepHook):
    """Hook to track stage progress and notify callbacks."""

    on_stage_start: Callable[[str, int, int], None] | None = None
    on_stage_complete: Callable[[str, int, int, dict], None] | None = None

    # Stage order for progress calculation
    STAGE_ORDER = [
        "idea_analysis",
        "market_context",
        "risk_assessment",
        "pivot_strategy",  # Optional
        "validation_summary",
    ]

    def pre_run_step(self, *, action, **kwargs):
        """Called before each action runs."""
        stage_name = action.name
        stage_index = self._get_stage_index(stage_name)
        total_stages = 4  # Excluding optional pivot_strategy

        logger.info(f"Starting: {stage_name} ({stage_index + 1}/{total_stages})")

        if self.on_stage_start:
            try:
                self.on_stage_start(stage_name, stage_index, total_stages)
            except Exception as e:
                logger.error(f"on_stage_start callback failed: {e}")

    def post_run_step(self, *, action, state, result, **kwargs):
        """Called after each action completes."""
        stage_name = action.name
        stage_index = self._get_stage_index(stage_name)
        total_stages = 4

        # Get stage status from state
        status_key = f"{stage_name}_status"
        status = state.get(status_key, "unknown")

        logger.info(f"Completed: {stage_name} (status={status})")

        if self.on_stage_complete:
            try:
                stage_result = {
                    "status": status,
                    "output": state.get(stage_name.replace("_", "_"), ""),
                }
                self.on_stage_complete(stage_name, stage_index, total_stages, stage_result)
            except Exception as e:
                logger.error(f"on_stage_complete callback failed: {e}")

    def _get_stage_index(self, stage_name: str) -> int:
        """Get 0-based index of stage."""
        try:
            return self.STAGE_ORDER.index(stage_name)
        except ValueError:
            return 0


# =============================================================================
# Workflow Factory
# =============================================================================


def create_validation_workflow(
    system_goal: str,
    session_manager: Any = None,
    app_id: str = "haytham-validation",
    on_stage_start: Callable | None = None,
    on_stage_complete: Callable | None = None,
    enable_tracking: bool = True,
    tracking_project: str = "haytham-ai",
) -> "Application":
    """Create the startup validation workflow.

    This workflow executes 4 stages with conditional branching:

    ```
    idea_analysis -> market_context -> risk_assessment
                                              |
                            +-----------------+----------------+
                            |                                  |
                         [HIGH]                            [DEFAULT]
                            |                                  |
                            v                                  |
                     pivot_strategy                            |
                            |                                  |
                            +----------------------------------+
                                              |
                                              v
                                    validation_summary (terminal)
    ```

    Args:
        system_goal: The startup idea to validate
        session_manager: SessionManager instance for persistence
        app_id: Unique identifier for this workflow instance
        on_stage_start: Callback(stage_name, index, total) when stage starts
        on_stage_complete: Callback(stage_name, index, total, result) when stage completes
        enable_tracking: Enable Burr tracking UI (default: True)
        tracking_project: Project name for tracking (default: "haytham-ai")

    Returns:
        Burr Application instance

    Note:
        When tracking is enabled, view the workflow at http://localhost:7241
        Start the UI server with: `burr`
    """
    logger.info(f"Creating validation workflow for: {system_goal[:50]}...")
    logger.info(f"App ID: {app_id}, Tracking: {enable_tracking}")

    # Create tracker for observability
    tracker = None
    if enable_tracking:
        tracker = LocalTrackingClient(project=tracking_project)
        logger.info(f"Burr tracking enabled for project: {tracking_project}")

    # Create progress hook with callbacks
    progress_hook = StageProgressHook(
        on_stage_start=on_stage_start,
        on_stage_complete=on_stage_complete,
    )

    # ADR-022: Load anchor from disk if it exists (for workflow resume)
    # This is needed because Burr doesn't persist state between sessions
    loaded_anchor, loaded_anchor_str = _load_anchor_from_disk(session_manager)

    # Build workflow
    builder = (
        ApplicationBuilder()
        # =========================================================
        # Define all actions (stages)
        # =========================================================
        .with_actions(
            idea_analysis=idea_analysis,
            market_context=market_context,
            risk_assessment=risk_assessment,
            pivot_strategy=pivot_strategy,
            validation_summary=validation_summary,
        )
        # =========================================================
        # Define transitions with conditions
        # =========================================================
        .with_transitions(
            # Stage 1 -> Stage 2 (always)
            ("idea_analysis", "market_context"),
            # Stage 2 -> Stage 3 (always)
            ("market_context", "risk_assessment"),
            # Stage 3 -> BRANCH based on risk_level
            # HIGH risk: Go to pivot strategy first
            ("risk_assessment", "pivot_strategy", when(risk_level="HIGH")),
            # MEDIUM/LOW risk: Go directly to validation summary
            ("risk_assessment", "validation_summary", default),
            # Pivot strategy -> Validation summary (always)
            ("pivot_strategy", "validation_summary"),
            # validation_summary is terminal (no outgoing transitions)
        )
        # =========================================================
        # Initial state
        # =========================================================
        .with_state(
            # Input
            system_goal=system_goal,
            session_manager=session_manager,
            # Stage outputs (populated during execution)
            idea_analysis="",
            idea_analysis_status="pending",
            # Concept anchor (ADR-022) - extracted after idea-analysis
            # to prevent concept drift across pipeline stages
            # Loaded from disk if resuming, otherwise populated by post_processor
            concept_anchor=loaded_anchor,
            concept_anchor_str=loaded_anchor_str,
            market_context="",
            market_context_status="pending",
            risk_assessment="",
            risk_level="",  # Used for conditional branching
            risk_assessment_status="pending",
            pivot_strategy="",  # Only populated if HIGH risk
            pivot_strategy_status="pending",
            validation_summary="",
            validation_summary_status="pending",
            # Current stage tracking
            current_stage="",
            # User feedback
            user_approved=True,
            user_feedback="",
        )
        # =========================================================
        # Entry point
        # =========================================================
        .with_entrypoint("idea_analysis")
        # =========================================================
        # Lifecycle hooks
        # =========================================================
        .with_hooks(progress_hook)
        # =========================================================
        # Identity (for persistence)
        # =========================================================
        .with_identifiers(app_id=app_id)
    )

    # Add tracker if enabled
    if tracker:
        builder = builder.with_tracker(tracker)

    app = builder.build()
    return app


# =============================================================================
# Workflow Runner
# =============================================================================


@dataclass
class WorkflowResult:
    """Result of workflow execution."""

    status: str  # COMPLETED, FAILED, IN_PROGRESS
    current_stage: str
    results: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    execution_time: float = 0.0
    failed_stage: str | None = None  # Stage that caused the failure
    recommendation: str | None = None  # GO/NO-GO/PIVOT for completed workflows


class BurrWorkflowRunner:
    """Runner for Burr-based validation workflow.

    This class provides the interface for executing the workflow
    and integrating with the Streamlit UI.
    """

    def __init__(
        self,
        session_manager: Any = None,
        on_stage_start: Callable | None = None,
        on_stage_complete: Callable | None = None,
        on_feedback_request: Callable | None = None,
    ):
        """Initialize the workflow runner.

        Args:
            session_manager: SessionManager for state persistence
            on_stage_start: Callback when stage starts
            on_stage_complete: Callback when stage completes
            on_feedback_request: Callback to request user feedback
        """
        self.session_manager = session_manager
        self.on_stage_start = on_stage_start
        self.on_stage_complete = on_stage_complete
        self.on_feedback_request = on_feedback_request
        self.app = None
        self._is_running = False

    def create_workflow(self, system_goal: str) -> None:
        """Create the workflow with the given system goal.

        Args:
            system_goal: The startup idea to validate
        """
        self.app = create_validation_workflow(
            system_goal=system_goal,
            session_manager=self.session_manager,
            on_stage_start=self.on_stage_start,
            on_stage_complete=self.on_stage_complete,
        )

    def run(
        self,
        system_goal: str,
        resume_from: str | None = None,
    ) -> WorkflowResult:
        """Run the workflow to completion.

        Args:
            system_goal: The startup idea to validate
            resume_from: Optional stage to resume from

        Returns:
            WorkflowResult with execution status and outputs
        """
        import time

        # Import telemetry (lazy to avoid circular imports)
        try:
            from haytham.telemetry import init_telemetry, workflow_span

            # Initialize telemetry if not already done
            init_telemetry()
        except ImportError:
            # Telemetry not available - use no-op context manager
            from contextlib import nullcontext

            def workflow_span(*args, **kwargs):
                return nullcontext()

        start_time = time.time()
        self._is_running = True

        # Generate session ID for tracing correlation
        session_id = str(uuid.uuid4())

        # Execute workflow within a workflow span
        with workflow_span(
            workflow_name="idea-validation",
            system_goal=system_goal,
            session_id=session_id,
        ) as span:
            try:
                # Create workflow
                self.create_workflow(system_goal)

                logger.info("=" * 60)
                logger.info("BURR WORKFLOW EXECUTION STARTED")
                logger.info(f"System Goal: {system_goal[:50]}...")
                logger.info(f"Session ID: {session_id}")
                logger.info("=" * 60)

                # Run workflow to completion
                final_action, final_result, final_state = self.app.run(
                    halt_after=["validation_summary"],
                    inputs={},
                )

                execution_time = time.time() - start_time

                # Extract results from state
                results = self._extract_results(final_state)

                # Record workflow metrics in span
                if hasattr(span, "set_attribute"):
                    span.set_attribute("workflow.duration_seconds", execution_time)
                    span.set_attribute("workflow.final_stage", final_action.name)
                    risk_level = final_state.get("risk_level", "UNKNOWN")
                    span.set_attribute("workflow.risk_level", risk_level)

                # Check for failures and identify which stage failed
                stage_names = [
                    "idea_analysis",
                    "market_context",
                    "risk_assessment",
                    "validation_summary",
                ]
                failed_stage = None
                stage_error = None

                for stage in stage_names:
                    if final_state.get(f"{stage}_status") == "failed":
                        failed_stage = stage
                        # Try to get the error from the stage output
                        stage_output = final_state.get(stage, "")
                        if isinstance(stage_output, str) and stage_output.startswith("Error"):
                            stage_error = stage_output
                        break

                if failed_stage:
                    # Convert stage name to display format
                    failed_stage_display = failed_stage.replace("_", " ").title()
                    error_msg = stage_error or f"Stage '{failed_stage_display}' failed"

                    if hasattr(span, "set_attribute"):
                        span.set_attribute("workflow.status", "FAILED")
                        span.set_attribute("workflow.failed_stage", failed_stage)

                    return WorkflowResult(
                        status="FAILED",
                        current_stage=final_action.name,
                        results=results,
                        error=error_msg,
                        failed_stage=failed_stage_display,
                        execution_time=execution_time,
                    )

                # Extract recommendation from results
                recommendation = None
                if results.get("validation_summary"):
                    summary = results["validation_summary"]
                    if "GO" in summary.upper():
                        recommendation = "GO" if "NO-GO" not in summary.upper() else "NO-GO"
                    elif "PIVOT" in summary.upper():
                        recommendation = "PIVOT"

                logger.info("=" * 60)
                logger.info("WORKFLOW COMPLETED SUCCESSFULLY")
                logger.info(f"Execution time: {execution_time:.1f}s")
                logger.info(f"Recommendation: {recommendation or 'See results'}")
                logger.info("=" * 60)

                if hasattr(span, "set_attribute"):
                    span.set_attribute("workflow.status", "COMPLETED")
                    if recommendation:
                        span.set_attribute("workflow.recommendation", recommendation)

                return WorkflowResult(
                    status="COMPLETED",
                    current_stage=final_action.name,
                    results=results,
                    execution_time=execution_time,
                    recommendation=recommendation,
                )

            except Exception as e:
                execution_time = time.time() - start_time
                logger.error(f"Workflow execution failed: {e}", exc_info=True)

                if hasattr(span, "set_attribute"):
                    span.set_attribute("workflow.status", "FAILED")
                    span.set_attribute("workflow.error", str(e))

                return WorkflowResult(
                    status="FAILED",
                    current_stage="unknown",
                    results={},
                    error=str(e),
                    execution_time=execution_time,
                )

            finally:
                self._is_running = False

    def run_single_stage(
        self,
        stage_name: str,
        system_goal: str,
        previous_outputs: dict[str, str] = None,
    ) -> dict[str, Any]:
        """Run a single stage of the workflow.

        This is useful for step-by-step execution with user approval
        between stages.

        Args:
            stage_name: Name of the stage to run
            system_goal: The startup idea
            previous_outputs: Outputs from previous stages

        Returns:
            Dict with stage output and status
        """
        if previous_outputs is None:
            previous_outputs = {}

        # Create workflow with previous state
        self.create_workflow(system_goal)

        # Update state with previous outputs
        if previous_outputs:
            # This would require modifying the workflow state
            # For now, context is passed through state
            pass

        # Run until this stage completes
        action, result, state = self.app.run(
            halt_after=[stage_name],
            inputs={},
        )

        return {
            "stage": stage_name,
            "status": state.get(f"{stage_name}_status", "unknown"),
            "output": state.get(stage_name.replace("_status", ""), ""),
        }

    def _extract_results(self, state: State) -> dict[str, Any]:
        """Extract results from workflow state."""
        return {
            "idea-analysis": {
                "status": state.get("idea_analysis_status", "pending"),
                "outputs": {"concept_expansion": state.get("idea_analysis", "")},
            },
            "market-context": {
                "status": state.get("market_context_status", "pending"),
                "outputs": {"combined": state.get("market_context", "")},
            },
            "risk-assessment": {
                "status": state.get("risk_assessment_status", "pending"),
                "outputs": {"startup_validator": state.get("risk_assessment", "")},
                "risk_level": state.get("risk_level", "MEDIUM"),
            },
            "pivot-strategy": {
                "status": state.get("pivot_strategy_status", "pending"),
                "outputs": {"pivot_advisor": state.get("pivot_strategy", "")},
            },
            "validation-summary": {
                "status": state.get("validation_summary_status", "pending"),
                "outputs": {"report_synthesis": state.get("validation_summary", "")},
            },
        }

    @property
    def is_running(self) -> bool:
        """Check if workflow is currently running."""
        return self._is_running


# =============================================================================
# Async Wrapper
# =============================================================================


async def run_workflow_async(
    system_goal: str,
    session_manager: Any = None,
    on_stage_start: Callable | None = None,
    on_stage_complete: Callable | None = None,
) -> WorkflowResult:
    """Run the workflow asynchronously.

    Args:
        system_goal: The startup idea to validate
        session_manager: SessionManager for persistence
        on_stage_start: Async callback when stage starts
        on_stage_complete: Async callback when stage completes

    Returns:
        WorkflowResult with execution status
    """
    import asyncio

    runner = BurrWorkflowRunner(
        session_manager=session_manager,
        on_stage_start=on_stage_start,
        on_stage_complete=on_stage_complete,
    )

    # Run in thread pool since Burr is synchronous
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        None,
        lambda: runner.run(system_goal),
    )

    return result
