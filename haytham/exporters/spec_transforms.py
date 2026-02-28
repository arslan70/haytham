"""Shared transformation utilities for project-level exporters.

All transformations are deterministic (no LLM calls). Used by both
OpenSpec and Spec Kit exporters.
"""

import re
from collections import defaultdict

from haytham.exporters.project_model import ExportableCapability
from haytham.workflow.contracts.execution_contract import AcceptanceCriterion, ContractStory

_SLUGIFY_RE = re.compile(r"[^a-z0-9]+")

# Verb endings where the third-person-singular is formed by adding -es after
# a sibilant consonant cluster. Stripping -es recovers the infinitive.
_SIBILANT_ENDINGS = ("sses", "shes", "ches", "xes", "zes")

_TRAIT_ARTICLE_MAP = {
    "interface": "Interface Principle",
    "authentication": "Security Principle",
    "deployment": "Infrastructure Principle",
    "data_layer": "Data Principle",
    "realtime": "Communication Principle",
    "communication": "Messaging Principle",
    "payments": "Commerce Principle",
    "scheduling": "Scheduling Principle",
}


def slugify(name: str) -> str:
    """Convert a human-readable name to a URL-safe slug.

    Example: "User Authentication" -> "user-authentication"
    """
    return _SLUGIFY_RE.sub("-", name.lower()).strip("-")


def _to_bare_infinitive(word: str) -> str:
    """Convert a third-person-singular English verb to its bare infinitive.

    Handles the standard English conjugation rules in reverse:
    - ``-ies`` → ``-y``  (identifies → identify)
    - sibilant + ``-es`` → strip ``-es``  (processes → process, pushes → push)
    - ``-s`` → strip ``-s``  (ensures → ensure, maintains → maintain)

    Words of 3 characters or fewer, and words ending in ``-ss`` or ``-us``,
    are returned unchanged to avoid false positives (access, process, focus).
    """
    if len(word) <= 3 or not word.endswith("s"):
        return word
    # -ies → -y (identifies → identify, notifies → notify)
    if word.endswith("ies") and len(word) > 4:
        return word[:-3] + "y"
    # sibilant + es (processes, pushes, matches, fixes, buzzes)
    for ending in _SIBILANT_ENDINGS:
        if word.endswith(ending):
            return word[:-2]
    # Words ending in -ss or -us are typically not conjugated verbs
    # (access, process, express, focus, bonus, status)
    if word.endswith("ss") or word.endswith("us"):
        return word
    return word[:-1]


def capability_to_shall_statement(cap: ExportableCapability) -> str:
    """Convert a capability description to a formal SHALL statement.

    Lowercases and deconjugates the leading verb so that descriptions like
    "Ensures secure communication" become "The system SHALL ensure secure
    communication" (bare infinitive after SHALL).

    Returns a placeholder statement when the description is empty.
    """
    desc = cap.description
    if not desc:
        return f"The system SHALL provide {cap.name}."
    if desc[0].isupper():
        desc = desc[0].lower() + desc[1:]
    # Deconjugate the leading verb: "ensures X" → "ensure X"
    first_space = desc.find(" ")
    if first_space > 0:
        first_word = desc[:first_space]
        rest = desc[first_space:]
        desc = _to_bare_infinitive(first_word) + rest
    else:
        desc = _to_bare_infinitive(desc)
    if not desc.endswith((".", "!", "?")):
        desc += "."
    return f"The system SHALL {desc}"


def render_gherkin_scenario(ac: AcceptanceCriterion, *, bold_keywords: bool = True) -> list[str]:
    """Render a single acceptance criterion as Gherkin-style lines.

    Args:
        ac: The acceptance criterion to render.
        bold_keywords: If True, wrap Given/When/Then in **bold** (OpenSpec style).
            If False, render plain text (Spec Kit style).

    Returns:
        List of markdown lines (without trailing blank line).
    """
    lines: list[str] = []
    if bold_keywords:
        if ac.given:
            lines.append(f"- **Given** {ac.given}")
        if ac.when:
            lines.append(f"- **When** {ac.when}")
        if ac.then:
            lines.append(f"- **Then** {ac.then}")
    else:
        if ac.given:
            lines.append(f"- Given {ac.given}")
        if ac.when:
            lines.append(f"- When {ac.when}")
        if ac.then:
            lines.append(f"- Then {ac.then}")
    return lines


def group_stories_by_layer(stories: list[ContractStory]) -> dict[int, list[ContractStory]]:
    """Group stories into layer buckets.

    Returns a regular dict keyed by layer number.
    """
    groups: dict[int, list[ContractStory]] = defaultdict(list)
    for story in stories:
        groups[story.layer].append(story)
    return dict(groups)


def traits_to_constitution_articles(traits: dict) -> str:
    """Map system traits to constitution-style principle articles.

    Keys ending with ``_explanation`` are used as sub-text for their parent
    trait and are not rendered as standalone articles. Unknown keys that do
    not appear in the trait-article mapping are silently skipped.
    """
    lines: list[str] = []
    article_num = 0

    for key, value in traits.items():
        if key.endswith("_explanation"):
            continue
        title = _TRAIT_ARTICLE_MAP.get(key)
        if title is None:
            continue

        article_num += 1
        key_title = key.replace("_", " ").title()
        explanation = traits.get(f"{key}_explanation")

        lines.append(f"### Article {article_num}: {title}")
        lines.append("")
        if explanation:
            lines.append(f"**{key_title}:** {value}")
            lines.append(f"  {explanation}")
        else:
            lines.append(f"**{key_title}:** {value}")
        lines.append("")

    return "\n".join(lines)


def strip_wrapping_fences(content: str) -> str:
    """Strip an outer code fence wrapper if the content is entirely enclosed.

    Handles ``markdown``, ``gherkin``, and bare fence markers. Preserves
    content that contains internal fences but isn't fully wrapped.
    """
    if not content:
        return content
    lines = content.strip().splitlines()
    if len(lines) < 2:
        return content
    if lines[0].strip().startswith("```") and lines[-1].strip() == "```":
        return "\n".join(lines[1:-1])
    return content
