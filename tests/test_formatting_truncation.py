"""
Tests for formatting and truncation functionality in ContextSummarizer.
"""

import pytest

from haytham.agents.utils.context_summarizer import ContextSummarizer


class TestSmartTruncation:
    """Test smart truncation at paragraph and sentence boundaries."""

    def test_truncate_at_paragraph_boundary(self):
        """Test that truncation happens at paragraph boundaries when possible."""
        summarizer = ContextSummarizer()

        text = "First paragraph.\n\nSecond paragraph.\n\nThird paragraph."
        max_chars = 30  # Should fit first paragraph + separator

        result = summarizer._truncate_smartly(text, max_chars)

        # Should include first paragraph and ellipsis
        assert "First paragraph." in result
        assert "Second paragraph." not in result
        assert "[...]" in result

    def test_truncate_at_sentence_boundary(self):
        """Test that truncation falls back to sentence boundaries."""
        summarizer = ContextSummarizer()

        text = "First sentence. Second sentence. Third sentence."
        max_chars = 30  # Should fit first sentence

        result = summarizer._truncate_smartly(text, max_chars)

        # Should include first sentence and ellipsis
        assert "First sentence." in result
        assert "Third sentence." not in result
        assert "[...]" in result

    def test_no_truncation_when_under_limit(self):
        """Test that text is not truncated when under the limit."""
        summarizer = ContextSummarizer()

        text = "Short text."
        max_chars = 100

        result = summarizer._truncate_smartly(text, max_chars)

        # Should return original text without ellipsis
        assert result == text
        assert "[...]" not in result

    def test_ellipsis_added_when_truncated(self):
        """Test that ellipsis is added when text is truncated."""
        summarizer = ContextSummarizer()

        text = "A" * 1000
        max_chars = 100

        result = summarizer._truncate_smartly(text, max_chars)

        # Should have ellipsis
        assert "[...]" in result
        assert len(result) < len(text)


class TestMarkdownFormatting:
    """Test consistent markdown formatting."""

    def test_agent_name_headers_use_double_hash(self):
        """Test that agent names are formatted with ## headers."""
        summarizer = ContextSummarizer(target_tokens=500)

        agent_outputs = {
            "code_analyzer_agent": "Analysis complete.",
            "market_intelligence_agent": "Market research done.",
        }

        result = summarizer.summarize_agent_outputs(agent_outputs)

        # Should have ## headers for agent names
        assert "## Code Analyzer Agent" in result
        assert "## Market Intelligence Agent" in result

    def test_section_separators_use_triple_dash(self):
        """Test that sections are separated with ---."""
        summarizer = ContextSummarizer(target_tokens=500)

        agent_outputs = {"agent_one": "First output.", "agent_two": "Second output."}

        result = summarizer.summarize_agent_outputs(agent_outputs)

        # Should have --- separator between agents
        assert "\n\n---\n\n" in result

    def test_section_names_use_double_asterisk(self):
        """Test that section names are formatted with ** bold."""
        summarizer = ContextSummarizer(target_tokens=500)

        agent_outputs = {
            "test_agent": "# Summary\nThis is a summary.\n\n# Conclusion\nThis is the conclusion."
        }

        result = summarizer.summarize_agent_outputs(agent_outputs)

        # Should have ** for section names
        assert "**Summary**" in result or "**Conclusion**" in result

    def test_consistent_spacing(self):
        """Test that spacing is consistent throughout."""
        summarizer = ContextSummarizer(target_tokens=500)

        agent_outputs = {
            "agent_one": "# Section One\nContent here.",
            "agent_two": "# Section Two\nMore content.",
        }

        result = summarizer.summarize_agent_outputs(agent_outputs)

        # Should have consistent \n\n spacing
        assert "\n\n" in result
        # Should not have excessive spacing
        assert "\n\n\n\n" not in result

    def test_metrics_formatting(self):
        """Test that metrics are formatted with ** and bullet points."""
        summarizer = ContextSummarizer(target_tokens=500)

        agent_outputs = {"test_agent": "The system has 1,000 users and $50,000 revenue."}

        result = summarizer.summarize_agent_outputs(agent_outputs)

        # Should have Key Metrics section if metrics found
        if "1,000" in result or "$50,000" in result:
            assert "**Key Metrics**" in result
            assert "- " in result  # Bullet point


class TestIntegratedFormatting:
    """Test that formatting and truncation work together."""

    def test_truncated_output_maintains_formatting(self):
        """Test that truncated output still has proper markdown formatting."""
        summarizer = ContextSummarizer(target_tokens=100)  # Very small target

        agent_outputs = {
            "test_agent": "# Summary\n" + ("A" * 1000) + "\n\n# Conclusion\n" + ("B" * 1000)
        }

        result = summarizer.summarize_agent_outputs(agent_outputs)

        # Should still have proper formatting
        assert "## Test Agent" in result
        # Should have truncation indicator
        assert "[...]" in result

    def test_multiple_agents_with_truncation(self):
        """Test formatting with multiple agents and truncation."""
        summarizer = ContextSummarizer(target_tokens=200)

        agent_outputs = {
            "agent_one": "# Summary\n" + ("Content " * 100),
            "agent_two": "# Conclusion\n" + ("More content " * 100),
        }

        result = summarizer.summarize_agent_outputs(agent_outputs)

        # Should have both agent headers
        assert "## Agent One" in result
        assert "## Agent Two" in result
        # Should have separator
        assert "---" in result
        # Should have truncation
        assert "[...]" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
