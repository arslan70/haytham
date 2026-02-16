"""
Concept Expansion Agent for Haytham.

This agent transforms vague startup ideas into structured, actionable concepts
using problem-solution frameworks, Jobs-to-be-Done methodology, and design
thinking approaches. It expands raw ideas into comprehensive problem statements,
opportunity assessments, and solution concepts.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from strands import Agent, tool

# Import logging utilities
from haytham.agents.utils.agent_output_writer import write_agent_output_to_file
from haytham.agents.utils.logging_utils import create_agent_logger
from haytham.agents.utils.model_provider import create_model


class ConceptExpansionAgent:
    """
    Agent that expands raw ideas into structured concepts.

    This agent specializes in:
    - Problem statement clarification using JTBD framework
    - Opportunity identification and validation
    - Solution concept development
    - Assumption identification
    - Initial feature brainstorming
    - Problem-solution fit assessment
    """

    def __init__(self, model: Any | None = None, system_prompt: str | None = None, **kwargs):
        """
        Initialize the Concept Expansion Agent.

        Args:
            model: BedrockModel instance (defaults to Claude Sonnet 4.5)
            system_prompt: Custom system prompt (defaults to loading from prompt.txt)
            **kwargs: Additional arguments passed to Agent constructor
        """
        if model is None:
            model = create_model()

        if system_prompt is None:
            prompt_path = Path(__file__).parent / "worker_concept_expansion_prompt.txt"
            system_prompt = prompt_path.read_text().strip()

        self.model = model
        self.system_prompt = system_prompt
        self.kwargs = kwargs

        # Initialize agent logger
        self.logger = create_agent_logger("concept_expansion")

    def __call__(self, idea: str) -> str:
        """
        Expand raw idea into structured concept.

        Args:
            idea: Raw startup idea text

        Returns:
            Structured concept with problem statement, opportunity analysis, and solution approach
        """
        try:
            query = f"Expand this startup idea into a structured concept:\n\n{idea}"

            # Log LLM input
            full_prompt = f"System Prompt:\n{self.system_prompt}\n\nQuery:\n{query}"
            self.logger.log_llm_input(full_prompt, metadata={"agent": "concept_expansion"})

            # Execute agent
            agent = Agent(model=self.model, system_prompt=self.system_prompt, **self.kwargs)

            result = agent(query)

            # Log LLM output
            self.logger.log_llm_output(str(result), metadata={"agent": "concept_expansion"})

            return result

        except Exception as e:
            self.logger.log_error(e, context="Concept expansion execution")
            raise

    from haytham.agents.utils.agent_output_writer import write_agent_output_to_file


@tool
def concept_expansion_tool(idea: str) -> str:
    """
    Expands raw startup ideas into structured concepts with problem, opportunity, and solution.

    This tool transforms vague ideas into comprehensive frameworks including:
    - Problem Statement: Target users, core problem, severity, current alternatives, JTBD analysis
    - Opportunity Identification: Market opportunity, value creation, competitive landscape, strategic fit
    - Solution Concept: Solution hypothesis, value proposition, approach, assumptions, features, success criteria

    The expansion uses proven frameworks:
    - Jobs-to-be-Done (JTBD) for understanding customer needs
    - Problem-Solution Fit methodology
    - Design Thinking (Empathize, Define, Ideate)
    - Lean Startup principles
    - Value Proposition Design

    Args:
        idea: Raw startup idea text (can be vague or high-level)

    Returns:
        Structured concept document with detailed problem-solution framework ready for market research
    """
    agent = ConceptExpansionAgent()

    result = str(agent(idea))

    # Write output to file for file-based context passing
    write_agent_output_to_file("concept_expansion_agent", result)

    return result
