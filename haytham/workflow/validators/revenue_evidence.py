"""Revenue evidence consistency validation.

Checks that the Revenue Viability dimension score in the validation summary
is consistent with upstream evidence (Revenue Evidence Tag from competitor
analysis and WTP signal from the concept anchor).

Pure-Python mechanical check — no LLM calls.
"""

import json
import logging
import re
from typing import TYPE_CHECKING

from ._scorecard_utils import extract_dimension_score

if TYPE_CHECKING:
    from burr.core import State

logger = logging.getLogger(__name__)

# Regex to extract Revenue Evidence Tag from market_context (competitor analysis section).
_REVENUE_TAG_RE = re.compile(
    r"\*\*Revenue Evidence Tag:\*\*\s*\[?(Priced|Freemium-Dominant|No-Pricing-Found)\]?",
    re.IGNORECASE,
)

# Regex to extract WTP signal from concept anchor string.
_WTP_RE = re.compile(
    r"\*\*Willingness to Pay:\*\*\s*(Present|Unclear|Absent)",
    re.IGNORECASE,
)

# Regex to extract competitor price range (e.g. "$0-$12.50/user/mo").
_PRICE_RANGE_RE = re.compile(
    r"[Pp]rice range[^:]*:\s*\$?([\d,.]+)\s*[-–]\s*\$?([\d,.]+)",
)


def _extract_revenue_tag(market_context: str) -> str:
    """Extract Revenue Evidence Tag from market context output."""
    match = _REVENUE_TAG_RE.search(market_context)
    return match.group(1).strip() if match else ""


def _extract_wtp(anchor_str: str) -> str:
    """Extract Willingness-to-Pay signal from concept anchor string."""
    match = _WTP_RE.search(anchor_str)
    return match.group(1).strip() if match else ""


def _extract_price_range(market_context: str) -> tuple[float, float] | None:
    """Extract competitor price range from market context.

    Returns (low, high) tuple or None if not found.
    """
    match = _PRICE_RANGE_RE.search(market_context)
    if not match:
        return None
    try:
        low = float(match.group(1).replace(",", ""))
        high = float(match.group(2).replace(",", ""))
        return (low, high)
    except ValueError:
        return None


def _extract_assumed_price(output: str) -> float | None:
    """Extract assumed price from validation summary lean_canvas.revenue_model.

    Looks for dollar amounts in the revenue_model field.
    """
    try:
        data = json.loads(output)
    except (json.JSONDecodeError, TypeError):
        return None

    revenue_model = data.get("lean_canvas", {}).get("revenue_model", "")
    if not isinstance(revenue_model, str):
        return None

    # Find dollar amounts like $10, $99.99, $1,000
    price_matches = re.findall(r"\$\s*([\d,.]+)", revenue_model)
    if not price_matches:
        return None
    try:
        return float(price_matches[0].replace(",", ""))
    except ValueError:
        return None


def validate_revenue_evidence(output: str, state: "State") -> list[str]:
    """Check Revenue Viability score consistency with upstream evidence.

    Returns a list of warning strings (empty if consistent).
    """
    warnings: list[str] = []

    rev_score = extract_dimension_score(output, "revenue")
    if rev_score is None:
        return warnings

    market_context = state.get("market_context", "")
    anchor_str = state.get("concept_anchor_str", "")

    # State field first (from recording tools), regex fallback for old sessions
    pricing_tag = state.get("revenue_evidence_tag", "") or _extract_revenue_tag(market_context)
    wtp_signal = _extract_wtp(anchor_str)

    if rev_score >= 4 and pricing_tag == "No-Pricing-Found":
        warnings.append(
            f"Revenue Viability scored {rev_score}/5 but competitor pricing was not found"
        )
    if rev_score >= 4 and wtp_signal in ("Absent", "Unclear"):
        warnings.append(f"Revenue Viability scored {rev_score}/5 but WTP signal is '{wtp_signal}'")
    if rev_score <= 2 and pricing_tag == "Priced" and wtp_signal == "Present":
        warnings.append(
            f"Revenue Viability scored {rev_score}/5 but pricing evidence exists — may be too low"
        )

    # Price range consistency check
    price_range = _extract_price_range(market_context)
    assumed_price = _extract_assumed_price(output)
    if price_range and assumed_price:
        low, high = price_range
        if assumed_price > high * 2.0:
            warnings.append(
                f"Assumed price ${assumed_price:.0f} is >2x competitor ceiling "
                f"(${low:.0f}-${high:.0f})"
            )

    if warnings:
        logger.warning("Revenue evidence inconsistencies: %s", "; ".join(warnings))

    return warnings
