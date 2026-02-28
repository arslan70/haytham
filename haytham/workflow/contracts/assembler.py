"""Assemble an ExecutionContract from story dicts and session state.

All transformation is deterministic. The LLM output (StoryHybrid) is consumed
as-is; this module only restructures and enriches it for downstream consumers.
"""

import logging
from datetime import UTC, datetime
from typing import Any

from haytham.workflow.contracts.execution_contract import (
    ContractMetadata,
    ContractStory,
    ExecutionContract,
)
from haytham.workflow.contracts.gherkin_parser import parse_acceptance_criteria

logger = logging.getLogger("haytham")


def _parse_traits_from_markdown(markdown: str) -> dict[str, str | list[str]]:
    """Extract system traits from the markdown format stored on disk.

    Handles two writer formats:
    - Plain:  ``**Key:** Value``
    - Bullet: ``- **Key:** Value``  (produced by SystemTraitsOutput.to_markdown)

    Multi-select traits use single brackets: ``[Container, Serverless]``.
    Enum traits may use double brackets: ``[[mobile_native]]``, treated as
    a single value with the brackets stripped.
    """
    traits: dict[str, str | list[str]] = {}
    for line in markdown.splitlines():
        stripped = line.strip()
        # Strip leading bullet marker so both "- **key:**" and "**key:**" work
        if stripped.startswith("- "):
            stripped = stripped[2:]
        if not stripped.startswith("**") or ":**" not in stripped:
            continue

        # Split on the first ":**" to get key and value
        marker_end = stripped.index(":**")
        key = stripped[2:marker_end].strip().lower()
        # Value starts after ":**", skip any trailing bold markers
        raw_value = stripped[marker_end + 3 :].strip().rstrip("*").strip()

        if not key or not raw_value:
            continue

        # Double brackets [[value]]: enum single-value notation
        if raw_value.startswith("[[") and raw_value.endswith("]]"):
            traits[key] = raw_value[2:-2]
        # Single brackets [A, B]: multi-select list
        elif raw_value.startswith("[") and "]" in raw_value:
            bracket_end = raw_value.index("]")
            inner = raw_value[1:bracket_end]
            traits[key] = [v.strip() for v in inner.split(",")]
        else:
            # Strip trailing "(ambiguous)" marker if present
            if raw_value.endswith("(ambiguous)"):
                raw_value = raw_value[: -len("(ambiguous)")].strip()
            traits[key] = raw_value

    return traits


def _split_implements(refs: list[str]) -> tuple[list[str], list[str]]:
    """Split mixed implements list into (capabilities, decisions)."""
    caps = []
    decs = []
    for r in refs:
        if r.startswith(("CAP-F-", "CAP-NF-")):
            caps.append(r)
        elif r.startswith("DEC-"):
            decs.append(r)
        else:
            logger.debug("Unknown reference prefix, excluded from contract: %s", r)
    return caps, decs


_STRUCTURAL_HEADINGS = frozenset(
    {
        "description",
        "details",
        "overview",
        "files to create",
        "acceptance criteria",
        "configuration",
        "required permissions",
    }
)


def _extract_summary(content: str, title: str) -> str:
    """Extract summary from story content.

    Takes the first non-empty, non-structural line, stripping markdown
    heading markers. Skips code fence delimiters and generic headings
    like "Description" or "Files to Create".
    Falls back to title if content is empty or only structural.
    """
    if not content or not content.strip():
        return title
    for line in content.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        # Skip code fence markers
        if stripped.startswith("```"):
            continue
        # Strip heading markers and check for structural headings
        heading_text = stripped.lstrip("#").strip()
        if heading_text.lower() in _STRUCTURAL_HEADINGS:
            continue
        return heading_text
    return title


def assemble_execution_contract(
    stories: list[dict[str, Any]],
    session_manager: Any,
    system_goal: str,
    appetite: str = "",
) -> ExecutionContract:
    """Build an ExecutionContract from story dicts and session state.

    Args:
        stories: List of story dicts (from stories.json / StoryHybrid.model_dump).
        session_manager: Active session manager for loading stage outputs.
        system_goal: The system goal / idea summary string.
        appetite: The appetite/scope constraint string. Passed explicitly by the
            caller to avoid duplicating session_manager.get_system_goal() calls.
    """
    # Load system traits from the markdown on disk
    traits: dict[str, str | list[str]] = {}
    traits_output = session_manager.load_stage_output("system-traits")
    if traits_output:
        traits = _parse_traits_from_markdown(traits_output)

    # Build contract stories
    contract_stories = []
    for story in stories:
        implements_raw = story.get("implements", [])
        caps, decs = _split_implements(implements_raw)
        content = story.get("content", "")
        title = story.get("title", "")

        contract_stories.append(
            ContractStory(
                id=story.get("id", ""),
                title=title,
                layer=story.get("layer", 0),
                summary=_extract_summary(content, title),
                implements=caps,
                uses=decs,
                depends_on=story.get("depends_on", []),
                acceptance_criteria=parse_acceptance_criteria(content),
                content=content,
            )
        )

    return ExecutionContract(
        metadata=ContractMetadata(
            generated_at=datetime.now(UTC).isoformat(),
            idea_summary=system_goal,
            appetite=appetite,
        ),
        system_traits=traits,
        stories=contract_stories,
    )
