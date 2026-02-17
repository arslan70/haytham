"""Web Search Tool with Fallback Chain.

Implements a resilient web search with multiple providers:
1. DuckDuckGo (ddgs library) - Free, no API key required
2. Brave Search API - Requires BRAVE_API_KEY
3. Tavily API - Requires TAVILY_API_KEY

Falls back to next provider on failure. Includes session-based
rate limiting to prevent runaway agent loops from exhausting quotas.

See ADR-014 for design details.
"""

import logging
import os
import threading

from strands import tool

from .brave_search import (
    BraveAPIKeyMissing,
    BraveSearchError,
    format_brave_results,
    get_brave_api_key,
    search_brave,
)
from .duckduckgo_search import (
    DDGSException,
    RatelimitException,
    format_duckduckgo_results,
    search_duckduckgo,
)

logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# Session-based search limits (cost protection)
# -----------------------------------------------------------------------------

_session_search_count: int = 0
_session_id: str | None = None
_session_lock = threading.Lock()


def _safe_int_env(name: str, default: int) -> int:
    """Read an integer env var, falling back to *default* on bad values."""
    raw = os.getenv(name, "")
    try:
        return int(raw) if raw else default
    except ValueError:
        logger.warning("Invalid integer for %s=%r, using default %d", name, raw, default)
        return default


def _get_session_limit() -> int:
    """Get configured session limit from environment."""
    return _safe_int_env("WEB_SEARCH_SESSION_LIMIT", 20)


def _get_warning_threshold() -> int:
    """Get warning threshold from environment."""
    return _safe_int_env("WEB_SEARCH_WARNING_THRESHOLD", 15)


def _check_session_limit() -> tuple[bool, str]:
    """
    Check if session search limit has been reached.

    Thread-safe: uses ``_session_lock`` to protect the shared counter
    since agents may run searches in parallel.

    Returns:
        Tuple of (allowed, warning_message)
        - allowed: True if search is permitted
        - warning_message: Empty string or warning about remaining quota
    """
    global _session_search_count

    with _session_lock:
        limit = _get_session_limit()
        warning_threshold = _get_warning_threshold()

        if _session_search_count >= limit:
            return False, (
                f"Search limit reached ({_session_search_count}/{limit}). "
                "Use existing results or training knowledge. "
                "Limit resets with new session."
            )

        # Increment counter
        _session_search_count += 1
        remaining = limit - _session_search_count

        # Warning message when approaching limit
        if _session_search_count >= warning_threshold:
            warning = f"[WARNING: {remaining} searches remaining in session]"
        else:
            warning = ""

        return True, warning


def reset_session_counter(session_id: str | None = None) -> None:
    """
    Reset the session search counter.

    Called at workflow start to give each session a fresh quota.
    Thread-safe: uses ``_session_lock``.

    Args:
        session_id: Optional session identifier for logging
    """
    global _session_search_count, _session_id
    with _session_lock:
        _session_search_count = 0
        _session_id = session_id
    logger.info(f"Web search session counter reset (session: {session_id})")


def get_session_stats() -> dict:
    """Get current session search statistics."""
    with _session_lock:
        count = _session_search_count
        sid = _session_id
    limit = _get_session_limit()
    return {
        "count": count,
        "limit": limit,
        "remaining": max(0, limit - count),
        "session_id": sid,
    }


# -----------------------------------------------------------------------------
# Tavily Search (using strands-agents-tools)
# -----------------------------------------------------------------------------


def _get_tavily_api_key() -> str | None:
    """Get Tavily API key from environment."""
    return os.getenv("TAVILY_API_KEY")


def _search_tavily(
    query: str,
    max_results: int,
    include_domains: list[str] | None = None,
    search_depth: str = "basic",
) -> str | None:
    """
    Search using Tavily API via strands-agents-tools.

    Args:
        query: Search query
        max_results: Maximum results to return
        include_domains: Optional list of domains to restrict results to (native Tavily support)
        search_depth: "basic" or "advanced" (native Tavily support)

    Returns formatted results string or None if unavailable/failed.
    """
    api_key = _get_tavily_api_key()
    if not api_key:
        logger.debug("Tavily API key not configured, skipping")
        return None

    try:
        # Import tavily tool from strands-agents-tools
        from strands_tools import tavily_search

        # Build kwargs — Tavily natively supports include_domains and search_depth
        kwargs: dict = {"query": query, "max_results": max_results}
        if include_domains:
            kwargs["include_domains"] = include_domains
        if search_depth and search_depth != "basic":
            kwargs["search_depth"] = search_depth

        # Call the tavily tool
        result = tavily_search(**kwargs)

        if result:
            logger.info("Tavily search successful")
            # Add source attribution if not present
            if "(Source:" not in result:
                result = f"Search results for: {query}\n(Source: Tavily)\n\n{result}"
            return result

    except ImportError:
        logger.warning("strands_tools.tavily_search not available")
    except (ConnectionError, TimeoutError, ValueError) as e:
        logger.error(f"Tavily search error: {e}")

    return None


# -----------------------------------------------------------------------------
# Fallback Chain Implementation
# -----------------------------------------------------------------------------


