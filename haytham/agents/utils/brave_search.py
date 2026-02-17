"""Brave Search Provider.

Uses the Brave Web Search API for reliable web search results.
Requires a BRAVE_API_KEY environment variable.

API Documentation: https://api-dashboard.search.brave.com/documentation/services/web-search
"""

import logging
import os
from dataclasses import dataclass

import httpx

logger = logging.getLogger(__name__)

BRAVE_API_URL = "https://api.search.brave.com/res/v1/web/search"


class BraveSearchError(Exception):
    """Error during Brave Search API call."""

    pass


class BraveAPIKeyMissing(BraveSearchError):
    """Brave API key is not configured."""

    pass


@dataclass
class BraveResult:
    """A single Brave search result."""

    title: str
    url: str
    snippet: str


def get_brave_api_key() -> str | None:
    """Get Brave API key from environment."""
    return os.getenv("BRAVE_API_KEY")


def search_brave(query: str, max_results: int = 5) -> list[BraveResult]:
    """
    Search the web using Brave Search API.

    Args:
        query: The search query string
        max_results: Maximum number of results to return

    Returns:
        List of BraveResult objects

    Raises:
        BraveAPIKeyMissing: If BRAVE_API_KEY is not set
        BraveSearchError: If API call fails
    """
    api_key = get_brave_api_key()
    if not api_key:
        raise BraveAPIKeyMissing("BRAVE_API_KEY environment variable not set")

    logger.info("Brave search executing")

    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.get(
                BRAVE_API_URL,
                params={
                    "q": query,
                    "count": max_results,
                    "text_decorations": False,
                    "search_lang": "en",
                },
                headers={
                    "Accept": "application/json",
                    "Accept-Encoding": "gzip",
                    "X-Subscription-Token": api_key,
                },
            )
            response.raise_for_status()
            data = response.json()

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            raise BraveSearchError("Invalid Brave API key") from e
        if e.response.status_code == 429:
            raise BraveSearchError("Brave API rate limit exceeded") from e
        raise BraveSearchError(f"Brave API error: {e.response.status_code}") from e
    except httpx.TimeoutException as e:
        raise BraveSearchError("Brave API timeout") from e
    except Exception as e:
        raise BraveSearchError(f"Brave search failed: {e}") from e

    # Extract results from response
    web_results = data.get("web", {}).get("results", [])
    results = []

    for item in web_results[:max_results]:
        results.append(
            BraveResult(
                title=item.get("title", ""),
                url=item.get("url", ""),
                snippet=item.get("description", ""),
            )
        )

    logger.info(f"Brave returned {len(results)} results")
    return results


__all__ = [
    "BraveResult",
    "BraveSearchError",
    "BraveAPIKeyMissing",
    "search_brave",
    "get_brave_api_key",
]
