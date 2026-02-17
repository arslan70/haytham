"""Feedback router for determining which stages need revision.

This module provides a lightweight LLM-based router that analyzes user feedback
and determines which stage(s) within the current workflow need to be revised.

The router uses Claude Haiku for fast, cheap routing decisions with structured output.
It only considers stages within the current workflow - no cross-workflow routing.
"""

import json
import logging
from dataclasses import dataclass

from strands import Agent

from haytham.agents.utils.model_provider import create_model
from haytham.workflow.stage_registry import get_stage_registry

logger = logging.getLogger(__name__)


@dataclass
class FeedbackRouteResult:
    """Result of feedback routing.

    Attributes:
        affected_stages: List of stage slugs that need revision (earliest first)
        reasoning: Brief explanation of why these stages were selected
    """

    affected_stages: list[str]
    reasoning: str


# Router prompt template for analyzing feedback
ROUTER_PROMPT = """You are a feedback router for a startup validation system. Your job is to analyze user feedback and determine which stage(s) within the CURRENT WORKFLOW need to be revised.

## Current Workflow: {workflow_type}

## Available Stages (in execution order):
{stage_descriptions}

## Routing Rules:
1. ONLY select stages from the list above - these are the only stages in the current workflow
2. Identify the EARLIEST stage that the feedback directly applies to
3. Use these guidelines for routing:
   - Feedback about the core idea, problem, or value proposition → idea-analysis
   - Feedback about market size, trends, or competitors → market-context
   - Feedback about risks, validation, or viability → risk-assessment
   - Feedback about pivot options or alternatives → pivot-strategy
   - Feedback about the overall validation or summary → validation-summary
   - Feedback about MVP features, scope, or priorities → mvp-scope
   - Feedback about technical capabilities or requirements → capability-model
   - Feedback about user stories or implementation tasks → story-generation
4. If the feedback is unclear or could apply to multiple stages, select the most specific/relevant one
5. You may select multiple stages if the feedback explicitly mentions different aspects

## User Feedback:
{feedback}

Respond with a JSON object containing:
- "affected_stages": List of stage slugs that need revision (earliest first)
- "reasoning": Brief explanation (1-2 sentences) of why these stages were selected

Example response:
{{"affected_stages": ["market-context"], "reasoning": "The feedback requests additional competitor analysis, which is handled in the market-context stage."}}
"""


def route_feedback(
    feedback: str,
    workflow_type: str,
    available_stages: list[str],
) -> FeedbackRouteResult:
    """Route user feedback to appropriate stage(s) within the current workflow.

    Uses a lightweight LLM call to analyze the feedback and determine which
    stages need revision. Only stages within the current workflow are considered.

    Args:
        feedback: User's feedback text
        workflow_type: Type of workflow (e.g., "idea-validation", "mvp-specification")
        available_stages: List of stage slugs in the current workflow (ordered)

    Returns:
        FeedbackRouteResult with affected stages and reasoning

    Example:
        >>> result = route_feedback(
        ...     feedback="Add payment processing to the MVP features",
        ...     workflow_type="mvp-specification",
        ...     available_stages=["mvp-scope", "capability-model"],
        ... )
        >>> print(result.affected_stages)
        ['mvp-scope']
    """
    logger.info(f"Routing feedback for workflow '{workflow_type}': {feedback[:100]}...")

    # Build stage descriptions for the prompt
    stage_descriptions = _get_stage_descriptions(available_stages)

    # Format the router prompt
    prompt = ROUTER_PROMPT.format(
        workflow_type=workflow_type,
        stage_descriptions=stage_descriptions,
        feedback=feedback,
    )

    try:
        # Create a lightweight model for routing (use Haiku for speed/cost)
        # Fall back to the default model if Haiku isn't available
        model = create_model(
            max_tokens=500,
            streaming=False,  # No streaming for simple routing
            temperature=0.0,  # Deterministic routing
        )

        # Create a simple agent for the routing task
        router_agent = Agent(
            system_prompt="You are a routing assistant. Analyze feedback and return JSON.",
            model=model,
            tools=[],  # No tools needed for routing
        )

        # Get the routing decision
        result = router_agent(prompt)

        # Extract the response text
        response_text = _extract_response_text(result)

        # Parse the JSON response
        route_result = _parse_router_response(response_text, available_stages)

        logger.info(
            f"Routed feedback to stages: {route_result.affected_stages} "
            f"(reason: {route_result.reasoning})"
        )

        return route_result

    except Exception as e:
        logger.error(f"Error routing feedback: {e}")
        # Fall back to routing to the last stage in the workflow
        fallback_stage = available_stages[-1] if available_stages else None
        return FeedbackRouteResult(
            affected_stages=[fallback_stage] if fallback_stage else [],
            reasoning=f"Fallback routing due to error: {str(e)[:100]}",
        )


def _get_stage_descriptions(stage_slugs: list[str]) -> str:
    """Build formatted stage descriptions for the router prompt.

    Args:
        stage_slugs: List of stage slugs to describe

    Returns:
        Formatted string with stage descriptions
    """
    registry = get_stage_registry()
    descriptions = []

    for slug in stage_slugs:
        stage = registry.get_by_slug_safe(slug)
        if stage:
            # Truncate description to keep prompt concise
            desc = (
                stage.description[:150] + "..."
                if len(stage.description) > 150
                else stage.description
            )
            descriptions.append(f"- {slug}: {stage.display_name} - {desc}")
        else:
            descriptions.append(f"- {slug}: (unknown stage)")

    return "\n".join(descriptions)


def _extract_response_text(result) -> str:
    """Extract text from agent result.

    Args:
        result: Agent execution result

    Returns:
        Response text string
    """
    from haytham.agents.output_utils import extract_text_from_result

    return extract_text_from_result(result)


def _parse_router_response(
    response_text: str,
    available_stages: list[str],
) -> FeedbackRouteResult:
    """Parse the router's JSON response.

    Args:
        response_text: Raw response text from the router
        available_stages: List of valid stage slugs

    Returns:
        Parsed FeedbackRouteResult
    """
    # Try to extract JSON from the response
    try:
        # Look for JSON in the response (might be wrapped in markdown code blocks)
        json_str = response_text
        if "```json" in response_text:
            json_str = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            json_str = response_text.split("```")[1].split("```")[0].strip()

        # Try to find JSON object in the text
        start_idx = json_str.find("{")
        end_idx = json_str.rfind("}") + 1
        if start_idx != -1 and end_idx > start_idx:
            json_str = json_str[start_idx:end_idx]

        data = json.loads(json_str)

        # Extract and validate affected stages
        affected_stages = data.get("affected_stages", [])
        if isinstance(affected_stages, str):
            affected_stages = [affected_stages]

        # Filter to only valid stages in the current workflow
        valid_stages = [s for s in affected_stages if s in available_stages]

        # Get reasoning
        reasoning = data.get("reasoning", "No reasoning provided")

        # If no valid stages found, default to last stage
        if not valid_stages and available_stages:
            valid_stages = [available_stages[-1]]
            reasoning = f"Defaulted to last stage. Original reasoning: {reasoning}"

        return FeedbackRouteResult(
            affected_stages=valid_stages,
            reasoning=reasoning,
        )

    except (json.JSONDecodeError, KeyError, IndexError) as e:
        logger.warning(f"Failed to parse router response: {e}. Response: {response_text[:200]}")
        # Default to last stage if parsing fails
        fallback_stage = available_stages[-1] if available_stages else None
        return FeedbackRouteResult(
            affected_stages=[fallback_stage] if fallback_stage else [],
            reasoning="Failed to parse response, defaulting to last stage",
        )
