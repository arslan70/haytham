"""
Competitor Analysis Agent - Identifies and evaluates competitors.

This agent analyzes the competitive landscape based on validated upstream
outputs, focusing on capability adjacency, domain overlap, and category-level
positioning without fabricating specific competitor details.
"""

from haytham.agents.worker_competitor_analysis.worker_competitor_analysis import (
    competitor_analysis_tool,
)

__all__ = ["competitor_analysis_tool"]
