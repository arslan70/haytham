"""Tests for ChangeRequestHandler.

Updated for single-session architecture - uses SessionManager instead of CheckpointManager.
Updated for stage-based workflow - uses stage_slug instead of phase_num.
"""

import time

import pytest

from haytham.feedback.change_request_handler import (
    ChangeRequestHandler,
    RetryConfig,
)
from haytham.feedback.user_feedback_loop import ChangeRequest
from haytham.session.session_manager import SessionManager


@pytest.fixture
def temp_session_dir(tmp_path):
    """Create temporary session directory structure with stage slug directories."""
    session_dir = tmp_path / "session"
    session_dir.mkdir(parents=True, exist_ok=True)

    # Create stage directories using slugs
    stage_slugs = [
        "idea-analysis",
        "market-context",
        "risk-assessment",
        "pivot-strategy",
        "validation-summary",
        "mvp-scope",
        "capability-model",
        "system-traits",
        "build-buy-analysis",
        "architecture-decisions",
        "story-generation",
        "story-validation",
        "dependency-ordering",
    ]

    for slug in stage_slugs:
        (session_dir / slug).mkdir(parents=True, exist_ok=True)

    return tmp_path


@pytest.fixture
def session_manager(temp_session_dir):
    """Create SessionManager instance."""
    return SessionManager(base_dir=str(temp_session_dir))


@pytest.fixture
def change_request_handler(session_manager):
    """Create ChangeRequestHandler instance."""
    return ChangeRequestHandler(session_manager=session_manager)


class TestRetryConfig:
    """Tests for RetryConfig."""

    def test_default_config(self):
        """Test default retry configuration."""
        config = RetryConfig()

        assert config.max_retries == 3
        assert config.base_delay == 1.0
        assert config.max_delay == 60.0
        assert config.exponential_base == 2.0

    def test_custom_config(self):
        """Test custom retry configuration."""
        config = RetryConfig(
            max_retries=5,
            base_delay=2.0,
            max_delay=120.0,
            exponential_base=3.0,
        )

        assert config.max_retries == 5
        assert config.base_delay == 2.0
        assert config.max_delay == 120.0
        assert config.exponential_base == 3.0

    def test_calculate_delay_exponential_growth(self):
        """Test exponential backoff delay calculation."""
        config = RetryConfig(base_delay=1.0, exponential_base=2.0, max_delay=60.0)

        assert config.calculate_delay(0) == 1.0
        assert config.calculate_delay(1) == 2.0
        assert config.calculate_delay(2) == 4.0
        assert config.calculate_delay(3) == 8.0
        assert config.calculate_delay(4) == 16.0
        assert config.calculate_delay(5) == 32.0

    def test_calculate_delay_max_cap(self):
        """Test that delay is capped at max_delay."""
        config = RetryConfig(base_delay=1.0, exponential_base=2.0, max_delay=60.0)

        assert config.calculate_delay(6) == 60.0
        assert config.calculate_delay(7) == 60.0
        assert config.calculate_delay(10) == 60.0

    def test_calculate_delay_custom_base(self):
        """Test delay calculation with custom exponential base."""
        config = RetryConfig(base_delay=2.0, exponential_base=3.0, max_delay=100.0)

        assert config.calculate_delay(0) == 2.0
        assert config.calculate_delay(1) == 6.0
        assert config.calculate_delay(2) == 18.0
        assert config.calculate_delay(3) == 54.0


