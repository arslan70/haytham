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

# Domain signals in the idea description that imply regulatory requirements.
# Maps regex pattern (applied to system_goal) -> expected compliance keyword in report.
_DOMAIN_COMPLIANCE_MAP: list[tuple[re.Pattern[str], str, str]] = [
    (
        re.compile(
            # Word stems: "therap" matches therapy/therapist, "psycholog" matches psychologist, etc.
            r"\b(health|wellness|therap\w*|patient|medical|clinic|doctor|mental.health|"
            r"diagnos\w*|treatment|symptom|psycholog\w*|psychiatr\w*|counseling|pharma\w*)\b",
            re.IGNORECASE,
        ),
        "HIPAA",
        "health/wellness/therapy",
    ),
    (
        re.compile(
            r"\b(payment\w*|fintech|banking|financial|credit.card|transaction\w*|lending|"
            r"insurance|invest\w*|trading|crypto\w*|wallet)\b",
            re.IGNORECASE,
        ),
        "PCI-DSS",
        "fintech/payments",
    ),
    (
        re.compile(
            r"\b(child\w*|kids|minor\w*|under.13|youth|elementary|middle.school|"
            r"parental.consent|young.learner\w*)\b",
            re.IGNORECASE,
        ),
        "COPPA",
        "children/minors",
    ),
    (
        re.compile(
            r"\b(student.record\w*|education.record\w*|school.data|transcript\w*|"
            r"student.information.system)\b",
            re.IGNORECASE,
        ),
        "FERPA",
        "education records",
    ),
]


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
    """Flag missing compliance frameworks for ideas in regulated domains.

    Two checks:
    1. If the idea description (system_goal) contains domain signals
       (health, fintech, children, etc.) but the report does NOT mention
       the expected compliance framework (HIPAA, PCI-DSS, COPPA, etc.),
       warn that the risk assessment is incomplete.
    2. If the report mentions compliance frameworks AND recommendation is
       GO, warn to review the risk assessment carefully.
    """
    try:
        data = json.loads(output)
        recommendation = data.get("recommendation", "").upper().strip()
        text = data.get("report", output)
    except (json.JSONDecodeError, TypeError, AttributeError):
        recommendation = ""
        text = output

    raw_goal = state.get("system_goal", "") if state else ""
    system_goal = raw_goal if isinstance(raw_goal, str) else ""

    warnings: list[str] = []

    # Check 1: Missing compliance frameworks for regulated domains
    for domain_re, expected_keyword, domain_label in _DOMAIN_COMPLIANCE_MAP:
        if domain_re.search(system_goal) and not re.search(
            rf"\b{re.escape(expected_keyword)}\b", text, re.IGNORECASE
        ):
            warnings.append(
                f"Idea involves {domain_label} but report does not mention "
                f"{expected_keyword}. Risk Assessment may be incomplete."
            )

    # Check 2: GO recommendation with regulatory complexity
    if recommendation == "GO":
        found_keywords = {kw.upper() for kw in _REGULATORY_RE.findall(text)}
        if found_keywords:
            sorted_kw = ", ".join(sorted(found_keywords))
            warnings.append(
                f"GO recommendation with regulatory compliance ({sorted_kw}). "
                "Review the Risk Assessment section before proceeding."
            )

    return warnings
