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


# =============================================================================
# Backward-Compatible Factory Functions
# =============================================================================
# These functions maintain the existing API but delegate to create_agent_by_name


def create_concept_expansion_agent(model_id: str | None = None) -> Agent:
    """Create the Concept Expansion Agent."""
    return create_agent_by_name("concept_expansion", model_id)


def create_market_intelligence_agent(model_id: str | None = None) -> Agent:
    """Create the Market Intelligence Agent."""
    return create_agent_by_name("market_intelligence", model_id)


def create_pivot_strategy_agent(model_id: str | None = None) -> Agent:
    """Create the Pivot Strategy Agent."""
    return create_agent_by_name("pivot_strategy", model_id)


def create_validation_scorer_agent(model_id: str | None = None) -> Agent:
    """Create the Validation Scorer Agent."""
    return create_agent_by_name("validation_scorer", model_id)


def create_validation_narrator_agent(model_id: str | None = None) -> Agent:
    """Create the Validation Narrator Agent."""
    return create_agent_by_name("validation_narrator", model_id)


def create_mvp_specification_agent(model_id: str | None = None) -> Agent:
    """Create the MVP Specification Agent."""
    return create_agent_by_name("mvp_specification", model_id)


def create_competitor_analysis_agent(model_id: str | None = None) -> Agent:
    """Create the Competitor Analysis Agent."""
    return create_agent_by_name("competitor_analysis", model_id)


def create_startup_validator_agent(model_id: str | None = None) -> Agent:
    """Create the Startup Validator Agent."""
    return create_agent_by_name("startup_validator", model_id)


def create_mvp_scope_agent(model_id: str | None = None) -> Agent:
    """Create the MVP Scope Agent."""
    return create_agent_by_name("mvp_scope", model_id)


def create_mvp_scope_core_agent(model_id: str | None = None) -> Agent:
    """Create the MVP Scope Core sub-agent (The One Thing, user segment, input method, appetite)."""
    return create_agent_by_name("mvp_scope_core", model_id)


def create_mvp_scope_boundaries_agent(model_id: str | None = None) -> Agent:
    """Create the MVP Scope Boundaries sub-agent (IN/OUT scope, success criteria)."""
    return create_agent_by_name("mvp_scope_boundaries", model_id)


def create_mvp_scope_flows_agent(model_id: str | None = None) -> Agent:
    """Create the MVP Scope Flows sub-agent (user flows, scope metadata)."""
    return create_agent_by_name("mvp_scope_flows", model_id)


def create_capability_model_agent(model_id: str | None = None) -> Agent:
    """Create the Capability Model Agent."""
    return create_agent_by_name("capability_model", model_id)


def create_idea_gatekeeper_agent(model_id: str | None = None) -> Agent:
    """Create the Idea Gatekeeper Agent for input validation."""
    return create_agent_by_name("idea_gatekeeper", model_id)


def create_idea_discovery_agent(model_id: str | None = None) -> Agent:
    """Create the Idea Discovery Agent for Lean Canvas gap analysis."""
    return create_agent_by_name("idea_discovery", model_id)


def create_system_traits_agent(model_id: str | None = None) -> Agent:
    """Create the System Traits Classification Agent."""
    return create_agent_by_name("system_traits", model_id)


def create_build_buy_advisor_agent(model_id: str | None = None) -> Agent:
    """Create the Build vs Buy Advisor Agent (legacy).

    Note: Prefer using create_build_buy_analyzer_agent for new code.
    """
    return create_agent_by_name("build_buy_advisor", model_id)


def create_build_buy_analyzer_agent(model_id: str | None = None) -> Agent:
    """Create the Build vs Buy Analyzer Agent with structured output."""
    return create_agent_by_name("build_buy_analyzer", model_id)


def create_anchor_extractor_agent(model_id: str | None = None) -> Agent:
    """Create the Concept Anchor Extractor Agent (ADR-022).

    This agent extracts a structured anchor from the original idea to prevent
    concept drift across the pipeline. The anchor captures invariants that must
    be preserved by all downstream stages.
    """
    return create_agent_by_name("anchor_extractor", model_id)


def create_phase_verifier_agent(model_id: str | None = None) -> Agent:
    """Create the Phase Verifier Agent (ADR-022).

    This agent independently verifies phase outputs against the concept anchor
    at decision gates. It checks for invariant violations and genericization.
    """
    return create_agent_by_name("phase_verifier", model_id)


# Factory function mapping for dynamic agent creation (backward compatibility)
AGENT_FACTORIES = {
    "concept_expansion": create_concept_expansion_agent,
    "competitor_analysis": create_competitor_analysis_agent,
    "market_intelligence": create_market_intelligence_agent,
    "startup_validator": create_startup_validator_agent,
    "mvp_specification": create_mvp_specification_agent,
    "mvp_scope": create_mvp_scope_agent,
    "mvp_scope_core": create_mvp_scope_core_agent,
    "mvp_scope_boundaries": create_mvp_scope_boundaries_agent,
    "mvp_scope_flows": create_mvp_scope_flows_agent,
    "capability_model": create_capability_model_agent,
    "pivot_strategy": create_pivot_strategy_agent,
    "validation_scorer": create_validation_scorer_agent,
    "validation_narrator": create_validation_narrator_agent,
    "idea_gatekeeper": create_idea_gatekeeper_agent,
    "idea_discovery": create_idea_discovery_agent,
    "system_traits": create_system_traits_agent,
    "build_buy_advisor": create_build_buy_advisor_agent,  # Legacy
    "build_buy_analyzer": create_build_buy_analyzer_agent,
    "anchor_extractor": create_anchor_extractor_agent,
    "phase_verifier": create_phase_verifier_agent,
}
