"""Agent execution helpers extracted from burr_actions.py.

This module contains the core agent-running functions that both
``burr_actions`` and ``stage_executor`` depend on. By living in its
own module it breaks the circular dependency that previously required
lazy imports inside function bodies in stage_executor.py.

Functions:
    run_agent          -- Execute a single agent via the agent factory.
    run_parallel_agents -- Execute multiple agents concurrently.
    save_stage_output  -- Persist agent output to the session directory.
    _is_token_limit_error -- Classify Bedrock token-limit exceptions.
    _get_user_friendly_error -- Map exceptions to user-facing messages.
"""

import concurrent.futures
import logging
import time
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger(__name__)


# =============================================================================
# Error Handling Helpers
# =============================================================================


def _is_token_limit_error(error: Exception) -> bool:
    """Check if an error is a token limit error from Bedrock.

    Args:
        error: The exception to check

    Returns:
        True if this is a token limit error
    """
    error_str = str(error).lower()

    # Check for common token limit indicators from AWS Bedrock
    token_limit_indicators = [
        "token",
        "maxtoken",
        "max_token",
        "context length",
        "too long",
        "exceeds the max",
        "input is too long",
        "validationexception",
        "input too large",
    ]

    return any(indicator in error_str for indicator in token_limit_indicators)


_TRANSIENT_INDICATORS = [
    "response ended prematurely",
    "connection reset",
    "connection aborted",
    "broken pipe",
    "timed out",
    "read timed out",
    "network is unreachable",
    "internal server error",
]

_MAX_RETRIES = 2
_RETRY_DELAY_SECONDS = 5


def _is_transient_error(error: Exception) -> bool:
    """Check if an error is a transient network error worth retrying.

    Walks the full exception chain (__cause__) to catch errors wrapped
    by the Strands SDK's EventLoopException.

    Args:
        error: The exception to check.

    Returns:
        True if this looks like a transient network/server error.
    """
    parts = [str(error).lower()]
    cause = error.__cause__
    while cause:
        parts.append(str(cause).lower())
        cause = cause.__cause__
    combined = " ".join(parts)
    return any(indicator in combined for indicator in _TRANSIENT_INDICATORS)


def _get_user_friendly_error(error: Exception, agent_name: str) -> str:
    """Get a user-friendly error message for display.

    Args:
        error: The exception that occurred
        agent_name: Name of the agent that failed

    Returns:
        User-friendly error message
    """
    if _is_token_limit_error(error):
        return (
            f"Token limit exceeded in {agent_name}. "
            "Your idea description may be too long. Try shortening it, "
            "or reduce the DEFAULT_MAX_TOKENS setting in .env if outputs are being truncated."
        )

    # For other errors, return the original message
    return str(error)


# =============================================================================
# Agent Execution Helpers
# =============================================================================


def run_agent(
    agent_name: str,
    query: str,
    context: dict[str, Any],
    session_manager: Any = None,
    use_context_tools: bool = False,
    trace_attributes: dict[str, Any] | None = None,
    output_as_json: bool = False,
) -> dict[str, Any]:
    """Execute an agent using the existing agent factory.

    Timing, lifecycle logging, and OTEL span annotation are handled by
    HaythamAgentHooks (registered on every agent via agent_factory.py).
    This function focuses on context building, output extraction, and
    error classification.

    Args:
        agent_name: Name of the agent to run (e.g., "concept_expansion")
        query: Query string for the agent
        context: Context dict with previous stage outputs
        session_manager: Optional SessionManager for file operations
        use_context_tools: If True, set up context store for context retrieval tools
                          instead of pre-building context summary
        trace_attributes: Optional attributes for OpenTelemetry tracing
        output_as_json: If True, return JSON from Pydantic structured outputs
                       instead of rendering markdown

    Returns:
        Dict with agent output and metadata
    """
    # Lazy import: avoids circular dep (context_builder → stage_registry → ... → agent_runner)
    from .context_builder import build_context_summary

    start_time = time.time()

    try:
        # Lazy import: workflow/ → agents/ would create circular dep at module level
        from haytham.agents.factory.agent_factory import create_agent_by_name

        agent = create_agent_by_name(agent_name, trace_attributes=trace_attributes)

        if agent is None:
            raise ValueError(f"Agent factory returned None for {agent_name}")

        # Build full query
        full_query = query

        if use_context_tools:
            # Lazy import: workflow/ → agents/ would create circular dep at module level
            from haytham.agents.tools.context_retrieval import (
                clear_context_store,
                set_context_store,
            )

            set_context_store(context)
            full_query += "\n\nUse the context retrieval tools to access relevant information from previous stages."
        else:
            context_summary = build_context_summary(context)
            if context_summary:
                full_query += f"\n\n## Context from Previous Stages:\n{context_summary}"

        logger.info(f"Running agent {agent_name} with query length: {len(full_query)}")

        try:
            # Retry loop for transient network errors (e.g. Bedrock stream drops).
            # Boto3 retries don't cover mid-stream failures when streaming=True.
            for attempt in range(_MAX_RETRIES + 1):
                try:
                    result = agent(full_query)
                    break
                except Exception as e:
                    if (
                        attempt < _MAX_RETRIES
                        and _is_transient_error(e)
                        and not _is_token_limit_error(e)
                    ):
                        logger.warning(
                            "Agent %s transient error (attempt %d/%d): %s. Retrying in %ds...",
                            agent_name,
                            attempt + 1,
                            _MAX_RETRIES + 1,
                            e,
                            _RETRY_DELAY_SECONDS,
                        )
                        time.sleep(_RETRY_DELAY_SECONDS)
                        continue
                    raise

            # Lazy import: workflow/ → agents/ would create circular dep at module level
            from haytham.agents.output_utils import extract_text_from_result

            output_text = extract_text_from_result(result, output_as_json=output_as_json)
            execution_time = time.time() - start_time

            if not output_text or not output_text.strip():
                logger.error(f"Agent {agent_name} returned empty output")
                return {
                    "output": f"Error: Agent {agent_name} produced no output. This may indicate a structured output parsing failure or token limit issue.",
                    "agent_name": agent_name,
                    "status": "failed",
                    "error": "Empty output",
                    "execution_time": execution_time,
                }

            return {
                "output": output_text,
                "agent_name": agent_name,
                "status": "completed",
                "execution_time": execution_time,
            }
        finally:
            if use_context_tools:
                clear_context_store()

    except Exception as e:
        execution_time = time.time() - start_time
        user_error = _get_user_friendly_error(e, agent_name)
        is_token_error = _is_token_limit_error(e)

        # Classify and log — HaythamAgentHooks handles generic lifecycle logging,
        # but error classification is business logic that stays here.
        if is_token_error:
            logger.error(
                f"Agent {agent_name} token limit error: {e}",
                extra={"agent": agent_name, "error_type": "token_limit"},
            )
        else:
            logger.error(
                f"Agent {agent_name} failed: {e}",
                exc_info=True,
                extra={"agent": agent_name, "error_type": type(e).__name__},
            )

        return {
            "output": f"Error executing {agent_name}: {user_error}",
            "agent_name": agent_name,
            "status": "failed",
            "error": user_error,
            "error_type": "token_limit" if is_token_error else type(e).__name__,
            "original_error": str(e),
            "execution_time": execution_time,
        }


