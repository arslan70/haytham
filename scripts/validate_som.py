#!/usr/bin/env python3
"""Validate SOM arithmetic consistency in a validation report.

Ported from haytham/workflow/validators/report_guardrails.py.

Usage: python validate_som.py <path-to-validation-report.json>

Outputs warnings to stderr. Exit 0 always (non-blocking).
"""

import json
import os
import re
import sys

# Dollar amount near "SOM": captures optional $ sign, digits (with optional
# commas/decimals), and an optional K/M/B suffix.
_SOM_AMOUNT_RE = re.compile(
    r"SOM[^$\d]{0,40}\$\s*([\d,]+(?:\.\d+)?)\s*([KkMmBb](?:illion|illion)?)?",
    re.IGNORECASE,
)

# Domain signals that imply regulatory requirements.
_DOMAIN_COMPLIANCE_MAP = [
    (
        re.compile(
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
    """Convert a captured dollar string like '3.2' + 'M' to a float."""
    value = float(digits_str.replace(",", ""))
    if not suffix:
        return value
    code = suffix[0].upper()
    multipliers = {"K": 1_000, "M": 1_000_000, "B": 1_000_000_000}
    return value * multipliers.get(code, 1)


def _format_amount(value: float) -> str:
    """Format a dollar amount for display (e.g., 3200000 -> '3.2M')."""
    if value >= 1_000_000_000:
        return f"{value / 1_000_000_000:.1f}B"
    if value >= 1_000_000:
        return f"{value / 1_000_000:.1f}M"
    if value >= 1_000:
        return f"{value / 1_000:.0f}K"
    return f"{value:.0f}"


def validate_som_arithmetic(report_text: str) -> list[str]:
    """Flag SOM dollar-amount mismatches in the report."""
    matches = _SOM_AMOUNT_RE.findall(report_text)
    if len(matches) < 2:
        return []

    amounts = [_normalize_dollar_amount(digits, suffix) for digits, suffix in matches]

    for i in range(len(amounts)):
        for j in range(i + 1, len(amounts)):
            a, b = amounts[i], amounts[j]
            if a == 0 or b == 0:
                continue
            ratio = max(a, b) / min(a, b)
            if ratio > 2.0:
                fmt_a = _format_amount(a)
                fmt_b = _format_amount(b)
                return [
                    f"SOM arithmetic mismatch: found ${fmt_a} in one section "
                    f"and ${fmt_b} in another. Verify the calculation."
                ]

    return []


def validate_regulated_domain_safety(
    report_text: str, idea_text: str, recommendation: str
) -> list[str]:
    """Flag missing compliance frameworks for regulated domains."""
    warnings = []

    # Check 1: Missing compliance frameworks
    for domain_re, expected_keyword, domain_label in _DOMAIN_COMPLIANCE_MAP:
        if domain_re.search(idea_text) and not re.search(
            rf"\b{re.escape(expected_keyword)}\b", report_text, re.IGNORECASE
        ):
            warnings.append(
                f"Idea involves {domain_label} but report does not mention "
                f"{expected_keyword}. Risk Assessment may be incomplete."
            )

    # Check 2: GO recommendation with regulatory complexity
    if recommendation.upper().strip() == "GO":
        regulatory_keywords = {
            "HIPAA",
            "PCI-DSS",
            "COPPA",
            "FDA",
            "SOX",
            "GDPR",
            "FERPA",
            "CCPA",
        }
        regulatory_re = re.compile(
            r"\b("
            + "|".join(re.escape(kw) for kw in sorted(regulatory_keywords))
            + r")\b",
            re.IGNORECASE,
        )
        found = {kw.upper() for kw in regulatory_re.findall(report_text)}
        if found:
            sorted_kw = ", ".join(sorted(found))
            warnings.append(
                f"GO recommendation with regulatory compliance ({sorted_kw}). "
                "Review the Risk Assessment section before proceeding."
            )

    return warnings


def main():
    """Validate a validation-report.json file."""
    if len(sys.argv) < 2:
        sys.exit(0)

    file_path = sys.argv[1]

    try:
        with open(file_path) as f:
            data = json.load(f)
    except (json.JSONDecodeError, FileNotFoundError, OSError):
        sys.exit(0)

    report_text = data.get("report", "")
    recommendation = data.get("recommendation", "")

    warnings = validate_som_arithmetic(report_text)

    # Try to read the idea from project.yaml for regulated domain checks.
    # Resolve it from the report's own .haytham root, not the CWD — the
    # process may run from a directory that has an unrelated .haytham/.
    idea_text = ""
    parts = os.path.abspath(file_path).split(os.sep)
    if ".haytham" in parts:
        haytham_root = os.sep.join(parts[: parts.index(".haytham") + 1])
        project_yaml = os.path.join(haytham_root, "project.yaml")
    else:
        project_yaml = os.path.join(".haytham", "project.yaml")
    try:
        import yaml

        with open(project_yaml) as f:
            project = yaml.safe_load(f)
            idea_text = project.get("idea", "")
    except Exception:
        # If yaml isn't available or file doesn't exist, try plain read
        try:
            with open(project_yaml) as f:
                idea_text = f.read()
        except (FileNotFoundError, OSError):
            pass

    warnings.extend(
        validate_regulated_domain_safety(report_text, idea_text, recommendation)
    )

    if warnings:
        print("\n".join(warnings), file=sys.stderr)

    sys.exit(0)


if __name__ == "__main__":
    main()
