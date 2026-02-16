"""
Langfuse integration for LLM tracing and observability.

This module provides comprehensive tracing for the phased workflow execution:
- Root trace for entire workflow
- Phase-level spans
- Agent-level spans
- LLM generation tracking
- Tool call tracing
- User feedback integration
- Token usage and cost tracking
- Error tracking

Trace Hierarchy:
    Root Trace: idea_validation_workflow
    ├── Phase Span: Phase 1 - Concept Expansion
    │   └── Agent Span: concept_expansion_agent
    │       ├── Generation: LLM call
    │       └── Tool Span: file_write
    ├── Phase Span: Phase 2 - Market Research
    │   ├── Agent Span: market_intelligence_agent
    │   │   ├── Generation: LLM call
    │   │   ├── Tool Span: http_request
    │   │   └── Tool Span: file_write
    │   └── Agent Span: competitor_analysis_agent
    │       └── ...
    └── ...
"""

import logging
import os
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ModelPricing:
    """Model pricing configuration for cost calculation."""

    input_price_per_1k: float  # Price per 1K input tokens
    output_price_per_1k: float  # Price per 1K output tokens


# Model pricing configuration
MODEL_PRICING = {
    "anthropic.claude-3-5-sonnet-20241022-v2:0": ModelPricing(
        input_price_per_1k=0.003, output_price_per_1k=0.015
    ),
    "eu.anthropic.claude-3-5-sonnet-20241022-v2:0": ModelPricing(
        input_price_per_1k=0.003, output_price_per_1k=0.015
    ),
    "us.anthropic.claude-3-5-sonnet-20241022-v2:0": ModelPricing(
        input_price_per_1k=0.003, output_price_per_1k=0.015
    ),
    "eu.amazon.nova-pro-v1:0": ModelPricing(input_price_per_1k=0.0008, output_price_per_1k=0.0032),
    "us.amazon.nova-pro-v1:0": ModelPricing(input_price_per_1k=0.0008, output_price_per_1k=0.0032),
}


