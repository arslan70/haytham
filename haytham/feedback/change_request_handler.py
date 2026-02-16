"""Change request handler for stage-based workflow execution.

This module provides functionality to process user change requests,
apply modifications to stage execution, and implement retry logic
with exponential backoff.

Updated for single-session architecture - no project_id or session_id parameters.
Updated for stage-based workflow - uses stage_slug instead of phase_num.
"""

import logging
import time
from dataclasses import dataclass

from haytham.feedback.user_feedback_loop import ChangeRequest
from haytham.phases.stage_config import get_stage_by_slug
from haytham.session.session_manager import SessionManager

logger = logging.getLogger(__name__)


@dataclass
class RetryConfig:
    """Configuration for retry behavior with exponential backoff.

    Attributes:
        max_retries: Maximum number of retry attempts (default: 3)
        base_delay: Base delay in seconds for exponential backoff (default: 1.0)
        max_delay: Maximum delay in seconds (default: 60.0)
        exponential_base: Base for exponential calculation (default: 2.0)
    """

    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0

    def calculate_delay(self, retry_count: int) -> float:
        """Calculate delay for given retry count using exponential backoff.

        Formula: min(base_delay * (exponential_base ^ retry_count), max_delay)

        Args:
            retry_count: Current retry attempt number (0-indexed)

        Returns:
            Delay in seconds

        Example:
            With defaults (base_delay=1.0, exponential_base=2.0):
            - retry_count=0: 1.0s
            - retry_count=1: 2.0s
            - retry_count=2: 4.0s
            - retry_count=3: 8.0s
            - retry_count=4: 16.0s
            - retry_count=5: 32.0s
            - retry_count=6: 60.0s (capped at max_delay)
        """
        delay = self.base_delay * (self.exponential_base**retry_count)
        return min(delay, self.max_delay)


