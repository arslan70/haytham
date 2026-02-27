"""Parse acceptance criteria from story content into structured Gherkin.

Handles three formats the detail agents produce:
1. Checkbox lists: ``- [ ] Given X, When Y, Then Z``
2. Fenced Gherkin blocks: ```gherkin ... ```
3. Unfenced Gherkin: ``**Scenario:** ... Given ... When ... Then ...``

Lines that don't match any Gherkin structure are preserved as criteria with
scenario=line and empty given/when/then fields.

Uses string methods (startswith, split) instead of regex for robustness.
"""

from haytham.workflow.contracts.execution_contract import AcceptanceCriterion


def _strip_checkbox_prefix(line: str) -> str | None:
    """Strip ``- [ ] `` or ``- [x] `` prefix, return remainder or None."""
    if not line.startswith("- ["):
        return None
    # Expect "- [ ] " or "- [x] "
    bracket_end = line.find("]", 3)
    if bracket_end == -1:
        return None
    return line[bracket_end + 1 :].strip()


def _is_fence(line: str) -> bool:
    """Check if a line is a fenced code block delimiter (``` or ```gherkin)."""
    if not line.startswith("```"):
        return False
    after = line[3:].strip().lower()
    return after in ("", "gherkin")


def _strip_keyword(line: str, keyword: str) -> str | None:
    """If line starts with keyword (case-insensitive), return the rest."""
    lower = line.lower()
    if not lower.startswith(keyword):
        return None
    rest = line[len(keyword) :].strip()
    return rest if rest else None


def _strip_scenario_prefix(line: str) -> str | None:
    """Extract scenario name from ``Scenario: X`` or ``**Scenario:** X``."""
    cleaned = line.replace("*", "")
    return _strip_keyword(cleaned, "scenario:")


def _parse_checkbox_gwt(text: str) -> dict[str, str] | None:
    """Parse ``Given X, When Y, Then Z`` from a checkbox remainder."""
    lower = text.lower()
    given_idx = lower.find("given ")
    when_idx = lower.find("when ")
    then_idx = lower.find("then ")

    if given_idx == -1 or when_idx == -1 or then_idx == -1:
        return None
    if not (given_idx < when_idx < then_idx):
        return None

    given = text[given_idx + 6 : when_idx].strip().rstrip(",")
    when = text[when_idx + 5 : then_idx].strip().rstrip(",")
    then = text[then_idx + 5 :].strip()

    return {
        "scenario": f"Given {given}",
        "given": given,
        "when": when,
        "then": then,
    }


def parse_acceptance_criteria(content: str) -> list[AcceptanceCriterion]:
    """Extract acceptance criteria from story content.

    Returns a list of AcceptanceCriterion with sequential IDs (AC-001, etc.).
    """
    if not content or not content.strip():
        return []

    raw_criteria: list[dict[str, str]] = []
    lines = content.splitlines()

    in_fence = False
    current: dict[str, str] | None = None

    for line in lines:
        stripped = line.strip()

        # Track fenced block boundaries
        if _is_fence(stripped):
            if in_fence:
                if current:
                    raw_criteria.append(current)
                    current = None
                in_fence = False
            else:
                in_fence = True
            continue

        if not stripped:
            continue

        # Format 1: Checkbox with Given/When/Then
        checkbox_body = _strip_checkbox_prefix(stripped)
        if checkbox_body:
            gwt = _parse_checkbox_gwt(checkbox_body)
            if gwt:
                raw_criteria.append(gwt)
                continue

        # Format 2 & 3: Gherkin keywords (inside or outside fences)
        scenario_name = _strip_scenario_prefix(stripped)
        if scenario_name is not None:
            if current:
                raw_criteria.append(current)
            current = {
                "scenario": scenario_name,
                "given": "",
                "when": "",
                "then": "",
            }
            continue

        given = _strip_keyword(stripped, "given ")
        if given is not None:
            if current is None:
                current = {"scenario": "", "given": "", "when": "", "then": ""}
            current["given"] = given
            if not current["scenario"]:
                current["scenario"] = f"Given {given}"
            continue

        when = _strip_keyword(stripped, "when ")
        if when is not None and current is not None:
            current["when"] = when
            continue

        then = _strip_keyword(stripped, "then ")
        if then is not None and current is not None:
            current["then"] = then
            continue

    # Flush any remaining criterion
    if current:
        raw_criteria.append(current)

    return [
        AcceptanceCriterion(id=f"AC-{i + 1:03d}", **crit) for i, crit in enumerate(raw_criteria)
    ]