def _apply_domain_filter(query: str, include_domains: list[str] | None) -> str:
    """Prepend site: operators to a query for providers that don't support native domain filtering.

    Args:
        query: Original search query
        include_domains: List of domains to restrict results to

    Returns:
        Modified query with site: prefixes, or original query if no domains
    """
    if not include_domains:
        return query
    # Use OR-joined site: operators — most engines support this
    site_prefix = " OR ".join(f"site:{d}" for d in include_domains)
    return f"{site_prefix} {query}"


def _execute_search_with_fallback(
    query: str,
    max_results: int,
    include_domains: list[str] | None = None,
    search_depth: str = "basic",
) -> str:
    """
    Execute search with fallback chain: DuckDuckGo → Brave → Tavily.

    Args:
        query: Search query
        max_results: Maximum results to return
        include_domains: Optional list of domains to restrict results to
        search_depth: "basic" or "advanced" (Tavily-specific, others ignore)

    Returns:
        Formatted search results string
    """
    errors = []

    # For DuckDuckGo and Brave, translate include_domains into site: prefix
    filtered_query = _apply_domain_filter(query, include_domains)

    # Provider 1: DuckDuckGo (no API key required)
    try:
        results = search_duckduckgo(filtered_query, max_results)
        if results:
            return format_duckduckgo_results(results, query)
        errors.append("DuckDuckGo: No results")
    except RatelimitException as e:
        logger.warning(f"DuckDuckGo rate limited: {e}")
        errors.append("DuckDuckGo: Rate limited")
    except DDGSException as e:
        logger.warning(f"DuckDuckGo error: {e}")
        errors.append(f"DuckDuckGo: {e}")
    except (ConnectionError, TimeoutError, OSError, ValueError) as e:
        logger.warning(f"DuckDuckGo unexpected error: {e}")
        errors.append(f"DuckDuckGo: {e}")

    # Provider 2: Brave Search (requires API key)
    if get_brave_api_key():
        try:
            results = search_brave(filtered_query, max_results)
            if results:
                return format_brave_results(results, query)
            errors.append("Brave: No results")
        except BraveAPIKeyMissing:
            pass  # Already checked, shouldn't happen
        except BraveSearchError as e:
            logger.warning(f"Brave search error: {e}")
            errors.append(f"Brave: {e}")
        except (ConnectionError, TimeoutError, OSError, ValueError) as e:
            logger.warning(f"Brave unexpected error: {e}")
            errors.append(f"Brave: {e}")
    else:
        logger.debug("Brave API key not configured, skipping")

    # Provider 3: Tavily (requires API key, supports native include_domains)
    tavily_result = _search_tavily(
        query,
        max_results,
        include_domains=include_domains,
        search_depth=search_depth,
    )
    if tavily_result:
        return tavily_result
    if _get_tavily_api_key():
        errors.append("Tavily: No results or error")

    # All providers failed
    error_summary = "; ".join(errors) if errors else "No providers available"
    logger.error(f"All search providers failed. Errors: {error_summary}")

    return (
        f"Web search unavailable for: {query}\n\n"
        f"All providers failed. Errors:\n{chr(10).join(f'- {e}' for e in errors)}\n\n"
        "Please use your training knowledge or existing information."
    )


# -----------------------------------------------------------------------------
# Main Tool
# -----------------------------------------------------------------------------


@tool
def web_search(
    query: str,
    max_results: int = 5,
    include_domains: list[str] | None = None,
    search_depth: str = "basic",
) -> str:
    """Search the web using the best available provider.

    Attempts providers in order: DuckDuckGo → Brave → Tavily.
    Falls back to next provider on failure.

    Limited to prevent runaway costs - check remaining quota in response.

    Args:
        query: The search query string
        max_results: Maximum number of results to return (default: 5, max: 10)
        include_domains: Optional list of domains to restrict results to
            (e.g. ["g2.com", "capterra.com"]). Tavily supports this natively;
            DuckDuckGo and Brave translate to site: query prefix.
        search_depth: Search depth — "basic" (default) or "advanced".
            Tavily supports this natively; other providers ignore it.

    Returns:
        Formatted search results with titles, URLs, and snippets.
        May include a warning about remaining search quota.

    Example:
        >>> results = web_search("AI product validation market trends 2024")
        >>> print(results)
        Search results for: AI product validation market trends 2024
        (Source: DuckDuckGo)

        1. Title of First Result
           URL: https://example.com/page
           Description snippet...
    """
    if not query or not query.strip():
        return "Error: Search query cannot be empty"

    # Enforce max_results bounds
    max_results = min(max(1, max_results), 10)

    # Check session limit FIRST (cost protection)
    allowed, warning = _check_session_limit()
    if not allowed:
        logger.warning("Search limit reached, blocking query")
        return warning

    # Log search with session context
    logger.info(
        "Web search executing",
        extra={
            "query_length": len(query),
            "session_count": _session_search_count,
            "session_limit": _get_session_limit(),
            "session_id": _session_id,
        },
    )

    # Execute search with fallback chain
    result = _execute_search_with_fallback(
        query,
        max_results,
        include_domains=include_domains,
        search_depth=search_depth,
    )

    # Append warning if approaching limit
    if warning:
        result = f"{result}\n\n{warning}"

    return result


__all__ = [
    "web_search",
    "reset_session_counter",
    "get_session_stats",
]
