"""Burr-based workflow engine for Haytham.

This package provides a state machine-based workflow using Burr,
replacing the previous linear stage execution with support for
conditional branching and more sophisticated control flow.
"""

# Anchor schema imports (no external dependencies, ADR-022)
from .anchor_schema import (
    AnchorComplianceReport,
    ConceptAnchor,
    IdeaArchetype,
    IdentityFeature,
    Intent,
    Invariant,
    InvariantOverride,
)

# Stage output envelope (ADR-022 Part 6)
from .stage_output import Claim, StageOutput, StageOutputWithMetrics

# Stage registry imports (no external dependencies)
from .stage_registry import (
    StageMetadata,
    StageRegistry,
    WorkflowType,
    format_query,
    get_all_stage_slugs,
    get_stage_by_action,
    get_stage_by_slug,
    get_stage_registry,
)


# Lazy import for Burr-dependent modules to avoid import errors
# when burr is not installed (e.g., during testing)
def __getattr__(name):
    """Lazy import for Burr-dependent modules."""
    if name in ("BurrWorkflowRunner", "create_validation_workflow"):
        from .burr_workflow import BurrWorkflowRunner, create_validation_workflow

        if name == "BurrWorkflowRunner":
            return BurrWorkflowRunner
        return create_validation_workflow
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    # Burr workflow (lazy loaded)
    "create_validation_workflow",
    "BurrWorkflowRunner",
    # Stage registry (always available)
    "StageRegistry",
    "StageMetadata",
    "WorkflowType",
    "get_stage_registry",
    "get_stage_by_slug",
    "get_stage_by_action",
    "get_all_stage_slugs",
    "format_query",
    # Anchor schema (ADR-022)
    "ConceptAnchor",
    "IdeaArchetype",
    "Intent",
    "Invariant",
    "IdentityFeature",
    "InvariantOverride",
    "AnchorComplianceReport",
    # Stage output envelope (ADR-022 Part 6)
    "StageOutput",
    "StageOutputWithMetrics",
    "Claim",
]
