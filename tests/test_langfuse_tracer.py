"""
Tests for Langfuse tracer integration.

Tests cover:
- Tracer initialization with/without credentials
- Trace creation and hierarchy
- Phase span creation
- Agent span creation
- Generation tracking
- Tool span creation
- User feedback integration
- Error tracking
- Cost calculation
- Context managers
- Graceful degradation when disabled
"""

import os
from unittest.mock import MagicMock, patch

import pytest

from haytham.agents.utils.langfuse_tracer import (
    MODEL_PRICING,
    LangfuseTracer,
    get_langfuse_tracer,
)


@pytest.fixture
def mock_langfuse_client():
    """Mock Langfuse client."""
    # Mock the langfuse module import
    mock_langfuse_module = MagicMock()
    client = MagicMock()
    mock_langfuse_module.Langfuse.return_value = client

    with patch.dict("sys.modules", {"langfuse": mock_langfuse_module}):
        yield client


@pytest.fixture
def tracer_enabled(mock_langfuse_client):
    """Create enabled tracer with mocked client."""
    tracer = LangfuseTracer(
        enabled=True, public_key="pk-test", secret_key="sk-test", host="https://test.langfuse.com"
    )
    return tracer


@pytest.fixture
def tracer_disabled():
    """Create disabled tracer."""
    tracer = LangfuseTracer(enabled=False)
    return tracer


class TestLangfuseTracerInitialization:
    """Test tracer initialization."""

    def test_init_disabled(self):
        """Test initialization when disabled."""
        tracer = LangfuseTracer(enabled=False)

        assert tracer.enabled is False
        assert tracer.client is None

    def test_init_enabled_with_credentials(self, mock_langfuse_client):
        """Test initialization when enabled with credentials."""
        tracer = LangfuseTracer(
            enabled=True,
            public_key="pk-test",
            secret_key="sk-test",
            host="https://test.langfuse.com",
            environment="production",
        )

        assert tracer.enabled is True
        assert tracer.client is not None
        assert tracer.public_key == "pk-test"
        assert tracer.secret_key == "sk-test"
        assert tracer.host == "https://test.langfuse.com"
        assert tracer.environment == "production"

    def test_init_enabled_without_credentials(self):
        """Test initialization when enabled but missing credentials."""
        tracer = LangfuseTracer(enabled=True, public_key=None, secret_key=None)

        # Should fall back to disabled
        assert tracer.enabled is False
        assert tracer.client is None

    def test_init_from_environment_variables(self, mock_langfuse_client):
        """Test initialization from environment variables."""
        with patch.dict(
            os.environ,
            {
                "ENABLE_LANGFUSE": "true",
                "LANGFUSE_PUBLIC_KEY": "pk-env",
                "LANGFUSE_SECRET_KEY": "sk-env",
                "LANGFUSE_HOST": "https://env.langfuse.com",
            },
        ):
            tracer = LangfuseTracer()

            assert tracer.enabled is True
            assert tracer.public_key == "pk-env"
            assert tracer.secret_key == "sk-env"
            assert tracer.host == "https://env.langfuse.com"

    def test_init_langfuse_not_installed(self):
        """Test initialization when langfuse package not installed."""
        # Mock langfuse module not being available
        with patch.dict("sys.modules", {"langfuse": None}):
            tracer = LangfuseTracer(enabled=True, public_key="pk-test", secret_key="sk-test")

            # Should fall back to disabled
            assert tracer.enabled is False
            assert tracer.client is None


class TestTraceCreation:
    """Test trace creation."""

    def test_create_trace_enabled(self, tracer_enabled, mock_langfuse_client):
        """Test creating trace when enabled."""
        trace = tracer_enabled.create_trace(
            trace_id="trace-123",
            session_id="session-456",
            user_id="user-789",
            name="test_workflow",
            metadata={"key": "value"},
            tags=["test"],
        )

        assert trace is not None
        mock_langfuse_client.trace.assert_called_once()

        call_kwargs = mock_langfuse_client.trace.call_args[1]
        assert call_kwargs["id"] == "trace-123"
        assert call_kwargs["name"] == "test_workflow"
        assert call_kwargs["session_id"] == "session-456"
        assert call_kwargs["user_id"] == "user-789"
        assert call_kwargs["metadata"] == {"key": "value"}
        assert "test" in call_kwargs["tags"]
        assert "development" in call_kwargs["tags"]  # Default environment tag

    def test_create_trace_disabled(self, tracer_disabled):
        """Test creating trace when disabled."""
        trace = tracer_disabled.create_trace(
            trace_id="trace-123", session_id="session-456", user_id="user-789"
        )

        assert trace is None


