"""Stage orchestration modules.

Each module contains the domain-specific orchestration functions for a group
of related stages.  The assembled ``STAGE_CONFIGS`` dict is the single public
export consumed by :mod:`haytham.workflow.stage_executor`.
"""

from .concept_anchor import (
    extract_concept_anchor,
    get_anchor_context_string,
    get_anchor_from_state,
)
from .configs import STAGE_CONFIGS

__all__ = [
    "STAGE_CONFIGS",
    "extract_concept_anchor",
    "get_anchor_from_state",
    "get_anchor_context_string",
]
