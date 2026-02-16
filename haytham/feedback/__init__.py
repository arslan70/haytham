"""Feedback mechanism for workflow execution.

This module provides two feedback systems:

1. **Per-Stage Feedback** (legacy):
   - UserFeedbackLoop: Record approvals, skips, and change requests
   - ChangeRequestHandler: Process change requests with retry logic

2. **Post-Workflow Feedback** (new):
   - FeedbackProcessor: Orchestrates complete feedback flow
   - FeedbackRouter: Routes feedback to affected stages using LLM
   - CascadeEngine: Calculates downstream stages to revise
   - RevisionExecutor: Re-invokes agents with feedback context

The new post-workflow feedback system allows users to provide feedback
after a complete workflow finishes, with changes cascading to downstream
stages within the same workflow.
"""

# Legacy per-stage feedback (maintained for backward compatibility)
from haytham.feedback.cascade_engine import (
    get_cascade_summary,
    get_downstream_stages,
    get_stages_to_revise,
    is_cascade_needed,
)
from haytham.feedback.change_request_handler import (
    ChangeRequestHandler,
    RetryConfig,
)
from haytham.feedback.feedback_processor import (
    FeedbackProcessor,
    FeedbackResult,
)

# New post-workflow feedback system
from haytham.feedback.feedback_router import (
    FeedbackRouteResult,
    route_feedback,
)
from haytham.feedback.revision_executor import (
    STAGE_AGENT_MAP,
    RevisionResult,
    execute_revision,
)
from haytham.feedback.user_feedback_loop import (
    ChangeRequest,
    FeedbackAction,
    UserFeedbackLoop,
)

__all__ = [
    # Legacy per-stage feedback
    "UserFeedbackLoop",
    "FeedbackAction",
    "ChangeRequest",
    "ChangeRequestHandler",
    "RetryConfig",
    # New post-workflow feedback - Router
    "route_feedback",
    "FeedbackRouteResult",
    # New post-workflow feedback - Cascade
    "get_downstream_stages",
    "get_stages_to_revise",
    "is_cascade_needed",
    "get_cascade_summary",
    # New post-workflow feedback - Executor
    "execute_revision",
    "RevisionResult",
    "STAGE_AGENT_MAP",
    # New post-workflow feedback - Processor
    "FeedbackProcessor",
    "FeedbackResult",
]