def run_parallel_agents(
    agent_configs: list[dict[str, str]],
    context: dict[str, Any],
    session_manager: Any = None,
    use_context_tools: bool = False,
) -> dict[str, Any]:
    """Execute multiple agents in parallel.

    Args:
        agent_configs: List of dicts with 'name' and 'query' keys
        context: Shared context for all agents
        session_manager: Optional SessionManager for file operations
        use_context_tools: If True, set up context store for context retrieval tools

    Returns:
        Dict mapping agent_name -> result
    """

    # Snapshot context to prevent race conditions if callers mutate it later.
    # Each thread gets the same frozen view (read-only by convention).
    frozen_context = context.copy()

    def run_single(config):
        return run_agent(
            agent_name=config["name"],
            query=config["query"],
            context=frozen_context,
            session_manager=session_manager,
            use_context_tools=use_context_tools,
        )

    results = {}

    try:
        # Use ThreadPoolExecutor for parallel execution
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            futures = {
                executor.submit(run_single, config): config["name"] for config in agent_configs
            }

            for future in concurrent.futures.as_completed(futures):
                agent_name = futures[future]
                try:
                    results[agent_name] = future.result()
                except Exception as e:
                    user_error = _get_user_friendly_error(e, agent_name)
                    is_token_error = _is_token_limit_error(e)
                    logger.error(
                        f"Parallel agent {agent_name} failed: {e}",
                        extra={
                            "agent": agent_name,
                            "error_type": "token_limit" if is_token_error else type(e).__name__,
                        },
                    )
                    results[agent_name] = {
                        "output": f"Error: {user_error}",
                        "agent_name": agent_name,
                        "status": "failed",
                        "error": user_error,
                        "error_type": "token_limit" if is_token_error else type(e).__name__,
                        "original_error": str(e),
                    }

    except Exception as e:
        logger.error(f"Parallel execution failed: {e}")
        # Fallback to sequential
        for config in agent_configs:
            results[config["name"]] = run_agent(
                agent_name=config["name"],
                query=config["query"],
                context=context,
                session_manager=session_manager,
                use_context_tools=use_context_tools,
            )

    return results


def save_stage_output(
    session_manager: Any,
    stage_slug: str,
    agent_name: str,
    output: str,
    status: str = "completed",
) -> None:
    """Save agent output to session directory."""
    if session_manager is None:
        logger.warning(f"No session manager, skipping save for {stage_slug}/{agent_name}")
        return

    # Save output file first - this is the critical artifact
    try:
        stage_dir = session_manager.session_dir / stage_slug
        stage_dir.mkdir(parents=True, exist_ok=True)

        output_file = stage_dir / f"{agent_name}.md"
        output_file.write_text(output, encoding="utf-8")

        logger.info(f"Saved output to {output_file}")
    except OSError as e:
        logger.error(f"Failed to save stage output file: {e}")

    # Save checkpoint separately - non-critical, don't block on failure
    try:
        session_manager.save_checkpoint(
            stage_slug=stage_slug,
            status=status,
            agents=[{"agent_name": agent_name, "status": status, "output_length": len(output)}],
            completed=datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        )
    except (OSError, TypeError, ValueError) as e:
        logger.error(f"Failed to save checkpoint for {stage_slug}: {e}")
