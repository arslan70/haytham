"""Unit tests for ContextLoader.

Tests the single-session ContextLoader that uses stage slugs.
Updated to use current stage slugs from the stage registry.
"""

import json
import tempfile
from pathlib import Path

import pytest
import yaml

from haytham.context import ContextLoader

# Test system goal used across all tests
TEST_SYSTEM_GOAL = "A product that lets you create a startup by writing prompts"


@pytest.fixture
def temp_base_dir():
    """Create a temporary base directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def sample_session(temp_base_dir):
    """Create a sample session with agent outputs using current stage slugs."""
    session_dir = Path(temp_base_dir) / "session"
    session_dir.mkdir(parents=True)

    # Create project.yaml with system_goal
    project_yaml = {
        "system_goal": TEST_SYSTEM_GOAL,
        "created_at": "2024-01-15T10:00:00Z",
        "updated_at": "2024-01-15T10:00:00Z",
        "status": "in_progress",
    }
    (session_dir / "project.yaml").write_text(yaml.dump(project_yaml, default_flow_style=False))

    # Create stage directories using current slugs
    for slug in [
        "idea-analysis",
        "market-context",
        "risk-assessment",
        "validation-summary",
        "mvp-scope",
        "capability-model",
    ]:
        (session_dir / slug).mkdir()

    # Create agent outputs
    concept_output = """# Agent Output: concept_expansion

## Metadata
- Agent: concept_expansion
- Stage: idea-analysis - Idea Analysis
- Executed: 2024-01-15T10:00:00Z
- Duration: 120s
- Status: completed

## Execution Details
- Model: claude-sonnet-4.5
- Input Tokens: 1000
- Output Tokens: 2000
- Tools Used: []

## Output

This is the concept expansion output.
It contains the expanded startup idea.
"""

    market_output = """# Agent Output: market_intelligence

## Metadata
- Agent: market_intelligence
- Stage: market-context - Market Context
- Executed: 2024-01-15T10:05:00Z
- Duration: 180s
- Status: completed

## Execution Details
- Model: claude-sonnet-4.5
- Input Tokens: 2000
- Output Tokens: 3000
- Tools Used: [http_request, file_write]

## Output

This is the market intelligence output.
It contains market research findings.
"""

    competitor_output = """# Agent Output: competitor_analysis

## Metadata
- Agent: competitor_analysis
- Stage: market-context - Market Context
- Executed: 2024-01-15T10:10:00Z
- Duration: 200s
- Status: completed

## Execution Details
- Model: claude-sonnet-4.5
- Input Tokens: 2500
- Output Tokens: 3500
- Tools Used: [http_request, file_write]

## Output

This is the competitor analysis output.
It contains competitive landscape analysis.
"""

    validator_output = """# Agent Output: startup_validator

## Metadata
- Agent: startup_validator
- Stage: risk-assessment - Risk Assessment
- Executed: 2024-01-15T10:15:00Z
- Duration: 150s
- Status: completed

## Execution Details
- Model: claude-sonnet-4.5
- Input Tokens: 3000
- Output Tokens: 2500
- Tools Used: [file_read, file_write]

## Output

