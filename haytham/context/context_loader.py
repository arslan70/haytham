"""Context loading and management for stage-based workflow execution.

This module provides selective context loading based on stage requirements,
automatic preferences loading, context summarization, and caching.

Simplified for single-session architecture using stage slugs instead of phase numbers.
"""

import json
import logging
import re
from pathlib import Path
from typing import Any

from haytham.agents.utils.context_summarizer import ContextSummarizer
from haytham.phases.stage_config import (
    STAGES,
    get_stage_by_slug,
    get_stage_index,
)
from haytham.project.project_state import ProjectStateManager

logger = logging.getLogger(__name__)


class ContextLoader:
    """Manages context loading for stage-based workflow execution.

    The ContextLoader handles:
    - Selective context loading based on stage required_context
    - Automatic preferences loading from session/preferences.json
    - Context summarization for large outputs (>8K tokens)
    - Context caching to avoid re-reading files

    Stage Context Requirements (from StageConfig.required_context):
        idea-analysis: [] (no previous context)
        market-context: ["idea-analysis"]
        risk-assessment: ["idea-analysis", "market-context"]
        validation-summary: ["all"] (load ALL previous stages)
    """

    # Agent to stage mapping (for loading agent outputs from stage directories)
    AGENT_STAGES = {
        "concept_expansion": "idea-analysis",
        "market_intelligence": "market-context",
        "competitor_analysis": "market-context",
        "startup_validator": "risk-assessment",
        "report_synthesis": "validation-summary",
        # Legacy mappings (for backwards compatibility with old sessions)
        "niche_identification": "opportunity-discovery",
        "decision_agent": "opportunity-discovery",
        "product_strategy": "product-planning",
        "business_planning": "business-model",
        "claims_extraction": "validation",
        "three_track_validator": "validation",
        "risk_validator": "validation",
    }

    def __init__(
        self,
        base_dir: str = ".",
        summarization_threshold: int = 4000,
        target_summary_tokens: int = 2000,
    ):
        """Initialize the ContextLoader.

        Args:
            base_dir: Base directory containing session/ folder (default: ".")
            summarization_threshold: Token threshold for triggering summarization (default: 4000)
            target_summary_tokens: Target token count for summaries (default: 2000)
        """
        self.base_dir = Path(base_dir)
        self.session_dir = self.base_dir / "session"
        self.summarization_threshold = summarization_threshold
        self.target_summary_tokens = target_summary_tokens
        self.summarizer = ContextSummarizer(target_tokens=target_summary_tokens)

        # Initialize ProjectStateManager for system goal access
        self.project_state = ProjectStateManager(self.session_dir)

        # Context cache: {cache_key: context_dict}
        self._cache: dict[str, dict[str, Any]] = {}

        logger.info(
            f"ContextLoader initialized: base_dir={base_dir}, "
            f"session_dir={self.session_dir}, "
            f"summarization_threshold={summarization_threshold}, "
            f"target_summary_tokens={target_summary_tokens}"
        )

    def load_context(
        self,
        stage_slug: str,
        disable_summarization: bool = False,
    ) -> dict[str, Any]:
        """Load context for a specific stage.

        Args:
            stage_slug: Stage slug (e.g., "idea-refinement", "market-analysis")
            disable_summarization: If True, disable automatic summarization (default: False)

        Returns:
            Dict containing:
                - agent_outputs: Dict mapping agent names to their outputs
                - preferences: User preferences (if applicable)
                - system_goal: The system goal from project.yaml
                - _missing_agents: List of required agents with missing outputs
                - _context_size_tokens: Estimated token count
                - _summarized: Whether summarization was applied

        Raises:
            ValueError: If stage_slug is invalid
            FileNotFoundError: If session directory does not exist
        """
        # Validate stage slug
        try:
            stage = get_stage_by_slug(stage_slug)
        except ValueError as e:
            raise ValueError(f"Invalid stage_slug: {stage_slug}") from e

        # Check cache first
        cache_key = f"stage_{stage_slug}"
        if cache_key in self._cache:
            logger.info(f"Returning cached context for stage {stage_slug}")
            return self._cache[cache_key]

        logger.info(f"Loading context for stage: {stage.display_name} ({stage_slug})")

        # Verify session directory exists
        if not self.session_dir.exists():
            raise FileNotFoundError(f"Session directory not found: {self.session_dir}")

        # Get required agent outputs for this stage
        required_agents = self._get_required_agents(stage_slug)

        # Load agent outputs
        agent_outputs, missing_agents = self._load_agent_outputs(required_agents)

        # Load preferences if applicable (stages with requires_preferences=True)
        preferences = self._load_preferences(stage_slug)

        # Calculate context size
        context_size_tokens = self._estimate_tokens(agent_outputs, preferences)

        # Apply summarization if needed
        summarized = False
        if not disable_summarization and context_size_tokens > self.summarization_threshold:
            logger.info(
                f"Context size ({context_size_tokens} tokens) exceeds threshold "
                f"({self.summarization_threshold} tokens) - applying summarization"
            )
            agent_outputs = self._summarize_outputs(agent_outputs)
            summarized = True
            context_size_tokens = self._estimate_tokens(agent_outputs, preferences)

        # Get system goal from project state
        system_goal = self.project_state.get_system_goal()
        if not system_goal:
            raise ValueError("No system goal set in project.yaml. Cannot load context.")

        # Build context dict
        context = {
            "agent_outputs": agent_outputs,
            "preferences": preferences,
            "system_goal": system_goal,
            "_missing_agents": missing_agents,
            "_context_size_tokens": context_size_tokens,
            "_summarized": summarized,
        }

        # Log warnings for missing context
        if missing_agents:
            logger.warning(
                f"Missing required context for stage {stage_slug}: {', '.join(missing_agents)}"
            )

        logger.info(
            f"Context loaded for stage {stage_slug}: "
            f"{len(agent_outputs)} agents, {context_size_tokens} tokens, "
            f"summarized={summarized}, missing={len(missing_agents)}"
        )

        # Cache the context
        self._cache[cache_key] = context

        return context

    def clear_cache(self) -> None:
        """Clear the context cache.

        Should be called between sessions to prevent memory leaks.
        """
        cache_size = len(self._cache)
        self._cache.clear()
        logger.info(f"Context cache cleared ({cache_size} entries removed)")

    def _get_required_agents(self, stage_slug: str) -> list[str]:
        """Get list of required agent outputs for a stage.

        Args:
            stage_slug: Stage slug (e.g., "idea-refinement")

        Returns:
            List of required agent names
        """
        stage = get_stage_by_slug(stage_slug)
        required_context = stage.required_context

        # Handle "all" context loading for report-generation stage
        if required_context == ["all"]:
            # Load all agents from all previous stages
            all_agents = []
            current_index = get_stage_index(stage_slug)

            for i, prev_stage in enumerate(STAGES):
                if i >= current_index:
                    break  # Don't include current or future stages
                all_agents.extend(prev_stage.agent_names)

            return all_agents

        # Convert stage slugs to agent names
        required_agents = []
        for source in required_context:
            if source == "preferences":
                continue  # Preferences handled separately

            # source is a stage slug - get agents from that stage
            try:
                source_stage = get_stage_by_slug(source)
                required_agents.extend(source_stage.agent_names)
            except ValueError:
                logger.warning(f"Unknown context source: {source}")

        return required_agents

    def _load_agent_outputs(self, required_agents: list[str]) -> tuple[dict[str, str], list[str]]:
        """Load agent outputs from session directory.

        Args:
            required_agents: List of required agent names

        Returns:
            Tuple of (agent_outputs dict, missing_agents list)
        """
        agent_outputs = {}
        missing_agents = []

        for agent_name in required_agents:
            # Find the stage directory for this agent
            agent_stage_slug = self.AGENT_STAGES.get(agent_name)

            if agent_stage_slug is None:
                logger.warning(f"Unknown agent: {agent_name}")
                missing_agents.append(agent_name)
                continue

            stage_dir = self.session_dir / agent_stage_slug

            # Special handling for validation stage: load JSON file for startup_validator
            if agent_name == "startup_validator" and agent_stage_slug == "validation":
                json_file = stage_dir / "validation_report.json"
                if json_file.exists():
                    try:
                        content = json_file.read_text()
                        agent_outputs[agent_name] = content
                        logger.debug(
                            f"Loaded validation JSON for {agent_name}: {len(content)} chars"
                        )
                        continue
                    except Exception as e:
                        logger.warning(f"Failed to read validation_report.json: {e}")
                        # Fall through to try markdown file

            output_file = stage_dir / f"{agent_name}.md"

            if output_file.exists():
                try:
                    content = output_file.read_text()
                    # Extract just the output content (skip metadata)
                    output_content = self._extract_output_content(content)
                    agent_outputs[agent_name] = output_content
                    logger.debug(f"Loaded output for {agent_name}: {len(output_content)} chars")
                except Exception as e:
                    logger.error(f"Failed to read output for {agent_name}: {e}")
                    missing_agents.append(agent_name)
            else:
                logger.debug(f"Output file not found for {agent_name}: {output_file}")
                missing_agents.append(agent_name)

        return agent_outputs, missing_agents

    def _load_preferences(self, stage_slug: str) -> dict[str, Any] | None:
        """Load user preferences if available.

        Loads from session/preferences.json if the file exists.

        Args:
            stage_slug: Stage slug (e.g., "product-planning")

        Returns:
            User preferences dict or None if not available
        """
        # Load from session/preferences.json
        preferences_file = self.session_dir / "preferences.json"

        if preferences_file.exists():
            try:
                with open(preferences_file) as f:
                    preferences = json.load(f)
                if preferences and any(preferences.values()):
                    logger.info("Loaded preferences from session/preferences.json")
                    return preferences
            except Exception as e:
                logger.warning(f"Failed to load preferences.json: {e}")

        logger.debug(f"No preferences available for stage {stage_slug}")
        return None

    def _extract_output_content(self, full_content: str) -> str:
        """Extract just the output content from agent output file.

        Skips metadata sections and extracts the ## Output section.

        Args:
            full_content: Full agent output file content

        Returns:
            Extracted output content
        """
        # Find the "## Output" section
        if "## Output" not in full_content:
            return full_content

        # Extract content after "## Output"
        parts = full_content.split("## Output", 1)
        if len(parts) < 2:
            return full_content

        output_section = parts[1]

        # Check if output contains a raw SwarmResult string (from old buggy saves)
        # If so, try to extract the actual text from it
        if "SwarmResult(" in output_section and "'text':" in output_section:
            # Extract text content from the SwarmResult string representation
            # Pattern: 'text': 'actual content here'
            text_matches = re.findall(r"'text':\s*'([^']*(?:''[^']*)*)'", output_section)
            if text_matches:
                # Join all text blocks and unescape
                extracted_text = "\n\n".join(text_matches)
                # Unescape common escape sequences
                extracted_text = extracted_text.replace("\\n", "\n")
                extracted_text = extracted_text.replace("\\t", "\t")
                extracted_text = extracted_text.replace("\\'", "'")
                return extracted_text.strip()

        # Remove any subsequent top-level sections (## Error Details, ## Metadata, etc.)
        # But keep content headers like "## 1. Problem" or "## 2. Solution"
        # Look for sections that are NOT numbered (i.e., metadata sections)
        # Split on sections that start with ## but NOT followed by a digit
        # This preserves numbered sections like "## 1. Problem" but removes "## Error Details"
        lines = output_section.split("\n")
        result_lines = []
        for line in lines:
            # Check if this is a top-level metadata section (not a numbered content section)
            if line.strip().startswith("## ") and not re.match(r"##\s+\d+\.", line.strip()):
                # This is a metadata section like "## Error Details", stop here
                break
            result_lines.append(line)

        output_section = "\n".join(result_lines)

        return output_section.strip()

    def _estimate_tokens(
        self, agent_outputs: dict[str, str], preferences: dict[str, Any] | None
    ) -> int:
        """Estimate token count for context.

        Uses rough approximation: 1 token ≈ 4 characters.

        Args:
            agent_outputs: Dict of agent outputs
            preferences: User preferences dict

        Returns:
            Estimated token count
        """
        total_chars = sum(len(output) for output in agent_outputs.values())

        if preferences:
            # Estimate preferences as JSON string
            prefs_str = json.dumps(preferences)
            total_chars += len(prefs_str)

        return total_chars // 4

    def _summarize_outputs(self, agent_outputs: dict[str, str]) -> dict[str, str]:
        """Summarize agent outputs to reduce context size.

        Args:
            agent_outputs: Dict of agent outputs

        Returns:
            Dict of summarized agent outputs
        """
        # Use ContextSummarizer to create extractive summaries
        summarized_text = self.summarizer.summarize_agent_outputs(agent_outputs)

        # Parse summarized text back into dict format
        # The summarizer formats as: ## Agent Name\n\ncontent\n\n---\n\n## Next Agent...
        summarized_outputs = {}

        sections = summarized_text.split("\n\n---\n\n")

        for section in sections:
            if section.strip():
                # Extract agent name from ## header
                lines = section.split("\n", 1)
                if lines and lines[0].startswith("## "):
                    agent_name_display = lines[0].replace("## ", "").strip()

                    # Remove [PRESERVED] marker if present
                    agent_name_display = agent_name_display.replace(" [PRESERVED]", "")

                    # Convert display name back to agent name format
                    agent_name = agent_name_display.lower().replace(" ", "_")

                    # Get content (everything after first line)
                    content = lines[1] if len(lines) > 1 else ""

                    summarized_outputs[agent_name] = content.strip()

        return summarized_outputs

    def validate_stage_context(self, stage_slug: str) -> tuple[bool, list[str]]:
        """Validate that required context is available for a stage.

        Args:
            stage_slug: Stage slug (e.g., "market-analysis")

        Returns:
            Tuple of (is_valid, list_of_missing_agents)
        """
        try:
            context = self.load_context(
                stage_slug,
                disable_summarization=True,  # Don't summarize for validation
            )

            missing_agents = context.get("_missing_agents", [])

            if missing_agents:
                logger.warning(
                    f"Stage {stage_slug} validation failed: "
                    f"missing {len(missing_agents)} required agents"
                )
                return False, missing_agents

            logger.info(f"Stage {stage_slug} context validation passed")
            return True, []

        except Exception as e:
            logger.error(f"Stage {stage_slug} context validation error: {e}")
            return False, [str(e)]

    def enforce_temporal_guardrail(self, stage_slug: str, requested_files: list[str]) -> None:
        """Enforce temporal guardrail: prevent stages before validation-summary from loading risk artifacts.

        Args:
            stage_slug: Current stage slug
            requested_files: List of file paths being requested

        Raises:
            ValueError: If stage before validation-summary attempts to load risk artifacts
        """
        # validation-summary can access everything
        if stage_slug == "validation-summary":
            return

        # Check for risk assessment stage artifacts
        forbidden_files = [
            "startup_validator.md",
            "validation_report.json",
        ]

        for requested_file in requested_files:
            for forbidden in forbidden_files:
                if forbidden in requested_file:
                    raise ValueError(
                        f"Temporal guardrail violation: Stage {stage_slug} cannot access "
                        f"risk artifact: {forbidden}. "
                        f"Only validation-summary stage may access risk artifacts."
                    )

        logger.debug(f"Temporal guardrail check passed for stage {stage_slug}")

    def get_system_goal(self) -> str:
        """Get the system goal from project state.

        Reads the system goal from project.yaml via ProjectStateManager.

        Returns:
            The system goal string

        Raises:
            ValueError: If system goal is not set in project.yaml
        """
        goal = self.project_state.get_system_goal()
        if not goal:
            raise ValueError("No system goal set in project.yaml")
        return goal
