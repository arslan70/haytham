"""Revision executor for re-invoking agents with feedback.

This module handles the actual re-execution of agents when user feedback
requires revisions. Agents are invoked with their previous output and
the user's feedback, allowing them to make targeted modifications.

Key Features:
- Agents retain full tool access (web search, etc.) during revision
- Revision prompts guide agents to focus on the feedback
- Cascade prompts help downstream agents stay consistent
- Outputs are saved back to the session, replacing originals
"""

import logging
from collections.abc import Callable
from dataclasses import dataclass

from haytham.agents.factory.agent_factory import create_agent_by_name
from haytham.session.session_manager import SessionManager
from haytham.workflow.stage_registry import get_stage_registry

logger = logging.getLogger(__name__)


# Mapping from stage slug to the agent(s) responsible for that stage
# This maps to the agent_names in StageMetadata but provides a direct lookup
STAGE_AGENT_MAP: dict[str, list[str]] = {
    # Idea Validation workflow
    "idea-analysis": ["concept_expansion"],
    "market-context": ["market_intelligence", "competitor_analysis"],
    "risk-assessment": ["startup_validator"],
    "pivot-strategy": ["pivot_strategy"],
    "validation-summary": ["validation_scorer", "validation_narrator"],
    # MVP Specification workflow
    "mvp-scope": ["mvp_scope"],
    "capability-model": ["capability_model"],
    # Story Generation workflow (future)
    "story-generation": ["story_generator"],
}


# Prompt template for direct feedback revision
REVISION_PROMPT_TEMPLATE = """Please revise your previous output based on user feedback.

## User Feedback:
{feedback}

## Your Previous Output:
{previous_output}

## Original Context:
{original_context}

## Instructions:
1. Carefully consider the user's feedback
2. Revise your output to address the feedback
3. Maintain the same structure and format as before
4. Only change what's necessary to address the feedback
5. If the feedback requests additional research or information (e.g., "research competitor X", "find more examples"), use your available tools to gather that information
6. If the feedback is a simple modification (e.g., "remove feature X", "rename Y to Z"), make the change directly without unnecessary research
7. Stay focused on the feedback - don't expand scope beyond what's requested
"""


# Prompt template for cascade revision (downstream stages)
CASCADE_PROMPT_TEMPLATE = """A previous stage in the workflow was revised based on user feedback.
Please update your output to be consistent with the upstream changes.

## What Changed:
{change_summary}

## Your Previous Output:
{previous_output}

## Updated Upstream Context:
{upstream_context}

## Instructions:
1. Review the upstream changes
2. Update your output to align with the new context
3. Maintain the same structure and format as before
4. If the upstream changes introduce new information that requires research to properly address in your section, use your available tools
5. Keep changes proportional to the upstream changes - don't over-expand scope
"""


@dataclass
class RevisionResult:
    """Result of a stage revision.

    Attributes:
        stage_slug: Stage that was revised
        agent_name: Name of the agent that performed the revision
        output: Revised output content
        success: Whether the revision succeeded
        error: Error message if revision failed
    """

    stage_slug: str
    agent_name: str
    output: str
    success: bool
    error: str | None = None


