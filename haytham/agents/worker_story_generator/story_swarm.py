"""Story Generation - Two-Pass Specification Generator.

Generates implementation-ready specification stories in two passes:
1. Skeleton pass: Plans holistic coverage with lightweight skeletons
2. Detail pass: Layer-specialized agents fill in full content per skeleton

Uses Strands structured_output for the skeleton pass and freeform markdown
for the detail pass. Return type stays tuple[str, list[dict]] — no changes
to stage_executor, Streamlit, or downstream stages.
"""

import json
import logging
import re
from concurrent.futures import ThreadPoolExecutor, as_completed

from strands import Agent

from haytham.agents.utils.model_provider import create_model
from haytham.agents.utils.prompt_loader import load_agent_prompt

from .story_generation_models import (
    StoryGenerationHybridOutput,
    StoryHybrid,
    StorySkeleton,
    StorySkeletonOutput,
)

logger = logging.getLogger(__name__)

# Regex for splitting YAML frontmatter story blocks from markdown output
_STORY_BLOCK_PATTERN = re.compile(r"---\s*\n(id:\s*STORY-\d+.*?)(?=\n---\s*\nid:|$)", re.DOTALL)

# Maps layer number to the detail prompt filename
LAYER_DETAIL_PROMPTS: dict[int, str] = {
    0: "detail_foundation_prompt.txt",
    1: "detail_auth_prompt.txt",
    2: "detail_integration_prompt.txt",
    3: "detail_core_prompt.txt",
    4: "detail_ui_prompt.txt",
    5: "detail_realtime_prompt.txt",
}


def _extract_text(result) -> str:
    """Extract text from agent result."""
    from haytham.agents.output_utils import extract_text_from_result

    return extract_text_from_result(result)


def _build_shared_context(
    system_goal: str,
    mvp_scope: str,
    capability_model: str,
    architecture_decisions: str,
    build_buy_analysis: str,
) -> str:
    """Build the shared context block used by both passes."""
    return f"""## System Goal
{system_goal}

## MVP Scope
{mvp_scope}

## Capability Model
{capability_model}

## Architecture Decisions
{architecture_decisions}

## Build vs Buy Analysis
{build_buy_analysis}"""


def _build_skeleton_summary(skeletons: list[StorySkeleton]) -> str:
    """Build a compact summary of all skeletons for cross-referencing."""
    lines = []
    for s in skeletons:
        implements_str = ", ".join(s.implements) if s.implements else "none"
        depends_str = ", ".join(s.depends_on) if s.depends_on else "none"
        lines.append(
            f"- {s.id} (L{s.layer}): {s.title} | implements: [{implements_str}] | depends: [{depends_str}] | {s.summary}"
        )
    return "\n".join(lines)


def _select_detail_prompt(layer: int) -> str:
    """Select the detail prompt filename for a given layer."""
    filename = LAYER_DETAIL_PROMPTS.get(layer)
    if filename is None:
        # Default to core prompt for unknown layers
        logger.warning(f"No detail prompt for layer {layer}, using core prompt")
        filename = "detail_core_prompt.txt"
    return filename


def _run_skeleton_pass(
    shared_context: str,
    model_id: str,
) -> list[StorySkeleton]:
    """Pass 1: Generate lightweight story skeletons with holistic coverage."""
    skeleton_prompt = load_agent_prompt("worker_story_generator", "story_skeleton_prompt.txt")

    skeleton_agent = Agent(
        name="story_skeleton_planner",
        system_prompt=skeleton_prompt,
        model=create_model(
            model_id=model_id,
            max_tokens=4096,
            read_timeout=300,
            connect_timeout=30,
        ),
        structured_output_model=StorySkeletonOutput,
    )

    task = f"""Plan ALL story skeletons for this MVP. Target 15-25 stories with complete coverage.

{shared_context}

Generate all story skeletons now.
"""

    logger.info("Pass 1: Generating story skeletons...")
    result = skeleton_agent(task)

    # Extract structured output
    if hasattr(result, "structured_output") and isinstance(
        result.structured_output, StorySkeletonOutput
    ):
        skeletons = result.structured_output.stories
        logger.info(f"Pass 1: {len(skeletons)} skeletons generated")
        return skeletons

    # Fallback: try to parse JSON from text
    logger.warning("No structured skeleton output, attempting text extraction")
    text = _extract_text(result)
    try:
        parsed = json.loads(text)
        output = StorySkeletonOutput.model_validate(parsed)
        logger.info(f"Pass 1: Parsed {len(output.stories)} skeletons from text")
        return output.stories
    except (json.JSONDecodeError, Exception) as e:
        logger.error(f"Pass 1 FAILED: Could not parse skeletons: {e}")
        raise RuntimeError(f"Skeleton pass failed: {e}") from e