class LangfuseTracer:
    """
    Langfuse tracer for phased workflow execution.

    Provides comprehensive tracing with:
    - Hierarchical trace structure (workflow → phase → agent → generation/tool)
    - Token usage and cost tracking
    - User feedback integration
    - Error tracking
    - Metadata and tags
    - Async trace submission (non-blocking)
    """

    def __init__(
        self,
        enabled: bool | None = None,
        public_key: str | None = None,
        secret_key: str | None = None,
        host: str | None = None,
        environment: str = "development",
    ):
        """
        Initialize Langfuse tracer.

        Args:
            enabled: Enable/disable Langfuse (defaults to ENABLE_LANGFUSE env var)
            public_key: Langfuse public key (defaults to LANGFUSE_PUBLIC_KEY env var)
            secret_key: Langfuse secret key (defaults to LANGFUSE_SECRET_KEY env var)
            host: Langfuse host URL (defaults to LANGFUSE_HOST env var or cloud.langfuse.com)
            environment: Environment tag ("development" or "production")
        """
        # Check if Langfuse is enabled
        self.enabled = (
            enabled
            if enabled is not None
            else os.getenv("ENABLE_LANGFUSE", "false").lower() == "true"
        )

        if not self.enabled:
            logger.info("Langfuse tracing is disabled")
            self.client = None
            return

        # Get credentials from environment
        self.public_key = public_key or os.getenv("LANGFUSE_PUBLIC_KEY")
        self.secret_key = secret_key or os.getenv("LANGFUSE_SECRET_KEY")
        self.host = host or os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")
        self.environment = environment

        if not self.public_key or not self.secret_key:
            logger.warning(
                "Langfuse credentials not found. Set LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY "
                "environment variables to enable tracing."
            )
            self.enabled = False
            self.client = None
            return

        # Initialize Langfuse client
        try:
            from langfuse import Langfuse

            self.client = Langfuse(
                public_key=self.public_key,
                secret_key=self.secret_key,
                host=self.host,
                enabled=True,
                flush_at=10,  # Batch size for async submission
                flush_interval=1.0,  # Flush interval in seconds
            )

            logger.info(
                f"Langfuse tracer initialized (environment: {self.environment}, host: {self.host})"
            )

        except ImportError:
            logger.error("langfuse package not installed. Install with: pip install langfuse")
            self.enabled = False
            self.client = None
        except Exception as e:
            logger.error(f"Failed to initialize Langfuse client: {e}")
            self.enabled = False
            self.client = None

    def create_trace(
        self,
        trace_id: str,
        session_id: str,
        user_id: str,
        name: str = "idea_validation_workflow",
        metadata: dict[str, Any] | None = None,
        tags: list[str] | None = None,
    ) -> Any:
        """
        Create root trace for workflow execution.

        Args:
            trace_id: Unique trace identifier (workflow_trace_id)
            session_id: Session identifier
            user_id: User identifier
            name: Trace name (default: "idea_validation_workflow")
            metadata: Optional metadata (workflow_type, start_time, etc.)
            tags: Optional tags (environment, workflow_type, etc.)

        Returns:
            Langfuse trace object or None if disabled
        """
        if not self.enabled or not self.client:
            return None

        try:
            default_tags = [self.environment, "idea_validation"]
            all_tags = (tags or []) + default_tags

            trace = self.client.trace(
                id=trace_id,
                name=name,
                session_id=session_id,
                user_id=user_id,
                metadata=metadata or {},
                tags=all_tags,
            )

            logger.info(f"Created Langfuse trace: {trace_id} (session: {session_id})")
            return trace

        except Exception as e:
            logger.error(f"Failed to create Langfuse trace: {e}")
            return None

    def create_phase_span(
        self,
        trace_id: str,
        phase_number: int,
        phase_name: str,
        metadata: dict[str, Any] | None = None,
    ) -> Any:
        """
        Create span for phase execution.

        Args:
            trace_id: Parent trace identifier
            phase_number: Phase number (1-7)
            phase_name: Phase name (e.g., "Concept Expansion")
            metadata: Optional metadata (execution_mode, agents, etc.)

        Returns:
            Langfuse span object or None if disabled
        """
        if not self.enabled or not self.client:
            return None

        try:
            span = self.client.span(
                trace_id=trace_id,
                name=f"Phase {phase_number}: {phase_name}",
                metadata={
                    "phase_number": phase_number,
                    "phase_name": phase_name,
                    **(metadata or {}),
                },
                start_time=datetime.now(),
            )

            logger.debug(f"Created phase span: Phase {phase_number} - {phase_name}")
            return span

        except Exception as e:
            logger.error(f"Failed to create phase span: {e}")
            return None

    def create_agent_span(
        self,
        trace_id: str,
        parent_span_id: str,
        agent_name: str,
        metadata: dict[str, Any] | None = None,
    ) -> Any:
        """
        Create span for agent execution.

        Args:
            trace_id: Parent trace identifier
            parent_span_id: Parent phase span identifier
            agent_name: Agent name (e.g., "market_intelligence_agent")
            metadata: Optional metadata (agent_type, model, etc.)

        Returns:
            Langfuse span object or None if disabled
        """
        if not self.enabled or not self.client:
            return None

        try:
            span = self.client.span(
                trace_id=trace_id,
                parent_observation_id=parent_span_id,
                name=agent_name,
                metadata={"agent_name": agent_name, **(metadata or {})},
                start_time=datetime.now(),
            )

            logger.debug(f"Created agent span: {agent_name}")
            return span

        except Exception as e:
            logger.error(f"Failed to create agent span: {e}")
            return None

    def create_generation(
        self,
        trace_id: str,
        parent_span_id: str,
        model: str,
        input_messages: list[dict[str, Any]] | None = None,
        output_text: str | None = None,
        input_tokens: int | None = None,
        output_tokens: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Any:
        """
        Create generation for LLM call.

        Args:
            trace_id: Parent trace identifier
            parent_span_id: Parent agent span identifier
            model: Model identifier
            input_messages: Input messages/prompt
            output_text: Generated text
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            metadata: Optional metadata (temperature, max_tokens, etc.)

        Returns:
            Langfuse generation object or None if disabled
        """
        if not self.enabled or not self.client:
            return None

        try:
            # Calculate cost
            cost = self._calculate_cost(model, input_tokens or 0, output_tokens or 0)

            generation = self.client.generation(
                trace_id=trace_id,
                parent_observation_id=parent_span_id,
                name="llm_call",
                model=model,
                input=input_messages,
                output=output_text,
                usage={
                    "input": input_tokens or 0,
                    "output": output_tokens or 0,
                    "total": (input_tokens or 0) + (output_tokens or 0),
                    "unit": "TOKENS",
                },
                metadata={"cost_usd": cost, **(metadata or {})},
                start_time=datetime.now(),
            )

            logger.debug(f"Created generation for model: {model} (cost: ${cost:.4f})")
            return generation

        except Exception as e:
            logger.error(f"Failed to create generation: {e}")
            return None

    def create_tool_span(
        self,
        trace_id: str,
        parent_span_id: str,
        tool_name: str,
        input_params: dict[str, Any] | None = None,
        output_result: Any = None,
        metadata: dict[str, Any] | None = None,
    ) -> Any:
        """
        Create span for tool call.

        Args:
            trace_id: Parent trace identifier
            parent_span_id: Parent agent span identifier
            tool_name: Tool name (e.g., "http_request", "file_read")
            input_params: Tool input parameters
            output_result: Tool output result
            metadata: Optional metadata (execution_time, success_status, etc.)

        Returns:
            Langfuse span object or None if disabled
        """
        if not self.enabled or not self.client:
            return None

        try:
            span = self.client.span(
                trace_id=trace_id,
                parent_observation_id=parent_span_id,
                name=f"tool_{tool_name}",
                input=input_params,
                output=output_result,
                metadata={"tool_name": tool_name, **(metadata or {})},
                start_time=datetime.now(),
            )

            logger.debug(f"Created tool span: {tool_name}")
            return span

        except Exception as e:
            logger.error(f"Failed to create tool span: {e}")
            return None

    def end_span(self, span: Any, status: str = "success", error: Exception | None = None) -> None:
        """
        End a span with status and optional error.

        Args:
            span: Langfuse span object
            status: Status ("success" or "error")
            error: Optional exception if status is "error"
        """
        if not self.enabled or not self.client or not span:
            return

        try:
            if status == "error" and error:
                span.end(
                    end_time=datetime.now(),
                    level="ERROR",
                    status_message=str(error),
                    metadata={"error_type": type(error).__name__, "error_message": str(error)},
                )
            else:
                span.end(end_time=datetime.now())

            logger.debug(f"Ended span with status: {status}")

        except Exception as e:
            logger.error(f"Failed to end span: {e}")

    def add_user_feedback(
        self,
        trace_id: str,
        phase_number: int,
        action: str,
        comment: str | None = None,
        score: float | None = None,
    ) -> None:
        """
        Add user feedback to trace.

        Args:
            trace_id: Trace identifier
            phase_number: Phase number where feedback was given
            action: User action ("approve", "request_changes", "skip")
            comment: Optional user comment
            score: Optional numeric score (0-1)
        """
        if not self.enabled or not self.client:
            return

        try:
            # Map action to score if not provided
            if score is None:
                score_map = {"approve": 1.0, "skip": 0.5, "request_changes": 0.0}
                score = score_map.get(action, 0.5)

            self.client.score(
                trace_id=trace_id,
                name="user_feedback",
                value=score,
                comment=comment or f"Phase {phase_number}: {action}",
                data_type="NUMERIC",
            )

            logger.info(f"Added user feedback to trace {trace_id}: {action} (score: {score})")

        except Exception as e:
            logger.error(f"Failed to add user feedback: {e}")

    def track_error(
        self,
        trace_id: str,
        error: Exception,
        phase_number: int | None = None,
        agent_name: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> None:
        """
        Track error in trace.

        Args:
            trace_id: Trace identifier
            error: Exception that occurred
            phase_number: Optional phase number where error occurred
            agent_name: Optional agent name where error occurred
            context: Optional additional context
        """
        if not self.enabled or not self.client:
            return

        try:
            error_data = {
                "error_type": type(error).__name__,
                "error_message": str(error),
                "phase_number": phase_number,
                "agent_name": agent_name,
                **(context or {}),
            }

            # Create event for error
            self.client.event(trace_id=trace_id, name="error", metadata=error_data, level="ERROR")

            logger.info(f"Tracked error in trace {trace_id}: {type(error).__name__}")

        except Exception as e:
            logger.error(f"Failed to track error: {e}")

    def flush(self) -> None:
        """
        Flush pending traces to Langfuse.

        Call this at the end of workflow execution to ensure all traces are sent.
        """
        if not self.enabled or not self.client:
            return

        try:
            self.client.flush()
            logger.info("Flushed pending traces to Langfuse")

        except Exception as e:
            logger.error(f"Failed to flush traces: {e}")

    def _calculate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        """
        Calculate cost for LLM call.

        Args:
            model: Model identifier
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens

        Returns:
            Cost in USD
        """
        pricing = MODEL_PRICING.get(model)

        if not pricing:
            logger.warning(f"No pricing configured for model: {model}")
            return 0.0

        input_cost = (input_tokens / 1000) * pricing.input_price_per_1k
        output_cost = (output_tokens / 1000) * pricing.output_price_per_1k

        return input_cost + output_cost

    @contextmanager
    def trace_phase(
        self,
        trace_id: str,
        phase_number: int,
        phase_name: str,
        metadata: dict[str, Any] | None = None,
    ):
        """
        Context manager for tracing phase execution.

        Usage:
            with tracer.trace_phase(trace_id, 1, "Concept Expansion"):
                # Execute phase
                pass

        Args:
            trace_id: Parent trace identifier
            phase_number: Phase number (1-7)
            phase_name: Phase name
            metadata: Optional metadata
        """
        span = self.create_phase_span(trace_id, phase_number, phase_name, metadata)

        try:
            yield span
            self.end_span(span, status="success")
        except Exception as e:
            self.end_span(span, status="error", error=e)
            raise

    @contextmanager
    def trace_agent(
        self,
        trace_id: str,
        parent_span_id: str,
        agent_name: str,
        metadata: dict[str, Any] | None = None,
    ):
        """
        Context manager for tracing agent execution.

        Usage:
            with tracer.trace_agent(trace_id, phase_span_id, "market_intelligence_agent"):
                # Execute agent
                pass

        Args:
            trace_id: Parent trace identifier
            parent_span_id: Parent phase span identifier
            agent_name: Agent name
            metadata: Optional metadata
        """
        span = self.create_agent_span(trace_id, parent_span_id, agent_name, metadata)

        try:
            yield span
            self.end_span(span, status="success")
        except Exception as e:
            self.end_span(span, status="error", error=e)
            raise


# Global tracer instance
_langfuse_tracer: LangfuseTracer | None = None


def get_langfuse_tracer() -> LangfuseTracer:
    """
    Get or create global Langfuse tracer instance.

    Returns:
        LangfuseTracer instance
    """
    global _langfuse_tracer

    if _langfuse_tracer is None:
        _langfuse_tracer = LangfuseTracer()
        logger.info("Created global LangfuseTracer instance")

    return _langfuse_tracer
