"""Custom span creation for workflow and stage-level tracing.

This module provides decorators and context managers for creating
OpenTelemetry spans at the workflow and stage level. These wrap
the automatic agent/LLM/tool spans created by Strands.

Span Hierarchy:
    workflow_span (root)
    └── stage_span (per stage)
        └── agent_span (created by Strands)
            └── llm_span (created by Strands)
            └── tool_span (created by Strands)
"""

import logging
from collections.abc import Generator
from contextlib import contextmanager
from functools import wraps
from typing import Any

logger = logging.getLogger(__name__)

# Tracer instance - lazily initialized
_tracer = None


def get_tracer():
    """Get the OpenTelemetry tracer for custom spans.

    Returns a tracer instance that can be used to create custom spans.
    If OpenTelemetry is not available or disabled, returns a no-op tracer.
    """
    global _tracer

    if _tracer is not None:
        return _tracer

    try:
        from opentelemetry import trace

        _tracer = trace.get_tracer("haytham.workflow")
        logger.debug("OpenTelemetry tracer initialized")
    except ImportError:
        logger.debug("OpenTelemetry not available, using no-op tracer")
        _tracer = _NoOpTracer()

    return _tracer


class _NoOpSpan:
    """No-op span for when OpenTelemetry is not available."""

    def set_attribute(self, key: str, value: Any) -> None:
        pass

    def set_status(self, status: Any) -> None:
        pass

    def record_exception(self, exception: Exception) -> None:
        pass

    def add_event(self, name: str, attributes: dict | None = None) -> None:
        pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


class _NoOpTracer:
    """No-op tracer for when OpenTelemetry is not available."""

    @contextmanager
    def start_as_current_span(self, name: str, **kwargs) -> Generator[_NoOpSpan, None, None]:
        yield _NoOpSpan()

    def start_span(self, name: str, **kwargs) -> _NoOpSpan:
        return _NoOpSpan()


@contextmanager
def workflow_span(
    workflow_name: str,
    system_goal: str,
    session_id: str | None = None,
    **attributes: Any,
) -> Generator[Any, None, None]:
    """Create a span for an entire workflow execution.

    This is the root span for a workflow run. All stage spans should be
    created as children of this span.

    Args:
        workflow_name: Name of the workflow (e.g., "idea-validation")
        system_goal: The startup idea being processed
        session_id: Optional session ID for correlation
        **attributes: Additional span attributes

    Yields:
        The OpenTelemetry span (or no-op span if OTel unavailable)

    Example:
        with workflow_span("idea-validation", "AI startup validator") as span:
            span.set_attribute("custom.field", "value")
            # ... run stages ...
    """
    tracer = get_tracer()

    span_attributes = {
        "workflow.name": workflow_name,
        "workflow.system_goal": system_goal[:500],  # Truncate for safety
        "workflow.system_goal_length": len(system_goal),
    }

    if session_id:
        span_attributes["session.id"] = session_id

    span_attributes.update(attributes)

    with tracer.start_as_current_span(
        name=f"workflow:{workflow_name}",
        attributes=span_attributes,
    ) as span:
        try:
            yield span
            # Set success status
            try:
                from opentelemetry.trace import StatusCode

                span.set_status(StatusCode.OK)
            except ImportError:
                pass
        except Exception as e:
            # Record exception and set error status
            span.record_exception(e)
            try:
                from opentelemetry.trace import StatusCode

                span.set_status(StatusCode.ERROR, str(e))
            except ImportError:
                pass
            raise


