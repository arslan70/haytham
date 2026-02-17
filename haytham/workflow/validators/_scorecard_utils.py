"""Shared utilities for scorecard post-validators.

Extracts dimension scores from the validation summary JSON output.
All 6 post-validators parse the same scorecard structure — this module
provides a single implementation to avoid per-validator duplication.
"""

import json


def extract_dimension_score(output: str, keyword: str) -> int | None:
    """Extract a dimension score by keyword from validation summary JSON.

    Searches the ``go_no_go_assessment.scorecard`` array for a dimension
    whose name contains *keyword* (case-insensitive substring match).

    Args:
        output: Raw JSON string from the validation-summary stage.
        keyword: Case-insensitive substring to match against dimension names
            (e.g. ``"revenue"``, ``"adoption"``, ``"problem severity"``).

    Returns:
        The integer score (1-5) if found, else ``None``.
    """
    try:
        data = json.loads(output)
    except (json.JSONDecodeError, TypeError):
        return None

    scorecard = data.get("go_no_go_assessment", {}).get("scorecard", [])
    keyword_lower = keyword.lower()
    for dim in scorecard:
        if isinstance(dim, dict) and keyword_lower in dim.get("dimension", "").lower():
            score = dim.get("score")
            if isinstance(score, int):
                return score
    return None