def _detail_single_story(
    skeleton: StorySkeleton,
    shared_context: str,
    skeleton_summary: str,
    model_id: str,
) -> StoryHybrid:
    """Generate detailed content for a single story skeleton."""
    prompt_filename = _select_detail_prompt(skeleton.layer)
    detail_prompt = load_agent_prompt("worker_story_generator", prompt_filename)

    detail_agent = Agent(
        name=f"story_detail_L{skeleton.layer}",
        system_prompt=detail_prompt,
        model=create_model(
            model_id=model_id,
            max_tokens=4096,
            read_timeout=300,
            connect_timeout=30,
        ),
    )

    implements_str = ", ".join(skeleton.implements) if skeleton.implements else "none"
    depends_str = ", ".join(skeleton.depends_on) if skeleton.depends_on else "none"

    task = f"""Write the detailed content for this story:

## Story Skeleton
- **ID**: {skeleton.id}
- **Title**: {skeleton.title}
- **Layer**: {skeleton.layer}
- **Implements**: [{implements_str}]
- **Depends On**: [{depends_str}]
- **Summary**: {skeleton.summary}

## All Stories (for cross-referencing)
{skeleton_summary}

## Project Context
{shared_context}

Write the full markdown content for {skeleton.id}: {skeleton.title}.
"""

    try:
        result = detail_agent(task)
        content = _extract_text(result)

        if not content or content.strip() == "":
            logger.warning(f"Empty content for {skeleton.id}, using summary as fallback")
            content = f"## Description\n\n{skeleton.summary}"

        return StoryHybrid(
            id=skeleton.id,
            title=skeleton.title,
            layer=skeleton.layer,
            implements=skeleton.implements,
            depends_on=skeleton.depends_on,
            content=content.strip(),
        )
    except Exception as e:
        logger.error(f"Detail agent failed for {skeleton.id}: {e}")
        # Fallback: use skeleton summary as content
        return StoryHybrid(
            id=skeleton.id,
            title=skeleton.title,
            layer=skeleton.layer,
            implements=skeleton.implements,
            depends_on=skeleton.depends_on,
            content=f"## Description\n\n{skeleton.summary}",
        )


def _run_detail_pass(
    skeletons: list[StorySkeleton],
    shared_context: str,
    model_id: str,
) -> list[StoryHybrid]:
    """Pass 2: Generate detailed content for each skeleton in parallel."""
    skeleton_summary = _build_skeleton_summary(skeletons)
    stories: list[StoryHybrid] = []

    logger.info(f"Pass 2: Detailing {len(skeletons)} stories with max_workers=4...")

    with ThreadPoolExecutor(max_workers=4) as executor:
        future_to_skeleton = {
            executor.submit(
                _detail_single_story,
                skeleton,
                shared_context,
                skeleton_summary,
                model_id,
            ): skeleton
            for skeleton in skeletons
        }

        for future in as_completed(future_to_skeleton):
            skeleton = future_to_skeleton[future]
            try:
                story = future.result()
                stories.append(story)
                logger.info(f"Pass 2: Detailed {story.id} ({story.title})")
            except Exception as e:
                logger.error(f"Pass 2: Failed for {skeleton.id}: {e}")
                # Fallback
                stories.append(
                    StoryHybrid(
                        id=skeleton.id,
                        title=skeleton.title,
                        layer=skeleton.layer,
                        implements=skeleton.implements,
                        depends_on=skeleton.depends_on,
                        content=f"## Description\n\n{skeleton.summary}",
                    )
                )

    # Sort by story ID to maintain deterministic order
    stories.sort(key=lambda s: s.id)
    logger.info(f"Pass 2: {len(stories)} stories detailed")
    return stories


