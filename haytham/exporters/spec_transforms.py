"""Shared transformation utilities for project-level exporters.

All transformations are deterministic (no LLM calls). Used by both
OpenSpec and Spec Kit exporters.
"""

import re
from collections import defaultdict

from haytham.exporters.project_model import ExportableCapability
from haytham.workflow.contracts.execution_contract import ContractStory

_SLUGIFY_RE = re.compile(r"[^a-z0-9]+")

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


def capability_to_shall_statement(cap: ExportableCapability) -> str:
    """Convert a capability description to a formal SHALL statement.

    Lowercases the first character of the description if it starts uppercase.
    Returns a placeholder statement when the description is empty.
    """
    desc = cap.description
    if not desc:
        return f"The system SHALL provide {cap.name}."
    if desc[0].isupper():
        desc = desc[0].lower() + desc[1:]
    return f"The system SHALL {desc}"


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
