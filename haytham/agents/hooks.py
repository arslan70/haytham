"""Agent lifecycle hooks for observability.

Provides a HookProvider that centralizes timing, logging, and OTEL
recording for all Strands agent invocations. Injected via agent_factory.py.
"""

import logging
import time

from strands.hooks import (
    AfterInvocationEvent,
    AfterToolCallEvent,
    BeforeInvocationEvent,
    BeforeToolCallEvent,
    HookProvider,
    HookRegistry,
)

logger = logging.getLogger(__name__)


class HaythamAgentHooks(HookProvider):
    """Observability hooks for Haytham agent invocations.

    Records timing, logs lifecycle events, and annotates OTEL spans.
    Does NOT retry or modify agent behavior — purely observational.
    """

    def __init__(self):
        self._start_time: float | None = None
        self.execution_time: float = 0.0

    def register_hooks(self, registry: HookRegistry, **kwargs) -> None:
        registry.add_callback(BeforeInvocationEvent, self._on_before_invocation)
        registry.add_callback(AfterInvocationEvent, self._on_after_invocation)
        registry.add_callback(BeforeToolCallEvent, self._on_before_tool)
        registry.add_callback(AfterToolCallEvent, self._on_after_tool)

    def _on_before_invocation(self, event: BeforeInvocationEvent) -> None:
        self._start_time = time.time()
        agent_name = getattr(event.agent, "name", "unknown")
        logger.info(f"Agent {agent_name} invocation started")

    def _on_after_invocation(self, event: AfterInvocationEvent) -> None:
        self.execution_time = time.time() - (self._start_time or time.time())
        agent_name = getattr(event.agent, "name", "unknown")

        if event.result:
            stop_reason = getattr(event.result, "stop_reason", "unknown")
            logger.info(
                f"Agent {agent_name} invocation completed in {self.execution_time:.2f}s "
                f"(stop_reason={stop_reason})"
            )

            # Log cache metrics when available
            self._log_cache_metrics(agent_name, event.result)

            # Annotate current OTEL span if available
            self._record_span_attributes(agent_name, stop_reason)
        else:
            logger.warning(
                f"Agent {agent_name} invocation completed in {self.execution_time:.2f}s "
                f"with no result"
            )

    def _on_before_tool(self, event: BeforeToolCallEvent) -> None:
        tool_name = event.tool_use.get("name", "unknown") if event.tool_use else "unknown"
        agent_name = getattr(event.agent, "name", "unknown")
        logger.debug(f"Agent {agent_name} calling tool: {tool_name}")

    def _on_after_tool(self, event: AfterToolCallEvent) -> None:
        tool_name = event.tool_use.get("name", "unknown") if event.tool_use else "unknown"
        agent_name = getattr(event.agent, "name", "unknown")
        logger.debug(f"Agent {agent_name} tool {tool_name} completed")

    def _log_cache_metrics(self, agent_name: str, result) -> None:
        """Log Bedrock prompt/tool cache hit/write metrics."""
        metrics = getattr(result, "metrics", None)
        usage = getattr(metrics, "accumulated_usage", None) if metrics else None
        if not usage:
            return

        cache_write = usage.get("cacheWriteInputTokens", 0)
        cache_read = usage.get("cacheReadInputTokens", 0)
        if cache_write or cache_read:
            logger.info(f"Agent {agent_name} cache: write={cache_write} read={cache_read} tokens")

    def _record_span_attributes(self, agent_name: str, stop_reason: str) -> None:
        """Record execution metadata to current OTEL span if available."""
        try:
            from opentelemetry import trace

            span = trace.get_current_span()
            if span and hasattr(span, "set_attribute"):
                span.set_attribute("agent.name", agent_name)
                span.set_attribute("agent.execution_time_seconds", self.execution_time)
                span.set_attribute("agent.stop_reason", str(stop_reason))
        except ImportError:
            pass
