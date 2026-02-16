"""
Pivot Strategy Agent for Haytham.

This agent suggests strategic pivot options when a startup idea receives
a high risk assessment. It focuses on reducing risk while preserving
the core value proposition.
"""

from __future__ import annotations

from pathlib import Path

from strands import Agent, tool

from haytham.agents.utils.agent_output_writer import write_agent_output_to_file
from haytham.agents.utils.logging_utils import create_agent_logger
from haytham.agents.utils.model_provider import create_model


class PivotStrategyAgent:
    """
    Agent that suggests strategic pivot options for high-risk startup concepts.

    This agent specializes in:
    - Analyzing critical risks
    - Proposing alternative approaches
    - Balancing risk reduction with value preservation
    - Providing actionable next steps
    """

    def __init__(self, model=None, system_prompt: str | None = None, **kwargs):
        """
        Initialize the Pivot Strategy Agent.

        Args:
            model: BedrockModel instance
            system_prompt: Custom system prompt (defaults to loading from prompt.txt)
            **kwargs: Additional arguments passed to Agent constructor
        """
        if model is None:
            model = create_model()

        if system_prompt is None:
            prompt_path = Path(__file__).parent / "worker_pivot_strategy_prompt.txt"
            system_prompt = prompt_path.read_text().strip()

        self.model = model
        self.system_prompt = system_prompt
        self.kwargs = kwargs

        # Initialize agent logger
        self.logger = create_agent_logger("pivot_strategy")

    def __call__(self, risk_assessment: str, idea_analysis: str = "") -> str:
        """
        Suggest strategic pivot options based on risk assessment.

        Args:
            risk_assessment: The high-risk assessment output
            idea_analysis: Original idea analysis for context

        Returns:
            Strategic pivot recommendations with actionable next steps
        """
        try:
            query = f"""Based on the following HIGH risk assessment, suggest strategic pivot options:

ORIGINAL IDEA ANALYSIS:
{idea_analysis[:2000] if idea_analysis else "Not provided"}

RISK ASSESSMENT:
{risk_assessment}

Provide 2-3 pivot options that reduce risk while preserving the core value proposition."""

            # Log LLM input
            full_prompt = f"System Prompt:\n{self.system_prompt}\n\nQuery:\n{query}"
            self.logger.log_llm_input(full_prompt, metadata={"agent": "pivot_strategy"})

            # Execute agent
            agent = Agent(model=self.model, system_prompt=self.system_prompt, **self.kwargs)

            result = agent(query)

            # Log LLM output
            self.logger.log_llm_output(str(result), metadata={"agent": "pivot_strategy"})

            return result

        except Exception as e:
            self.logger.log_error(e, context="Pivot strategy execution")
            raise


@tool
def pivot_strategy_tool(risk_assessment: str, idea_analysis: str = "") -> str:
    """
    Suggests strategic pivot options for high-risk startup concepts.

    This tool analyzes the risk assessment and proposes alternative approaches
    that reduce risk while preserving the core value proposition.

    The analysis includes:
    - Risk summary highlighting critical issues
    - 2-3 pivot alternatives with trade-offs
    - Recommended pivot with rationale
    - Go/No-Go signal with confidence level

    Args:
        risk_assessment: The high-risk assessment output from startup_validator
        idea_analysis: Original idea analysis for context (optional)

    Returns:
        Strategic pivot recommendations with actionable next steps
    """
    agent = PivotStrategyAgent()

    result = str(agent(risk_assessment, idea_analysis))

    # Write output to file for file-based context passing
    write_agent_output_to_file("pivot_strategy_agent", result)

    return result
