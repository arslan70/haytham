"""
Competitor Analysis Agent - Identifies and evaluates competitors.

This agent analyzes the competitive landscape using web search to find
real competitor information, user reviews, and market positioning data.
It focuses on:
- Real competitor identification with verifiable traction
- Actual user sentiment from reviews and forums
- Competitive positioning and pricing
- Switching dynamics and market entry challenges

The agent uses web_search to find real data and avoids fabricating
competitor details, pricing, or user sentiment.
"""

import logging
from pathlib import Path

from strands import Agent, tool

from haytham.agents.utils.agent_output_writer import write_agent_output_to_file
from haytham.agents.utils.logging_utils import create_agent_logger
from haytham.agents.utils.model_provider import create_model
from haytham.agents.utils.web_search import web_search

# Configure module logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class CompetitorAnalysisAgent:
    """
    Agent that analyzes the competitive landscape using web search.

    This agent specializes in:
    - Finding real competitors with verifiable traction data
    - Gathering actual user sentiment from reviews and forums
    - Analyzing competitive positioning and pricing
    - Identifying switching dynamics and entry barriers
    - Challenging assumptions with required skepticism
    """

    def __init__(
        self,
        model=None,
        system_prompt: str | None = None,
        tools: list | None = None,
        **kwargs,
    ):
        """
        Initialize the Competitor Analysis Agent.

        Args:
            model: BedrockModel instance (defaults to Claude Sonnet)
            system_prompt: Custom system prompt (defaults to loading from prompt.txt)
            tools: List of tools available to the agent (defaults to [web_search])
            **kwargs: Additional arguments passed to Agent constructor
        """
        if model is None:
            model = create_model()

        if system_prompt is None:
            prompt_path = Path(__file__).parent / "worker_competitor_analysis_prompt.txt"
            system_prompt = prompt_path.read_text().strip()

        if tools is None:
            tools = [web_search]

        self.model = model
        self.system_prompt = system_prompt
        self.tools = tools
        self.kwargs = kwargs

        # Initialize agent logger
        self.logger = create_agent_logger("competitor_analysis")

    def __call__(self, query: str) -> str:
        """
        Analyze the competitive landscape for the given query.

        Args:
            query: Product concept or startup idea to analyze competitors for

        Returns:
            Comprehensive competitor analysis with real data
        """
        try:
            # Log LLM input
            full_prompt = f"System Prompt:\n{self.system_prompt}\n\nQuery:\n{query}"
            self.logger.log_llm_input(full_prompt, metadata={"agent": "competitor_analysis"})

            # Execute agent with tools
            agent = Agent(
                model=self.model, system_prompt=self.system_prompt, tools=self.tools, **self.kwargs
            )

            result = agent(query)

            # Log LLM output
            self.logger.log_llm_output(str(result), metadata={"agent": "competitor_analysis"})

            return str(result)

        except Exception as e:
            self.logger.log_error(e, context="competitor_analysis execution")
            raise


@tool
def competitor_analysis_tool(query: str) -> str:
    """
    Analyze the competitive landscape using web search for real data.

    This tool identifies and evaluates competitors relevant to the product
    concept, using web search to find:
    - Real competitors with verifiable traction (downloads, users, funding)
    - Actual user sentiment from App Store reviews, Reddit, G2, etc.
    - Competitive positioning and pricing data
    - Switching dynamics and market entry barriers

    The analysis includes:
    - 3-5 real competitors with traction evidence
    - User sentiment from actual reviews (not fabricated)
    - Competitive positioning and pricing
    - Switching analysis
    - Opportunities and challenges with required skepticism

    Args:
        query: Product concept or startup idea to analyze competitors for

    Returns:
        Competitor analysis with real, verifiable data

    Example:
        >>> result = competitor_analysis_tool(
        ...     "Analyze competitors for a meal prep app that suggests recipes based on grocery sales"
        ... )
    """
    logger.info("Executing competitor analysis agent with web search")

    agent = CompetitorAnalysisAgent()
    result = agent(query)

    # Write output to file for file-based context passing
    write_agent_output_to_file("competitor_analysis_agent", result)

    return result


# Agent metadata
competitor_analysis_tool.agent_name = "competitor_analysis_agent"
competitor_analysis_tool.description = (
    "Analyzes the competitive landscape using web search to find real competitors, "
    "actual user sentiment, pricing data, and market entry challenges."
)