class TestPhaseSpan:
    """Test phase span creation."""

    def test_create_phase_span_enabled(self, tracer_enabled, mock_langfuse_client):
        """Test creating phase span when enabled."""
        span = tracer_enabled.create_phase_span(
            trace_id="trace-123",
            phase_number=2,
            phase_name="Market Research",
            metadata={"execution_mode": "parallel"},
        )

        assert span is not None
        mock_langfuse_client.span.assert_called_once()

        call_kwargs = mock_langfuse_client.span.call_args[1]
        assert call_kwargs["trace_id"] == "trace-123"
        assert call_kwargs["name"] == "Phase 2: Market Research"
        assert call_kwargs["metadata"]["phase_number"] == 2
        assert call_kwargs["metadata"]["phase_name"] == "Market Research"
        assert call_kwargs["metadata"]["execution_mode"] == "parallel"

    def test_create_phase_span_disabled(self, tracer_disabled):
        """Test creating phase span when disabled."""
        span = tracer_disabled.create_phase_span(
            trace_id="trace-123", phase_number=1, phase_name="Concept Expansion"
        )

        assert span is None


class TestAgentSpan:
    """Test agent span creation."""

    def test_create_agent_span_enabled(self, tracer_enabled, mock_langfuse_client):
        """Test creating agent span when enabled."""
        span = tracer_enabled.create_agent_span(
            trace_id="trace-123",
            parent_span_id="phase-span-456",
            agent_name="market_intelligence_agent",
            metadata={"model": "claude-sonnet"},
        )

        assert span is not None
        mock_langfuse_client.span.assert_called()

        call_kwargs = mock_langfuse_client.span.call_args[1]
        assert call_kwargs["trace_id"] == "trace-123"
        assert call_kwargs["parent_observation_id"] == "phase-span-456"
        assert call_kwargs["name"] == "market_intelligence_agent"
        assert call_kwargs["metadata"]["agent_name"] == "market_intelligence_agent"
        assert call_kwargs["metadata"]["model"] == "claude-sonnet"

    def test_create_agent_span_disabled(self, tracer_disabled):
        """Test creating agent span when disabled."""
        span = tracer_disabled.create_agent_span(
            trace_id="trace-123",
            parent_span_id="phase-span-456",
            agent_name="market_intelligence_agent",
        )

        assert span is None


class TestGeneration:
    """Test generation tracking."""

    def test_create_generation_enabled(self, tracer_enabled, mock_langfuse_client):
        """Test creating generation when enabled."""
        generation = tracer_enabled.create_generation(
            trace_id="trace-123",
            parent_span_id="agent-span-789",
            model="anthropic.claude-3-5-sonnet-20241022-v2:0",
            input_messages=[{"role": "user", "content": "test"}],
            output_text="response",
            input_tokens=100,
            output_tokens=50,
            metadata={"temperature": 0.7},
        )

        assert generation is not None
        mock_langfuse_client.generation.assert_called_once()

        call_kwargs = mock_langfuse_client.generation.call_args[1]
        assert call_kwargs["trace_id"] == "trace-123"
        assert call_kwargs["parent_observation_id"] == "agent-span-789"
        assert call_kwargs["model"] == "anthropic.claude-3-5-sonnet-20241022-v2:0"
        assert call_kwargs["input"] == [{"role": "user", "content": "test"}]
        assert call_kwargs["output"] == "response"
        assert call_kwargs["usage"]["input"] == 100
        assert call_kwargs["usage"]["output"] == 50
        assert call_kwargs["usage"]["total"] == 150
        assert "cost_usd" in call_kwargs["metadata"]
        assert call_kwargs["metadata"]["temperature"] == 0.7

    def test_create_generation_disabled(self, tracer_disabled):
        """Test creating generation when disabled."""
        generation = tracer_disabled.create_generation(
            trace_id="trace-123",
            parent_span_id="agent-span-789",
            model="claude-sonnet",
            input_tokens=100,
            output_tokens=50,
        )

        assert generation is None


