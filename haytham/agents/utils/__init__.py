"""
Utilities package for Haytham agents.

This package provides shared utilities including:
- logging_utils: Comprehensive logging infrastructure for agent interactions
- phase_logger: Phase-level logging for phased workflow execution
- prompt_loader: Utility for loading agent system prompts with caching
"""

# Import logging utilities
from haytham.agents.utils.logging_utils import (
    AgentLogger,
    LogEntry,
    SessionManager,
    create_agent_logger,
    estimate_tokens,
    get_session_manager,
)

# Import phase logging utilities
from haytham.agents.utils.phase_logger import (
    PhaseLogEntry,
    PhaseLogger,
    get_phase_logger,
)

# Import prompt loader utilities
from haytham.agents.utils.prompt_loader import (
    AVAILABLE_AGENTS,
    PromptLoadError,
    clear_prompt_cache,
    get_cached_prompts,
    load_agent_prompt,
    preload_prompts,
)

__all__ = [
    # Logging utilities
    "SessionManager",
    "AgentLogger",
    "LogEntry",
    "estimate_tokens",
    "get_session_manager",
    "create_agent_logger",
    # Phase logging utilities
    "PhaseLogger",
    "PhaseLogEntry",
    "get_phase_logger",
    # Prompt loader utilities
    "load_agent_prompt",
    "clear_prompt_cache",
    "get_cached_prompts",
    "preload_prompts",
    "PromptLoadError",
    "AVAILABLE_AGENTS",
]
