"""
File-based context passing for agent outputs.

This module provides utilities for agents to write their outputs to files
and read outputs from other agents, reducing conversation context size
and preventing context window overflow.
"""

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class FileContextManager:
    """
    Manages file-based context passing between agents.

    Each agent writes its output to a file, and subsequent agents can read
    only the outputs they need, dramatically reducing conversation context.
    """

    def __init__(self, output_dir: Path | None = None):
        """
        Initialize the file context manager.

        Args:
            output_dir: Directory to store agent outputs (defaults to ./agent_outputs)
        """
        if output_dir is None:
            output_dir = Path("./agent_outputs")

        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"FileContextManager initialized with output_dir: {self.output_dir}")

    def write_agent_output(
        self, agent_name: str, output: str, metadata: dict | None = None
    ) -> Path:
        """
        Write an agent's output to a file.

        Args:
            agent_name: Name of the agent (e.g., "code_analyzer_agent")
            output: The agent's output text
            metadata: Optional metadata to store with the output

        Returns:
            Path to the written file
        """
        # Sanitize agent name for filename
        safe_name = agent_name.replace(" ", "_").replace("/", "_")
        output_file = self.output_dir / f"{safe_name}.txt"
        metadata_file = self.output_dir / f"{safe_name}_metadata.json"

        # Write output
        output_file.write_text(output, encoding="utf-8")
        logger.info(f"Wrote {len(output)} chars to {output_file} for agent {agent_name}")

        # Write metadata if provided
        if metadata:
            metadata_file.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
            logger.debug(f"Wrote metadata to {metadata_file}")

        return output_file

    def read_agent_output(self, agent_name: str) -> str | None:
        """
        Read an agent's output from a file.

        Args:
            agent_name: Name of the agent to read output from

        Returns:
            The agent's output text, or None if file doesn't exist
        """
        safe_name = agent_name.replace(" ", "_").replace("/", "_")
        output_file = self.output_dir / f"{safe_name}.txt"

        if not output_file.exists():
            logger.warning(f"Output file not found for agent {agent_name}: {output_file}")
            return None

        output = output_file.read_text(encoding="utf-8")
        logger.info(f"Read {len(output)} chars from {output_file} for agent {agent_name}")

        return output

    def read_agent_metadata(self, agent_name: str) -> dict | None:
        """
        Read an agent's metadata from a file.

        Args:
            agent_name: Name of the agent to read metadata from

        Returns:
            The agent's metadata dict, or None if file doesn't exist
        """
        safe_name = agent_name.replace(" ", "_").replace("/", "_")
        metadata_file = self.output_dir / f"{safe_name}_metadata.json"

        if not metadata_file.exists():
            return None

        metadata = json.loads(metadata_file.read_text(encoding="utf-8"))
        logger.debug(f"Read metadata from {metadata_file}")

        return metadata

    def read_all_agent_outputs(
        self,
        summarize_if_large: bool = True,
        threshold_tokens: int = 15000,
        preserve_agents: list[str] | None = None,
    ) -> dict[str, str]:
        """
        Read outputs from all agents that have written files.

        Optionally applies automatic summarization if total context exceeds
        threshold, reducing context size while preserving key information.

        Args:
            summarize_if_large: Enable automatic summarization (default: True)
            threshold_tokens: Token threshold for triggering summarization (default: 20000)
            preserve_agents: Optional list of agent names to preserve in full

        Returns:
            Dictionary mapping agent names to their output text, or a single
            "_context_summary" entry if summarization was applied
        """
        agent_outputs = {}

        # Find all .txt files in output directory (excluding metadata files)
        for output_file in self.output_dir.glob("*.txt"):
            # Skip metadata files
            if output_file.stem.endswith("_metadata"):
                continue

            # Extract agent name from filename
            agent_name = output_file.stem

            # Read output
            output = output_file.read_text(encoding="utf-8")
            agent_outputs[agent_name] = output

            logger.debug(f"Read {len(output)} chars for agent {agent_name} from {output_file}")

        logger.info(
            f"Read outputs from {len(agent_outputs)} agents: {', '.join(agent_outputs.keys())}"
        )

        # Check if summarization should be applied (Requirement 7.2)
        if not summarize_if_large:
            # Summarization disabled (Requirement 4.5)
            logger.info("Automatic summarization disabled, returning original outputs")
            return agent_outputs

        if not agent_outputs:
            # No outputs to summarize (Requirement 4.5)
            logger.info("No agent outputs available, skipping summarization")
            return agent_outputs

        if summarize_if_large and agent_outputs:
            total_tokens = sum(len(output) // 4 for output in agent_outputs.values())

            logger.info(
                f"Total context size: ~{total_tokens:,} tokens "
                f"(threshold: {threshold_tokens:,} tokens)"
            )

            if total_tokens > threshold_tokens:
                # Apply automatic summarization (Requirement 7.2, 7.3)
                logger.info(
                    f"Context exceeds threshold ({total_tokens:,} > {threshold_tokens:,}), "
                    "applying automatic summarization"
                )

                try:
                    # Import here to avoid circular dependency
                    from haytham.agents.utils.context_summarizer import ContextSummarizer

                    # Create summarizer with target of 30% of threshold
                    target_tokens = int(threshold_tokens * 0.3)
                    summarizer = ContextSummarizer(target_tokens=target_tokens)

                    # Summarize outputs
                    summary = summarizer.summarize_agent_outputs(
                        agent_outputs, preserve_agents=preserve_agents
                    )

                    # Get statistics for logging
                    stats = summarizer.get_summary_stats(agent_outputs)

                    logger.info(
                        f"Summarization complete: {stats['original_tokens']:,} → "
                        f"{stats['estimated_summary_tokens']:,} tokens "
                        f"({stats['estimated_reduction_percent']:.1f}% reduction)"
                    )

                    # Return single summary entry (Requirement 7.3)
                    return {"_context_summary": summary}

                except Exception as e:
                    logger.error(f"Automatic summarization failed: {str(e)}", exc_info=True)
                    logger.warning("Falling back to original outputs")
                    # Fall through to return original outputs
            else:
                # Context is below threshold (Requirement 7.4)
                logger.info(
                    f"Context below threshold ({total_tokens:,} <= {threshold_tokens:,}), "
                    "no summarization applied"
                )

        # Return original outputs (Requirement 7.4)
        return agent_outputs

    def list_available_agents(self) -> list[str]:
        """
        List all agents that have written output files.

        Returns:
            List of agent names that have outputs available
        """
        agent_names = []

        for output_file in self.output_dir.glob("*.txt"):
            if not output_file.stem.endswith("_metadata"):
                agent_names.append(output_file.stem)

        return sorted(agent_names)

    def clear_outputs(self) -> None:
        """
        Clear all agent output files.

        This should be called at the start of a new workflow execution
        to ensure clean state.
        """
        count = 0
        for file in self.output_dir.glob("*"):
            if file.is_file():
                file.unlink()
                count += 1

        logger.info(f"Cleared {count} files from {self.output_dir}")

    def get_output_summary(self) -> dict:
        """
        Get a summary of all available agent outputs.

        Returns:
            Dictionary with summary information:
            - agent_count: Number of agents with outputs
            - total_chars: Total characters across all outputs
            - agents: List of agent names with their output sizes
        """
        agent_outputs = self.read_all_agent_outputs()

        agents_info = []
        total_chars = 0

        for agent_name, output in agent_outputs.items():
            char_count = len(output)
            total_chars += char_count
            agents_info.append(
                {"name": agent_name, "chars": char_count, "estimated_tokens": char_count // 4}
            )

        return {
            "agent_count": len(agent_outputs),
            "total_chars": total_chars,
            "estimated_total_tokens": total_chars // 4,
            "agents": sorted(agents_info, key=lambda x: x["chars"], reverse=True),
        }


# Global instance for convenience
_global_context_manager: FileContextManager | None = None


def get_file_context_manager(output_dir: Path | None = None) -> FileContextManager:
    """
    Get the global file context manager instance.

    Args:
        output_dir: Directory to store agent outputs (only used on first call)

    Returns:
        FileContextManager instance
    """
    global _global_context_manager

    if _global_context_manager is None:
        _global_context_manager = FileContextManager(output_dir)

    return _global_context_manager


def reset_file_context_manager() -> None:
    """Reset the global file context manager instance."""
    global _global_context_manager
    _global_context_manager = None
