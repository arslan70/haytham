"""Tests for UserFeedbackLoop.

Updated for synchronous API - tests the record_* methods and format_stage_results.
"""

import pytest

from haytham.feedback.user_feedback_loop import (
    ChangeRequest,
    FeedbackAction,
    UserFeedbackLoop,
)
from haytham.session.session_manager import SessionManager


@pytest.fixture
def temp_session_dir(tmp_path):
    """Create temporary session directory."""
    session_dir = tmp_path / "session"
    session_dir.mkdir(parents=True, exist_ok=True)

    # Create stage directories
    stage_dirs = [
        "idea-analysis",
        "market-context",
        "risk-assessment",
        "validation-summary",
    ]

    for stage_dir_name in stage_dirs:
        stage_dir = session_dir / stage_dir_name
        stage_dir.mkdir(parents=True, exist_ok=True)

    return tmp_path


@pytest.fixture
def session_manager(temp_session_dir):
    """Create SessionManager instance."""
    return SessionManager(base_dir=str(temp_session_dir))


@pytest.fixture
def feedback_loop(session_manager):
    """Create UserFeedbackLoop instance."""
    return UserFeedbackLoop(session_manager=session_manager)


class TestChangeRequest:
    """Tests for ChangeRequest dataclass."""

    def test_change_request_creation(self):
        """Test creating a ChangeRequest."""
        request = ChangeRequest(change_type="modify_prompt", modified_prompt="New prompt")

        assert request.change_type == "modify_prompt"
        assert request.modified_prompt == "New prompt"
        assert request.additional_guidance is None
        assert request.timestamp is not None

    def test_change_request_with_guidance(self):
        """Test creating a ChangeRequest with guidance."""
        request = ChangeRequest(change_type="provide_guidance", additional_guidance="Focus on X")

        assert request.change_type == "provide_guidance"
        assert request.additional_guidance == "Focus on X"
        assert request.modified_prompt is None

    def test_change_request_retry_same(self):
        """Test creating a retry_with_same ChangeRequest."""
        request = ChangeRequest(change_type="retry_with_same")

        assert request.change_type == "retry_with_same"
        assert request.modified_prompt is None
        assert request.additional_guidance is None


class TestUserFeedbackLoop:
    """Tests for UserFeedbackLoop class."""

    def test_initialization(self, feedback_loop, session_manager):
        """Test UserFeedbackLoop initialization."""
        assert feedback_loop.session_manager is session_manager

    def test_record_approval(self, feedback_loop, temp_session_dir):
        """Test record_approval method."""
        action = feedback_loop.record_approval(stage_slug="idea-analysis", comments="Looks good!")

        assert action == FeedbackAction.APPROVE

        # Verify feedback was saved
        feedback_path = temp_session_dir / "session" / "idea-analysis" / "user_feedback.md"
        assert feedback_path.exists()

        content = feedback_path.read_text()
        assert "approved" in content.lower()
        assert "Looks good!" in content

    def test_record_approval_default_comment(self, feedback_loop, temp_session_dir):
        """Test record_approval with default comment."""
        action = feedback_loop.record_approval(stage_slug="idea-analysis")

        assert action == FeedbackAction.APPROVE

        feedback_path = temp_session_dir / "session" / "idea-analysis" / "user_feedback.md"
        content = feedback_path.read_text()
        assert "User approved stage results" in content

    def test_record_skip(self, feedback_loop, temp_session_dir):
        """Test record_skip method."""
        action = feedback_loop.record_skip(stage_slug="market-context", comments="Skipping for now")

        assert action == FeedbackAction.SKIP

        # Verify feedback was saved
        feedback_path = temp_session_dir / "session" / "market-context" / "user_feedback.md"
        assert feedback_path.exists()

        content = feedback_path.read_text()
        assert "skip" in content.lower()

    def test_record_change_request_modify_prompt(self, feedback_loop, temp_session_dir):
        """Test record_change_request with modified prompt."""
        change_request = ChangeRequest(
            change_type="modify_prompt", modified_prompt="New custom prompt for this stage"
        )

        action = feedback_loop.record_change_request(
            stage_slug="risk-assessment", change_request=change_request, retry_count=0
        )

        assert action == FeedbackAction.REQUEST_CHANGES

        # Verify feedback was saved
        feedback_path = temp_session_dir / "session" / "risk-assessment" / "user_feedback.md"
        assert feedback_path.exists()

        content = feedback_path.read_text()
        assert "retry_with_changes" in content.lower()
        assert "modify_prompt" in content

    def test_record_change_request_provide_guidance(self, feedback_loop, temp_session_dir):
        """Test record_change_request with additional guidance."""
        change_request = ChangeRequest(
            change_type="provide_guidance", additional_guidance="Focus on technical risks"
        )

        action = feedback_loop.record_change_request(
            stage_slug="risk-assessment", change_request=change_request, retry_count=1
        )

        assert action == FeedbackAction.REQUEST_CHANGES

        feedback_path = temp_session_dir / "session" / "risk-assessment" / "user_feedback.md"
        content = feedback_path.read_text()
        assert "provide_guidance" in content

    def test_record_change_request_retry_same(self, feedback_loop, temp_session_dir):
        """Test record_change_request with retry_with_same."""
        change_request = ChangeRequest(change_type="retry_with_same")

        action = feedback_loop.record_change_request(
            stage_slug="validation-summary", change_request=change_request, retry_count=0
        )

        assert action == FeedbackAction.REQUEST_CHANGES

    def test_format_stage_results(self, feedback_loop):
        """Test format_stage_results method."""
        result = feedback_loop.format_stage_results(
            stage_slug="idea-analysis",
            agent_outputs={"concept_expansion": "This is a test output that is quite long " * 50},
            duration=125.7,
            tokens_used=15000,
            cost=0.0375,
        )

        assert "Idea Analysis" in result
        assert "2m 5s" in result  # Duration formatted
        assert "15,000" in result  # Tokens formatted
        assert "$0.0375" in result  # Cost formatted
        assert "concept_expansion" in result
        assert "truncated" in result  # Long output should be truncated

    def test_format_stage_results_short_duration(self, feedback_loop):
        """Test format_stage_results with short duration."""
        result = feedback_loop.format_stage_results(
            stage_slug="idea-analysis",
            agent_outputs={"concept_expansion": "Short output"},
            duration=45.3,
            tokens_used=5000,
            cost=0.0125,
        )

        assert "45s" in result  # Duration in seconds only
        assert "5,000" in result
        assert "$0.0125" in result

    def test_format_stage_results_multiple_agents(self, feedback_loop):
        """Test format_stage_results with multiple agents."""
        result = feedback_loop.format_stage_results(
            stage_slug="market-context",
            agent_outputs={
                "market_intelligence": "Market data...",
                "competitor_analysis": "Competitor data...",
            },
            duration=180.0,
            tokens_used=25000,
            cost=0.0625,
        )

        assert "market_intelligence" in result
        assert "competitor_analysis" in result
        assert "3m 0s" in result


class TestFeedbackAction:
    """Tests for FeedbackAction enum."""

    def test_feedback_action_values(self):
        """Test FeedbackAction enum values."""
        assert FeedbackAction.APPROVE.value == "approved"
        assert FeedbackAction.REQUEST_CHANGES.value == "retry_with_changes"
        assert FeedbackAction.SKIP.value == "skip_stage"