class TestToolSpan:
    """Test tool span creation."""

    def test_create_tool_span_enabled(self, tracer_enabled, mock_langfuse_client):
        """Test creating tool span when enabled."""
        span = tracer_enabled.create_tool_span(
            trace_id="trace-123",
            parent_span_id="agent-span-789",
            tool_name="http_request",
            input_params={"url": "https://example.com"},
            output_result={"status": 200},
            metadata={"execution_time": 0.5},
        )

        assert span is not None
        mock_langfuse_client.span.assert_called()

        call_kwargs = mock_langfuse_client.span.call_args[1]
        assert call_kwargs["trace_id"] == "trace-123"
        assert call_kwargs["parent_observation_id"] == "agent-span-789"
        assert call_kwargs["name"] == "tool_http_request"
        assert call_kwargs["input"] == {"url": "https://example.com"}
        assert call_kwargs["output"] == {"status": 200}
        assert call_kwargs["metadata"]["tool_name"] == "http_request"
        assert call_kwargs["metadata"]["execution_time"] == 0.5

    def test_create_tool_span_disabled(self, tracer_disabled):
        """Test creating tool span when disabled."""
        span = tracer_disabled.create_tool_span(
            trace_id="trace-123", parent_span_id="agent-span-789", tool_name="file_read"
        )

        assert span is None


class TestSpanEnding:
    """Test span ending."""

    def test_end_span_success(self, tracer_enabled):
        """Test ending span with success status."""
        span = MagicMock()

        tracer_enabled.end_span(span, status="success")

        span.end.assert_called_once()
        call_kwargs = span.end.call_args[1]
        assert "end_time" in call_kwargs

    def test_end_span_error(self, tracer_enabled):
        """Test ending span with error status."""
        span = MagicMock()
        error = ValueError("test error")

        tracer_enabled.end_span(span, status="error", error=error)

        span.end.assert_called_once()
        call_kwargs = span.end.call_args[1]
        assert call_kwargs["level"] == "ERROR"
        assert call_kwargs["status_message"] == "test error"
        assert call_kwargs["metadata"]["error_type"] == "ValueError"

    def test_end_span_disabled(self, tracer_disabled):
        """Test ending span when disabled."""
        span = MagicMock()

        tracer_disabled.end_span(span, status="success")

        # Should not call span.end
        span.end.assert_not_called()


class TestUserFeedback:
    """Test user feedback integration."""

    def test_add_user_feedback_enabled(self, tracer_enabled, mock_langfuse_client):
        """Test adding user feedback when enabled."""
        tracer_enabled.add_user_feedback(
            trace_id="trace-123", phase_number=2, action="approve", comment="Looks good", score=1.0
        )

        mock_langfuse_client.score.assert_called_once()

        call_kwargs = mock_langfuse_client.score.call_args[1]
        assert call_kwargs["trace_id"] == "trace-123"
        assert call_kwargs["name"] == "user_feedback"
        assert call_kwargs["value"] == 1.0
        assert call_kwargs["comment"] == "Looks good"

    def test_add_user_feedback_auto_score(self, tracer_enabled, mock_langfuse_client):
        """Test adding user feedback with automatic score mapping."""
        # Test approve
        tracer_enabled.add_user_feedback(trace_id="trace-123", phase_number=1, action="approve")
        assert mock_langfuse_client.score.call_args[1]["value"] == 1.0

        # Test skip
        tracer_enabled.add_user_feedback(trace_id="trace-123", phase_number=2, action="skip")
        assert mock_langfuse_client.score.call_args[1]["value"] == 0.5

        # Test request_changes
        tracer_enabled.add_user_feedback(
            trace_id="trace-123", phase_number=3, action="request_changes"
        )
        assert mock_langfuse_client.score.call_args[1]["value"] == 0.0

    def test_add_user_feedback_disabled(self, tracer_disabled):
        """Test adding user feedback when disabled."""
        # Should not raise error
        tracer_disabled.add_user_feedback(trace_id="trace-123", phase_number=1, action="approve")


class TestErrorTracking:
    """Test error tracking."""

    def test_track_error_enabled(self, tracer_enabled, mock_langfuse_client):
        """Test tracking error when enabled."""
        error = RuntimeError("test error")

        tracer_enabled.track_error(
            trace_id="trace-123",
            error=error,
            phase_number=3,
            agent_name="product_strategy_agent",
            context={"additional": "info"},
        )

        mock_langfuse_client.event.assert_called_once()

        call_kwargs = mock_langfuse_client.event.call_args[1]
        assert call_kwargs["trace_id"] == "trace-123"
        assert call_kwargs["name"] == "error"
        assert call_kwargs["level"] == "ERROR"
        assert call_kwargs["metadata"]["error_type"] == "RuntimeError"
        assert call_kwargs["metadata"]["error_message"] == "test error"
        assert call_kwargs["metadata"]["phase_number"] == 3
        assert call_kwargs["metadata"]["agent_name"] == "product_strategy_agent"
        assert call_kwargs["metadata"]["additional"] == "info"

    def test_track_error_disabled(self, tracer_disabled):
        """Test tracking error when disabled."""
        error = RuntimeError("test error")

        # Should not raise error
        tracer_disabled.track_error(trace_id="trace-123", error=error)


