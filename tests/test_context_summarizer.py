"""
Tests for ContextSummarizer class.

Tests the statistics functionality and core summarization features.
"""

import pytest

from haytham.agents.utils.context_summarizer import ContextSummarizer


class TestGetSummaryStats:
    """Test suite for get_summary_stats method."""

    def test_empty_input_returns_zero_stats(self):
        """Test that empty input returns statistics with zero values (Requirement 6.5)."""
        summarizer = ContextSummarizer(target_tokens=10000)

        stats = summarizer.get_summary_stats({})

        assert stats["original_tokens"] == 0
        assert stats["estimated_summary_tokens"] == 0
        assert stats["estimated_reduction_percent"] == 0.0
        assert stats["agent_count"] == 0
        assert stats["tokens_per_agent"] == 0

    def test_calculates_original_token_count(self):
        """Test that original token count is calculated correctly (Requirement 6.1)."""
        summarizer = ContextSummarizer(target_tokens=10000)

        agent_outputs = {
            "agent1": "a" * 400,  # ~100 tokens
            "agent2": "b" * 800,  # ~200 tokens
            "agent3": "c" * 1200,  # ~300 tokens
        }

        stats = summarizer.get_summary_stats(agent_outputs)

        # Total: 2400 chars / 4 = 600 tokens
        assert stats["original_tokens"] == 600

    def test_estimates_summary_tokens(self):
        """Test that summary tokens are estimated based on target (Requirement 6.2)."""
        summarizer = ContextSummarizer(target_tokens=5000)

        agent_outputs = {
            "agent1": "a" * 40000,  # ~10,000 tokens
            "agent2": "b" * 40000,  # ~10,000 tokens
        }

        stats = summarizer.get_summary_stats(agent_outputs)

        # Original: 20,000 tokens
        # Estimated: min(5000, 20000/3) = min(5000, 6666) = 5000
        assert stats["estimated_summary_tokens"] == 5000

    def test_calculates_reduction_percentage(self):
        """Test that reduction percentage is calculated correctly (Requirement 6.3)."""
        summarizer = ContextSummarizer(target_tokens=3000)

        agent_outputs = {
            "agent1": "a" * 40000,  # ~10,000 tokens
        }

        stats = summarizer.get_summary_stats(agent_outputs)

        # Original: 10,000 tokens
        # Estimated: min(3000, 10000/3) = 3000
        # Reduction: (1 - 3000/10000) * 100 = 70%
        assert stats["estimated_reduction_percent"] == 70.0

    def test_returns_agent_count(self):
        """Test that agent count is returned (Requirement 6.4)."""
        summarizer = ContextSummarizer(target_tokens=10000)

        agent_outputs = {
            "agent1": "content1",
            "agent2": "content2",
            "agent3": "content3",
        }

        stats = summarizer.get_summary_stats(agent_outputs)

        assert stats["agent_count"] == 3

    def test_returns_average_tokens_per_agent(self):
        """Test that average tokens per agent is calculated (Requirement 6.4)."""
        summarizer = ContextSummarizer(target_tokens=10000)

        agent_outputs = {
            "agent1": "a" * 400,  # ~100 tokens
            "agent2": "b" * 800,  # ~200 tokens
            "agent3": "c" * 1200,  # ~300 tokens
        }

        stats = summarizer.get_summary_stats(agent_outputs)

        # Total: 600 tokens / 3 agents = 200 tokens per agent
        assert stats["tokens_per_agent"] == 200

    def test_single_agent_stats(self):
        """Test statistics with a single agent."""
        summarizer = ContextSummarizer(target_tokens=5000)

        agent_outputs = {
            "agent1": "a" * 8000,  # ~2000 tokens
        }

        stats = summarizer.get_summary_stats(agent_outputs)

        assert stats["original_tokens"] == 2000
        assert stats["agent_count"] == 1
        assert stats["tokens_per_agent"] == 2000
        # Estimated: min(5000, 2000/3) = 666
        assert stats["estimated_summary_tokens"] == 666

    def test_large_context_stats(self):
        """Test statistics with large context requiring significant reduction."""
        summarizer = ContextSummarizer(target_tokens=10000)

        # Simulate 6 agents with large outputs
        agent_outputs = {
            f"agent{i}": "x" * 20000  # ~5000 tokens each
            for i in range(6)
        }

        stats = summarizer.get_summary_stats(agent_outputs)

        # Total: 30,000 tokens
        assert stats["original_tokens"] == 30000
        assert stats["agent_count"] == 6
        assert stats["tokens_per_agent"] == 5000
        # Estimated: min(10000, 30000/3) = 10000
        assert stats["estimated_summary_tokens"] == 10000
        # Reduction: (1 - 10000/30000) * 100 = 66.67%
        assert abs(stats["estimated_reduction_percent"] - 66.67) < 0.1


class TestContextSummarizerBasics:
    """Basic tests for ContextSummarizer initialization and core functionality."""

    def test_initialization_with_default_target(self):
        """Test that summarizer initializes with default target tokens."""
        summarizer = ContextSummarizer()
        assert summarizer.target_tokens == 3000

    def test_initialization_with_custom_target(self):
        """Test that summarizer initializes with custom target tokens."""
        summarizer = ContextSummarizer(target_tokens=5000)
        assert summarizer.target_tokens == 5000

    def test_empty_agent_outputs_returns_empty_string(self):
        """Test that empty agent outputs returns empty string (Requirement 1.5)."""
        summarizer = ContextSummarizer()
        result = summarizer.summarize_agent_outputs({})
        assert result == ""

    def test_format_agent_name(self):
        """Test agent name formatting."""
        summarizer = ContextSummarizer()

        assert summarizer._format_agent_name("code_analyzer_agent") == "Code Analyzer Agent"
        assert summarizer._format_agent_name("market_intelligence") == "Market Intelligence"
        assert summarizer._format_agent_name("simple") == "Simple"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
