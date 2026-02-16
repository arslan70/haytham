"""DuckDuckGo Search Provider using ddgs library.

Uses the official ddgs package which handles rate limiting and bot detection
more gracefully than raw HTML scraping.
"""

import logging
from dataclasses import dataclass

from ddgs import DDGS
from ddgs.exceptions import DDGSException, RatelimitException

logger = logging.getLogger(__name__)


@dataclass
class DuckDuckGoResult:
    """A single DuckDuckGo search result."""

    title: str
    url: str
    snippet: str


def search_duckduckgo(query: str, max_results: int = 5) -> list[DuckDuckGoResult]:
    """
    Search the web using DuckDuckGo via the ddgs library.

    Args:
        query: The search query string
        max_results: Maximum number of results to return

    Returns:
        List of DuckDuckGoResult objects

    Raises:
        RatelimitException: If rate limited by DuckDuckGo
        DuckDuckGoSearchException: If search fails
    """
    logger.info(f"DuckDuckGo search: {query[:100]}")

    results = []
    with DDGS() as ddgs:
        search_results = list(ddgs.text(query, max_results=max_results))

    for item in search_results:
        results.append(
            DuckDuckGoResult(
                title=item.get("title", ""),
                url=item.get("href", ""),
                snippet=item.get("body", ""),
            )
        )

    logger.info(f"DuckDuckGo returned {len(results)} results")
    return results


def format_duckduckgo_results(results: list[DuckDuckGoResult], query: str) -> str:
    """Format DuckDuckGo results into a readable string."""
    if not results:
        return f"No results found for: {query}"

    lines = [f"Search results for: {query}", "(Source: DuckDuckGo)", ""]

    for i, result in enumerate(results, 1):
        lines.append(f"{i}. {result.title}")
        lines.append(f"   URL: {result.url}")
        if result.snippet:
            lines.append(f"   {result.snippet}")
        lines.append("")

    return "\n".join(lines)


__all__ = [
    "DuckDuckGoResult",
    "search_duckduckgo",
    "format_duckduckgo_results",
    "RatelimitException",
    "DDGSException",
]
