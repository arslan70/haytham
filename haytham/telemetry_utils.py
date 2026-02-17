"""Shared telemetry helpers.

Provides lazy-import wrappers so callers don't duplicate the
try/except ImportError pattern for optional telemetry.
"""

from contextlib import nullcontext


def get_workflow_span():
    """Return (init_telemetry, workflow_span) or no-op equivalents."""
    try:
        from haytham.telemetry import init_telemetry, workflow_span

        return init_telemetry, workflow_span
    except ImportError:

        def _noop_init():
            pass

        def _noop_span(*args, **kwargs):
            return nullcontext()

        return _noop_init, _noop_span


def get_stage_span():
    """Return stage_span or a no-op equivalent."""
    try:
        from haytham.telemetry import stage_span

        return stage_span
    except ImportError:

        def _noop_span(*args, **kwargs):
            return nullcontext()

        return _noop_span