def execute_revision(
    stage_slug: str,
    feedback: str | None,
    session_manager: SessionManager,
    system_goal: str,
    is_cascade: bool = False,
    upstream_context: str | None = None,
    on_progress: Callable[[str, str], None] | None = None,
) -> RevisionResult:
    """Execute revision on a single stage.

    This invokes the agent(s) responsible for the stage with either:
    - Direct feedback revision (user provided feedback for this stage)
    - Cascade revision (upstream stage was revised, this stage needs updating)

    Agents retain full tool access during revision, allowing them to perform
    additional research if the feedback requests it.

    Args:
        stage_slug: Stage to revise (e.g., "market-context")
        feedback: User's feedback text (None if cascade-only)
        session_manager: Session manager for loading/saving outputs
        system_goal: Original startup idea for context
        is_cascade: True if this is a cascading update (not direct feedback)
        upstream_context: Context from revised upstream stages (for cascade)
        on_progress: Optional callback for progress updates (stage_slug, status)

    Returns:
        RevisionResult with the revised output and status

    Raises:
        ValueError: If no agents are configured for the stage or no previous output exists
    """
    logger.info(f"Executing revision for stage '{stage_slug}' (cascade={is_cascade})")

    if on_progress:
        on_progress(stage_slug, "revising")

    try:
        # Get agent(s) for this stage
        agent_names = _get_agents_for_stage(stage_slug)
        if not agent_names:
            raise ValueError(f"No agents configured for stage: {stage_slug}")

        # Load previous output for the stage
        previous_output = session_manager.load_stage_output(stage_slug)
        if not previous_output:
            # For cascade revisions, skip stages that don't have output yet
            if is_cascade:
                logger.info(f"Skipping cascade revision for '{stage_slug}' - no previous output")
                return RevisionResult(
                    stage_slug=stage_slug,
                    agent_name=agent_names[0] if agent_names else "unknown",
                    output="",
                    success=True,  # Not a failure, just nothing to update
                    error=None,
                )
            raise ValueError(f"No previous output found for stage: {stage_slug}")

        # Build the appropriate prompt
        if is_cascade:
            prompt = CASCADE_PROMPT_TEMPLATE.format(
                change_summary=feedback or "Upstream stages were revised based on user feedback",
                previous_output=previous_output,
                upstream_context=upstream_context or "See revised upstream content above",
            )
        else:
            prompt = REVISION_PROMPT_TEMPLATE.format(
                feedback=feedback,
                previous_output=previous_output,
                original_context=f"Startup Idea: {system_goal}",
            )

        # Execute agent(s) and collect outputs
        # Use higher max_tokens for revisions since they include previous output in prompt
        REVISION_MAX_TOKENS = 4000

        revised_outputs = []
        for agent_name in agent_names:
            logger.info(
                f"Invoking agent '{agent_name}' for revision with max_tokens={REVISION_MAX_TOKENS}"
            )

            agent = create_agent_by_name(agent_name, max_tokens_override=REVISION_MAX_TOKENS)
            result = agent(prompt)

            # Extract the output text
            revised_output = _extract_agent_output(result)
            revised_outputs.append(revised_output)

            # Save the revised output (replaces original)
            _save_revised_output(
                session_manager=session_manager,
                stage_slug=stage_slug,
                agent_name=agent_name,
                output=revised_output,
            )

            logger.info(f"Agent '{agent_name}' revision complete, output saved")

        # Combine outputs if multiple agents
        combined_output = "\n\n".join(revised_outputs)

        if on_progress:
            on_progress(stage_slug, "completed")

        return RevisionResult(
            stage_slug=stage_slug,
            agent_name=agent_names[0],  # Primary agent
            output=combined_output,
            success=True,
        )

    except Exception as e:
        logger.error(f"Error revising stage '{stage_slug}': {e}")

        if on_progress:
            on_progress(stage_slug, "failed")

        return RevisionResult(
            stage_slug=stage_slug,
            agent_name=agent_names[0] if agent_names else "unknown",
            output="",
            success=False,
            error=str(e),
        )


def _get_agents_for_stage(stage_slug: str) -> list[str]:
    """Get the agent name(s) responsible for a stage.

    First checks the hardcoded STAGE_AGENT_MAP, then falls back to
    the StageRegistry metadata.

    Args:
        stage_slug: Stage slug to look up

    Returns:
        List of agent names for the stage
    """
    # Check the hardcoded map first
    if stage_slug in STAGE_AGENT_MAP:
        return STAGE_AGENT_MAP[stage_slug]

    # Fall back to registry
    registry = get_stage_registry()
    stage = registry.get_by_slug_safe(stage_slug)
    if stage and stage.agent_names:
        return stage.agent_names

    logger.warning(f"No agents found for stage '{stage_slug}'")
    return []


def _extract_agent_output(result) -> str:
    """Extract text output from agent execution result.

    Args:
        result: Result from agent() call

    Returns:
        Output text string
    """
    from haytham.agents.output_utils import extract_text_from_result

    return extract_text_from_result(result)


def _save_revised_output(
    session_manager: SessionManager,
    stage_slug: str,
    agent_name: str,
    output: str,
) -> None:
    """Save revised output to the session, replacing the original.

    Args:
        session_manager: Session manager instance
        stage_slug: Stage slug for the output
        agent_name: Name of the agent that produced the output
        output: Revised output content
    """
    # Get the stage directory
    stage_dir = session_manager.session_dir / stage_slug
    if not stage_dir.exists():
        stage_dir.mkdir(parents=True, exist_ok=True)

    # Write the output file (overwrites existing)
    output_file = stage_dir / f"{agent_name}.md"

    # Format with metadata header
    content = f"""## Output

{output}
"""

    output_file.write_text(content)
    logger.debug(f"Saved revised output to {output_file}")


def get_revision_context_for_stage(
    session_manager: SessionManager,
    stage_slug: str,
    revised_stages: list[str],
) -> str:
    """Build context string from revised upstream stages.

    This is used when cascading to provide downstream agents with
    the updated content from upstream stages.

    Args:
        session_manager: Session manager for loading outputs
        stage_slug: Current stage being revised
        revised_stages: List of stages that have been revised (in order)

    Returns:
        Formatted context string with upstream revisions
    """
    registry = get_stage_registry()
    context_parts = []

    for revised_slug in revised_stages:
        # Only include stages that come before the current one
        if revised_slug == stage_slug:
            break

        stage = registry.get_by_slug_safe(revised_slug)
        if not stage:
            continue

        output = session_manager.load_stage_output(revised_slug)
        if output:
            context_parts.append(f"## {stage.display_name}\n\n{output}")

    return "\n\n---\n\n".join(context_parts) if context_parts else ""
