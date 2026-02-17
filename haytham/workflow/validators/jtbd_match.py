"""JTBD match consistency validation.

Checks that the Market Opportunity dimension score in the validation summary
is consistent with JTBD Match tags from competitor analysis. Flags when
most competitors solve adjacent/unrelated jobs but Market Opportunity scores high.

Pure-Python mechanical check — no LLM calls.
"""

import logging
import re
from typing import TYPE_CHECKING

from ._scorecard_utils import extract_dimension_score

if TYPE_CHECKING:
    from burr.core import State

logger = logging.getLogger(__name__)

_JTBD_MATCH_RE = re.compile(
    r"\*\*JTBD Match:\*\*\s*\[?(Direct|Adjacent|Unrelated)\]?",
    re.IGNORECASE,
)


def _extract_jtbd_matches(market_context: str) -> list[str]:
    """Extract all JTBD Match tags from market context (competitor analysis section)."""
    return [m.group(1).strip() for m in _JTBD_MATCH_RE.finditer(market_context)]


def validate_jtbd_match(output: str, state: "State") -> list[str]:
    """Check Market Opportunity score consistency with JTBD Match tags.

    Returns a list of warning strings (empty if consistent).
    """
    warnings: list[str] = []

    market_context = state.get("market_context", "")
    # State field first (from recording tools), regex fallback for old sessions
    matches = state.get("competitor_jtbd_matches", []) or _extract_jtbd_matches(market_context)

    # Backward compat: no JTBD Match tags → nothing to validate
    if not matches:
        return warnings

    # Only flag when we have enough competitors to be meaningful
    if len(matches) < 2:
        return warnings

    direct_count = sum(1 for m in matches if m.lower() == "direct")
    if direct_count > 0:
        return warnings

    # All competitors are Adjacent/Unrelated — check if Market Opportunity is high
    mo_score = extract_dimension_score(output, "market opportunity")
    if mo_score is not None and mo_score >= 4:
        warnings.append(
            f"Market Opportunity scored {mo_score}/5 but no competitors solve the same core JTBD "
            f"({len(matches)} competitors, all Adjacent/Unrelated)"
        )

    if warnings:
        logger.warning("JTBD match inconsistencies: %s", "; ".join(warnings))

    return warnings
