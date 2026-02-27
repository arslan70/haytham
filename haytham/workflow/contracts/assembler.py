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

    Parses lines matching ``**Key:** Value``. Multi-select traits use
    bracket notation: ``**Deployment:** [Container, Serverless]``.
    """
    traits: dict[str, str | list[str]] = {}
    for line in markdown.splitlines():
        stripped = line.strip()
        if not stripped.startswith("**") or ":**" not in stripped:
            continue

        # Split on the first ":**" to get key and value
        marker_end = stripped.index(":**")
        key = stripped[2:marker_end].strip().lower()
        # Value starts after ":**", skip any trailing bold markers
        raw_value = stripped[marker_end + 3 :].strip().rstrip("*").strip()

        if not key or not raw_value:
            continue

        # Multi-select: [Container, Serverless]
        if raw_value.startswith("[") and "]" in raw_value:
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
    caps = [r for r in refs if r.startswith(("CAP-F-", "CAP-NF-"))]
    decs = [r for r in refs if r.startswith("DEC-")]
    return caps, decs


def _extract_summary(content: str, title: str) -> str:
    """Extract summary from story content.

    Takes the first non-empty line, stripping markdown heading markers.
    Falls back to title if content is empty.
    """
    if not content or not content.strip():
        return title
    for line in content.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped.lstrip("#").strip()
    return title


def assemble_execution_contract(
    stories: list[dict[str, Any]],
    session_manager: Any,
    system_goal: str,
) -> ExecutionContract:
    """Build an ExecutionContract from story dicts and session state.

    Args:
        stories: List of story dicts (from stories.json / StoryHybrid.model_dump).
        session_manager: Active session manager for loading stage outputs.
        system_goal: The system goal / idea summary string.
    """
    # Load system traits from the markdown on disk
    traits: dict[str, str | list[str]] = {}
    traits_output = session_manager.load_stage_output("system-traits")
    if traits_output:
        traits = _parse_traits_from_markdown(traits_output)

    # Load appetite from session
    appetite = ""
    try:
        appetite = session_manager.get_system_goal() or ""
    except (AttributeError, TypeError):
        pass

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
