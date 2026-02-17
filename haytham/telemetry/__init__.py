"""Telemetry and observability for Haytham.

This module provides OpenTelemetry-based observability using Strands' built-in
telemetry support. It adds workflow and stage-level tracing on top of the
automatic agent/LLM/tool tracing provided by Strands.

Usage:
    from haytham.telemetry import init_telemetry, get_tracer

    # Initialize once at startup
    init_telemetry()

    # Get tracer for custom spans
    tracer = get_tracer()
    with tracer.start_as_current_span("my_operation") as span:
        span.set_attribute("custom.attribute", "value")
        # ... do work ...

Environment Variables:
    LOG_LEVEL: Logging level (DEBUG, INFO, WARNING, ERROR) - default: INFO
    OTEL_EXPORTER_OTLP_ENDPOINT: OTLP collector endpoint - default: http://localhost:4317
    OTEL_SERVICE_NAME: Service name for traces - default: haytham-ai
    OTEL_TRACES_EXPORTER: Exporter type (otlp, console, none) - default: otlp
    OTEL_SDK_DISABLED: Disable all telemetry - default: false
"""

from .config import (
    TelemetryConfig,
    get_telemetry_config,
    init_telemetry,
    is_telemetry_enabled,
    shutdown_telemetry,
)
from .spans import (
    get_tracer,
    record_error,
    stage_span,
    workflow_span,
)

__all__ = [
    # Configuration
    "TelemetryConfig",
    "get_telemetry_config",
    "init_telemetry",
    "shutdown_telemetry",
    "is_telemetry_enabled",
    # Spans
    "get_tracer",
    "workflow_span",
    "stage_span",
    "record_error",
]
