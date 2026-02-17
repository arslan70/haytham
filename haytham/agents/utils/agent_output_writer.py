"""
Helper utilities for agents to write their outputs to files.

This module provides a simple decorator and function to automatically
write agent outputs to files for file-based context passing.
"""

import functools
import logging
import os
from collections.abc import Callable

logger = logging.getLogger(__name__)


def write_agent_output_to_file(agent_name: str, output: str) -> None:
    """
    Write an agent's output to a file for file-based context passing.

    This function should be called by each agent after generating its output
    to enable file-based context passing and reduce conversation context.

    Args:
        agent_name: Name of the agent (e.g., "code_analyzer_agent")
        output: The agent's output text
    """
    # Check if file-based context is enabled
    enable_file_context = os.getenv("ENABLE_FILE_CONTEXT", "true").lower() in (
        "true",
        "1",
        "yes",
        "on",
    )

    if not enable_file_context:
        logger.debug(f"File-based context disabled, skipping output write for {agent_name}")
        return

    try:
        from haytham.agents.utils.file_context import get_file_context_manager

        context_manager = get_file_context_manager()
        output_file = context_manager.write_agent_output(agent_name, output)

        logger.info(f"Agent {agent_name} wrote {len(output)} chars to {output_file}")
    except Exception as e:
        # Don't fail the agent if file writing fails
        logger.error(f"Failed to write output for agent {agent_name}: {e}", exc_info=True)


def with_file_output(agent_name: str) -> Callable:
    """
    Decorator to automatically write agent output to a file.

    This decorator wraps an agent tool function and automatically writes
    its output to a file for file-based context passing.

    Args:
        agent_name: Name of the agent (e.g., "code_analyzer_agent")

    Returns:
        Decorator function

    Example:
        @tool
        @with_file_output("code_analyzer_agent")
        def code_analyzer_tool(project_path: str) -> str:
            # ... agent logic ...
            return analysis_result
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Call the original function
            result = func(*args, **kwargs)

            # Write output to file
            if result is not None:
                write_agent_output_to_file(agent_name, str(result))

            return result

        return wrapper

    return decorator
