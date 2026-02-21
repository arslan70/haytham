"""Post-synthesis guardrails for report quality (ADR-026).

Lightweight validators that surface concerns for human reviewers.
They never reject or rewrite output, only return warning strings.

Signature: ``(output: str, state: State) -> list[str]``
"""

import json
import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from burr.core import State

# Dollar amount near "SOM": captures optional $ sign, digits (with optional
# commas/decimals), and an optional K/M/B suffix.
_SOM_AMOUNT_RE = re.compile(
    r"SOM[^$\d]{0,40}\$\s*([\d,]+(?:\.\d+)?)\s*([KkMmBb](?:illion|illion)?)?",
    re.IGNORECASE,
)

_REGULATORY_KEYWORDS = frozenset(
    ["HIPAA", "PCI-DSS", "COPPA", "FDA", "SOX", "GDPR", "FERPA", "CCPA"]
)

# Word-boundary regex for each keyword so partial matches (e.g. "GDPRA") are ignored.
_REGULATORY_RE = re.compile(
    r"\b(" + "|".join(re.escape(kw) for kw in sorted(_REGULATORY_KEYWORDS)) + r")\b",
    re.IGNORECASE,
)


def _normalize_dollar_amount(digits_str: str, suffix: str | None) -> float:
    """Convert a captured dollar string like '3.2' + 'M' to a float (3_200_000)."""
    value = float(digits_str.replace(",", ""))
    if not suffix:
        return value
    code = suffix[0].upper()
    multipliers = {"K": 1_000, "M": 1_000_000, "B": 1_000_000_000}
    return value * multipliers.get(code, 1)


def validate_som_arithmetic(output: str, state: "State") -> list[str]:
    """Flag SOM dollar-amount mismatches in the report.

    Scans the report markdown for dollar figures near "SOM" mentions.
    If any two figures differ by more than 2x, returns a warning.
    """
    # The output is JSON from ValidationReport; extract the markdown report.
    try:
        data = json.loads(output)
        text = data.get("report", output)
    except (json.JSONDecodeError, TypeError, AttributeError):
        text = output

    matches = _SOM_AMOUNT_RE.findall(text)
    if len(matches) < 2:
        return []

    amounts = [_normalize_dollar_amount(digits, suffix) for digits, suffix in matches]

    warnings: list[str] = []
    for i in range(len(amounts)):
        for j in range(i + 1, len(amounts)):
            a, b = amounts[i], amounts[j]
            # Avoid division by zero
            if a == 0 or b == 0:
                continue
            ratio = max(a, b) / min(a, b)
            if ratio > 2.0:
                # Format amounts for readability
                fmt_a = _format_amount(a)
                fmt_b = _format_amount(b)
                warnings.append(
                    f"SOM arithmetic mismatch: found ${fmt_a} in one section "
                    f"and ${fmt_b} in another. Verify the calculation."
                )
                # One warning is sufficient
                return warnings

    return warnings


def _format_amount(value: float) -> str:
    """Format a dollar amount for display (e.g. 3200000 -> '3.2M')."""
    if value >= 1_000_000_000:
        return f"{value / 1_000_000_000:.1f}B"
    if value >= 1_000_000:
        return f"{value / 1_000_000:.1f}M"
    if value >= 1_000:
        return f"{value / 1_000:.0f}K"
    return f"{value:.0f}"


def validate_regulated_domain_safety(output: str, state: "State") -> list[str]:
    """Flag GO recommendations for ideas involving regulated domains.

    Scans the report for regulatory keywords (HIPAA, PCI-DSS, etc.).
    If found AND recommendation is GO, returns a warning to review the
    risk assessment section.
    """
    # Extract recommendation from JSON output
    recommendation = ""
    try:
        data = json.loads(output)
        recommendation = data.get("recommendation", "").upper().strip()
        text = data.get("report", output)
    except (json.JSONDecodeError, TypeError, AttributeError):
        text = output

    # Only warn on GO recommendations
    if recommendation != "GO":
        return []

    found_keywords = set(_REGULATORY_RE.findall(text))
    # Normalize to uppercase for display
    found_keywords = {kw.upper() for kw in found_keywords}

    if not found_keywords:
        return []

    sorted_kw = ", ".join(sorted(found_keywords))
    return [
        f"This idea involves regulatory compliance ({sorted_kw}). "
        "Review the Risk Assessment section before proceeding."
    ]
