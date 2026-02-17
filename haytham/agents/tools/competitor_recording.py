"""Competitor analysis recording tools.

Server-side accumulator for structured data captured alongside the competitor
analysis agent's markdown prose.  Follows the same accumulator + clear/get
lifecycle pattern as ``recommendation.py``.

The agent calls ``record_competitor``, ``record_sentiment``, and
``record_market_positioning`` as it works.  The stage executor brackets each
run with ``clear_competitor_accumulator()`` before and
``get_competitor_data()`` after to harvest the structured fields.
"""

from strands import tool

# ---------------------------------------------------------------------------
# Module-level accumulator (same pattern as recommendation.py)
# ---------------------------------------------------------------------------

_accumulator: dict = {
    "competitors": [],
    "sentiment": [],
    "market_positioning": {},
}

_JTBD_MATCH_VALUES = frozenset({"Direct", "Adjacent", "Unrelated"})
_REVENUE_TAG_VALUES = frozenset({"Priced", "Freemium-Dominant", "No-Pricing-Found"})
_SWITCHING_COST_VALUES = frozenset({"Low", "Medium", "High"})


def clear_competitor_accumulator() -> None:
    """Reset the accumulator to empty state."""
    _accumulator["competitors"] = []
    _accumulator["sentiment"] = []
    _accumulator["market_positioning"] = {}


def get_competitor_data() -> dict:
    """Return a copy of the current accumulator state."""
    return {
        "competitors": list(_accumulator["competitors"]),
        "sentiment": list(_accumulator["sentiment"]),
        "market_positioning": dict(_accumulator["market_positioning"]),
    }


# ---------------------------------------------------------------------------
# @tool functions (scalar parameters, no LLM calls)
# ---------------------------------------------------------------------------


@tool
def record_competitor(
    name: str,
    url: str,
    traction: str,
    target_segment: str,
    jtbd_match: str,
) -> str:
    """Record a competitor identified during analysis.

    Call this after analyzing each competitor in Section 1.

    Args:
        name: Competitor company name.
        url: Competitor website URL.
        traction: Summary of traction evidence (downloads, funding, rating).
        target_segment: Who uses this product.
        jtbd_match: How this competitor relates to the core JTBD.
            Must be one of: Direct, Adjacent, Unrelated.

    Returns:
        Confirmation message or error if jtbd_match is invalid.
    """
    if jtbd_match not in _JTBD_MATCH_VALUES:
        return (
            f"REJECTED: jtbd_match '{jtbd_match}' is invalid. "
            f"Must be one of: {', '.join(sorted(_JTBD_MATCH_VALUES))}. "
            f"Re-call with a valid value."
        )

    _accumulator["competitors"].append(
        {
            "name": name,
            "url": url,
            "traction": traction,
            "target_segment": target_segment,
            "jtbd_match": jtbd_match,
        }
    )
    n = len(_accumulator["competitors"])
    return f"Recorded competitor '{name}' (JTBD: {jtbd_match}). Total competitors: {n}"


@tool
def record_sentiment(
    competitor: str,
    love: str,
    hate: str,
    wish: str,
    source: str,
) -> str:
    """Record user sentiment analysis for a competitor.

    Call this after analyzing each competitor in Section 2.

    Args:
        competitor: Competitor name.
        love: What users love (quote or paraphrase).
        hate: What users hate (quote or paraphrase).
        wish: What users wish for (quote or paraphrase).
        source: Source of the sentiment data (e.g. "Reddit r/fitness", "G2 reviews").

    Returns:
        Confirmation message.
    """
    _accumulator["sentiment"].append(
        {
            "competitor": competitor,
            "love": love,
            "hate": hate,
            "wish": wish,
            "source": source,
        }
    )
    n = len(_accumulator["sentiment"])
    return f"Recorded sentiment for '{competitor}'. Total sentiment entries: {n}"


@tool
def record_market_positioning(
    revenue_evidence_tag: str,
    switching_cost: str,
    price_range_low: str,
    price_range_high: str,
    market_structure: str,
) -> str:
    """Record market positioning and revenue evidence from Section 3 & 4.

    Call this once after completing Sections 3 and 4.

    Args:
        revenue_evidence_tag: Revenue evidence classification.
            Must be one of: Priced, Freemium-Dominant, No-Pricing-Found.
        switching_cost: User switching cost assessment.
            Must be one of: Low, Medium, High.
        price_range_low: Low end of competitor pricing (e.g. "0", "9.99").
            Use empty string if not found.
        price_range_high: High end of competitor pricing (e.g. "49.99").
            Use empty string if not found.
        market_structure: Market structure classification
            (e.g. "Fragmented", "Winner-take-all", "Consolidating").

    Returns:
        Confirmation message or error if enum values are invalid.
    """
    if revenue_evidence_tag not in _REVENUE_TAG_VALUES:
        return (
            f"REJECTED: revenue_evidence_tag '{revenue_evidence_tag}' is invalid. "
            f"Must be one of: {', '.join(sorted(_REVENUE_TAG_VALUES))}. "
            f"Re-call with a valid value."
        )

    if switching_cost not in _SWITCHING_COST_VALUES:
        return (
            f"REJECTED: switching_cost '{switching_cost}' is invalid. "
            f"Must be one of: {', '.join(sorted(_SWITCHING_COST_VALUES))}. "
            f"Re-call with a valid value."
        )

    _accumulator["market_positioning"] = {
        "revenue_evidence_tag": revenue_evidence_tag,
        "switching_cost": switching_cost,
        "price_range_low": price_range_low,
        "price_range_high": price_range_high,
        "market_structure": market_structure,
    }
    return (
        f"Recorded market positioning: revenue={revenue_evidence_tag}, "
        f"switching_cost={switching_cost}, market={market_structure}"
    )
