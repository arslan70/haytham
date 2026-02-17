"""
Prompt loader utility for Haytham agents.

This module provides functionality to load system prompts from existing
worker_*_prompt.txt files with caching and error handling.
"""

import logging
from pathlib import Path

# Configure module logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Global cache for loaded prompts
_prompt_cache: dict[str, str] = {}


class PromptLoadError(Exception):
    """Exception raised when a prompt file cannot be loaded."""

    pass


def load_agent_prompt(agent_name: str, filename: str | None = None, use_cache: bool = True) -> str:
    """
    Load system prompt from existing prompt file.

    This function loads prompts from the worker_*_prompt.txt files in the
    haytham/agents directory structure. It supports caching to avoid
    repeated file reads.

    Args:
        agent_name: Name of the agent (e.g., 'worker_concept_expansion',
                   'concept_expansion', or 'concept_expansion_agent')
        filename: Optional custom filename (e.g., 'story_creator_prompt.txt').
                 If not provided, uses default naming: {agent_name}_prompt.txt
        use_cache: Whether to use cached prompts (default: True)

    Returns:
        System prompt text

    Raises:
        PromptLoadError: If the prompt file cannot be found or read

    Examples:
        >>> prompt = load_agent_prompt('worker_concept_expansion')
        >>> prompt = load_agent_prompt('concept_expansion')
        >>> prompt = load_agent_prompt('worker_story_generator', 'story_creator_prompt.txt')
    """
    # Normalize agent name to worker_* format
    normalized_name = _normalize_agent_name(agent_name)

    # Create cache key that includes filename if custom
    cache_key = f"{normalized_name}:{filename}" if filename else normalized_name

    # Check cache first
    if use_cache and cache_key in _prompt_cache:
        logger.debug(f"Loading prompt for '{cache_key}' from cache")
        return _prompt_cache[cache_key]

    # Construct prompt file path
    prompt_file = _get_prompt_file_path(normalized_name, filename)

    # Load prompt from file
    try:
        prompt_text = prompt_file.read_text(encoding="utf-8")
        logger.info(f"Loaded prompt for '{cache_key}' from {prompt_file}")

        # Cache the prompt
        _prompt_cache[cache_key] = prompt_text

        return prompt_text

    except FileNotFoundError:
        error_msg = f"Prompt file not found for agent '{agent_name}'. Expected file: {prompt_file}"
        logger.error(error_msg)
        raise PromptLoadError(error_msg) from None

    except PermissionError:
        error_msg = (
            f"Permission denied reading prompt file for agent '{agent_name}'. File: {prompt_file}"
        )
        logger.error(error_msg)
        raise PromptLoadError(error_msg) from None

    except Exception as e:
        error_msg = (
            f"Unexpected error loading prompt for agent '{agent_name}': {e}. File: {prompt_file}"
        )
        logger.error(error_msg)
        raise PromptLoadError(error_msg) from e


def _normalize_agent_name(agent_name: str) -> str:
    """
    Normalize agent name to worker_* format.

    Handles various input formats:
    - 'worker_concept_expansion' -> 'worker_concept_expansion'
    - 'concept_expansion' -> 'worker_concept_expansion'
    - 'concept_expansion_agent' -> 'worker_concept_expansion'

    Args:
        agent_name: Agent name in any format

    Returns:
        Normalized agent name in worker_* format
    """
    # Remove '_agent' suffix if present
    if agent_name.endswith("_agent"):
        agent_name = agent_name[:-6]

    # Add 'worker_' prefix if not present
    if not agent_name.startswith("worker_"):
        agent_name = f"worker_{agent_name}"

    return agent_name


def _get_prompt_file_path(normalized_agent_name: str, filename: str | None = None) -> Path:
    """
    Get the path to the prompt file for the given agent.

    Args:
        normalized_agent_name: Agent name in worker_* format
        filename: Optional custom filename. If not provided, uses default naming.

    Returns:
        Path to the prompt file
    """
    # Base agents directory
    agents_dir = Path(__file__).parent.parent

    # Agent-specific directory
    agent_dir = agents_dir / normalized_agent_name

    # Prompt file path - use custom filename if provided
    if filename:
        prompt_file = agent_dir / filename
    else:
        prompt_file = agent_dir / f"{normalized_agent_name}_prompt.txt"

    return prompt_file


def clear_prompt_cache() -> None:
    """
    Clear the prompt cache.

    This is useful for testing or when prompts are updated at runtime.
    """
    global _prompt_cache
    _prompt_cache.clear()
    logger.info("Prompt cache cleared")


def get_cached_prompts() -> dict[str, str]:
    """
    Get a copy of the current prompt cache.

    Returns:
        Dictionary mapping agent names to cached prompts
    """
    return _prompt_cache.copy()


def preload_prompts(agent_names: list[str]) -> dict[str, str]:
    """
    Preload prompts for multiple agents into the cache.

    This is useful for warming up the cache at application startup.

    Args:
        agent_names: List of agent names to preload

    Returns:
        Dictionary mapping agent names to loaded prompts

    Raises:
        PromptLoadError: If any prompt file cannot be loaded
    """
    loaded_prompts = {}

    for agent_name in agent_names:
        try:
            prompt = load_agent_prompt(agent_name, use_cache=False)
            loaded_prompts[agent_name] = prompt
        except PromptLoadError as e:
            logger.warning(f"Failed to preload prompt for '{agent_name}': {e}")
            # Continue loading other prompts
            continue

    logger.info(f"Preloaded {len(loaded_prompts)} prompts into cache")
    return loaded_prompts


# List of all available worker agents
AVAILABLE_AGENTS = [
    "worker_build_buy_advisor",
    "worker_capability_model",
    "worker_competitor_analysis",
    "worker_concept_expansion",
    "worker_idea_discovery",
    "worker_idea_gatekeeper",
    "worker_market_intelligence",
    "worker_mvp_scope",
    "worker_mvp_specification",
    "worker_pivot_strategy",
    "worker_startup_validator",
    "worker_story_generator",
    "worker_validation_scorer",
    "worker_validation_narrator",
]