@contextmanager
def stage_span(
    stage_slug: str,
    stage_name: str,
    workflow_type: str | None = None,
    agent_names: list[str] | None = None,
    **attributes: Any,
) -> Generator[Any, None, None]:
    """Create a span for a stage execution.

    This should be called within a workflow_span context so stages
    are properly nested under their parent workflow.

    Args:
        stage_slug: Stage identifier (e.g., "idea-analysis")
        stage_name: Human-readable stage name (e.g., "Idea Analysis")
        workflow_type: Optional workflow type this stage belongs to
        agent_names: Optional list of agents that will execute in this stage
        **attributes: Additional span attributes

    Yields:
        The OpenTelemetry span (or no-op span if OTel unavailable)

    Example:
        with stage_span("idea-analysis", "Idea Analysis") as span:
            span.add_event("agent_started", {"agent": "concept_expansion"})
            # ... execute agents ...
            span.set_attribute("stage.tokens_used", 1500)
    """
    tracer = get_tracer()

    span_attributes = {
        "stage.slug": stage_slug,
        "stage.name": stage_name,
    }

    if workflow_type:
        span_attributes["stage.workflow_type"] = workflow_type

    if agent_names:
        span_attributes["stage.agent_count"] = len(agent_names)
        span_attributes["stage.agents"] = ",".join(agent_names)

    span_attributes.update(attributes)

    with tracer.start_as_current_span(
        name=f"stage:{stage_slug}",
        attributes=span_attributes,
    ) as span:
        try:
            yield span
            # Set success status
            try:
                from opentelemetry.trace import StatusCode

                span.set_status(StatusCode.OK)
            except ImportError:
                pass
        except Exception as e:
            # Record exception and set error status
            span.record_exception(e)
            try:
                from opentelemetry.trace import StatusCode

                span.set_status(StatusCode.ERROR, str(e))
            except ImportError:
                pass
            raise


def traced_stage(stage_slug: str, stage_name: str, **span_attributes):
    """Decorator to trace a stage execution function.

    Args:
        stage_slug: Stage identifier
        stage_name: Human-readable stage name
        **span_attributes: Additional attributes to add to the span

    Example:
        @traced_stage("idea-analysis", "Idea Analysis")
        def execute_idea_analysis(system_goal: str) -> str:
            # ... execute stage ...
            return result
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            with stage_span(stage_slug, stage_name, **span_attributes) as span:
                result = func(*args, **kwargs)

                # Try to extract metrics from result if it's a dict
                if isinstance(result, dict):
                    if "execution_time" in result:
                        span.set_attribute("stage.duration_seconds", result["execution_time"])
                    if "tokens_used" in result:
                        span.set_attribute("stage.tokens_used", result["tokens_used"])
                    if "status" in result:
                        span.set_attribute("stage.status", result["status"])

                return result

        return wrapper

    return decorator


def add_agent_attributes(span, agent_name: str, **attributes) -> None:
    """Add agent execution attributes to a span.

    Helper function to add standardized agent attributes to a stage span.

    Args:
        span: The span to add attributes to
        agent_name: Name of the agent
        **attributes: Additional attributes (execution_time, tokens, etc.)
    """
    span.set_attribute(f"agent.{agent_name}.executed", True)

    for key, value in attributes.items():
        span.set_attribute(f"agent.{agent_name}.{key}", value)


def record_stage_event(span, event_name: str, **attributes) -> None:
    """Record an event within a stage span.

    Args:
        span: The span to add the event to
        event_name: Name of the event (e.g., "agent_started", "checkpoint_created")
        **attributes: Event attributes
    """
    span.add_event(event_name, attributes=attributes)


def record_error(span, error: Exception, agent_name: str | None = None) -> None:
    """Record an error to a span with structured attributes.

    Args:
        span: The span to record the error on
        error: The exception that occurred
        agent_name: Optional agent name if error occurred during agent execution
    """
    error_type = type(error).__name__
    error_message = str(error)

    # Set error attributes
    span.set_attribute("error", True)
    span.set_attribute("error.type", error_type)
    span.set_attribute("error.message", error_message[:500])  # Truncate for safety

    if agent_name:
        span.set_attribute("error.agent", agent_name)

    # Check for token limit errors (Bedrock-specific)
    is_token_limit = _is_token_limit_error(error)
    span.set_attribute("error.is_token_limit", is_token_limit)

    # Record the exception
    span.record_exception(error)

    # Set error status
    try:
        from opentelemetry.trace import StatusCode

        span.set_status(StatusCode.ERROR, error_message[:100])
    except ImportError:
        pass


def _is_token_limit_error(error: Exception) -> bool:
    """Check if an error is a token limit error from Bedrock.

    Args:
        error: The exception to check

    Returns:
        True if this is a token limit error
    """
    error_str = str(error).lower()

    # Check for common token limit indicators
    token_limit_indicators = [
        "token",
        "maxtoken",
        "max_token",
        "context length",
        "too long",
        "exceeds the max",
        "input is too long",
        "validationexception",
    ]

    return any(indicator in error_str for indicator in token_limit_indicators)
