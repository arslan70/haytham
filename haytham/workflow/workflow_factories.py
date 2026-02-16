"""Workflow Factories for Separated Workflow Execution.

This module provides factory functions to create separate Burr workflows
for each workflow type as defined in ADR-016 (Four-Phase Architecture):

1. Idea Validation Workflow (Phase 1: WHY): idea_analysis -> market_context -> risk_assessment -> validation_summary
2. MVP Specification Workflow (Phase 2: WHAT): mvp_scope -> capability_model
3. Technical Design Workflow (Phase 3: HOW): build_buy_analysis -> architecture_decisions
4. Story Generation Workflow (Phase 4: STORIES): story_generation -> story_validation -> dependency_ordering

Each workflow is independent and validates entry conditions before starting.
Decision gates between workflows allow users to review outputs before proceeding.
"""

import json
import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from burr.core import ApplicationBuilder, default, when
from burr.lifecycle import PostRunStepHook, PreRunStepHook
from burr.tracking import LocalTrackingClient

from haytham.workflow.entry_conditions import validate_workflow_entry
from haytham.workflow.stage_registry import WorkflowType

from .burr_actions import (
    architecture_decisions,
    build_buy_analysis,
    capability_model,
    dependency_ordering,
    idea_analysis,
    market_context,
    mvp_scope,
    pivot_strategy,
    risk_assessment,
    story_generation,
    story_validation,
    system_traits,
    validation_summary,
)

if TYPE_CHECKING:
    from haytham.session.session_manager import SessionManager

logger = logging.getLogger(__name__)


def _load_anchor_from_disk(session_manager: "SessionManager | None") -> tuple[Any, str]:
    """Load concept anchor from disk if it exists.

    ADR-022: When resuming a workflow, the anchor must be loaded from disk
    since Burr doesn't persist state between sessions. The anchor file is
    created by the post_processor after idea-analysis completes.

    Args:
        session_manager: SessionManager with session_dir, or None

    Returns:
        Tuple of (anchor_dict or None, anchor_str or "")
    """
    if not session_manager or not hasattr(session_manager, "session_dir"):
        return None, ""

    anchor_file = session_manager.session_dir / "concept_anchor.json"
    if not anchor_file.exists():
        return None, ""

    try:
        data = json.loads(anchor_file.read_text())
        anchor = data.get("anchor")
        anchor_str = data.get("anchor_str", "")
        logger.info(f"Loaded concept anchor from disk ({len(anchor_str)} chars)")
        return anchor, anchor_str
    except Exception as e:
        logger.warning(f"Failed to load anchor from disk: {e}")
        return None, ""


# =============================================================================
# Lifecycle Hooks
# =============================================================================


@dataclass
class WorkflowProgressHook(PostRunStepHook, PreRunStepHook):
    """Hook to track stage progress within a workflow."""

    on_stage_start: Callable[[str, int, int], None] | None = None
    on_stage_complete: Callable[[str, int, int, dict], None] | None = None
    stage_order: list[str] | None = None

    def pre_run_step(self, *, action, **kwargs):
        """Called before each action runs."""
        stage_name = action.name
        stage_index = self._get_stage_index(stage_name)
        total_stages = len(self.stage_order) if self.stage_order else 1

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
        total_stages = len(self.stage_order) if self.stage_order else 1

        status_key = f"{stage_name}_status"
        status = state.get(status_key, "unknown")

        logger.info(f"Completed: {stage_name} (status={status})")

        if self.on_stage_complete:
            try:
                stage_result = {
                    "status": status,
                    "output": state.get(stage_name, ""),
                }
                self.on_stage_complete(stage_name, stage_index, total_stages, stage_result)
            except Exception as e:
                logger.error(f"on_stage_complete callback failed: {e}")

    def _get_stage_index(self, stage_name: str) -> int:
        """Get 0-based index of stage."""
        if self.stage_order:
            try:
                return self.stage_order.index(stage_name)
            except ValueError:
                pass
        return 0


# =============================================================================
# Workflow 1: Idea Validation
# =============================================================================

