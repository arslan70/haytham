"""
Market Intelligence Agent for Haytham.

This agent conducts comprehensive market research, competitive analysis, and
trend identification for startup planning. It analyzes market landscapes,
identifies opportunities and threats, and provides data-driven insights that
inform product strategy and business decisions.

The agent integrates the Market Trends Analyzer as a sub-tool for intelligent
trend analysis.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from strands import Agent, tool

# Import logging utilities
from haytham.agents.utils.agent_output_writer import write_agent_output_to_file
from haytham.agents.utils.logging_utils import create_agent_logger
from haytham.agents.utils.model_provider import create_model
from haytham.agents.utils.web_search import web_search

# Import the Market Trends Analyzer sub-tool
from haytham.agents.worker_market_trends.worker_market_trends import market_trends_analyzer_tool


class MarketIntelligenceAgent:
    """
    Agent that conducts comprehensive market research and competitive analysis.

    This agent specializes in:
    - Market sizing (TAM/SAM/SOM framework)
    - Competitive landscape analysis (Porter's Five Forces)
    - Detailed competitor profiling
    - Market trend identification (via Market Trends Analyzer sub-tool)
    - Market segmentation and targeting
    - SWOT analysis
    - Market entry strategy recommendations
    - Strategic insights and recommendations

    The agent integrates the Market Trends Analyzer tool for intelligent
    trend analysis across technology, customer behavior, industry dynamics,
    economic factors, and social/cultural shifts.
    """

    def __init__(
        self,
        model: Any | None = None,
        system_prompt: str | None = None,
        tools: list | None = None,
        **kwargs,
    ):
        """
        Initialize the Market Intelligence Agent.

        Args:
            model: BedrockModel instance (defaults to Claude Sonnet 4.5)
            system_prompt: Custom system prompt (defaults to loading from prompt.txt)
            tools: List of tools available to the agent (defaults to [market_trends_analyzer_tool])
            **kwargs: Additional arguments passed to Agent constructor
        """
        if model is None:
            model = create_model()

        if system_prompt is None:
            prompt_path = Path(__file__).parent / "worker_market_intelligence_prompt.txt"
            system_prompt = prompt_path.read_text().strip()

        if tools is None:
            # Integrate web_search and Market Trends Analyzer as tools
            tools = [web_search, market_trends_analyzer_tool]

        self.model = model
        self.system_prompt = system_prompt
        self.tools = tools
        self.kwargs = kwargs

        # Initialize agent logger
        self.logger = create_agent_logger("market_intelligence")

    def __call__(self, concept: str) -> str:
        """
        Conduct comprehensive market research and competitive analysis.

        Args:
            concept: Product concept, idea, or POC application description

        Returns:
            Comprehensive market intelligence report including:
            - Market overview (size, growth, maturity, dynamics)
            - Competitive landscape (Porter's Five Forces)
            - Competitor analysis (detailed profiles)
            - Market trends analysis (via Market Trends Analyzer)
            - Market segmentation (target identification)
            - SWOT analysis (strategic assessment)
            - Market entry strategy (go-to-market foundation)
            - Key insights and recommendations (actionable intelligence)
        """
        try:
            query = (
                f"Conduct comprehensive market intelligence for this product concept:\n\n{concept}"
            )

            # Log LLM input
            full_prompt = f"System Prompt:\n{self.system_prompt}\n\nQuery:\n{query}"
            self.logger.log_llm_input(full_prompt, metadata={"agent": "market_intelligence"})

            # Execute agent
            agent = Agent(
                model=self.model, system_prompt=self.system_prompt, tools=self.tools, **self.kwargs
            )

            result = agent(query)

            # Log LLM output
            self.logger.log_llm_output(str(result), metadata={"agent": "market_intelligence"})

            return result

        except Exception as e:
            self.logger.log_error(e, context="market_intelligence execution")
            raise

    from haytham.agents.utils.agent_output_writer import write_agent_output_to_file


@tool
def market_intelligence_tool(concept: str) -> str:
    """
    Conducts comprehensive market research and competitive analysis for startup planning.

    This tool provides in-depth market intelligence including:

    1. Market Overview:
       - Market definition and boundaries
       - Market sizing (TAM/SAM/SOM framework)
       - Market maturity and growth projections
       - Key market dynamics and drivers

    2. Competitive Landscape (Porter's Five Forces):
       - Threat of new entrants
       - Bargaining power of suppliers
       - Bargaining power of buyers
       - Threat of substitutes
       - Competitive rivalry intensity
       - Overall market attractiveness score

    3. Competitor Analysis:
       - Direct competitor profiles (top 3-5)
       - Indirect competitors
       - Potential future competitors
       - Competitive positioning map
       - Competitive advantage assessment

    4. Market Trends Analysis:
       - Technology trends (via Market Trends Analyzer sub-tool)
       - Customer behavior trends
       - Industry trends
       - Economic and social trends
       - Trend synthesis and implications

    5. Market Segmentation:
       - Segmentation approach and dimensions
       - Identified segments with attractiveness scores
       - Target segment recommendations
       - Prioritization rationale

    6. SWOT Analysis:
       - Strengths (internal, positive)
       - Weaknesses (internal, negative)
       - Opportunities (external, positive)
       - Threats (external, negative)
       - Strategic implications (SO/WO/ST/WT strategies)

    7. Market Entry Strategy:
       - Recommended entry approach
       - Entry barriers assessment
       - Entry timing recommendations
       - Geographic and partnership strategies

    8. Key Insights and Recommendations:
       - Market opportunity assessment
       - Critical success factors
       - Key risks and mitigation strategies
       - Strategic recommendations (immediate, short-term, medium-term)
       - Positioning recommendations
       - Red flags and data gaps

    The agent uses the Market Trends Analyzer as a sub-tool for intelligent
    trend analysis, providing LLM-powered insights on emerging patterns and
    strategic implications.

    Args:
        concept: Product concept, startup idea, or POC application description

    Returns:
        Comprehensive market intelligence report with 8 detailed sections and
        actionable strategic recommendations
    """
    agent = MarketIntelligenceAgent()

    result = str(agent(concept))

    # Write output to file for file-based context passing
    write_agent_output_to_file("market_intelligence_agent", result)

    return result
