"""Stage configuration - DEPRECATED.

This module is deprecated. Import from haytham.workflow.stage_registry instead.

All exports are re-exported from stage_registry for backward compatibility.
This module will be removed in a future version.

Migration guide:
    # Old (deprecated)
    from haytham.phases.stage_config import STAGES, get_stage_by_slug, WorkflowType

    # New (recommended)
    from haytham.workflow.stage_registry import (
        get_stage_registry,
        get_stage_by_slug,
        WorkflowType,
    )
"""

import warnings

# Re-export everything from stage_registry
from haytham.workflow.stage_registry import (
    StageMetadata,
    WorkflowType,
    format_query,
    get_all_stage_slugs,
    get_stage_by_slug,
    get_stage_registry,
)

__all__ = [
    "STAGES",
    "StageConfig",
    "StageMetadata",
    "WorkflowType",
    "format_query",
    "get_all_stage_slugs",
    "get_stage_by_slug",
    "get_stage_count",
    "get_stage_index",
    "get_stage_registry",
    "get_stages_for_workflow",
    "get_workflow_stage_slugs",
    "get_workflow_for_stage",
    "get_first_stage_of_workflow",
    "get_last_stage_of_workflow",
    "is_last_stage_of_workflow",
    "IDEA_VALIDATION_STAGES",
    "MVP_SPECIFICATION_STAGES",
    "STORY_GENERATION_STAGES",
]

# Emit deprecation warning on import (only once)
warnings.warn(
    "haytham.phases.stage_config is deprecated. "
    "Import from haytham.workflow.stage_registry instead.",
    DeprecationWarning,
    stacklevel=2,
)


# =============================================================================
# Backward Compatibility Aliases
# =============================================================================

# StageConfig is now StageMetadata
StageConfig = StageMetadata


def _get_stages_list() -> list[StageMetadata]:
    """Get stages as a list for backward compatibility."""
    return get_stage_registry().all_stages(include_optional=True)


# STAGES list - now dynamically generated from registry
# Note: This is a function call, so it's evaluated each time STAGES is accessed
# For true backward compatibility, we compute it once at import time
STAGES = _get_stages_list()


def get_stage_index(slug: str) -> int:
    """Get the index (0-based) of a stage in the workflow.

    DEPRECATED: Use stage_registry methods instead.
    """
    for i, stage in enumerate(STAGES):
        if stage.slug == slug:
            return i
    raise ValueError(f"Unknown stage: {slug}")


def get_stage_count() -> int:
    """Get the total number of stages.

    DEPRECATED: Use len(get_stage_registry()) instead.
    """
    return len(STAGES)


def get_stages_for_workflow(workflow_type: WorkflowType) -> list[StageMetadata]:
    """Get all stages belonging to a specific workflow.

    DEPRECATED: Use get_stage_registry().get_stages_for_workflow() instead.
    """
    return get_stage_registry().get_stages_for_workflow(workflow_type)


def get_workflow_stage_slugs(workflow_type: WorkflowType) -> list[str]:
    """Get ordered list of stage slugs for a specific workflow.

    DEPRECATED: Use get_stage_registry().get_workflow_stage_slugs() instead.
    """
    return get_stage_registry().get_workflow_stage_slugs(workflow_type)


def get_workflow_for_stage(slug: str) -> WorkflowType:
    """Get the workflow type for a given stage.

    DEPRECATED: Use get_stage_registry().get_workflow_for_stage() instead.
    """
    return get_stage_registry().get_workflow_for_stage(slug)


def get_first_stage_of_workflow(workflow_type: WorkflowType) -> StageMetadata | None:
    """Get the first stage of a workflow.

    DEPRECATED: Use get_stage_registry().get_first_stage_of_workflow() instead.
    """
    return get_stage_registry().get_first_stage_of_workflow(workflow_type)


def get_last_stage_of_workflow(workflow_type: WorkflowType) -> StageMetadata | None:
    """Get the last stage of a workflow.

    DEPRECATED: Use get_stage_registry().get_last_stage_of_workflow() instead.
    """
    return get_stage_registry().get_last_stage_of_workflow(workflow_type)


def is_last_stage_of_workflow(slug: str) -> bool:
    """Check if a stage is the last stage of its workflow.

    DEPRECATED: Use get_stage_registry().is_last_stage_of_workflow() instead.
    """
    return get_stage_registry().is_last_stage_of_workflow(slug)


# Workflow-specific stage lists for backward compatibility
# These are computed once at import time
IDEA_VALIDATION_STAGES = get_stage_registry().get_stages_for_workflow(WorkflowType.IDEA_VALIDATION)
MVP_SPECIFICATION_STAGES = get_stage_registry().get_stages_for_workflow(
    WorkflowType.MVP_SPECIFICATION
)
STORY_GENERATION_STAGES = get_stage_registry().get_stages_for_workflow(
    WorkflowType.STORY_GENERATION
)


# Note: These deprecated items are no longer needed and not re-exported:
# - SubStageConfig (was unused)
# - duration_estimate (removed from model)
# - requires_preferences (removed from model)
# - estimate_total_duration() (removed)
# - estimate_workflow_duration() (removed)
