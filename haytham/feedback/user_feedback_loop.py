"""User feedback loop for stage-based workflow execution.

This module provides data structures and utilities for user feedback collection
after each stage, allowing users to approve, request changes, or skip stages.

Note: UI interaction has been moved to the Streamlit interface.
This module provides the core data structures and business logic.
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from haytham.phases.stage_config import get_stage_by_slug, get_stage_index
from haytham.session.session_manager import SessionManager

logger = logging.getLogger(__name__)


class FeedbackAction(Enum):
    """User feedback actions."""

    APPROVE = "approved"
    REQUEST_CHANGES = "retry_with_changes"
    SKIP = "skip_stage"


@dataclass
class ChangeRequest:
    """Represents a user's change request for a stage."""

    change_type: str  # "modify_prompt", "provide_guidance", "retry_with_same"
    modified_prompt: str | None = None
    additional_guidance: str | None = None
    timestamp: str | None = None

    def __post_init__(self):
        """Set timestamp if not provided."""
        if self.timestamp is None:
            self.timestamp = datetime.utcnow().isoformat() + "Z"


class UserFeedbackLoop:
    """Manages user feedback collection and processing for stage-based workflows.

    This class provides methods to:
    - Record user feedback and change requests
    - Save feedback to user_feedback.md files
    - Format stage results for display

    Note: UI interaction has been moved to the Streamlit interface.
    Use this class for programmatic feedback recording.

    Attributes:
        session_manager: SessionManager for saving feedback to session/ directory
    """

    def __init__(
        self,
        session_manager: SessionManager,
    ):
        """Initialize the UserFeedbackLoop.

        Args:
            session_manager: SessionManager instance for persistence
        """
        self.session_manager = session_manager
        self._logger = logging.getLogger(f"{__name__}.session")

    def record_approval(self, stage_slug: str, comments: str = "") -> FeedbackAction:
        """Record user approval for a stage.

        Args:
            stage_slug: Stage slug (e.g., "idea-refinement")
            comments: Optional comments

        Returns:
            FeedbackAction.APPROVE
        """
        self._logger.info(f"Recording approval for stage {stage_slug}")

        self.session_manager.save_user_feedback(
            stage_slug=stage_slug,
            feedback={
                "reviewed": True,
                "approved": True,
                "comments": comments or "User approved stage results",
                "action": "approved",
                "retry_count": 0,
            },
        )

        return FeedbackAction.APPROVE

    def record_skip(self, stage_slug: str, comments: str = "") -> FeedbackAction:
        """Record user skip for a stage.

        Args:
            stage_slug: Stage slug (e.g., "idea-refinement")
            comments: Optional comments

        Returns:
            FeedbackAction.SKIP
        """
        self._logger.info(f"Recording skip for stage {stage_slug}")

        self.session_manager.save_user_feedback(
            stage_slug=stage_slug,
            feedback={
                "reviewed": True,
                "approved": False,
                "comments": comments or "User skipped stage",
                "action": "skip_stage",
                "retry_count": 0,
            },
        )

        return FeedbackAction.SKIP

    def record_change_request(
        self,
        stage_slug: str,
        change_request: ChangeRequest,
        retry_count: int = 0,
    ) -> FeedbackAction:
        """Record a change request for a stage.

        Args:
            stage_slug: Stage slug (e.g., "idea-refinement")
            change_request: The change request details
            retry_count: Current retry count

        Returns:
            FeedbackAction.REQUEST_CHANGES
        """
        self._logger.info(
            f"Recording change request for stage {stage_slug}: {change_request.change_type}"
        )

        change_description = f"Change type: {change_request.change_type}"
        if change_request.modified_prompt:
            change_description += f", Modified prompt: {change_request.modified_prompt[:100]}..."
        if change_request.additional_guidance:
            change_description += (
                f", Additional guidance: {change_request.additional_guidance[:100]}..."
            )

        self.session_manager.save_user_feedback(
            stage_slug=stage_slug,
            feedback={
                "reviewed": True,
                "approved": False,
                "comments": f"User requested changes: {change_request.change_type}",
                "requested_changes": [change_description],
                "action": "retry_with_changes",
                "retry_count": retry_count + 1,
            },
        )

        return FeedbackAction.REQUEST_CHANGES

    def format_stage_results(
        self,
        stage_slug: str,
        agent_outputs: dict[str, str],
        duration: float,
        tokens_used: int,
        cost: float,
    ) -> str:
        """Format stage results for display.

        Args:
            stage_slug: Stage slug (e.g., "idea-refinement")
            agent_outputs: Agent outputs
            duration: Execution duration
            tokens_used: Tokens consumed
            cost: Estimated cost

        Returns:
            Formatted markdown string
        """
        stage_config = get_stage_by_slug(stage_slug)
        stage_index = get_stage_index(stage_slug)

        # Format duration
        duration_str = f"{int(duration)}s"
        if duration >= 60:
            minutes = int(duration // 60)
            seconds = int(duration % 60)
            duration_str = f"{minutes}m {seconds}s"

        # Format cost
        cost_str = f"${cost:.4f}"

        # Build message
        message = f"""## Stage {stage_index + 1} Complete: {stage_config.display_name}

**Execution Summary:**
- Duration: {duration_str}
- Tokens: {tokens_used:,}
- Cost: {cost_str}

**Agent Outputs:**
"""

        # Add agent outputs (truncated for display)
        for agent_name, output in agent_outputs.items():
            # Truncate long outputs
            display_output = output[:500]
            if len(output) > 500:
                display_output += "\n\n... (truncated, see full output in checkpoint files)"

            message += f"\n### {agent_name}\n\n{display_output}\n"

        return message
