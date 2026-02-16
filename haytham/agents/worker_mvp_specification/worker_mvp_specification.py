"""
MVP Specification Agent for Haytham.

This agent transforms concept expansion output into detailed, actionable MVP
specifications that can be used by implementation teams. It defines scope,
user journeys, feature specifications, technical boundaries, and success metrics.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from strands import Agent

from haytham.agents.utils.logging_utils import create_agent_logger
from haytham.agents.utils.model_provider import create_model


class MVPSpecificationAgent:
    """
    Agent that creates MVP specifications from concept expansion output.

    This agent specializes in:
    - MVP scope definition (P0/P1/P2 prioritization)
    - User journey mapping with "aha moment" identification
    - Feature specifications with user stories and acceptance criteria
    - Technical boundary guidance
    - Success metrics definition
    """

    def __init__(
        self,
        model: Any | None = None,
        system_prompt: str | None = None,
        **kwargs,
    ):
        """
        Initialize the MVP Specification Agent.

        Args:
            model: BedrockModel instance (defaults to environment config)
            system_prompt: Custom system prompt (defaults to loading from prompt.txt)
            **kwargs: Additional arguments passed to Agent constructor
        """
        if model is None:
            model = create_model()

        if system_prompt is None:
            prompt_path = Path(__file__).parent / "worker_mvp_specification_prompt.txt"
            system_prompt = prompt_path.read_text().strip()

        self.model = model
        self.system_prompt = system_prompt
        self.kwargs = kwargs

        # Initialize agent logger
        self.logger = create_agent_logger("mvp_specification")

    def __call__(self, validation_context: str) -> str:
        """
        Generate MVP specification from ALL validation stage outputs.

        Args:
            validation_context: Combined outputs from all validation stages:
                - Concept Expansion (idea analysis)
                - Market Intelligence (market research)
                - Competitor Analysis (competitive landscape)
                - Risk Assessment (startup validation)
                - Validation Summary (synthesis report)

        Returns:
            Detailed MVP specification with scope, features, and success metrics
        """
        try:
            query = f"""Based on the following validation outputs from ALL stages, create a detailed MVP specification:

{validation_context}

---

Generate a complete MVP specification following the template in your instructions.

IMPORTANT:
- Use insights from Market Intelligence for market sizing and positioning
- Use insights from Competitor Analysis for differentiation strategy
- Use insights from Risk Assessment to avoid risky features
- Use the Validation Summary as the overall guidance
- Focus on creating actionable, implementable specifications that address identified opportunities and mitigate risks

CRITICAL - REQUIRED OUTPUT SECTIONS:
You MUST include these sections at the END of your output for the implementation pipeline:

1. ## DOMAIN MODEL
   - List ALL data entities (e.g., User, Workout, Challenge, Leaderboard)
   - Each entity needs: E-XXX ID, attributes with types, relationships

2. ## STORY DEPENDENCY GRAPH
   - Convert each P0 feature into a user story with S-XXX ID
   - Include dependencies on entities and other stories
   - Include acceptance criteria

3. ## UNCERTAINTY REGISTRY
   - Flag any ambiguous requirements with AMB-XXX IDs

4. PIPELINE_DATA_COMPLETE marker at the very end

Without these sections, the implementation pipeline cannot proceed. Refer to Section 10 of your instructions for the exact format."""

            # Log LLM input
            full_prompt = f"System Prompt:\n{self.system_prompt}\n\nQuery:\n{query}"
            self.logger.log_llm_input(full_prompt, metadata={"agent": "mvp_specification"})

            # Execute agent
            agent = Agent(
                model=self.model,
                system_prompt=self.system_prompt,
                **self.kwargs,
            )

            result = agent(query)

            # Log LLM output
            self.logger.log_llm_output(str(result), metadata={"agent": "mvp_specification"})

            return str(result)

        except Exception as e:
            self.logger.log_error(e, context="MVP specification generation")
            raise