class ChangeRequestHandler:
    """Handles processing of user change requests for stage execution.

    This class provides methods to:
    - Process change requests and apply modifications
    - Implement retry logic with exponential backoff
    - Save change request details to user_feedback.md
    - Track retry counts and prevent infinite loops

    Updated for single-session architecture - uses SessionManager with fixed session/ path.
    Updated for stage-based workflow - uses stage_slug instead of phase_num.

    Attributes:
        session_manager: SessionManager for saving feedback to session/ directory
        retry_config: Configuration for retry behavior
    """

    def __init__(self, session_manager: SessionManager, retry_config: RetryConfig | None = None):
        """Initialize the ChangeRequestHandler.

        Args:
            session_manager: SessionManager instance for persistence
            retry_config: Optional retry configuration (uses defaults if not provided)
        """
        self.session_manager = session_manager
        self.retry_config = retry_config or RetryConfig()
        self._logger = logging.getLogger(f"{__name__}.session")

    def handle_change_request(
        self,
        stage_slug: str,
        change_request: ChangeRequest,
        default_query: str,
        retry_count: int = 0,
    ) -> tuple[str, bool]:
        """Process a change request and return modified query.

        This method:
        1. Validates retry count against max_retries
        2. Applies change request modifications to the query
        3. Saves change request details to user_feedback.md
        4. Implements exponential backoff delay if needed

        Args:
            stage_slug: Stage slug (e.g., "idea-refinement")
            change_request: ChangeRequest with modification details
            default_query: Default stage query to modify
            retry_count: Current retry count for this stage

        Returns:
            Tuple of (modified_query, should_retry):
                - modified_query: Query string to use for stage execution
                - should_retry: True if retry should proceed, False if max retries exceeded

        Example:
            >>> handler = ChangeRequestHandler(session_mgr)
            >>> change_req = ChangeRequest(
            ...     change_type="provide_guidance",
            ...     additional_guidance="Focus on B2B market"
            ... )
            >>> query, should_retry = handler.handle_change_request(
            ...     stage_slug="market-analysis",
            ...     change_request=change_req,
            ...     default_query="Conduct market research",
            ...     retry_count=0
            ... )
            >>> print(query)
            Conduct market research

            Additional guidance: Focus on B2B market
            >>> print(should_retry)
            True
        """
        stage_config = get_stage_by_slug(stage_slug)

        self._logger.info(
            f"Processing change request for stage {stage_slug}",
            extra={
                "stage_slug": stage_slug,
                "stage_name": stage_config.display_name,
                "change_type": change_request.change_type,
                "retry_count": retry_count,
            },
        )

        # Check if max retries exceeded
        if retry_count >= self.retry_config.max_retries:
            self._logger.warning(
                f"Max retries ({self.retry_config.max_retries}) exceeded for stage {stage_slug}",
                extra={
                    "stage_slug": stage_slug,
                    "retry_count": retry_count,
                    "max_retries": self.retry_config.max_retries,
                },
            )

            # Save max retries exceeded feedback
            self.session_manager.save_user_feedback(
                stage_slug=stage_slug,
                feedback={
                    "reviewed": True,
                    "approved": False,
                    "comments": f"Max retries ({self.retry_config.max_retries}) exceeded",
                    "action": "max_retries_exceeded",
                    "retry_count": retry_count,
                },
            )

            return default_query, False

        # Apply change request modifications
        modified_query = self._apply_modifications(
            change_request=change_request, default_query=default_query
        )

        # Save change request to user_feedback.md
        self._save_change_request(
            stage_slug=stage_slug, change_request=change_request, retry_count=retry_count
        )

        # Implement exponential backoff delay
        if retry_count > 0:
            delay = self.retry_config.calculate_delay(retry_count)
            self._logger.info(
                f"Applying exponential backoff delay: {delay:.2f}s",
                extra={
                    "stage_slug": stage_slug,
                    "retry_count": retry_count,
                    "delay_seconds": delay,
                },
            )
            time.sleep(delay)

        return modified_query, True

    def _apply_modifications(self, change_request: ChangeRequest, default_query: str) -> str:
        """Apply change request modifications to the default query.

        Args:
            change_request: ChangeRequest with modification details
            default_query: Default phase query

        Returns:
            Modified query string
        """
        if change_request.change_type == "modify_prompt":
            # Replace entire query with modified prompt
            if change_request.modified_prompt:
                self._logger.info("Applying modified prompt")
                return change_request.modified_prompt
            else:
                self._logger.warning("No modified prompt provided, using default")
                return default_query

        elif change_request.change_type == "provide_guidance":
            # Append additional guidance to default query
            if change_request.additional_guidance:
                self._logger.info("Appending additional guidance to default query")
                return (
                    f"{default_query}\n\nAdditional guidance: {change_request.additional_guidance}"
                )
            else:
                self._logger.warning("No additional guidance provided, using default")
                return default_query

        else:  # retry_with_same
            # Use default query without modifications
            self._logger.info("Using default query (retry with same settings)")
            return default_query

    def _save_change_request(
        self, stage_slug: str, change_request: ChangeRequest, retry_count: int
    ) -> None:
        """Save change request details to user_feedback.md.

        Args:
            stage_slug: Stage slug (e.g., "idea-refinement")
            change_request: ChangeRequest with modification details
            retry_count: Current retry count
        """
        get_stage_by_slug(stage_slug)  # Validate stage_slug

        # Build comments based on change type
        if change_request.change_type == "modify_prompt":
            comments = "User provided modified prompt"
            requested_changes = [
                f"Modified prompt: {change_request.modified_prompt[:200]}..."
                if change_request.modified_prompt and len(change_request.modified_prompt) > 200
                else f"Modified prompt: {change_request.modified_prompt}"
            ]
        elif change_request.change_type == "provide_guidance":
            comments = "User provided additional guidance"
            requested_changes = [
                f"Additional guidance: {change_request.additional_guidance[:200]}..."
                if change_request.additional_guidance
                and len(change_request.additional_guidance) > 200
                else f"Additional guidance: {change_request.additional_guidance}"
            ]
        else:  # retry_with_same
            comments = "User requested retry with same settings"
            requested_changes = ["Retry with same settings (no modifications)"]

        # Save to user_feedback.md
        self.session_manager.save_user_feedback(
            stage_slug=stage_slug,
            feedback={
                "reviewed": True,
                "approved": False,
                "comments": comments,
                "requested_changes": requested_changes,
                "action": "retry_with_changes",
                "retry_count": retry_count + 1,
            },
        )

        self._logger.info(
            "Saved change request to user_feedback.md",
            extra={
                "stage_slug": stage_slug,
                "change_type": change_request.change_type,
                "retry_count": retry_count + 1,
            },
        )

    def should_allow_retry(self, retry_count: int) -> bool:
        """Check if retry should be allowed based on retry count.

        Args:
            retry_count: Current retry count

        Returns:
            True if retry should be allowed, False otherwise
        """
        return retry_count < self.retry_config.max_retries

    def get_retry_delay(self, retry_count: int) -> float:
        """Get the delay for the given retry count.

        Args:
            retry_count: Current retry count

        Returns:
            Delay in seconds
        """
        return self.retry_config.calculate_delay(retry_count)
