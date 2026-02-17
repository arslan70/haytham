"""Dim 8 (Adoption & Engagement Risk) input consistency validation.

Checks that the Dim 8 score is consistent with Switching Cost signals
from competitor analysis.

Pure-Python mechanical check — no LLM calls.
"""

import logging
import re
from typing import TYPE_CHECKING

from ._scorecard_utils import extract_dimension_score

if TYPE_CHECKING:
    from burr.core import State

logger = logging.getLogger(__name__)

_SWITCHING_COST_RE = re.compile(
    r"\*\*Switching [Cc]ost:\*\*\s*\[?(Low|Medium|High)\]?",
    re.IGNORECASE,
)


def _extract_switching_cost(market_context: str) -> str:
    """Extract Switching Cost tag from market context (competitor analysis section).

    Returns the tag value (e.g. "High", "Low") or empty string if not found.
    """
    match = _SWITCHING_COST_RE.search(market_context)
    return match.group(1).strip() if match else ""


def validate_dim8_inputs(output: str, state: "State") -> list[str]:
    """Check Dim 8 score consistency with Switching Cost signals.

    A high Dim 8 score means low adoption risk (easy to adopt).
    High switching cost contradicts easy adoption — users face barriers
    leaving current solutions.

    Returns a list of warning strings (empty if consistent).
    """
    warnings: list[str] = []

    market_context = state.get("market_context", "")
    # State field first (from recording tools), regex fallback for old sessions
    switching_cost = state.get("switching_cost", "") or _extract_switching_cost(market_context)

    # Backward compat: no switching cost tag → nothing to validate
    if not switching_cost:
        return warnings

    dim8_score = extract_dimension_score(output, "adoption")
    if dim8_score is None:
        return warnings

    if switching_cost.lower() == "high" and dim8_score >= 4:
        warnings.append(
            f"Adoption & Engagement Risk scored {dim8_score}/5 (low risk) "
            f"but Switching Cost is 'High' — users face significant barriers to switching"
        )

    if warnings:
        logger.warning("Dim 8 input inconsistencies: %s", "; ".join(warnings))

    return warnings
