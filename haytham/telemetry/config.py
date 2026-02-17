"""Telemetry configuration and initialization.

This module handles:
- Reading telemetry configuration from environment variables
- Initializing Strands telemetry with OpenTelemetry
- Setting up Python logging with appropriate levels
- Configuring exporters (OTLP, console, file)
"""

import logging
import os
import sys
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)

# Global state
_telemetry_initialized = False
_strands_telemetry = None


class ExporterType(Enum):
    """Supported trace exporters."""

    OTLP = "otlp"
    CONSOLE = "console"
    NONE = "none"


@dataclass
class TelemetryConfig:
    """Configuration for telemetry and observability.

    All values are read from environment variables with sensible defaults.
    """

    # Logging
    log_level: str = "INFO"

    # OpenTelemetry
    service_name: str = "haytham-ai"
    otlp_endpoint: str = "http://localhost:4317"
    traces_exporter: ExporterType = ExporterType.OTLP
    otel_disabled: bool = False

    # Sampling (for production - reduce trace volume)
    traces_sampler: str = "always_on"  # or "traceidratio"
    traces_sampler_arg: float = 1.0  # 1.0 = 100% when using traceidratio

    # Custom attributes added to all traces
    default_attributes: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_env(cls) -> "TelemetryConfig":
        """Create config from environment variables."""
        # Parse exporter type
        exporter_str = os.getenv("OTEL_TRACES_EXPORTER", "otlp").lower()
        try:
            exporter = ExporterType(exporter_str)
        except ValueError:
            logger.warning(f"Unknown exporter type '{exporter_str}', defaulting to OTLP")
            exporter = ExporterType.OTLP

        # Parse disabled flag
        otel_disabled = os.getenv("OTEL_SDK_DISABLED", "false").lower() in ("true", "1", "yes")

        return cls(
            log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
            service_name=os.getenv("OTEL_SERVICE_NAME", "haytham-ai"),
            otlp_endpoint=os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317"),
            traces_exporter=exporter,
            otel_disabled=otel_disabled,
            traces_sampler=os.getenv("OTEL_TRACES_SAMPLER", "always_on"),
            traces_sampler_arg=float(os.getenv("OTEL_TRACES_SAMPLER_ARG", "1.0")),
        )


def _setup_logging(config: TelemetryConfig) -> None:
    """Configure Python logging based on config.

    Sets up:
    - Root logger with appropriate level
    - Strands logger (for agent/LLM logging)
    - Haytham logger (for workflow logging)
    - Console handler with structured format
    """
    # Map string level to logging constant
    level_map = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL,
    }
    level = level_map.get(config.log_level, logging.INFO)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Remove existing handlers to avoid duplicates
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Create console handler with structured format
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)

    # Use structured format that includes timestamp and logger name
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # Configure specific loggers
    # Strands - follows their log level recommendations
    logging.getLogger("strands").setLevel(level)

    # Haytham modules
    logging.getLogger("haytham").setLevel(level)

    # Reduce noise from third-party libraries unless in DEBUG mode
    if level > logging.DEBUG:
        logging.getLogger("urllib3").setLevel(logging.WARNING)
        logging.getLogger("botocore").setLevel(logging.WARNING)
        logging.getLogger("boto3").setLevel(logging.WARNING)

    # Suppress harmless OTEL context detach warnings from Swarm handoffs.
    # The threading instrumentation (installed by Strands SDK) creates context
    # tokens that can't be detached across async boundaries. This is a known
    # OTEL+asyncio incompatibility; the warnings are cosmetic only.
    logging.getLogger("opentelemetry.context").setLevel(logging.CRITICAL)

    logger.info(f"Logging configured: level={config.log_level}")


def _setup_strands_telemetry(config: TelemetryConfig) -> Any:
    """Initialize Strands telemetry with OpenTelemetry.

    Returns the StrandsTelemetry instance for further configuration.
    """
    if config.otel_disabled:
        logger.info("OpenTelemetry disabled via OTEL_SDK_DISABLED")
        return None

    try:
        from strands.telemetry import StrandsTelemetry
    except ImportError:
        logger.warning(
            "strands.telemetry not available. Install with: pip install 'strands-agents[otel]'"
        )
        return None

    try:
        # Create a custom TracerProvider with the service name
        from opentelemetry import trace
        from opentelemetry.sdk.resources import SERVICE_NAME, Resource
        from opentelemetry.sdk.trace import TracerProvider

        # Create resource with service name
        resource = Resource.create({SERVICE_NAME: config.service_name})
        tracer_provider = TracerProvider(resource=resource)

        # Set as global tracer provider
        trace.set_tracer_provider(tracer_provider)

        # Create Strands telemetry with the custom provider
        telemetry = StrandsTelemetry(tracer_provider=tracer_provider)

        # Configure exporter based on config
        if config.traces_exporter == ExporterType.OTLP:
            telemetry.setup_otlp_exporter(endpoint=config.otlp_endpoint)
            logger.info(f"OTLP exporter configured: endpoint={config.otlp_endpoint}")

        elif config.traces_exporter == ExporterType.CONSOLE:
            telemetry.setup_console_exporter()
            logger.info("Console exporter configured")

        # ExporterType.NONE - no exporter setup, traces not exported

        return telemetry

    except Exception as e:
        logger.warning(f"Failed to initialize OpenTelemetry: {e}")
        return None


def init_telemetry(config: TelemetryConfig | None = None) -> None:
    """Initialize the telemetry system.

    This should be called once at application startup, before creating
    any agents or running workflows.

    Args:
        config: Optional configuration. If not provided, reads from environment.
    """
    global _telemetry_initialized, _strands_telemetry

    if _telemetry_initialized:
        logger.debug("Telemetry already initialized, skipping")
        return

    if config is None:
        config = TelemetryConfig.from_env()

    # Setup logging first
    _setup_logging(config)

    # Setup Strands telemetry (OpenTelemetry)
    _strands_telemetry = _setup_strands_telemetry(config)

    _telemetry_initialized = True
    logger.info(
        f"Telemetry initialized: service={config.service_name}, "
        f"exporter={config.traces_exporter.value}, "
        f"otel_disabled={config.otel_disabled}"
    )


def shutdown_telemetry() -> None:
    """Shutdown telemetry and flush any pending traces.

    Call this at application shutdown to ensure all traces are exported.
    """
    global _telemetry_initialized, _strands_telemetry

    if not _telemetry_initialized:
        return

    # Strands telemetry handles its own shutdown via atexit
    # but we can force flush here if needed

    _telemetry_initialized = False
    _strands_telemetry = None
    logger.info("Telemetry shutdown complete")


def is_telemetry_enabled() -> bool:
    """Check if telemetry is initialized and enabled."""
    return _telemetry_initialized and _strands_telemetry is not None


def get_telemetry_config() -> TelemetryConfig:
    """Get the current telemetry configuration."""
    return TelemetryConfig.from_env()


def get_strands_telemetry():
    """Get the Strands telemetry instance.

    Returns None if telemetry is not initialized or disabled.
    """
    return _strands_telemetry
