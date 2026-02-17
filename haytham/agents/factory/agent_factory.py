"""
Agent factory for creating specialist Agent objects for swarm orchestration.

This module provides a config-driven factory for creating Agent objects.
Agent configurations are centralized in haytham/config.py.

Refactored Design:
- All agent configs defined declaratively in AGENT_CONFIGS
- Single generic factory function handles all agent creation
- Backward-compatible individual factory functions maintained for API stability
- OpenTelemetry tracing via Strands telemetry (trace_attributes)
"""

import importlib
import logging
from dataclasses import replace
from typing import Any

from strands import Agent

from haytham.agents.hooks import HaythamAgentHooks
from haytham.agents.utils.model_provider import (
    create_model,
    create_model_for_file_operations,
    get_model_id_for_tier,
)
from haytham.agents.utils.prompt_loader import load_agent_prompt
from haytham.config import (
    AGENT_CONFIGS,
    AgentConfig,
    get_tools_for_profile,
)

# Configure module logger
logger = logging.getLogger(__name__)


def get_bedrock_model_id() -> str:
    """
    Get the Bedrock model ID from environment configuration.

    Returns the LIGHT tier model ID. Callers that need a specific tier
    should use get_model_id_for_tier() directly.

    Returns:
        Bedrock model ID string

    Raises:
        ValueError: If no model ID can be resolved.
    """
    return get_model_id_for_tier("light")


def _create_agent_from_config(
    config: AgentConfig,
    model_id: str | None = None,
    trace_attributes: dict[str, Any] | None = None,
) -> Agent:
    """
    Create an agent from an AgentConfig object.

    This is the core factory function that all agent creation goes through.

    Args:
        config: AgentConfig defining the agent's settings
        model_id: Optional Bedrock model ID override
        trace_attributes: Optional attributes for OpenTelemetry tracing.
            These are passed to Strands Agent and appear in all spans
            created by this agent (agent, LLM, tool spans).

    Returns:
        Configured Agent instance

    Raises:
        PromptLoadError: If the prompt file cannot be loaded
        ValueError: If model_id is not provided and tier env var is not set
    """
    # Resolve model_id: use tier routing when no explicit override
    if model_id is None:
        model_id = get_model_id_for_tier(config.model_tier.value)

    # Get system prompt
    if config.custom_system_prompt:
        system_prompt = config.custom_system_prompt
    else:
        system_prompt = load_agent_prompt(config.prompt_key)

    # Create the model
    if config.use_file_ops_model:
        model = create_model_for_file_operations(
            model_id=model_id,
            max_tokens=config.max_tokens,
        )
    else:
        model_kwargs = {
            "model_id": model_id,
            "max_tokens": config.max_tokens,
            **config.timeout_config.to_dict(),
        }
        # Override streaming if explicitly set in config
        if config.streaming is not None:
            model_kwargs["streaming"] = config.streaming
        model = create_model(**model_kwargs)

    # Get tools
    tools = get_tools_for_profile(config.tool_profile)

    # Build agent kwargs
    agent_kwargs = {
        "system_prompt": system_prompt,
        "name": config.name,
        "model": model,
        "tools": tools,
        "hooks": [HaythamAgentHooks()],
    }

    # Add structured output model if specified
    if config.structured_output_model:
        agent_kwargs["structured_output_model"] = config.structured_output_model

    # Add trace attributes for OpenTelemetry
    # These appear in Strands' automatic agent/LLM/tool spans
    if trace_attributes:
        agent_kwargs["trace_attributes"] = trace_attributes

    # Create agent
    agent = Agent(**agent_kwargs)

    # Log creation
    tools_str = [t.__name__ for t in tools] if tools else "none"
    logger.info(
        f"Created {config.name} with model_tier={config.model_tier.value}, "
        f"max_tokens={config.max_tokens}, tools={tools_str}"
    )

    return agent


def create_agent_by_name(
    agent_name: str,
    model_id: str | None = None,
    max_tokens_override: int | None = None,
    trace_attributes: dict[str, Any] | None = None,
) -> Agent:
    """
    Create an agent by name using the centralized configuration.

    This is the primary factory method. Individual create_*_agent functions
    are maintained for backward compatibility but all delegate here.

    Args:
        agent_name: Name of the agent to create (e.g., 'concept_expansion')
        model_id: Optional Bedrock model ID. If not provided, uses environment config.
        max_tokens_override: Optional max_tokens override. If provided, uses this instead
            of the configured max_tokens. Useful for revision operations that need more tokens.
        trace_attributes: Optional attributes for OpenTelemetry tracing.
            Common attributes to include:
            - session.id: Workflow session ID
            - stage.slug: Current stage being executed
            - workflow.type: Type of workflow (idea-validation, etc.)

    Returns:
        Agent object for the specified agent

    Raises:
        ValueError: If agent_name is not recognized
        PromptLoadError: If the prompt file cannot be loaded
    """
    config = AGENT_CONFIGS.get(agent_name)
    if config is None:
        raise ValueError(
            f"Unknown agent name: {agent_name}. Available agents: {', '.join(AGENT_CONFIGS.keys())}"
        )

    # Resolve lazy structured output model from import path (OCP: no per-agent if-blocks)
    if config.structured_output_model is None and config.structured_output_model_path:
        module_path, class_name = config.structured_output_model_path.rsplit(":", 1)
        mod = importlib.import_module(module_path)
        config = replace(config, structured_output_model=getattr(mod, class_name))

    # Apply max_tokens override if provided
    if max_tokens_override is not None:
        config = replace(config, max_tokens=max_tokens_override)

    # Build trace attributes with agent name included
    final_trace_attributes = {"agent.name": agent_name}
    if trace_attributes:
        final_trace_attributes.update(trace_attributes)

    return _create_agent_from_config(config, model_id, trace_attributes=final_trace_attributes)