class TestCostCalculation:
    """Test cost calculation."""

    def test_calculate_cost_claude_sonnet(self, tracer_enabled):
        """Test cost calculation for Claude Sonnet."""
        cost = tracer_enabled._calculate_cost(
            model="anthropic.claude-3-5-sonnet-20241022-v2:0", input_tokens=1000, output_tokens=500
        )

        # 1000 * 0.003 / 1000 + 500 * 0.015 / 1000 = 0.003 + 0.0075 = 0.0105
        assert cost == pytest.approx(0.0105, rel=1e-6)

    def test_calculate_cost_nova_pro(self, tracer_enabled):
        """Test cost calculation for Nova Pro."""
        cost = tracer_enabled._calculate_cost(
            model="eu.amazon.nova-pro-v1:0", input_tokens=1000, output_tokens=500
        )

        # 1000 * 0.0008 / 1000 + 500 * 0.0032 / 1000 = 0.0008 + 0.0016 = 0.0024
        assert cost == pytest.approx(0.0024, rel=1e-6)

    def test_calculate_cost_unknown_model(self, tracer_enabled):
        """Test cost calculation for unknown model."""
        cost = tracer_enabled._calculate_cost(
            model="unknown-model", input_tokens=1000, output_tokens=500
        )

        # Should return 0.0 for unknown models
        assert cost == 0.0


class TestContextManagers:
    """Test context managers."""

    def test_trace_phase_context_manager_success(self, tracer_enabled, mock_langfuse_client):
        """Test trace_phase context manager with successful execution."""
        with tracer_enabled.trace_phase("trace-123", 1, "Concept Expansion") as span:
            assert span is not None

        # Should create and end span
        assert mock_langfuse_client.span.call_count >= 1

    def test_trace_phase_context_manager_error(self, tracer_enabled, mock_langfuse_client):
        """Test trace_phase context manager with error."""
        with pytest.raises(ValueError):
            with tracer_enabled.trace_phase("trace-123", 1, "Concept Expansion"):
                raise ValueError("test error")

        # Should create and end span with error
        assert mock_langfuse_client.span.call_count >= 1

    def test_trace_agent_context_manager_success(self, tracer_enabled, mock_langfuse_client):
        """Test trace_agent context manager with successful execution."""
        with tracer_enabled.trace_agent(
            "trace-123", "phase-span-456", "market_intelligence_agent"
        ) as span:
            assert span is not None

        # Should create and end span
        assert mock_langfuse_client.span.call_count >= 1

    def test_trace_agent_context_manager_error(self, tracer_enabled, mock_langfuse_client):
        """Test trace_agent context manager with error."""
        with pytest.raises(RuntimeError):
            with tracer_enabled.trace_agent(
                "trace-123", "phase-span-456", "market_intelligence_agent"
            ):
                raise RuntimeError("test error")

        # Should create and end span with error
        assert mock_langfuse_client.span.call_count >= 1


class TestFlush:
    """Test flush functionality."""

    def test_flush_enabled(self, tracer_enabled, mock_langfuse_client):
        """Test flushing traces when enabled."""
        tracer_enabled.flush()

        mock_langfuse_client.flush.assert_called_once()

    def test_flush_disabled(self, tracer_disabled):
        """Test flushing traces when disabled."""
        # Should not raise error
        tracer_disabled.flush()


class TestGlobalTracer:
    """Test global tracer instance."""

    def test_get_langfuse_tracer(self):
        """Test getting global tracer instance."""
        tracer1 = get_langfuse_tracer()
        tracer2 = get_langfuse_tracer()

        # Should return same instance
        assert tracer1 is tracer2


class TestModelPricing:
    """Test model pricing configuration."""

    def test_model_pricing_configured(self):
        """Test that model pricing is configured for all models."""
        expected_models = [
            "anthropic.claude-3-5-sonnet-20241022-v2:0",
            "eu.anthropic.claude-3-5-sonnet-20241022-v2:0",
            "us.anthropic.claude-3-5-sonnet-20241022-v2:0",
            "eu.amazon.nova-pro-v1:0",
            "us.amazon.nova-pro-v1:0",
        ]

        for model in expected_models:
            assert model in MODEL_PRICING
            pricing = MODEL_PRICING[model]
            assert pricing.input_price_per_1k > 0
            assert pricing.output_price_per_1k > 0
