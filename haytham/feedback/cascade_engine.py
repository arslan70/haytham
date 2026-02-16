"""Cascade engine for determining downstream stage revisions.

This module calculates which stages need to be revised when feedback affects
an earlier stage. Cascading only happens within the current workflow - changes
to one workflow never cascade to another.

Key Principle: If feedback affects stage N, all stages after N in the same
workflow must also be re-run to maintain consistency.
"""

import logging

logger = logging.getLogger(__name__)


def get_downstream_stages(
    stage_slug: str,
    workflow_stages: list[str],
) -> list[str]:
    """Get all stages that come after the given stage in the workflow.

    This identifies which stages would be affected if the given stage
    is revised (i.e., downstream dependencies).

    Args:
        stage_slug: Stage slug to find downstream stages for
        workflow_stages: Ordered list of all stages in the current workflow

    Returns:
        List of stage slugs that come after the given stage (empty if stage is last)

    Example:
        >>> stages = ["idea-analysis", "market-context", "risk-assessment", "validation-summary"]
        >>> get_downstream_stages("market-context", stages)
        ['risk-assessment', 'validation-summary']
    """
    try:
        stage_index = workflow_stages.index(stage_slug)
        downstream = workflow_stages[stage_index + 1 :]
        logger.debug(f"Downstream stages for '{stage_slug}': {downstream}")
        return downstream
    except ValueError:
        logger.warning(f"Stage '{stage_slug}' not found in workflow stages: {workflow_stages}")
        return []


def get_stages_to_revise(
    affected_stages: list[str],
    workflow_stages: list[str],
) -> list[str]:
    """Get complete list of stages to revise including downstream cascade.

    When feedback affects one or more stages, this function calculates the
    full set of stages that need revision. It finds the earliest affected
    stage and includes all subsequent stages in the workflow.

    This ensures consistency: if an early stage changes, all downstream
    stages must be updated to reflect those changes.

    Args:
        affected_stages: List of stages directly affected by feedback (from router)
        workflow_stages: Ordered list of all stages in the current workflow

    Returns:
        List of stage slugs to revise, in execution order (earliest affected + all downstream)

    Example:
        >>> stages = ["idea-analysis", "market-context", "risk-assessment", "validation-summary"]
        >>> # Feedback affects market-context
        >>> get_stages_to_revise(["market-context"], stages)
        ['market-context', 'risk-assessment', 'validation-summary']
        >>>
        >>> # Feedback affects multiple stages - cascade from earliest
        >>> get_stages_to_revise(["risk-assessment", "market-context"], stages)
        ['market-context', 'risk-assessment', 'validation-summary']
    """
    if not affected_stages:
        logger.warning("No affected stages provided, nothing to revise")
        return []

    if not workflow_stages:
        logger.warning("No workflow stages provided, nothing to revise")
        return []

    # Find the earliest affected stage
    earliest_index = None
    for stage in affected_stages:
        try:
            index = workflow_stages.index(stage)
            if earliest_index is None or index < earliest_index:
                earliest_index = index
        except ValueError:
            logger.warning(f"Affected stage '{stage}' not found in workflow stages")
            continue

    if earliest_index is None:
        logger.warning(f"None of the affected stages {affected_stages} found in workflow")
        return []

    # Return earliest + all downstream stages
    stages_to_revise = workflow_stages[earliest_index:]

    logger.info(
        f"Cascade calculation: affected={affected_stages}, "
        f"earliest_index={earliest_index}, "
        f"stages_to_revise={stages_to_revise}"
    )

    return stages_to_revise


def is_cascade_needed(
    affected_stages: list[str],
    workflow_stages: list[str],
) -> bool:
    """Check if cascading to downstream stages is needed.

    Cascading is needed when the affected stage is not the last stage
    in the workflow.

    Args:
        affected_stages: List of stages directly affected by feedback
        workflow_stages: Ordered list of all stages in the workflow

    Returns:
        True if downstream stages need to be revised, False otherwise

    Example:
        >>> stages = ["mvp-scope", "capability-model"]
        >>> is_cascade_needed(["mvp-scope"], stages)
        True
        >>> is_cascade_needed(["capability-model"], stages)
        False
    """
    if not affected_stages or not workflow_stages:
        return False

    # Find the earliest affected stage
    earliest_index = None
    for stage in affected_stages:
        try:
            index = workflow_stages.index(stage)
            if earliest_index is None or index < earliest_index:
                earliest_index = index
        except ValueError:
            continue

    if earliest_index is None:
        return False

    # Cascade is needed if there are stages after the earliest affected one
    return earliest_index < len(workflow_stages) - 1


def get_cascade_summary(
    affected_stages: list[str],
    stages_to_revise: list[str],
) -> str:
    """Generate a human-readable summary of the cascade.

    This is useful for displaying to users so they understand which
    stages will be affected by their feedback.

    Args:
        affected_stages: Stages directly affected by feedback
        stages_to_revise: All stages that will be revised (including cascade)

    Returns:
        Human-readable summary string

    Example:
        >>> get_cascade_summary(
        ...     ["market-context"],
        ...     ["market-context", "risk-assessment", "validation-summary"]
        ... )
        'Feedback affects Market Context. Will also update: Risk Assessment, Validation Summary.'
    """
    from haytham.workflow.stage_registry import get_stage_registry

    registry = get_stage_registry()

    # Get display names for affected stages
    affected_names = []
    for slug in affected_stages:
        stage = registry.get_by_slug_safe(slug)
        if stage:
            affected_names.append(stage.display_name)
        else:
            affected_names.append(slug)

    # Get display names for cascaded stages (excluding directly affected)
    cascaded_slugs = [s for s in stages_to_revise if s not in affected_stages]
    cascaded_names = []
    for slug in cascaded_slugs:
        stage = registry.get_by_slug_safe(slug)
        if stage:
            cascaded_names.append(stage.display_name)
        else:
            cascaded_names.append(slug)

    # Build summary
    affected_str = ", ".join(affected_names)
    summary = f"Feedback affects {affected_str}."

    if cascaded_names:
        cascaded_str = ", ".join(cascaded_names)
        summary += f" Will also update: {cascaded_str}."

    return summary
