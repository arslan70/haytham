"""
Market Intelligence Agent module.

Exports the MarketIntelligenceAgent class and market_intelligence_tool for use
by the CEO agent and other components.
"""

from haytham.agents.worker_market_intelligence.worker_market_intelligence import (
    MarketIntelligenceAgent,
    market_intelligence_tool,
)

__all__ = ["MarketIntelligenceAgent", "market_intelligence_tool"]
