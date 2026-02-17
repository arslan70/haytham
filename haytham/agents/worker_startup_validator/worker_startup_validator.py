"""Startup Validator Agent (MVP Mode - Phase 6)

This agent validates the user's startup by combining claims extraction,
three-track validation, and risk assessment into a single agent for
streamlined MVP mode execution.

It performs all three functions:
1. Extract 10-20 key claims about the user's startup from upstream outputs
2. Validate claims using three tracks (evidence quality, internal consistency, assumption identification)
3. Assess risks based on validation labels

CRITICAL: Validates user's startup against research evidence, NOT against requirements.md.
"""

import logging

from strands import Agent
from strands_tools import file_read, file_write

from haytham.agents.utils.prompt_loader import load_agent_prompt

# Configure module logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def create_startup_validator_agent(model_id: str | None = None) -> Agent:
    """
    Create the Startup Validator Agent for MVP Mode Phase 6.

    This agent combines three functions in one execution:
    1. Claims Extraction: Extract 10-20 key claims about user's startup from upstream outputs
    2. Three-Track Validation: Validate claims using:
       - Track 1: Evidence Quality Track (validate against research from phases 1-5)
       - Track 2: Internal Consistency Checker
       - Track 3: Assumption Identification Track
    3. Risk Assessment: Map validation labels to risks with mitigation strategies

    Key differences from Full Mode:
    - Extracts 10-20 key claims (vs 50-100 in full mode)
    - Single agent execution (vs 3 sequential agents)
    - Same validation logic as full mode (three-track approach)
    - Produces single validation_report.json

    Provisioned tools:
    - file_read: Available but not needed (context provided in query)
    - file_write: Write validation_report.json

    CRITICAL: Validates user's startup against research evidence, NOT requirements.md

    Args:
        model_id: Optional Bedrock model ID. If not provided, uses environment config.

    Returns:
        Agent object configured for startup validation

    Raises:
        PromptLoadError: If the prompt file cannot be loaded
        ValueError: If model_id is not provided and tier env var is not set
    """
    from haytham.agents.utils.model_provider import create_model, get_model_id_for_tier

    if model_id is None:
        model_id = get_model_id_for_tier("reasoning")

    # Load prompt from file
    system_prompt = load_agent_prompt("worker_startup_validator")

    # Provision tools: file_read, file_write
    # Note: file_read available but not needed (context provided in query)
    tools = [file_read, file_write]

    logger.info("Creating startup_validator_agent with file tools")

    # Create agent — must pass a Model instance, not a string model_id
    model = create_model(model_id=model_id)

    agent = Agent(
        system_prompt=system_prompt,
        name="startup_validator_agent",
        model=model,
        tools=tools,
    )

    logger.info(
        f"Created startup_validator_agent with model {model_id}, "
        f"tools: {[t.__name__ if hasattr(t, '__name__') else str(t) for t in tools]}"
    )

    return agent
