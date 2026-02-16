"""Stage configuration for unified workflow architecture.

DEPRECATED: This module is deprecated. Import from haytham.workflow instead.

Migration guide:
    # Old (deprecated)
    from haytham.phases import STAGES, get_stage_by_slug

    # New (recommended)
    from haytham.workflow import get_stage_registry, get_stage_by_slug
"""

# Re-export from stage_config for backward compatibility
from haytham.phases.stage_config import (
    STAGES,
    StageConfig,
    WorkflowType,
    get_stage_count,
    get_stage_index,
)

# These were removed from stage_config; import from canonical source
from haytham.workflow.stage_registry import (
    format_query,
    get_all_stage_slugs,
    get_stage_by_slug,
)

__all__ = [
    "StageConfig",
    "WorkflowType",
    "STAGES",
    "get_stage_by_slug",
    "get_stage_index",
    "get_all_stage_slugs",
    "get_stage_count",
    "format_query",
]
