"""SOM sanity validation.

Checks that the Serviceable Obtainable Market (SOM) figure from market
intelligence is plausible given the idea's scale indicators. Catches
fabricated SOM numbers when data is sparse (e.g., "$100K patients" for a
solo psychologist).

Pure-Python mechanical check — no LLM calls.
"""

import logging
import re
from typing import TYPE_CHECKING

from ._scorecard_utils import extract_dimension_score

if TYPE_CHECKING:
    from burr.core import State

logger = logging.getLogger(__name__)

# Regex to extract SOM dollar figure: **SOM:** ... $X million/billion
_SOM_RE = re.compile(
    r"\*\*SOM:\*\*.*?\$\s*([\d,.]+)\s*(million|billion|M|B)?",
    re.IGNORECASE,
)

# Regex to extract SAM dollar figure
_SAM_RE = re.compile(
    r"\*\*SAM:\*\*.*?\$\s*([\d,.]+)\s*(million|billion|M|B)?",
    re.IGNORECASE,
)

# Small-scale indicators in the system_goal / idea description
_SMALL_SCALE_RE = re.compile(
    r"\b(?:solo|individual\s+practitioner|single\s+location|"
    r"existing\s+(?:patients|customers|clients)|"
    r"(?:50|100|200|handful|few)\s+(?:patients|customers|clients|users))\b",
    re.IGNORECASE,
)


def _parse_dollar_amount(match: re.Match) -> float | None:
    """Convert a regex match to a dollar amount in millions."""
    try:
        value = float(match.group(1).replace(",", ""))
    except (ValueError, AttributeError):
        return None

    suffix = (match.group(2) or "").upper()
    if suffix in ("B", "BILLION"):
        value *= 1000  # Convert to millions
    elif suffix in ("M", "MILLION"):
        pass  # Already in millions
    else:
        # No suffix — assume raw millions if >= 1, else it's raw dollars
        if value >= 1000:
            value /= 1_000_000  # Convert raw dollars to millions
    return value


def validate_som_sanity(output: str, state: "State") -> list[str]:
    """Check SOM plausibility against idea scale and upstream signals.

    Returns a list of warning strings (empty if consistent).
    """
    warnings: list[str] = []

    market_context = state.get("market_context", "")
    system_goal = state.get("system_goal", "")

    # Extract SOM
    som_match = _SOM_RE.search(market_context)
    som_value = _parse_dollar_amount(som_match) if som_match else None

    # Extract SAM
    sam_match = _SAM_RE.search(market_context)
    sam_value = _parse_dollar_amount(sam_match) if sam_match else None

    # Check 1: SOM >= $1M but small-scale indicators present
    if som_value is not None and som_value >= 1.0:
        if _SMALL_SCALE_RE.search(system_goal):
            warnings.append(
                f"SOM ${som_value:.1f}M appears implausible — "
                f"idea description contains small-scale indicators "
                f"(solo practitioner, existing patients/clients, etc.)"
            )

    # Check 2: SOM > 10x SAM
    if som_value is not None and sam_value is not None and sam_value > 0:
        if som_value > 10 * sam_value:
            warnings.append(
                f"SOM ${som_value:.1f}M exceeds SAM ${sam_value:.1f}M by "
                f"more than 10x — SOM cannot be larger than SAM"
            )

    # Check 3: Market Opportunity >= 4 but no SOM figure
    market_opp_score = extract_dimension_score(output, "market opportunity")
    if market_opp_score is not None and market_opp_score >= 4 and som_value is None:
        warnings.append(
            f"Market Opportunity scored {market_opp_score}/5 but no "
            f"quantitative SOM figure found in market context — "
            f"score lacks quantitative basis"
        )

    if warnings:
        logger.warning("SOM sanity issues: %s", "; ".join(warnings))

    return warnings
