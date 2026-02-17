"""Burr Workflow Runner for Haytham Validation.

This module provides the BurrWorkflowRunner for workflow execution
and the WorkflowResult data class for capturing execution outcomes.

Workflow *creation* (graph definition, transitions, initial state) is
handled by :mod:`haytham.workflow.workflow_factories`.  This module is
the high-level execution layer that adds telemetry, error classification,
and result extraction on top.
"""

import json
import logging
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from burr.core import State

from haytham.agents.tools.metric_patterns import RE_RECOMMENDATION_PLAIN

from .stage_registry import WorkflowType, get_stage_registry
from .workflow_factories import (
    WORKFLOW_TERMINAL_STAGES,
    create_idea_validation_workflow,
)
from .workflow_specs import IDEA_VALIDATION_SPEC

logger = logging.getLogger(__name__)


# =============================================================================
# Backward-compatible alias
# =============================================================================

# Existing callers (e.g. haytham/workflow/__init__.py) import this name.
create_validation_workflow = create_idea_validation_workflow


# =============================================================================
# Recommendation Extraction
# =============================================================================


def _extract_recommendation(
    final_state: State,
    results: dict[str, Any],
    session_manager: Any,
) -> str | None:
    """Extract GO/NO-GO/PIVOT recommendation via 3-tier fallback.

    Tier 1: Burr state (written by extract_recommendation_processor).
    Tier 2: recommendation.json on disk (written by same processor).
    Tier 3: Anchored regex on validation-summary output (backward compat).

    Args:
        final_state: Final Burr state after workflow execution.
        results: Extracted results dict from _extract_results().
        session_manager: SessionManager instance (may be None).

    Returns:
        Recommendation string ("GO", "NO-GO", "PIVOT") or None.
    """
    # Tier 1: Burr state (set by extract_recommendation_processor post-processor)
    rec = final_state.get("recommendation")
    if rec and rec in ("GO", "NO-GO", "PIVOT"):
        logger.info(f"Recommendation from Burr state: {rec}")
        return rec

    # Tier 2: recommendation.json on disk
    if session_manager and hasattr(session_manager, "session_dir"):
        meta_path = Path(session_manager.session_dir) / "recommendation.json"
        if meta_path.exists():
            try:
                data = json.loads(meta_path.read_text())
                rec = data.get("recommendation", "").upper().strip()
                if rec in ("GO", "NO-GO", "PIVOT"):
                    logger.info(f"Recommendation from recommendation.json: {rec}")
                    return rec
            except (json.JSONDecodeError, OSError):
                pass

    # Tier 3: Anchored regex on validation-summary output (correct hyphenated key)
    vs_result = results.get("validation-summary")
    if vs_result:
        summary_text = ""
        if isinstance(vs_result, dict):
            outputs = vs_result.get("outputs", {})
            summary_text = outputs.get("report_synthesis", "")
        elif isinstance(vs_result, str):
            summary_text = vs_result
        if summary_text:
            match = RE_RECOMMENDATION_PLAIN.search(summary_text.upper())
            if match:
                rec = match.group(1)
                logger.info(f"Recommendation from regex fallback: {rec}")
                return rec

    return None


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
        from haytham.telemetry_utils import get_workflow_span

        init_telemetry, workflow_span = get_workflow_span()
        init_telemetry()

        start_time = time.time()
        self._is_running = True

        # Generate session ID for tracing correlation
        session_id = str(uuid.uuid4())

        # Terminal stage for the idea-validation workflow
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
                logger.info(f"System goal provided (length={len(system_goal)})")
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
                registry = get_stage_registry()
                stage_names = IDEA_VALIDATION_SPEC.stages
                failed_stage = None
                stage_error = None

                for stage in stage_names:
                    stage_meta = registry.get_by_action_safe(stage)
                    status_key = stage_meta.status_key if stage_meta else f"{stage}_status"
                    if final_state.get(status_key) == "failed":
                        failed_stage = stage
                        # Try to get the error from the stage output
                        state_key = stage_meta.state_key if stage_meta else stage
                        stage_output = final_state.get(state_key, "")
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

                # Extract recommendation via 3-tier fallback
                recommendation = _extract_recommendation(final_state, results, self.session_manager)

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

            except Exception as e:  # Intentional catch-all: top-level workflow boundary
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