class TestChangeRequestHandler:
    """Tests for ChangeRequestHandler."""

    def test_initialization(self, change_request_handler, session_manager):
        """Test handler initialization."""
        assert change_request_handler.session_manager is session_manager
        assert change_request_handler.retry_config is not None
        assert change_request_handler.retry_config.max_retries == 3

    def test_initialization_with_custom_config(self, session_manager):
        """Test handler initialization with custom retry config."""
        custom_config = RetryConfig(max_retries=5, base_delay=2.0)
        handler = ChangeRequestHandler(session_manager=session_manager, retry_config=custom_config)

        assert handler.retry_config.max_retries == 5
        assert handler.retry_config.base_delay == 2.0

    def test_handle_modify_prompt(self, change_request_handler, temp_session_dir):
        """Test handling modify_prompt change request."""
        change_request = ChangeRequest(
            change_type="modify_prompt",
            modified_prompt="New custom prompt for this stage",
        )

        modified_query, should_retry = change_request_handler.handle_change_request(
            stage_slug="idea-analysis",
            change_request=change_request,
            default_query="Default stage query",
            retry_count=0,
        )

        assert modified_query == "New custom prompt for this stage"
        assert should_retry

        # Verify feedback was saved
        feedback_file = temp_session_dir / "session" / "idea-analysis" / "user_feedback.md"
        assert feedback_file.exists()

        content = feedback_file.read_text()
        assert "Modified prompt:" in content
        assert "retry_with_changes" in content
        assert "Retry Count: 1" in content

    def test_handle_provide_guidance(self, change_request_handler, temp_session_dir):
        """Test handling provide_guidance change request."""
        change_request = ChangeRequest(
            change_type="provide_guidance",
            additional_guidance="Focus on B2B market segment",
        )

        modified_query, should_retry = change_request_handler.handle_change_request(
            stage_slug="market-context",
            change_request=change_request,
            default_query="Conduct market research",
            retry_count=0,
        )

        assert "Conduct market research" in modified_query
        assert "Additional guidance: Focus on B2B market segment" in modified_query
        assert should_retry

        # Verify feedback was saved
        feedback_file = temp_session_dir / "session" / "market-context" / "user_feedback.md"
        assert feedback_file.exists()

        content = feedback_file.read_text()
        assert "Additional guidance:" in content
        assert "Focus on B2B market segment" in content

    def test_handle_retry_with_same(self, change_request_handler, temp_session_dir):
        """Test handling retry_with_same change request."""
        change_request = ChangeRequest(change_type="retry_with_same")

        modified_query, should_retry = change_request_handler.handle_change_request(
            stage_slug="risk-assessment",
            change_request=change_request,
            default_query="Identify profitable niches",
            retry_count=0,
        )

        assert modified_query == "Identify profitable niches"
        assert should_retry

        # Verify feedback was saved
        feedback_file = temp_session_dir / "session" / "risk-assessment" / "user_feedback.md"
        assert feedback_file.exists()

        content = feedback_file.read_text()
        assert "Retry with same settings" in content

    def test_max_retries_exceeded(self, change_request_handler, temp_session_dir):
        """Test that max retries prevents further retries."""
        change_request = ChangeRequest(change_type="retry_with_same")

        modified_query, should_retry = change_request_handler.handle_change_request(
            stage_slug="idea-analysis",
            change_request=change_request,
            default_query="Default query",
            retry_count=3,
        )

        assert modified_query == "Default query"
        assert not should_retry

        # Verify max retries feedback was saved
        feedback_file = temp_session_dir / "session" / "idea-analysis" / "user_feedback.md"
        assert feedback_file.exists()

        content = feedback_file.read_text()
        assert "Max retries" in content
        assert "max_retries_exceeded" in content

    def test_exponential_backoff_delay(self, change_request_handler):
        """Test that exponential backoff delay is applied."""
        change_request = ChangeRequest(change_type="retry_with_same")

        start_time = time.time()

        modified_query, should_retry = change_request_handler.handle_change_request(
            stage_slug="idea-analysis",
            change_request=change_request,
            default_query="Default query",
            retry_count=1,
        )

        elapsed_time = time.time() - start_time

        assert elapsed_time >= 1.8
        assert should_retry

    def test_no_delay_on_first_attempt(self, change_request_handler):
        """Test that no delay is applied on first attempt (retry_count=0)."""
        change_request = ChangeRequest(change_type="retry_with_same")

        start_time = time.time()

        modified_query, should_retry = change_request_handler.handle_change_request(
            stage_slug="idea-analysis",
            change_request=change_request,
            default_query="Default query",
            retry_count=0,
        )

        elapsed_time = time.time() - start_time

        assert elapsed_time < 0.1
        assert should_retry

    def test_should_allow_retry(self, change_request_handler):
        """Test should_allow_retry method."""
        assert change_request_handler.should_allow_retry(0)
        assert change_request_handler.should_allow_retry(1)
        assert change_request_handler.should_allow_retry(2)
        assert not change_request_handler.should_allow_retry(3)
        assert not change_request_handler.should_allow_retry(4)

    def test_get_retry_delay(self, change_request_handler):
        """Test get_retry_delay method."""
        assert change_request_handler.get_retry_delay(0) == 1.0
        assert change_request_handler.get_retry_delay(1) == 2.0
        assert change_request_handler.get_retry_delay(2) == 4.0
        assert change_request_handler.get_retry_delay(3) == 8.0

    def test_empty_modified_prompt_fallback(self, change_request_handler):
        """Test fallback to default when modified prompt is empty."""
        change_request = ChangeRequest(change_type="modify_prompt", modified_prompt="")

        modified_query, should_retry = change_request_handler.handle_change_request(
            stage_slug="idea-analysis",
            change_request=change_request,
            default_query="Default query",
            retry_count=0,
        )

        assert modified_query == "Default query"
        assert should_retry

    def test_empty_guidance_fallback(self, change_request_handler):
        """Test fallback to default when guidance is empty."""
        change_request = ChangeRequest(change_type="provide_guidance", additional_guidance="")

        modified_query, should_retry = change_request_handler.handle_change_request(
            stage_slug="idea-analysis",
            change_request=change_request,
            default_query="Default query",
            retry_count=0,
        )

        assert modified_query == "Default query"
        assert should_retry

    def test_long_prompt_truncation_in_feedback(self, change_request_handler, temp_session_dir):
        """Test that long prompts are truncated in feedback file."""
        long_prompt = "A" * 300

        change_request = ChangeRequest(change_type="modify_prompt", modified_prompt=long_prompt)

        modified_query, should_retry = change_request_handler.handle_change_request(
            stage_slug="idea-analysis",
            change_request=change_request,
            default_query="Default query",
            retry_count=0,
        )

        # Verify feedback was saved with truncation
        feedback_file = temp_session_dir / "session" / "idea-analysis" / "user_feedback.md"

        content = feedback_file.read_text()
        assert "..." in content
        assert "A" * 300 not in content

    def test_multiple_retries_increment_count(self, change_request_handler, temp_session_dir):
        """Test that retry count increments correctly across multiple retries."""
        change_request = ChangeRequest(change_type="retry_with_same")

        for retry_count in range(3):
            _, should_retry = change_request_handler.handle_change_request(
                stage_slug="idea-analysis",
                change_request=change_request,
                default_query="Default query",
                retry_count=retry_count,
            )
            assert should_retry

        # Fourth retry (should fail - max retries exceeded)
        _, should_retry = change_request_handler.handle_change_request(
            stage_slug="idea-analysis",
            change_request=change_request,
            default_query="Default query",
            retry_count=3,
        )
        assert not should_retry


