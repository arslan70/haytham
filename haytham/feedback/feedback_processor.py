"""Feedback processor - main orchestrator for feedback handling.

This module provides the FeedbackProcessor class which orchestrates the
complete feedback processing flow:

1. Routes feedback to affected stages using the LLM router
2. Calculates cascade scope (downstream stages within the workflow)
3. Executes revisions in order
4. Updates session with revised outputs

The processor operates within a single workflow - feedback never affects
stages in other workflows.
"""

import logging
from collections.abc import Callable
from dataclasses import dataclass, field

from haytham.feedback.cascade_engine import get_cascade_summary, get_stages_to_revise
from haytham.feedback.feedback_router import FeedbackRouteResult, route_feedback
from haytham.feedback.revision_executor import (
    RevisionResult,
    execute_revision,
    get_revision_context_for_stage,
)
from haytham.session.session_manager import SessionManager

logger = logging.getLogger(__name__)


@dataclass
class FeedbackResult:
    """Result of feedback processing.

    Attributes:
        affected_stages: Stages directly affected by the feedback (from router)
        revised_stages: All stages that were revised (including cascade)
        revision_results: Individual results for each stage revision
        reasoning: Router's reasoning for stage selection
        cascade_summary: Human-readable summary of what was affected
        status: Overall status ("completed", "partial", "failed")
        error: Error message if processing failed
    """

    affected_stages: list[str]
    revised_stages: list[str]
    revision_results: list[RevisionResult] = field(default_factory=list)
    reasoning: str = ""
    cascade_summary: str = ""
    status: str = "completed"
    error: str | None = None

    @property
    def success(self) -> bool:
        """Check if all revisions succeeded."""
        return self.status == "completed" and all(r.success for r in self.revision_results)


