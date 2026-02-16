"""
Context summarization for reducing conversation context size.

This module provides utilities to extract key information from agent outputs
and create concise summaries, preventing context window overflow while
preserving essential information for downstream agents.
"""

import logging
import re

logger = logging.getLogger(__name__)


class ContextSummarizer:
    """
    Extracts key information from agent outputs to reduce context size.

    Uses extractive summarization to preserve exact information while
    dramatically reducing token count.
    """

    def __init__(self, target_tokens: int = 3000):
        """
        Initialize the context summarizer.

        Args:
            target_tokens: Target token count for summary (default: 3000)
        """
        self.target_tokens = target_tokens
        logger.info(f"ContextSummarizer initialized with target: {target_tokens} tokens")

    def summarize_agent_outputs(
        self, agent_outputs: dict[str, str], preserve_agents: list[str] = None
    ) -> str:
        """
        Create extractive summary of all agent outputs.

        Args:
            agent_outputs: Dictionary mapping agent names to their outputs
            preserve_agents: List of agent names to preserve in full (optional)

        Returns:
            Summarized context string with key information from all agents
        """
        # Handle empty input (Requirement 1.5)
        if not agent_outputs:
            logger.warning("Empty agent_outputs dict provided - returning empty string")
            return ""

        try:
            # Log start with agent count and target (Requirement 4.1)
            logger.info(
                f"Starting summarization: {len(agent_outputs)} agent outputs, "
                f"target: {self.target_tokens} tokens"
            )

            # Calculate original size
            original_tokens = sum(len(output) // 4 for output in agent_outputs.values())
            logger.info(f"Original context size: ~{original_tokens:,} tokens")

            # Handle preserve_agents parameter (Requirement 5.1, 5.4, 5.5)
            preserve_agents = preserve_agents or []

            # Validate preserve_agents list
            invalid_agents = [name for name in preserve_agents if name not in agent_outputs]
            if invalid_agents:
                logger.warning(f"Preserve list contains agents not in outputs: {invalid_agents}")

            # Filter to only valid preserved agents
            preserve_agents = [name for name in preserve_agents if name in agent_outputs]

            # Determine which agents to summarize
            agents_to_summarize = [
                name for name in agent_outputs.keys() if name not in preserve_agents
            ]

            # Log preservation strategy
            if preserve_agents:
                logger.info(
                    f"Preserving {len(preserve_agents)} agent(s) in full: "
                    f"{', '.join(preserve_agents)}"
                )

            if not agents_to_summarize:
                # All agents preserved (Requirement 5.5)
                logger.info("All agents preserved - no summarization applied")

            # Calculate tokens per agent (Requirement 5.2)
            if agents_to_summarize:
                tokens_per_agent = self.target_tokens // len(agents_to_summarize)
                logger.info(
                    f"Token allocation: {tokens_per_agent} tokens per agent "
                    f"({len(agents_to_summarize)} agents to summarize)"
                )
            else:
                tokens_per_agent = self.target_tokens

            # Summarize each agent
            summaries = []

            for agent_name, output in agent_outputs.items():
                try:
                    # Log per-agent processing (Requirement 4.2)
                    logger.debug(f"Processing agent: {agent_name}")

                    if agent_name in preserve_agents:
                        # Preserve in full with clear marking (Requirement 5.3)
                        formatted_name = self._format_agent_name(agent_name)
                        summary = f"## {formatted_name} [PRESERVED]\n\n{output}"
                        logger.debug(
                            f"Preserved {agent_name} in full: "
                            f"{len(output)} chars (~{len(output) // 4} tokens)"
                        )
                    else:
                        # Summarize
                        summary = self._summarize_single_output(
                            agent_name, output, tokens_per_agent
                        )
                        logger.debug(
                            f"Summarized {agent_name}: "
                            f"{len(output)} chars → {len(summary)} chars "
                            f"(~{len(output) // 4} → ~{len(summary) // 4} tokens)"
                        )

                    summaries.append(summary)

                except Exception as agent_error:
                    # Log error with agent name (Requirement 4.4)
                    logger.error(
                        f"Error processing agent '{agent_name}': {str(agent_error)}", exc_info=True
                    )
                    # Include original output as fallback for this agent
                    formatted_name = self._format_agent_name(agent_name)
                    summaries.append(f"## {formatted_name}\n\n{output}")

            # Combine summaries
            combined = "\n\n---\n\n".join(summaries)

            # Log completion with statistics (Requirement 4.3)
            summary_tokens = len(combined) // 4
            reduction = (1 - summary_tokens / original_tokens) * 100 if original_tokens > 0 else 0

            logger.info(
                f"Summarization complete: {original_tokens:,} → {summary_tokens:,} tokens "
                f"({reduction:.1f}% reduction)"
            )

            return combined

        except Exception as e:
            # Error handling with fallback (Requirement 1.4, 4.4)
            logger.error(f"Summarization failed with error: {str(e)}", exc_info=True)
            logger.warning("Falling back to original outputs due to summarization error")

            # Return original outputs as fallback
            fallback_parts = []
            for agent_name, output in agent_outputs.items():
                fallback_parts.append(f"## {self._format_agent_name(agent_name)}\n\n{output}")

            return "\n\n---\n\n".join(fallback_parts)

    def _summarize_single_output(self, agent_name: str, output: str, target_tokens: int) -> str:
        """
        Summarize a single agent's output using extractive methods.

        Preserves key metrics and prioritizes important sections like
        summary, conclusion, and key findings.

        Args:
            agent_name: Name of the agent
            output: The agent's full output
            target_tokens: Target token count for this agent's summary

        Returns:
            Summarized output
        """
        target_chars = target_tokens * 4

        # Extract key sections with priorities and metrics
        sections = self._extract_key_sections(output)
        metrics = self._extract_metrics(output)

        # Build summary
        summary_parts = [f"## {self._format_agent_name(agent_name)}"]
        current_chars = len(summary_parts[0])
        added_sections = set()

        # Add metrics section if metrics found (Requirement 2.2, 3.3)
        if metrics:
            metrics_text = "\n\n**Key Metrics**\n" + "\n".join(f"- {m}" for m in metrics)
            if current_chars + len(metrics_text) < target_chars:
                summary_parts.append(metrics_text)
                current_chars += len(metrics_text)

        # Sort sections by priority (0 = highest priority)
        sorted_sections = sorted(
            sections.items(),
            key=lambda x: x[1][1],  # Sort by priority value
        )

        # Add sections in priority order (Requirement 3.2)
        for section_name, (content, _priority) in sorted_sections:
            # Skip "Key Metrics" section since we extract metrics separately
            if section_name.lower() == "key metrics":
                continue

            if section_name not in added_sections:
                remaining = target_chars - current_chars
                if remaining > 100:  # At least 100 chars
                    truncated = self._truncate_smartly(content, remaining - 50)
                    section_text = f"\n\n**{section_name}**\n{truncated}"
                    summary_parts.append(section_text)
                    current_chars += len(section_text)
                    added_sections.add(section_name)
                else:
                    break

        return "".join(summary_parts)

    def _extract_metrics(self, output: str) -> list[str]:
        """
        Extract key metrics from agent output.

        Identifies lines containing numbers, percentages, currency, and
        other quantitative information.

        Args:
            output: Agent output text

        Returns:
            List of lines containing metrics (max 10)
        """
        metrics = []

        # Patterns for different metric types
        patterns = [
            r"\$[\d,]+(?:\.\d+)?[KMB]?",  # Currency: $1,000.00, $2.5M, $100K
            r"\d+(?:,\d{3})*(?:\.\d+)?%",  # Percentage: 15.5%
            r"\d+(?:,\d{3})*(?:\.\d+)?\s*(?:tokens|users|customers|lines|files)",  # Counts with units
            r"\d+(?:,\d{3})*(?:\.\d+)?[KMB]",  # Abbreviated numbers: 1.5M, 100K
            r"\d+(?:\.\d+)?x",  # Multipliers: 2.5x
        ]

        combined_pattern = "|".join(patterns)

        for line in output.split("\n"):
            line = line.strip()
            if line and re.search(combined_pattern, line):
                # Avoid duplicate metrics
                if line not in metrics:
                    metrics.append(line)
                    if len(metrics) >= 10:
                        break

        return metrics

    def _extract_key_sections(self, output: str) -> dict[str, tuple[str, int]]:
        """
        Extract key sections from markdown output with priority ordering.

        Identifies and prioritizes summary, conclusion, key findings, and overview
        sections to ensure they appear first in summaries.

        Args:
            output: Agent output text

        Returns:
            Dictionary mapping section names to tuples of (content, priority)
            where priority is 0 (highest) to 3 (lowest)
        """
        sections = {}

        # Priority keywords for section classification
        priority_keywords = {
            0: ["summary", "executive summary"],  # Highest priority
            1: ["conclusion", "conclusions"],
            2: ["key findings", "key findings", "overview", "highlights"],
            3: [],  # Default priority for other sections
        }

        # Parse markdown headers
        header_pattern = r"^(#{1,6})\s+(.+?)$"
        lines = output.split("\n")

        current_section = None
        current_content = []
        section_order = []  # Track original order

        for line in lines:
            match = re.match(header_pattern, line)
            if match:
                # Save previous section
                if current_section:
                    priority = self._get_section_priority(current_section, priority_keywords)
                    sections[current_section] = ("\n".join(current_content).strip(), priority)
                    section_order.append(current_section)

                # Start new section
                current_section = match.group(2).strip()
                current_content = []
            else:
                if current_section:
                    current_content.append(line)

        # Save last section
        if current_section:
            priority = self._get_section_priority(current_section, priority_keywords)
            sections[current_section] = ("\n".join(current_content).strip(), priority)
            section_order.append(current_section)

        # If no sections found, treat entire output as one section
        if not sections:
            sections["Content"] = (output, 3)

        return sections

    def _get_section_priority(
        self, section_name: str, priority_keywords: dict[int, list[str]]
    ) -> int:
        """
        Determine priority level for a section based on its name.

        Args:
            section_name: Name of the section
            priority_keywords: Dictionary mapping priority levels to keyword lists

        Returns:
            Priority level (0 = highest, 3 = lowest)
        """
        section_lower = section_name.lower()

        for priority, keywords in priority_keywords.items():
            for keyword in keywords:
                if keyword in section_lower:
                    return priority

        return 3  # Default priority

    def _truncate_smartly(self, text: str, max_chars: int) -> str:
        """
        Truncate text intelligently at sentence or paragraph boundaries.

        Args:
            text: Text to truncate
            max_chars: Maximum characters

        Returns:
            Truncated text
        """
        if len(text) <= max_chars:
            return text

        # Try to truncate at paragraph boundary
        paragraphs = text.split("\n\n")
        result = []
        current_len = 0

        for para in paragraphs:
            if current_len + len(para) + 2 <= max_chars:
                result.append(para)
                current_len += len(para) + 2
            else:
                # Try to fit partial paragraph at sentence boundary
                sentences = re.split(r"([.!?]\s+)", para)
                for i in range(0, len(sentences), 2):
                    sentence = sentences[i]
                    if i + 1 < len(sentences):
                        sentence += sentences[i + 1]

                    if current_len + len(sentence) <= max_chars:
                        result.append(sentence)
                        current_len += len(sentence)
                    else:
                        break
                break

        truncated = "\n\n".join(result)

        # Add ellipsis if truncated
        if len(truncated) < len(text):
            truncated += "\n\n[...]"

        return truncated

    def _format_agent_name(self, agent_name: str) -> str:
        """Format agent name for display."""
        return agent_name.replace("_", " ").title()

    def get_summary_stats(self, agent_outputs: dict[str, str]) -> dict:
        """
        Get statistics about summarization potential.

        Args:
            agent_outputs: Dictionary mapping agent names to their outputs

        Returns:
            Dictionary with statistics
        """
        # Handle empty input
        if not agent_outputs:
            logger.warning("Empty agent_outputs dict provided to get_summary_stats")
            return {
                "original_tokens": 0,
                "estimated_summary_tokens": 0,
                "estimated_reduction_percent": 0.0,
                "agent_count": 0,
                "tokens_per_agent": 0,
            }

        original_tokens = sum(len(output) // 4 for output in agent_outputs.values())

        # Estimate summary size
        estimated_summary_tokens = min(self.target_tokens, original_tokens // 3)
        estimated_reduction = (
            (1 - estimated_summary_tokens / original_tokens) * 100 if original_tokens > 0 else 0.0
        )

        stats = {
            "original_tokens": original_tokens,
            "estimated_summary_tokens": estimated_summary_tokens,
            "estimated_reduction_percent": estimated_reduction,
            "agent_count": len(agent_outputs),
            "tokens_per_agent": original_tokens // len(agent_outputs) if agent_outputs else 0,
        }

        logger.debug(f"Summary statistics calculated: {stats}")

        return stats
