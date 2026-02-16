"""ID generation utilities for pipeline entities.

The pipeline uses 4 ID types:
- S-XXX: Stories
- E-XXX: Entities
- T-XXX: Tasks
- D-XXX: Decisions

IDs are sequential within each type (001, 002, 003, etc.).

Reference: ADR-001a: ID Schemes
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .state_models import PipelineState


def _next_id(prefix: str, existing_ids: list[str]) -> str:
    """Generate next sequential ID with given prefix.

    Args:
        prefix: The ID prefix (S, E, T, or D)
        existing_ids: List of existing IDs to find the max from

    Returns:
        Next ID in format PREFIX-XXX (e.g., S-001, E-002)
    """
    max_num = 0
    for id_str in existing_ids:
        if id_str.startswith(f"{prefix}-"):
            try:
                num = int(id_str.split("-")[1])
                max_num = max(max_num, num)
            except (IndexError, ValueError):
                continue
    return f"{prefix}-{max_num + 1:03d}"


def next_story_id(state: PipelineState) -> str:
    """Generate next S-XXX ID based on existing stories.

    Args:
        state: Current pipeline state

    Returns:
        Next story ID (e.g., S-001, S-002)
    """
    existing = [s.id for s in state.stories if s.id]
    return _next_id("S", existing)


def next_entity_id(state: PipelineState) -> str:
    """Generate next E-XXX ID based on existing entities.

    Args:
        state: Current pipeline state

    Returns:
        Next entity ID (e.g., E-001, E-002)
    """
    existing = [e.id for e in state.entities if e.id]
    return _next_id("E", existing)


def next_task_id(state: PipelineState) -> str:
    """Generate next T-XXX ID based on existing tasks.

    Args:
        state: Current pipeline state

    Returns:
        Next task ID (e.g., T-001, T-002)
    """
    existing = [t.id for t in state.tasks if t.id]
    return _next_id("T", existing)


def next_decision_id(state: PipelineState) -> str:
    """Generate next D-XXX ID based on existing decisions.

    Args:
        state: Current pipeline state

    Returns:
        Next decision ID (e.g., D-001, D-002)
    """
    existing = [d.id for d in state.decisions if d.id]
    return _next_id("D", existing)
