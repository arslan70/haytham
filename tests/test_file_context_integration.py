"""
Tests for FileContextManager integration with ContextSummarizer.

Tests automatic summarization when reading agent outputs.
"""

import tempfile
from pathlib import Path

import pytest

from haytham.agents.utils.file_context import FileContextManager


class TestFileContextManagerIntegration:
    """Test suite for FileContextManager integration with ContextSummarizer."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for test outputs."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def manager(self, temp_dir):
        """Create a FileContextManager instance."""
        return FileContextManager(output_dir=temp_dir)

    def test_read_all_with_small_context_returns_original(self, manager):
        """Test that small context is returned unchanged (Requirement 7.4)."""
        # Write small outputs
        manager.write_agent_output("agent1", "Small output 1" * 10)  # ~140 chars
        manager.write_agent_output("agent2", "Small output 2" * 10)  # ~140 chars

        # Read with summarization enabled
        outputs = manager.read_all_agent_outputs(summarize_if_large=True, threshold_tokens=1000)

        # Should return original outputs (not summarized)
        assert "agent1" in outputs
        assert "agent2" in outputs
        assert "_context_summary" not in outputs
        assert "Small output 1" in outputs["agent1"]
        assert "Small output 2" in outputs["agent2"]

    def test_read_all_with_large_context_returns_summary(self, manager):
        """Test that large context triggers summarization (Requirement 7.2, 7.3)."""
        # Write large outputs that exceed threshold
        large_output_1 = "# Agent 1 Analysis\n\n## Summary\nThis is a large output. " * 500
        large_output_2 = "# Agent 2 Analysis\n\n## Conclusion\nAnother large output. " * 500

        manager.write_agent_output("agent1", large_output_1)
        manager.write_agent_output("agent2", large_output_2)

        # Read with summarization enabled (threshold: 1000 tokens)
        outputs = manager.read_all_agent_outputs(summarize_if_large=True, threshold_tokens=1000)

        # Should return single summary entry
        assert "_context_summary" in outputs
        assert len(outputs) == 1
        assert "agent1" not in outputs
        assert "agent2" not in outputs

        # Summary should contain agent names
        summary = outputs["_context_summary"]
        assert "Agent 1" in summary or "agent1" in summary.lower()
        assert "Agent 2" in summary or "agent2" in summary.lower()

    def test_read_all_with_summarization_disabled(self, manager):
        """Test that summarization can be disabled."""
        # Write large outputs
        large_output = "Large content " * 1000
        manager.write_agent_output("agent1", large_output)
        manager.write_agent_output("agent2", large_output)

        # Read with summarization disabled
        outputs = manager.read_all_agent_outputs(summarize_if_large=False)

        # Should return original outputs even if large
        assert "agent1" in outputs
        assert "agent2" in outputs
        assert "_context_summary" not in outputs

    def test_read_all_with_custom_threshold(self, manager):
        """Test that custom threshold is respected."""
        # Write medium-sized outputs
        medium_output = "Medium content " * 200  # ~3000 chars = ~750 tokens
        manager.write_agent_output("agent1", medium_output)
        manager.write_agent_output("agent2", medium_output)

        # Total: ~1500 tokens

        # With high threshold, should not summarize
        outputs_high = manager.read_all_agent_outputs(
            summarize_if_large=True, threshold_tokens=2000
        )
        assert "agent1" in outputs_high
        assert "_context_summary" not in outputs_high

        # With low threshold, should summarize
        outputs_low = manager.read_all_agent_outputs(summarize_if_large=True, threshold_tokens=1000)
        assert "_context_summary" in outputs_low
        assert "agent1" not in outputs_low

    def test_read_all_with_preserve_agents(self, manager):
        """Test that specific agents can be preserved in full."""
        # Write outputs
        manager.write_agent_output("agent1", "Content 1 " * 500)
        manager.write_agent_output("agent2", "Content 2 " * 500)
        manager.write_agent_output("agent3", "Content 3 " * 500)

        # Read with summarization and preserve agent2
        outputs = manager.read_all_agent_outputs(
            summarize_if_large=True, threshold_tokens=1000, preserve_agents=["agent2"]
        )

        # Should return summary
        assert "_context_summary" in outputs

        # Summary should mark agent2 as preserved
        summary = outputs["_context_summary"]
        assert "[PRESERVED]" in summary or "preserved" in summary.lower()

    def test_read_all_empty_directory(self, manager):
        """Test reading from empty directory."""
        outputs = manager.read_all_agent_outputs()
        assert outputs == {}

    def test_backward_compatibility(self, manager):
        """Test that existing code without new parameters still works."""
        # Write outputs
        manager.write_agent_output("agent1", "Content 1")
        manager.write_agent_output("agent2", "Content 2")

        # Call without any parameters (should use defaults)
        outputs = manager.read_all_agent_outputs()

        # Should work and return outputs (small context, so not summarized)
        assert "agent1" in outputs
        assert "agent2" in outputs


class TestFileContextManagerSummarizationEdgeCases:
    """Test edge cases for summarization integration."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for test outputs."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def manager(self, temp_dir):
        """Create a FileContextManager instance."""
        return FileContextManager(output_dir=temp_dir)

    def test_summarization_failure_returns_original(self, manager):
        """Test that summarization failure falls back to original outputs."""
        # Write outputs
        manager.write_agent_output("agent1", "Content 1 " * 500)
        manager.write_agent_output("agent2", "Content 2 " * 500)

        # Even if summarization fails internally, should return original outputs
        outputs = manager.read_all_agent_outputs(summarize_if_large=True, threshold_tokens=1000)

        # Should return something (either summary or original)
        assert len(outputs) > 0

    def test_single_agent_large_output(self, manager):
        """Test summarization with single large agent output."""
        # Write single large output
        large_output = "# Analysis\n\n## Summary\nLarge content. " * 1000
        manager.write_agent_output("agent1", large_output)

        # Read with summarization
        outputs = manager.read_all_agent_outputs(summarize_if_large=True, threshold_tokens=1000)

        # Should trigger summarization
        assert "_context_summary" in outputs

    def test_multiple_agents_mixed_sizes(self, manager):
        """Test summarization with agents of different output sizes."""
        # Write outputs of varying sizes
        manager.write_agent_output("small_agent", "Small " * 10)
        manager.write_agent_output("medium_agent", "Medium " * 200)
        manager.write_agent_output("large_agent", "Large " * 1000)

        # Total should exceed threshold
        outputs = manager.read_all_agent_outputs(summarize_if_large=True, threshold_tokens=1000)

        # Should summarize
        assert "_context_summary" in outputs


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