This is the startup validator output.
It contains risk assessment findings.
"""

    # Write agent outputs to stage directories
    (session_dir / "idea-analysis" / "concept_expansion.md").write_text(concept_output)
    (session_dir / "market-context" / "market_intelligence.md").write_text(market_output)
    (session_dir / "market-context" / "competitor_analysis.md").write_text(competitor_output)
    (session_dir / "risk-assessment" / "startup_validator.md").write_text(validator_output)

    # Create preferences.json in session directory
    preferences = {
        "target_niche": "B2B SaaS",
        "business_model": "subscription",
        "pricing_strategy": "usage-based",
        "go_to_market_approach": "product-led",
        "risk_tolerance": "medium",
        "target_region": "North America",
        "user_confirmed": True,
        "timestamp": "2024-01-15T10:20:00Z",
    }

    (session_dir / "preferences.json").write_text(json.dumps(preferences, indent=2))

    return {"session_dir": session_dir, "base_dir": temp_base_dir}


class TestContextLoader:
    """Test suite for ContextLoader."""

    def test_initialization(self, temp_base_dir):
        """Test ContextLoader initialization."""
        loader = ContextLoader(
            base_dir=temp_base_dir,
            summarization_threshold=20000,
            target_summary_tokens=10000,
        )

        assert loader.base_dir == Path(temp_base_dir)
        assert loader.session_dir == Path(temp_base_dir) / "session"
        assert loader.summarization_threshold == 20000
        assert loader.target_summary_tokens == 10000
        assert len(loader._cache) == 0

    def test_get_system_goal(self, sample_session):
        """Test that get_system_goal() returns the system goal from project.yaml."""
        loader = ContextLoader(base_dir=sample_session["base_dir"])

        assert loader.get_system_goal() == TEST_SYSTEM_GOAL

    def test_get_system_goal_missing(self, temp_base_dir):
        """Test that get_system_goal() raises error when project.yaml is missing."""
        session_dir = Path(temp_base_dir) / "session"
        session_dir.mkdir(parents=True)

        loader = ContextLoader(base_dir=temp_base_dir)

        with pytest.raises(ValueError, match="No system goal set in project.yaml"):
            loader.get_system_goal()

    def test_load_context_idea_analysis(self, sample_session):
        """Test loading context for idea-analysis stage (no previous context)."""
        loader = ContextLoader(base_dir=sample_session["base_dir"])

        context = loader.load_context(stage_slug="idea-analysis")

        # idea-analysis should have no agent outputs (first stage)
        assert context["agent_outputs"] == {}
        assert context["system_goal"] == TEST_SYSTEM_GOAL
        assert context["_missing_agents"] == []
        # Token count may be > 0 if preferences are loaded
        assert context["_summarized"] is False

    def test_load_context_market_context(self, sample_session):
        """Test loading context for market-context stage."""
        loader = ContextLoader(base_dir=sample_session["base_dir"])

        context = loader.load_context(stage_slug="market-context")

        # market-context requires ["idea-analysis"] -> concept_expansion
        assert "concept_expansion" in context["agent_outputs"]
        assert (
            "This is the concept expansion output" in context["agent_outputs"]["concept_expansion"]
        )
        assert context["system_goal"] == TEST_SYSTEM_GOAL
        assert context["_missing_agents"] == []
        assert context["_context_size_tokens"] > 0

    def test_load_context_risk_assessment(self, sample_session):
        """Test loading context for risk-assessment stage."""
        loader = ContextLoader(base_dir=sample_session["base_dir"])

        context = loader.load_context(stage_slug="risk-assessment")

        # risk-assessment requires ["idea-analysis", "market-context"]
        assert "concept_expansion" in context["agent_outputs"]
        assert "market_intelligence" in context["agent_outputs"]
        assert "competitor_analysis" in context["agent_outputs"]
        assert context["system_goal"] == TEST_SYSTEM_GOAL
        assert context["_missing_agents"] == []

    def test_context_caching(self, sample_session):
        """Test context caching functionality."""
        loader = ContextLoader(base_dir=sample_session["base_dir"])

        context1 = loader.load_context(stage_slug="market-context")
        context2 = loader.load_context(stage_slug="market-context")

        assert context1 is context2

    def test_clear_cache(self, sample_session):
        """Test cache clearing."""
        loader = ContextLoader(base_dir=sample_session["base_dir"])

        loader.load_context(stage_slug="market-context")
        assert len(loader._cache) > 0

        loader.clear_cache()
        assert len(loader._cache) == 0

    def test_validate_stage_context(self, sample_session):
        """Test stage context validation."""
        loader = ContextLoader(base_dir=sample_session["base_dir"])

        # market-context should be valid (concept_expansion exists)
        is_valid, missing = loader.validate_stage_context(stage_slug="market-context")
        assert is_valid is True
        assert missing == []

    def test_temporal_guardrail_enforcement(self, sample_session):
        """Test temporal guardrail prevents early stages from accessing risk artifacts."""
        loader = ContextLoader(base_dir=sample_session["base_dir"])

        # mvp-scope should not be able to access validation_report.json
        with pytest.raises(ValueError, match="Temporal guardrail violation"):
            loader.enforce_temporal_guardrail(
                stage_slug="mvp-scope",
                requested_files=["validation_report.json"],
            )

        # validation-summary should be able to access validation_report.json
        loader.enforce_temporal_guardrail(
            stage_slug="validation-summary",
            requested_files=["validation_report.json"],
        )

    def test_invalid_stage_slug(self, sample_session):
        """Test error handling for invalid stage slug."""
        loader = ContextLoader(base_dir=sample_session["base_dir"])

        with pytest.raises(ValueError, match="Invalid stage_slug"):
            loader.load_context(stage_slug="invalid-stage")

        with pytest.raises(ValueError, match="Invalid stage_slug"):
            loader.load_context(stage_slug="phase_1")

    def test_session_not_found(self, temp_base_dir):
        """Test error handling when session directory doesn't exist."""
        # Remove session directory if it exists
        session_dir = Path(temp_base_dir) / "session"
        if session_dir.exists():
            import shutil

            shutil.rmtree(session_dir)

        loader = ContextLoader(base_dir=temp_base_dir)

        with pytest.raises(FileNotFoundError, match="Session directory not found"):
            loader.load_context(stage_slug="market-context")

    def test_context_summarization(self, sample_session):
        """Test automatic context summarization when threshold is exceeded."""
        loader = ContextLoader(
            base_dir=sample_session["base_dir"],
            summarization_threshold=10,
            target_summary_tokens=5,
        )

        context = loader.load_context(stage_slug="risk-assessment")

        assert context["_summarized"] is True
        assert context["_context_size_tokens"] < 100

    def test_disable_summarization(self, sample_session):
        """Test disabling automatic summarization."""
        loader = ContextLoader(
            base_dir=sample_session["base_dir"],
            summarization_threshold=10,
            target_summary_tokens=5,
        )

        context = loader.load_context(
            stage_slug="risk-assessment",
            disable_summarization=True,
        )

        assert context["_summarized"] is False

    def test_extract_output_content(self, sample_session):
        """Test extraction of output content from agent output files."""
        loader = ContextLoader(base_dir=sample_session["base_dir"])

        full_content = """# Agent Output: test_agent

## Metadata
- Agent: test_agent
- Stage: idea-analysis - Idea Analysis

## Output

This is the actual output content.
It should be extracted.

## Error Details
- Error: None
"""

        extracted = loader._extract_output_content(full_content)

        assert "This is the actual output content" in extracted
        assert "## Metadata" not in extracted
        assert "## Error Details" not in extracted

    def test_estimate_tokens(self, sample_session):
        """Test token estimation."""
        loader = ContextLoader(base_dir=sample_session["base_dir"])

        agent_outputs = {
            "agent1": "a" * 400,
            "agent2": "b" * 800,
        }

        preferences = {"key": "value"}

        tokens = loader._estimate_tokens(agent_outputs, preferences)

        assert 250 < tokens < 350

    def test_system_goal_in_context(self, sample_session):
        """Test that system_goal is always included in context."""
        loader = ContextLoader(base_dir=sample_session["base_dir"])

        for stage_slug in ["idea-analysis", "market-context", "risk-assessment"]:
            loader.clear_cache()
            context = loader.load_context(stage_slug=stage_slug)
            assert "system_goal" in context
            assert context["system_goal"] == TEST_SYSTEM_GOAL

    def test_preferences_loaded_when_available(self, sample_session):
        """Test that preferences are loaded from session/preferences.json."""
        loader = ContextLoader(base_dir=sample_session["base_dir"])

        context = loader.load_context(stage_slug="risk-assessment")

        # Preferences are loaded for all stages when preferences.json exists
        assert context["preferences"] is not None
        assert context["preferences"]["target_niche"] == "B2B SaaS"
        assert context["preferences"]["business_model"] == "subscription"
