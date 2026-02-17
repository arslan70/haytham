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
    logger.info("DuckDuckGo search executing")

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


__all__ = [
    "DuckDuckGoResult",
    "search_duckduckgo",
    "RatelimitException",
    "DDGSException",
]
