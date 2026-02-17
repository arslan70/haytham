"""Shared workflow builder (ADR-024).

Constructs Burr Applications from WorkflowSpec definitions.
Centralizes the boilerplate that was previously duplicated across
5 factory functions in workflow_factories.py.
"""

import json
import logging
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from burr.core import ApplicationBuilder
from burr.lifecycle import PostRunStepHook, PreRunStepHook
from burr.tracking import LocalTrackingClient

from haytham.workflow.entry_validators import validate_workflow_entry
from haytham.workflow.workflow_specs import WorkflowSpec

if TYPE_CHECKING:
    from haytham.session.session_manager import SessionManager

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers (moved from workflow_factories.py)
# ---------------------------------------------------------------------------


def _load_anchor_from_disk(
    session_manager: "SessionManager | None",
) -> tuple[Any, str]:
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
    except (json.JSONDecodeError, OSError) as e:
        logger.warning(f"Failed to load anchor from disk: {e}")
        return None, ""


# ---------------------------------------------------------------------------
# Lifecycle Hooks (moved from workflow_factories.py)
# ---------------------------------------------------------------------------


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
            except (TypeError, AttributeError, ValueError) as e:
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
            except (TypeError, AttributeError, ValueError) as e:
                logger.error(f"on_stage_complete callback failed: {e}")

    def _get_stage_index(self, stage_name: str) -> int:
        """Get 0-based index of stage."""
        if self.stage_order:
            try:
                return self.stage_order.index(stage_name)
            except ValueError:
                pass
        return 0


# ---------------------------------------------------------------------------
# Builder
# ---------------------------------------------------------------------------


def build_workflow(
    spec: WorkflowSpec,
    session_manager: "SessionManager",
    system_goal: str | None = None,
    app_id: str | None = None,
    on_stage_start: Callable | None = None,
    on_stage_complete: Callable | None = None,
    enable_tracking: bool = True,
    tracking_project: str | None = None,
    force_override: bool = False,
    **extra_state: Any,
) -> Any:
    """Build a Burr Application from a WorkflowSpec.

    Args:
        spec: Workflow specification.
        session_manager: SessionManager for persistence.
        system_goal: System goal (required for Idea Validation, auto-loaded
            for others).
        app_id: Optional custom app ID.
        on_stage_start: Callback when stage starts.
        on_stage_complete: Callback when stage completes.
        enable_tracking: Enable Burr tracking UI.
        tracking_project: Override spec's tracking_project.
        force_override: Force past overridable failed entry conditions.
        **extra_state: Extra state values (e.g., archetype="").

    Returns:
        Burr Application instance.

    Raises:
        ValueError: If entry conditions are not met.
    """
    project = tracking_project or spec.tracking_project

    logger.info("=" * 60)
    logger.info(f"CREATING WORKFLOW: {spec.workflow_type.value}")
    logger.info("=" * 60)

    # 1. Validate entry conditions
    validation = validate_workflow_entry(
        spec.workflow_type, session_manager, force_override=force_override
    )
    if not validation.passed:
        error_msg = validation.message
        if validation.can_override:
            error_msg = f"OVERRIDABLE: {validation.message}"
        logger.error(f"Entry conditions not met: {error_msg}")
        raise ValueError(error_msg)

    logger.info(f"Entry conditions passed: {validation.message}")
    if validation.recommendation:
        logger.info(f"Recommendation: {validation.recommendation}")

    # 2. Get system_goal
    if system_goal is None:
        system_goal = session_manager.get_system_goal() or ""

    # 3. Generate app_id
    if app_id is None:
        app_id = f"{project}-{uuid.uuid4().hex[:8]}"

    logger.info(f"App ID: {app_id}")
    if system_goal:
        logger.info(f"System goal provided (length={len(system_goal)})")

    # 4. Create tracker
    tracker = None
    if enable_tracking:
        try:
            tracker = LocalTrackingClient(project=project)
            logger.info(f"Burr tracking enabled: {project}")
        except (OSError, ImportError, RuntimeError) as e:
            logger.warning(f"Could not enable tracking: {e}")

    # 5. Create progress hook
    progress_hook = WorkflowProgressHook(
        on_stage_start=on_stage_start,
        on_stage_complete=on_stage_complete,
        stage_order=spec.stages,
    )

    # 6. Load anchor from disk (ADR-022)
    loaded_anchor, loaded_anchor_str = _load_anchor_from_disk(session_manager)

    # 7. Load context from previous workflows
    context: dict[str, Any] = {}
    for stage_slug in spec.context_stages:
        key = stage_slug.replace("-", "_")
        context[key] = session_manager.load_stage_output(stage_slug) or ""

    # 8. Build state
    # NOTE: session_manager is a non-serializable Python object stored in Burr
    # state. This prevents Burr's built-in state serialization (checkpoints,
    # persistence). Refactoring it out requires changing 12+ Burr actions that
    # declare reads=["session_manager"]. Tracked for a future PR; the current
    # approach works because we only use in-process state, not Burr persistence.
    state: dict[str, Any] = {
        "system_goal": system_goal,
        "session_manager": session_manager,
        "workflow_type": spec.workflow_type.value,
        "concept_anchor": loaded_anchor,
        "concept_anchor_str": loaded_anchor_str,
        "current_stage": "",
        "user_approved": True,
        "user_feedback": "",
    }
    state.update(context)
    state.update(spec.build_default_state())
    state.update(extra_state)

    # 9. Build app
    builder = (
        ApplicationBuilder()
        .with_actions(**spec.actions)
        .with_transitions(*spec.transitions)
        .with_state(**state)
        .with_entrypoint(spec.entrypoint)
        .with_hooks(progress_hook)
        .with_identifiers(app_id=app_id)
    )

    if tracker:
        builder = builder.with_tracker(tracker)

    app = builder.build()

    logger.info(f"Workflow {spec.workflow_type.value} created successfully")
    return app