def run_story_swarm(
    mvp_scope: str,
    capability_model: str,
    architecture_decisions: str,
    build_buy_analysis: str,
    system_goal: str = "",
    model_id: str | None = None,
) -> tuple[str, list[dict]]:
    """Generate specification stories in two passes: skeleton planning + parallel detail.

    Args:
        mvp_scope: MVP scope definition
        capability_model: Capability model with CAP-F-* and CAP-NF-*
        architecture_decisions: Architecture decisions with DEC-*
        build_buy_analysis: Build vs buy analysis
        system_goal: Original system goal
        model_id: Optional model ID override

    Returns:
        Tuple of (markdown_output, stories_as_dicts):
        - markdown_output: Stories rendered as YAML frontmatter + body for display/session
        - stories_as_dicts: List of story dicts for structured consumption (stories.json)
    """
    from haytham.agents.factory.agent_factory import get_bedrock_model_id

    if model_id is None:
        model_id = get_bedrock_model_id()

    # Build shared context used by both passes
    shared_context = _build_shared_context(
        system_goal=system_goal,
        mvp_scope=mvp_scope,
        capability_model=capability_model,
        architecture_decisions=architecture_decisions,
        build_buy_analysis=build_buy_analysis,
    )

    # Pass 1: Skeleton
    skeletons = _run_skeleton_pass(shared_context, model_id)

    # Pass 2: Detail (parallel)
    stories = _run_detail_pass(skeletons, shared_context, model_id)

    # Assemble output
    output = StoryGenerationHybridOutput(stories=stories)
    return output.to_markdown(), output.to_dicts()


def parse_stories_from_markdown(markdown: str) -> list[dict]:
    """Parse stories from markdown format into structured dicts.

    Legacy function kept for backward compatibility with old sessions
    that don't have stories.json. New sessions use structured output directly.

    Args:
        markdown: Stories in markdown with YAML frontmatter

    Returns:
        List of story dicts with id, title, layer, implements, depends_on, content
    """
    stories = []

    # Split by story boundaries (--- followed by id:)
    matches = _STORY_BLOCK_PATTERN.findall(markdown)

    for match in matches:
        story = {}
        content = match.strip()

        # Extract YAML frontmatter fields
        id_match = re.search(r"^id:\s*(.+)$", content, re.MULTILINE)
        title_match = re.search(r"^title:\s*(.+)$", content, re.MULTILINE)
        layer_match = re.search(r"^layer:\s*(\d+)$", content, re.MULTILINE)
        implements_match = re.search(r"^implements:\s*\[([^\]]*)\]", content, re.MULTILINE)
        depends_match = re.search(r"^depends_on:\s*\[([^\]]*)\]", content, re.MULTILINE)

        if id_match:
            story["id"] = id_match.group(1).strip()
        if title_match:
            story["title"] = title_match.group(1).strip()
        if layer_match:
            story["layer"] = int(layer_match.group(1))
        if implements_match:
            implements_str = implements_match.group(1)
            story["implements"] = [
                x.strip().strip("'\"") for x in implements_str.split(",") if x.strip()
            ]
        if depends_match:
            depends_str = depends_match.group(1)
            story["depends_on"] = [
                x.strip().strip("'\"") for x in depends_str.split(",") if x.strip()
            ]

        # Find where frontmatter ends and content begins
        frontmatter_end = content.find("---", 3)
        if frontmatter_end > 0:
            story["content"] = content[frontmatter_end + 3 :].strip()
        else:
            desc_start = content.find("## Description")
            if desc_start > 0:
                story["content"] = content[desc_start:].strip()
            else:
                story["content"] = content

        if story.get("id"):
            stories.append(story)

    # Fallback: try simpler parsing if no stories found
    if not stories:
        simple_pattern = re.compile(r"###\s*(STORY-\d+):\s*(.+?)(?=###\s*STORY-|$)", re.DOTALL)
        simple_matches = simple_pattern.findall(markdown)

        for story_id, content in simple_matches:
            story = {
                "id": story_id.strip(),
                "title": content.split("\n")[0].strip() if content else "",
                "content": content.strip(),
                "layer": 0,
                "implements": [],
                "depends_on": [],
            }

            layer_match = re.search(r"\*\*Layer:\*\*\s*(\d+)", content)
            if layer_match:
                story["layer"] = int(layer_match.group(1))

            impl_match = re.search(r"\*\*Implements:\*\*\s*([^\n]+)", content)
            if impl_match:
                story["implements"] = [x.strip() for x in impl_match.group(1).split(",")]

            stories.append(story)

    logger.info(f"Parsed {len(stories)} stories from markdown")
    return stories
