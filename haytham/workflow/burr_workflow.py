"""Burr Workflow Runner for Haytham Validation.

This module provides the BurrWorkflowRunner for workflow execution
and the WorkflowResult data class for capturing execution outcomes.

Workflow *creation* (graph definition, transitions, initial state) is
handled by :mod:`haytham.workflow.workflow_factories`.  This module is
the high-level execution layer that adds telemetry, error classification,
and result extraction on top.
"""

import asyncio
import logging
import re
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from burr.core import State

from .workflow_factories import (
    WORKFLOW_TERMINAL_STAGES,
    create_idea_validation_workflow,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Backward-compatible alias
# =============================================================================

# Existing callers (e.g. haytham/workflow/__init__.py) import this name.
create_validation_workflow = create_idea_validation_workflow


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

        Delegates to :func:`workflow_factories.create_idea_validation_workflow`.

        Args:
            system_goal: The startup idea to validate
        """
        self.app = create_idea_validation_workflow(
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

        # Terminal stage for the idea-validation workflow
        from .stage_registry import WorkflowType

        terminal = WORKFLOW_TERMINAL_STAGES.get(WorkflowType.IDEA_VALIDATION, "validation_summary")

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
                    halt_after=[terminal],
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
                    match = re.search(r"\b(NO-GO|PIVOT|GO)\b", summary.upper())
                    if match:
                        recommendation = match.group(1)

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
    ) -> dict[str, Any]:
        """Run a single stage of the workflow.

        This is useful for step-by-step execution with user approval
        between stages.

        Args:
            stage_name: Name of the stage to run
            system_goal: The startup idea

        Returns:
            Dict with stage output and status
        """

        # Create workflow with previous state
        self.create_workflow(system_goal)

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
    runner = BurrWorkflowRunner(
        session_manager=session_manager,
        on_stage_start=on_stage_start,
        on_stage_complete=on_stage_complete,
    )

    # Run in thread pool since Burr is synchronous
    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(
        None,
        lambda: runner.run(system_goal),
    )

    return result
