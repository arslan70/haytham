"""Concept health binding constraint validation.

Checks that dimension scores in the validation summary respect binding
constraints from Concept Health signals (Pain Clarity, WTP).

Pure-Python mechanical check — no LLM calls.
"""

import logging
import re
from typing import TYPE_CHECKING

from ._scorecard_utils import extract_dimension_score

if TYPE_CHECKING:
    from burr.core import State

logger = logging.getLogger(__name__)

_PAIN_CLARITY_RE = re.compile(
    r"\*\*Pain Clarity:\*\*\s*(Clear|Ambiguous|Weak)",
    re.IGNORECASE,
)


def _extract_pain_clarity(anchor_str: str) -> str:
    """Extract Pain Clarity signal from concept anchor string."""
    match = _PAIN_CLARITY_RE.search(anchor_str)
    return match.group(1).strip() if match else ""


def validate_concept_health_bindings(output: str, state: "State") -> list[str]:
    """Check dimension scores respect Concept Health binding constraints.

    Returns a list of warning strings (empty if consistent).
    """
    warnings: list[str] = []

    anchor_str = state.get("concept_anchor_str", "")
    pain_clarity = _extract_pain_clarity(anchor_str)

    # Backward compat: no Pain Clarity signal → nothing to validate
    if not pain_clarity:
        return warnings

    problem_score = extract_dimension_score(output, "problem severity")
    if problem_score is None:
        return warnings

    if pain_clarity.lower() == "weak" and problem_score > 3:
        warnings.append(
            f"Problem Severity scored {problem_score}/5 but Pain Clarity is 'Weak' "
            f"(binding constraint: must be ≤ 3)"
        )

    if warnings:
        logger.warning("Concept health binding violations: %s", "; ".join(warnings))

    return warnings