class TestIntegration:
    """Integration tests for ChangeRequestHandler."""

    def test_full_workflow_with_retries(self, change_request_handler, temp_session_dir):
        """Test complete workflow with multiple retries."""
        # First attempt: provide guidance
        change_request_1 = ChangeRequest(
            change_type="provide_guidance",
            additional_guidance="Focus on enterprise customers",
        )

        query_1, should_retry_1 = change_request_handler.handle_change_request(
            stage_slug="market-context",
            change_request=change_request_1,
            default_query="Conduct market research",
            retry_count=0,
        )

        assert "Focus on enterprise customers" in query_1
        assert should_retry_1

        # Second attempt: modify prompt
        change_request_2 = ChangeRequest(
            change_type="modify_prompt",
            modified_prompt="Research only B2B SaaS market",
        )

        query_2, should_retry_2 = change_request_handler.handle_change_request(
            stage_slug="market-context",
            change_request=change_request_2,
            default_query="Conduct market research",
            retry_count=1,
        )

        assert query_2 == "Research only B2B SaaS market"
        assert should_retry_2

        # Third attempt: retry with same
        change_request_3 = ChangeRequest(change_type="retry_with_same")

        query_3, should_retry_3 = change_request_handler.handle_change_request(
            stage_slug="market-context",
            change_request=change_request_3,
            default_query="Conduct market research",
            retry_count=2,
        )

        assert query_3 == "Conduct market research"
        assert should_retry_3

        # Fourth attempt: should fail (max retries)
        change_request_4 = ChangeRequest(change_type="retry_with_same")

        query_4, should_retry_4 = change_request_handler.handle_change_request(
            stage_slug="market-context",
            change_request=change_request_4,
            default_query="Conduct market research",
            retry_count=3,
        )

        assert not should_retry_4