IDEA_VALIDATION_STAGES = [
    "idea_analysis",
    "market_context",
    "risk_assessment",
    "pivot_strategy",  # Optional, only if HIGH risk
    "validation_summary",
]


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

    This workflow validates a startup idea through 4 stages:
    1. idea_analysis - Transform raw idea into structured concept
    2. market_context - Research market and competitors (parallel agents)
    3. risk_assessment - Validate claims and assess risks
    4. validation_summary - Synthesize findings into GO/NO-GO recommendation

    Optional pivot_strategy stage is triggered if risk_level is HIGH.

    Args:
        system_goal: The startup idea to validate
        session_manager: SessionManager for persistence
        app_id: Optional custom app ID (default: auto-generated)
        on_stage_start: Callback(stage_name, index, total) when stage starts
        on_stage_complete: Callback(stage_name, index, total, result) when stage completes
        enable_tracking: Enable Burr tracking UI
        tracking_project: Project name for tracking

    Returns:
        Burr Application instance

    Raises:
        ValueError: If entry conditions are not met
    """
    logger.info("=" * 60)
    logger.info("CREATING WORKFLOW 1: IDEA VALIDATION")
    logger.info("=" * 60)

    # Validate entry conditions (always passes for Workflow 1)
    validation = validate_workflow_entry(WorkflowType.IDEA_VALIDATION, session_manager)
    if not validation.passed:
        raise ValueError(validation.message)

    # Generate app_id if not provided
    if app_id is None:
        import uuid

        app_id = f"haytham-validation-{uuid.uuid4().hex[:8]}"

    logger.info(f"System Goal: {system_goal[:50]}...")
    logger.info(f"App ID: {app_id}")

    # Create tracker
    tracker = None
    if enable_tracking:
        try:
            tracker = LocalTrackingClient(project=tracking_project)
            logger.info(f"Burr tracking enabled: {tracking_project}")
        except Exception as e:
            logger.warning(f"Could not enable tracking: {e}")

    # Create progress hook
    progress_hook = WorkflowProgressHook(
        on_stage_start=on_stage_start,
        on_stage_complete=on_stage_complete,
        stage_order=IDEA_VALIDATION_STAGES,
    )

    # ADR-022: Load anchor from disk if it exists (for workflow resume)
    loaded_anchor, loaded_anchor_str = _load_anchor_from_disk(session_manager)

    # Build workflow
    builder = (
        ApplicationBuilder()
        .with_actions(
            idea_analysis=idea_analysis,
            market_context=market_context,
            risk_assessment=risk_assessment,
            pivot_strategy=pivot_strategy,
            validation_summary=validation_summary,
        )
        .with_transitions(
            # idea_analysis -> market_context
            ("idea_analysis", "market_context"),
            # market_context -> risk_assessment
            ("market_context", "risk_assessment"),
            # risk_assessment branches on risk_level
            ("risk_assessment", "pivot_strategy", when(risk_level="HIGH")),
            ("risk_assessment", "validation_summary", default),
            # pivot_strategy -> validation_summary
            ("pivot_strategy", "validation_summary"),
            # validation_summary is terminal for this workflow
        )
        .with_state(
            # Input
            system_goal=system_goal,
            session_manager=session_manager,
            workflow_type=WorkflowType.IDEA_VALIDATION.value,
            # User-selected archetype (empty string = auto-detect)
            archetype=archetype or "",
            # Stage outputs
            idea_analysis="",
            idea_analysis_status="pending",
            # ADR-022: Concept anchor extracted after idea-analysis to prevent concept drift
            # Loaded from disk if resuming, otherwise populated by post_processor
            concept_anchor=loaded_anchor,
            concept_anchor_str=loaded_anchor_str,
            market_context="",
            market_context_status="pending",
            risk_assessment="",
            risk_level="",
            risk_assessment_status="pending",
            pivot_strategy="",
            pivot_strategy_status="pending",
            validation_summary="",
            validation_summary_status="pending",
            # Tracking
            current_stage="",
            user_approved=True,
            user_feedback="",
        )
        .with_entrypoint("idea_analysis")
        .with_hooks(progress_hook)
        .with_identifiers(app_id=app_id)
    )

    if tracker:
        builder = builder.with_tracker(tracker)

    app = builder.build()

    logger.info("Workflow 1 created successfully")
    return app


# =============================================================================
# Workflow 2: MVP Specification
# =============================================================================

MVP_SPECIFICATION_STAGES = [
    "mvp_scope",
    "capability_model",
    "system_traits",
]


def create_mvp_specification_workflow(
    session_manager: "SessionManager",
    app_id: str | None = None,
    on_stage_start: Callable | None = None,
    on_stage_complete: Callable | None = None,
    enable_tracking: bool = True,
    tracking_project: str = "haytham-mvp-spec",
    force_override: bool = False,
) -> Any:
    """Create the MVP Specification workflow (Workflow 2).

    This workflow defines what to build first through 2 stages:
    1. mvp_scope - Define focused, achievable MVP scope
    2. capability_model - Transform scope into capability model

    Entry conditions:
    - Idea Validation workflow must be complete
    - Recommendation must be GO or PIVOT (not NO-GO)
    - Validation Summary document must exist

    Args:
        session_manager: SessionManager for persistence
        app_id: Optional custom app ID
        on_stage_start: Callback when stage starts
        on_stage_complete: Callback when stage completes
        enable_tracking: Enable Burr tracking UI
        tracking_project: Project name for tracking
        force_override: If True, proceed despite NO-GO recommendation

    Returns:
        Burr Application instance

    Raises:
        ValueError: If entry conditions are not met (and not overridable or not overridden)
    """
    logger.info("=" * 60)
    logger.info("CREATING WORKFLOW 2: MVP SPECIFICATION")
    logger.info("=" * 60)

    # Validate entry conditions
    validation = validate_workflow_entry(
        WorkflowType.MVP_SPECIFICATION, session_manager, force_override=force_override
    )
    if not validation.passed:
        logger.error(f"Entry conditions not met: {validation.message}")
        # Include override info in error for UI to handle
        error_msg = validation.message
        if validation.can_override:
            error_msg = f"OVERRIDABLE: {validation.message}"
        raise ValueError(error_msg)

    logger.info(f"Entry conditions passed: {validation.message}")
    logger.info(f"Recommendation: {validation.recommendation}")

    # Get system_goal from session
    system_goal = session_manager.get_system_goal() or ""

    # Generate app_id if not provided
    if app_id is None:
        import uuid

        app_id = f"haytham-mvp-spec-{uuid.uuid4().hex[:8]}"

    logger.info(f"App ID: {app_id}")

    # Create tracker
    tracker = None
    if enable_tracking:
        try:
            tracker = LocalTrackingClient(project=tracking_project)
            logger.info(f"Burr tracking enabled: {tracking_project}")
        except Exception as e:
            logger.warning(f"Could not enable tracking: {e}")

    # Create progress hook
    progress_hook = WorkflowProgressHook(
        on_stage_start=on_stage_start,
        on_stage_complete=on_stage_complete,
        stage_order=MVP_SPECIFICATION_STAGES,
    )

    # Load context from previous workflow
    validation_summary_content = session_manager.load_stage_output("validation-summary") or ""
    idea_analysis_content = session_manager.load_stage_output("idea-analysis") or ""
    market_context_content = session_manager.load_stage_output("market-context") or ""
    risk_assessment_content = session_manager.load_stage_output("risk-assessment") or ""

    # ADR-022: Load anchor from disk - CRITICAL for WHAT phase to honor anchor constraints
    loaded_anchor, loaded_anchor_str = _load_anchor_from_disk(session_manager)
    if loaded_anchor_str:
        logger.info(f"Loaded concept anchor for MVP specification ({len(loaded_anchor_str)} chars)")
    else:
        logger.warning("No concept anchor found - MVP scope may drift from original intent")

    # Build workflow
    builder = (
        ApplicationBuilder()
        .with_actions(
            mvp_scope=mvp_scope,
            capability_model=capability_model,
            system_traits=system_traits,
        )
        .with_transitions(
            # mvp_scope -> capability_model
            ("mvp_scope", "capability_model"),
            # capability_model -> system_traits
            ("capability_model", "system_traits"),
            # system_traits is terminal for this workflow
        )
        .with_state(
            # Input
            system_goal=system_goal,
            session_manager=session_manager,
            workflow_type=WorkflowType.MVP_SPECIFICATION.value,
            # ADR-022: Concept anchor from Workflow 1 - prevents scope drift
            concept_anchor=loaded_anchor,
            concept_anchor_str=loaded_anchor_str,
            # Context from Workflow 1
            idea_analysis=idea_analysis_content,
            market_context=market_context_content,
            risk_assessment=risk_assessment_content,
            validation_summary=validation_summary_content,
            # Stage outputs
            mvp_scope="",
            mvp_scope_status="pending",
            capability_model="",
            capability_model_status="pending",
            system_traits="",
            system_traits_status="pending",
            system_traits_parsed=None,
            system_traits_warnings=None,
            # Tracking
            current_stage="",
            user_approved=True,
            user_feedback="",
        )
        .with_entrypoint("mvp_scope")
        .with_hooks(progress_hook)
        .with_identifiers(app_id=app_id)
    )

    if tracker:
        builder = builder.with_tracker(tracker)

    app = builder.build()

    logger.info("Workflow 2 created successfully")
    return app


# =============================================================================
# Workflow 3a: Build vs Buy Analysis (Phase 3a: HOW)
# =============================================================================

BUILD_BUY_ANALYSIS_STAGES: list[str] = [
    "build_buy_analysis",  # Analyze capabilities for build vs buy
]


def create_build_buy_analysis_workflow(
    session_manager: "SessionManager",
    app_id: str | None = None,
    on_stage_start: Callable | None = None,
    on_stage_complete: Callable | None = None,
    enable_tracking: bool = True,
    tracking_project: str = "haytham-build-buy",
) -> Any:
    """Create the Build vs Buy Analysis workflow (Workflow 3a / Phase 3a: HOW).

    This workflow analyzes capabilities for BUILD/BUY/HYBRID recommendations.

    Entry conditions:
    - MVP Specification workflow must be complete
    - Capability Model document must exist
    - At least 1 functional capability exists

    Args:
        session_manager: SessionManager for persistence
        app_id: Optional custom app ID
        on_stage_start: Callback when stage starts
        on_stage_complete: Callback when stage completes
        enable_tracking: Enable Burr tracking UI
        tracking_project: Project name for tracking

    Returns:
        Burr Application instance

    Raises:
        ValueError: If entry conditions are not met
    """
    logger.info("=" * 60)
    logger.info("CREATING WORKFLOW 3a: BUILD VS BUY ANALYSIS (Phase 3a: HOW)")
    logger.info("=" * 60)

    # Validate entry conditions
    validation = validate_workflow_entry(WorkflowType.BUILD_BUY_ANALYSIS, session_manager)
    if not validation.passed:
        logger.error(f"Entry conditions not met: {validation.message}")
        raise ValueError(validation.message)

    logger.info(f"Entry conditions passed: {validation.message}")

    # Get system_goal from session
    system_goal = session_manager.get_system_goal() or ""

    # Generate app_id if not provided
    if app_id is None:
        import uuid

        app_id = f"haytham-build-buy-{uuid.uuid4().hex[:8]}"

    logger.info(f"App ID: {app_id}")

    # Create tracker
    tracker = None
    if enable_tracking:
        try:
            tracker = LocalTrackingClient(project=tracking_project)
            logger.info(f"Burr tracking enabled: {tracking_project}")
        except Exception as e:
            logger.warning(f"Could not enable tracking: {e}")

    # Create progress hook
    progress_hook = WorkflowProgressHook(
        on_stage_start=on_stage_start,
        on_stage_complete=on_stage_complete,
        stage_order=BUILD_BUY_ANALYSIS_STAGES,
    )

    # Load context from Workflow 2
    capability_model_content = session_manager.load_stage_output("capability-model") or ""
    mvp_scope_content = session_manager.load_stage_output("mvp-scope") or ""

    # Also load earlier context for reference
    validation_summary_content = session_manager.load_stage_output("validation-summary") or ""
    idea_analysis_content = session_manager.load_stage_output("idea-analysis") or ""

    # ADR-022: Load anchor for build/buy consistency
    loaded_anchor, loaded_anchor_str = _load_anchor_from_disk(session_manager)

    # Build workflow - single stage, no transitions needed
    builder = (
        ApplicationBuilder()
        .with_actions(
            build_buy_analysis=build_buy_analysis,
        )
        .with_transitions()  # No transitions - single stage workflow
        .with_state(
            # Input
            system_goal=system_goal,
            session_manager=session_manager,
            workflow_type=WorkflowType.BUILD_BUY_ANALYSIS.value,
            # ADR-022: Concept anchor for consistency
            concept_anchor=loaded_anchor,
            concept_anchor_str=loaded_anchor_str,
            # Context from Workflow 1 & 2
            idea_analysis=idea_analysis_content,
            validation_summary=validation_summary_content,
            mvp_scope=mvp_scope_content,
            capability_model=capability_model_content,
            # Stage outputs
            build_buy_analysis="",
            build_buy_analysis_status="pending",
            # Tracking
            current_stage="",
            user_approved=True,
            user_feedback="",
        )
        .with_entrypoint("build_buy_analysis")
        .with_hooks(progress_hook)
        .with_identifiers(app_id=app_id)
    )

    if tracker:
        builder = builder.with_tracker(tracker)

    app = builder.build()

    logger.info("Workflow 3a (Build vs Buy Analysis) created successfully")
    return app


# =============================================================================
# Workflow 3b: Architecture Decisions (Phase 3b: HOW)
# =============================================================================

ARCHITECTURE_DECISIONS_STAGES: list[str] = [
    "architecture_decisions",  # Key technical decisions
]


def create_architecture_decisions_workflow(
    session_manager: "SessionManager",
    app_id: str | None = None,
    on_stage_start: Callable | None = None,
    on_stage_complete: Callable | None = None,
    enable_tracking: bool = True,
    tracking_project: str = "haytham-architecture",
) -> Any:
    """Create the Architecture Decisions workflow (Workflow 3b / Phase 3b: HOW).

    This workflow makes key technical architecture decisions based on build/buy analysis.

    Entry conditions:
    - Build vs Buy Analysis workflow must be complete
    - Build vs Buy Analysis document must exist

    Args:
        session_manager: SessionManager for persistence
        app_id: Optional custom app ID
        on_stage_start: Callback when stage starts
        on_stage_complete: Callback when stage completes
        enable_tracking: Enable Burr tracking UI
        tracking_project: Project name for tracking

    Returns:
        Burr Application instance

    Raises:
        ValueError: If entry conditions are not met
    """
    logger.info("=" * 60)
    logger.info("CREATING WORKFLOW 3b: ARCHITECTURE DECISIONS (Phase 3b: HOW)")
    logger.info("=" * 60)

    # Validate entry conditions
    validation = validate_workflow_entry(WorkflowType.ARCHITECTURE_DECISIONS, session_manager)
    if not validation.passed:
        logger.error(f"Entry conditions not met: {validation.message}")
        raise ValueError(validation.message)

    logger.info(f"Entry conditions passed: {validation.message}")

    # Get system_goal from session
    system_goal = session_manager.get_system_goal() or ""

    # Generate app_id if not provided
    if app_id is None:
        import uuid

        app_id = f"haytham-architecture-{uuid.uuid4().hex[:8]}"

    logger.info(f"App ID: {app_id}")

    # Create tracker
    tracker = None
    if enable_tracking:
        try:
            tracker = LocalTrackingClient(project=tracking_project)
            logger.info(f"Burr tracking enabled: {tracking_project}")
        except Exception as e:
            logger.warning(f"Could not enable tracking: {e}")

    # Create progress hook
    progress_hook = WorkflowProgressHook(
        on_stage_start=on_stage_start,
        on_stage_complete=on_stage_complete,
        stage_order=ARCHITECTURE_DECISIONS_STAGES,
    )

    # Load context from Workflow 2 & 3a
    capability_model_content = session_manager.load_stage_output("capability-model") or ""
    mvp_scope_content = session_manager.load_stage_output("mvp-scope") or ""
    build_buy_analysis_content = session_manager.load_stage_output("build-buy-analysis") or ""

    # Also load earlier context for reference
    validation_summary_content = session_manager.load_stage_output("validation-summary") or ""
    idea_analysis_content = session_manager.load_stage_output("idea-analysis") or ""

    # ADR-022: Load anchor for architecture consistency
    loaded_anchor, loaded_anchor_str = _load_anchor_from_disk(session_manager)

    # Build workflow - single stage, no transitions needed
    builder = (
        ApplicationBuilder()
        .with_actions(
            architecture_decisions=architecture_decisions,
        )
        .with_transitions()  # No transitions - single stage workflow
        .with_state(
            # Input
            system_goal=system_goal,
            session_manager=session_manager,
            workflow_type=WorkflowType.ARCHITECTURE_DECISIONS.value,
            # ADR-022: Concept anchor for consistency
            concept_anchor=loaded_anchor,
            concept_anchor_str=loaded_anchor_str,
            # Context from Workflow 1, 2 & 3a
            idea_analysis=idea_analysis_content,
            validation_summary=validation_summary_content,
            mvp_scope=mvp_scope_content,
            capability_model=capability_model_content,
            build_buy_analysis=build_buy_analysis_content,
            # Stage outputs
            architecture_decisions="",
            architecture_decisions_status="pending",
            # Tracking
            current_stage="",
            user_approved=True,
            user_feedback="",
        )
        .with_entrypoint("architecture_decisions")
        .with_hooks(progress_hook)
        .with_identifiers(app_id=app_id)
    )

    if tracker:
        builder = builder.with_tracker(tracker)

    app = builder.build()

    logger.info("Workflow 3b (Architecture Decisions) created successfully")
    return app


# =============================================================================
# Workflow 4: Story Generation (Phase 4: STORIES)
# =============================================================================

STORY_GENERATION_STAGES: list[str] = [
    "story_generation",  # Stage 9 - Generate stories from capabilities
    "story_validation",  # Stage 10 - Validate stories against capabilities
    "dependency_ordering",  # Stage 11 - Order stories by dependencies
]


def create_story_generation_workflow(
    session_manager: "SessionManager",
    app_id: str | None = None,
    on_stage_start: Callable | None = None,
    on_stage_complete: Callable | None = None,
    enable_tracking: bool = True,
    tracking_project: str = "haytham-stories",
) -> Any:
    """Create the Story Generation workflow (Workflow 4 / Phase 4: STORIES).

    This workflow generates implementation tasks:
    1. story_generation - User stories based on Build vs Buy decisions
    2. story_validation - Validate stories against capabilities
    3. dependency_ordering - Order stories by dependencies

    Entry conditions:
    - Technical Design workflow must be complete
    - Build vs Buy Analysis document must exist
    - Architecture Decisions document must exist

    Args:
        session_manager: SessionManager for persistence
        app_id: Optional custom app ID
        on_stage_start: Callback when stage starts
        on_stage_complete: Callback when stage completes
        enable_tracking: Enable Burr tracking UI
        tracking_project: Project name for tracking

    Returns:
        Burr Application instance

    Raises:
        ValueError: If entry conditions are not met
    """
    logger.info("=" * 60)
    logger.info("CREATING WORKFLOW 4: STORY GENERATION (Phase 4: STORIES)")
    logger.info("=" * 60)

    # Validate entry conditions
    validation = validate_workflow_entry(WorkflowType.STORY_GENERATION, session_manager)
    if not validation.passed:
        logger.error(f"Entry conditions not met: {validation.message}")
        raise ValueError(validation.message)

    logger.info(f"Entry conditions passed: {validation.message}")

    # Get system_goal from session
    system_goal = session_manager.get_system_goal() or ""

    # Generate app_id if not provided
    if app_id is None:
        import uuid

        app_id = f"haytham-stories-{uuid.uuid4().hex[:8]}"

    logger.info(f"App ID: {app_id}")

    # Create tracker
    tracker = None
    if enable_tracking:
        try:
            tracker = LocalTrackingClient(project=tracking_project)
            logger.info(f"Burr tracking enabled: {tracking_project}")
        except Exception as e:
            logger.warning(f"Could not enable tracking: {e}")

    # Create progress hook
    progress_hook = WorkflowProgressHook(
        on_stage_start=on_stage_start,
        on_stage_complete=on_stage_complete,
        stage_order=STORY_GENERATION_STAGES,
    )

    # Load context from Workflow 2 & 3
    capability_model_content = session_manager.load_stage_output("capability-model") or ""
    mvp_scope_content = session_manager.load_stage_output("mvp-scope") or ""
    build_buy_analysis_content = session_manager.load_stage_output("build-buy-analysis") or ""
    architecture_decisions_content = (
        session_manager.load_stage_output("architecture-decisions") or ""
    )

    # Also load earlier context for reference
    validation_summary_content = session_manager.load_stage_output("validation-summary") or ""
    idea_analysis_content = session_manager.load_stage_output("idea-analysis") or ""

    # ADR-022: Load anchor for story generation consistency
    loaded_anchor, loaded_anchor_str = _load_anchor_from_disk(session_manager)

    # Build workflow
    builder = (
        ApplicationBuilder()
        .with_actions(
            story_generation=story_generation,
            story_validation=story_validation,
            dependency_ordering=dependency_ordering,
        )
        .with_transitions(
            ("story_generation", "story_validation"),
            ("story_validation", "dependency_ordering"),
            # dependency_ordering is terminal for this workflow
        )
        .with_state(
            # Input
            system_goal=system_goal,
            session_manager=session_manager,
            workflow_type=WorkflowType.STORY_GENERATION.value,
            # ADR-022: Concept anchor for consistency
            concept_anchor=loaded_anchor,
            concept_anchor_str=loaded_anchor_str,
            # Context from Workflow 1, 2 & 3
            idea_analysis=idea_analysis_content,
            validation_summary=validation_summary_content,
            mvp_scope=mvp_scope_content,
            capability_model=capability_model_content,
            build_buy_analysis=build_buy_analysis_content,
            architecture_decisions=architecture_decisions_content,
            # Stage outputs
            story_generation="",
            story_generation_status="pending",
            story_validation="",
            story_validation_status="pending",
            dependency_ordering="",
            dependency_ordering_status="pending",
            # Tracking
            current_stage="",
            user_approved=True,
            user_feedback="",
        )
        .with_entrypoint("story_generation")
        .with_hooks(progress_hook)
        .with_identifiers(app_id=app_id)
    )

    if tracker:
        builder = builder.with_tracker(tracker)

    app = builder.build()

    logger.info("Workflow 4 (Story Generation) created successfully")
    return app


# =============================================================================
# Unified Factory Function
# =============================================================================


def create_workflow_for_type(
    workflow_type: WorkflowType,
    session_manager: "SessionManager",
    system_goal: str | None = None,
    **kwargs,
) -> Any:
    """Create a workflow of the specified type.

    This is the unified entry point for creating any workflow type.

    Args:
        workflow_type: The type of workflow to create
        session_manager: SessionManager for persistence
        system_goal: System goal (required for Workflow 1)
        **kwargs: Additional arguments passed to the specific factory

    Returns:
        Burr Application instance

    Raises:
        ValueError: If workflow_type is invalid or entry conditions not met
    """
    if workflow_type == WorkflowType.IDEA_VALIDATION:
        if not system_goal:
            system_goal = session_manager.get_system_goal()
        if not system_goal:
            raise ValueError("System goal is required for Idea Validation workflow")
        return create_idea_validation_workflow(
            system_goal=system_goal,
            session_manager=session_manager,
            **kwargs,
        )

    elif workflow_type == WorkflowType.MVP_SPECIFICATION:
        return create_mvp_specification_workflow(
            session_manager=session_manager,
            **kwargs,
        )

    elif workflow_type == WorkflowType.BUILD_BUY_ANALYSIS:
        return create_build_buy_analysis_workflow(
            session_manager=session_manager,
            **kwargs,
        )

    elif workflow_type == WorkflowType.ARCHITECTURE_DECISIONS:
        return create_architecture_decisions_workflow(
            session_manager=session_manager,
            **kwargs,
        )

    elif workflow_type == WorkflowType.STORY_GENERATION:
        return create_story_generation_workflow(
            session_manager=session_manager,
            **kwargs,
        )

    else:
        raise ValueError(f"Unknown workflow type: {workflow_type}")


# =============================================================================
# Terminal Stages for Each Workflow
# =============================================================================

WORKFLOW_TERMINAL_STAGES = {
    WorkflowType.IDEA_VALIDATION: "validation_summary",
    WorkflowType.MVP_SPECIFICATION: "system_traits",
    WorkflowType.BUILD_BUY_ANALYSIS: "build_buy_analysis",
    WorkflowType.ARCHITECTURE_DECISIONS: "architecture_decisions",
    WorkflowType.STORY_GENERATION: "dependency_ordering",
}


def get_terminal_stage(workflow_type: WorkflowType) -> str:
    """Get the terminal (final) stage for a workflow type.

    Args:
        workflow_type: The workflow type

    Returns:
        Name of the terminal stage action
    """
    return WORKFLOW_TERMINAL_STAGES.get(workflow_type, "")