class FeedbackProcessor:
    """Orchestrates feedback processing within a single workflow.

    This class manages the complete feedback loop:
    1. Routes feedback to determine which stages are affected
    2. Calculates which downstream stages need cascading updates
    3. Executes revisions in order (earliest affected first)
    4. Provides progress callbacks for UI updates

    The processor ensures feedback only affects stages within the current
    workflow - it will never modify stages from a different workflow.

    Attributes:
        session_manager: Session manager for loading/saving outputs
        workflow_type: Type of workflow being processed
        workflow_stages: Ordered list of stage slugs in the workflow
        system_goal: Original startup idea for context

    Example:
        >>> processor = FeedbackProcessor(
        ...     session_manager=session_mgr,
        ...     workflow_type="idea-validation",
        ...     workflow_stages=["idea-analysis", "market-context", "risk-assessment", "validation-summary"],
        ...     system_goal="A SaaS tool for validating startup ideas",
        ... )
        >>> result = processor.process_feedback(
        ...     feedback="Add more focus on B2B market segment",
        ...     on_stage_start=lambda slug: print(f"Revising {slug}..."),
        ...     on_stage_complete=lambda slug: print(f"Completed {slug}"),
        ... )
        >>> print(result.cascade_summary)
        'Feedback affects Market Context. Will also update: Risk Assessment, Validation Summary.'
    """

    def __init__(
        self,
        session_manager: SessionManager,
        workflow_type: str,
        workflow_stages: list[str],
        system_goal: str,
    ):
        """Initialize the feedback processor.

        Args:
            session_manager: Session manager for persistence
            workflow_type: Type of workflow (e.g., "idea-validation")
            workflow_stages: Ordered list of stage slugs in this workflow
            system_goal: Original startup idea for context
        """
        self.session_manager = session_manager
        self.workflow_type = workflow_type
        self.workflow_stages = workflow_stages
        self.system_goal = system_goal

    def process_feedback(
        self,
        feedback: str,
        on_stage_start: Callable[[str], None] | None = None,
        on_stage_complete: Callable[[str], None] | None = None,
    ) -> FeedbackResult:
        """Process user feedback end-to-end.

        This method:
        1. Routes feedback to determine affected stages
        2. Calculates cascade scope
        3. Revises stages in order
        4. Returns comprehensive results

        Args:
            feedback: User's feedback text
            on_stage_start: Optional callback when revision starts for a stage
            on_stage_complete: Optional callback when revision completes for a stage

        Returns:
            FeedbackResult with affected stages, revised stages, and status

        Note:
            If any stage revision fails, processing continues with remaining
            stages and the result status will be "partial".
        """
        logger.info(f"Processing feedback for workflow '{self.workflow_type}': {feedback[:100]}...")

        try:
            # Step 1: Route feedback to affected stages
            route_result = self._route_feedback(feedback)

            if not route_result.affected_stages:
                logger.warning("Router returned no affected stages")
                return FeedbackResult(
                    affected_stages=[],
                    revised_stages=[],
                    reasoning=route_result.reasoning,
                    cascade_summary="No stages affected by feedback.",
                    status="completed",
                )

            # Step 2: Calculate cascade scope
            stages_to_revise = get_stages_to_revise(
                affected_stages=route_result.affected_stages,
                workflow_stages=self.workflow_stages,
            )

            # Step 3: Generate cascade summary for UI
            cascade_summary = get_cascade_summary(
                affected_stages=route_result.affected_stages,
                stages_to_revise=stages_to_revise,
            )

            logger.info(f"Will revise stages: {stages_to_revise}")

            # Step 4: Execute revisions in order
            revision_results = self._execute_revisions(
                feedback=feedback,
                affected_stages=route_result.affected_stages,
                stages_to_revise=stages_to_revise,
                on_stage_start=on_stage_start,
                on_stage_complete=on_stage_complete,
            )

            # Determine overall status
            all_success = all(r.success for r in revision_results)
            any_success = any(r.success for r in revision_results)

            if all_success:
                status = "completed"
            elif any_success:
                status = "partial"
            else:
                status = "failed"

            revised_slugs = [r.stage_slug for r in revision_results if r.success]

            return FeedbackResult(
                affected_stages=route_result.affected_stages,
                revised_stages=revised_slugs,
                revision_results=revision_results,
                reasoning=route_result.reasoning,
                cascade_summary=cascade_summary,
                status=status,
            )

        except Exception as e:
            logger.error(f"Error processing feedback: {e}")
            return FeedbackResult(
                affected_stages=[],
                revised_stages=[],
                reasoning="",
                cascade_summary="",
                status="failed",
                error=str(e),
            )

    def _route_feedback(self, feedback: str) -> FeedbackRouteResult:
        """Route feedback to affected stages.

        Args:
            feedback: User's feedback text

        Returns:
            FeedbackRouteResult with affected stages
        """
        return route_feedback(
            feedback=feedback,
            workflow_type=self.workflow_type,
            available_stages=self.workflow_stages,
        )

    def _execute_revisions(
        self,
        feedback: str,
        affected_stages: list[str],
        stages_to_revise: list[str],
        on_stage_start: Callable[[str], None] | None = None,
        on_stage_complete: Callable[[str], None] | None = None,
    ) -> list[RevisionResult]:
        """Execute revisions for all stages in order.

        Stages directly affected by feedback get the full feedback context.
        Downstream stages (cascade) get context from revised upstream stages.

        Args:
            feedback: Original user feedback
            affected_stages: Stages directly affected by feedback
            stages_to_revise: All stages to revise (in order)
            on_stage_start: Progress callback
            on_stage_complete: Progress callback

        Returns:
            List of RevisionResult for each stage
        """
        results = []
        revised_so_far = []

        for stage_slug in stages_to_revise:
            logger.info(f"Revising stage '{stage_slug}'...")

            if on_stage_start:
                on_stage_start(stage_slug)

            # Determine if this is a direct feedback or cascade revision
            is_direct_feedback = stage_slug in affected_stages

            # For cascade revisions, build context from revised upstream stages
            upstream_context = None
            if not is_direct_feedback and revised_so_far:
                upstream_context = get_revision_context_for_stage(
                    session_manager=self.session_manager,
                    stage_slug=stage_slug,
                    revised_stages=revised_so_far,
                )

            # Execute the revision
            result = execute_revision(
                stage_slug=stage_slug,
                feedback=feedback if is_direct_feedback else None,
                session_manager=self.session_manager,
                system_goal=self.system_goal,
                is_cascade=not is_direct_feedback,
                upstream_context=upstream_context,
            )

            results.append(result)

            if result.success:
                revised_so_far.append(stage_slug)

            if on_stage_complete:
                on_stage_complete(stage_slug)

            # Note: We continue even if a stage fails, to provide partial results
            if not result.success:
                logger.warning(f"Stage '{stage_slug}' revision failed: {result.error}")

        return results

    def get_workflow_stages_display(self) -> list[dict]:
        """Get display information for all workflow stages.

        Useful for UI to show which stages exist in the current workflow.

        Returns:
            List of dicts with slug, display_name, and description
        """
        from haytham.workflow.stage_registry import get_stage_registry

        registry = get_stage_registry()
        stages_info = []

        for slug in self.workflow_stages:
            stage = registry.get_by_slug_safe(slug)
            if stage:
                stages_info.append(
                    {
                        "slug": slug,
                        "display_name": stage.display_name,
                        "description": stage.description,
                    }
                )

        return stages_info
