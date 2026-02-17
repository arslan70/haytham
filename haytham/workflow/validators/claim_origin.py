"""Claim origin consistency validation.

Checks that dimension scores in the validation summary are consistent with
the external claim support ratio from risk assessment. High scores with
weak external validation suggest score inflation from internal claims.

Pure-Python mechanical check — no LLM calls.
"""

import json
import logging
import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from burr.core import State

logger = logging.getLogger(__name__)

# Regex to extract "External Validation: X/Y external claims supported"
_EXTERNAL_VALIDATION_RE = re.compile(
    r"\*\*External Validation:\*\*\s*(\d+)/(\d+)\s+external claims supported",
    re.IGNORECASE,
)


def _extract_external_ratio(risk_assessment: str) -> tuple[int, int] | None:
    """Extract (supported, total) external claims from risk assessment output."""
    match = _EXTERNAL_VALIDATION_RE.search(risk_assessment)
    if match:
        return int(match.group(1)), int(match.group(2))
    return None


def _extract_composite_score(output: str) -> float | None:
    """Extract composite_score from validation summary JSON output."""
    try:
        data = json.loads(output)
    except (json.JSONDecodeError, TypeError):
        return None
    return data.get("go_no_go_assessment", {}).get("composite_score")


def validate_claim_origin(output: str, state: "State") -> list[str]:
    """Check score consistency with external claim support ratio.

    Returns a list of warning strings (empty if consistent).
    """
    warnings: list[str] = []

    composite = _extract_composite_score(output)
    if composite is None:
        return warnings

    risk_assessment = state.get("risk_assessment", "")
    ratio = _extract_external_ratio(risk_assessment)
    if ratio is None:
        return warnings

    supported, total = ratio
    if total == 0:
        return warnings

    external_support_pct = supported / total

    # High composite score with weak external support = likely inflation
    if composite > 3.5 and external_support_pct < 0.5:
        warnings.append(
            f"Composite score {composite} (GO) but only {supported}/{total} "
            f"({external_support_pct:.0%}) external claims supported — "
            f"score may be inflated by internal claims"
        )

    # Moderate check: high composite with no strong external support
    if composite > 3.0 and total >= 3 and supported == 0:
        warnings.append(
            f"Composite score {composite} but 0/{total} external claims supported — "
            f"no market evidence backing the score"
        )

    # Insufficient external claims — internal claims may be dominating the budget
    if total < 5:
        warnings.append(
            f"Only {total} external claims extracted — "
            f"at least 5 expected for meaningful market validation"
        )

    if warnings:
        logger.warning("Claim origin inconsistencies: %s", "; ".join(warnings))

    return warnings
