# ADR-014: Web Search Fallback Chain

## Status
**Accepted** — 2026-01-19

## Context

### Current State

The web search tool (`haytham/agents/utils/web_search.py`) uses DuckDuckGo's HTML interface for web searches:

```python
@tool
def web_search(query: str, max_results: int = 5) -> str:
    # POST to https://html.duckduckgo.com/html/
    # Custom HTML parsing with regex
```

### The Problem

**DuckDuckGo is blocking automated requests with 403 Forbidden errors:**

```
Tool #104: web_search
HTTP error searching for AI product validation tools market trends:
Client error '403 Forbidden' for url 'https://html.duckduckgo.com/html/'
```

This breaks two critical agents in Stage 2 (market_context):
- **market_intelligence** — researches market size, trends, industry data
- **competitor_analysis** — researches competitive landscape

### Root Cause

The current implementation:
1. Scrapes DuckDuckGo's HTML interface (not an official API)
2. DuckDuckGo actively blocks automated/bot traffic
3. Rate limiting and bot detection cause intermittent 403 errors
4. No fallback when the primary source fails

### Impact

| Scenario | Impact |
|----------|--------|
| Web search fails | Agents fall back to training data only |
| Stale market data | Validation reports may miss current trends |
| Competitor gaps | May not identify recent market entrants |
| User experience | Workflow appears broken with error logs |

---

## Decision

### Implement a Web Search Fallback Chain

We will replace the single-source web search with a resilient fallback chain that tries multiple providers in sequence.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        WEB SEARCH FALLBACK CHAIN                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐       │
│  │  DuckDuckGo     │────▶│  Brave Search   │────▶│  Tavily         │       │
│  │  (ddgs library) │ fail│  (API)          │ fail│  (API)          │       │
│  │  FREE           │     │  $0.003/query   │     │  FREE tier      │       │
│  └─────────────────┘     └─────────────────┘     └─────────────────┘       │
│         │                        │                        │                 │
│         ▼                        ▼                        ▼                 │
│    No API key             BRAVE_API_KEY            TAVILY_API_KEY          │
│    Rate limited           2,000 free/mo            1,000 free/mo           │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

### Provider Selection

| Priority | Provider | Package | API Key Required | Free Tier | Cost |
|----------|----------|---------|------------------|-----------|------|
| 1 | DuckDuckGo | `ddgs` | No | Unlimited* | Free |
| 2 | Brave Search | `httpx` | Yes | 2,000/month | $0.003/query |
| 3 | Tavily | `strands-agents-tools` | Yes | 1,000/month | $0.01/query |

*DuckDuckGo via `ddgs` library may still rate limit, but handles it more gracefully than raw HTML scraping.

---

### Session-Based Search Limits

**Critical:** Web search is a cost-bearing resource. An uncontrolled agent loop could exhaust API quotas and incur significant costs. We implement strict per-session limits.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        SESSION SEARCH LIMITS                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  Session Search Counter                                              │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                  │   │
│  │  │ Current: 3  │  │ Limit: 20   │  │ Remaining:17│                  │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘                  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  When limit reached:                                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  "Search limit reached (20/20). Please use existing results or      │   │
│  │   training knowledge. Limit resets with new session."               │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### Limit Configuration

| Setting | Default | Environment Variable | Description |
|---------|---------|---------------------|-------------|
| Max searches per session | 20 | `WEB_SEARCH_SESSION_LIMIT` | Hard cap on searches |
| Warning threshold | 15 | `WEB_SEARCH_WARNING_THRESHOLD` | Warn agent when approaching limit |

#### Implementation

```python
# Session-scoped search counter
_session_search_count: int = 0
_session_id: str | None = None

def _get_session_limit() -> int:
    """Get configured session limit from environment."""
    return int(os.getenv("WEB_SEARCH_SESSION_LIMIT", "20"))

def _get_warning_threshold() -> int:
    """Get warning threshold from environment."""
    return int(os.getenv("WEB_SEARCH_WARNING_THRESHOLD", "15"))

def _check_session_limit() -> tuple[bool, str]:
    """
    Check if session search limit has been reached.

    Returns:
        Tuple of (allowed, message)
    """
    global _session_search_count

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
        warning = f" [WARNING: {remaining} searches remaining in session]"
    else:
        warning = ""

    return True, warning

def reset_session_counter(session_id: str | None = None) -> None:
    """Reset the session search counter. Called at session start."""
    global _session_search_count, _session_id
    _session_search_count = 0
    _session_id = session_id
```

#### Integration with Search Tool

```python
@tool
def web_search(query: str, max_results: int = 5) -> str:
    """
    Search the web using the best available provider.

    Limited to prevent runaway costs. Check remaining quota in response.
    """
    # Check session limit FIRST
    allowed, message = _check_session_limit()
    if not allowed:
        return message

    # Proceed with search...
    result = _execute_search(query, max_results)

    # Append warning if approaching limit
    if message:  # Contains warning
        result += f"\n\n{message}"

    return result
```

#### Session Reset Points

The counter resets at these points:
1. **New workflow execution** — Each Burr workflow run starts fresh
2. **Manual reset** — Exposed for testing via `reset_session_counter()`
3. **Application restart** — Counter is in-memory, resets on restart

#### Workflow Integration

```python
# In workflow runner (frontend_streamlit/lib/workflow_runner.py)
from haytham.agents.utils.web_search import reset_session_counter

def run_workflow(workflow_type: str, session_id: str, ...):
    # Reset search counter at workflow start
    reset_session_counter(session_id)

    # Run workflow...
```

#### Agent Guidance

Update agent prompts to be aware of limits:

```markdown
## Web Search Guidelines

- You have a LIMITED number of web searches per session (default: 20)
- The tool will warn you when approaching the limit
- Plan your searches carefully - combine related queries when possible
- If limit is reached, rely on your training knowledge
- Prioritize searches for: market size, competitors, recent trends
```

#### Monitoring & Logging

```python
import logging

logger = logging.getLogger(__name__)

def web_search(query: str, max_results: int = 5) -> str:
    # Log search usage
    logger.info(
        "Web search executed",
        extra={
            "query": query[:100],
            "session_count": _session_search_count,
            "session_limit": _get_session_limit(),
            "session_id": _session_id,
        }
    )
    ...
```

---

### Implementation Architecture

#### Tool Design

Each search provider will be implemented as a **Strands tool** following the custom tools pattern:

```python
from strands import tool

@tool
def duckduckgo_search(query: str, max_results: int = 5) -> str:
    """
    Search the web using DuckDuckGo.

    Args:
        query: The search query string
        max_results: Maximum number of results to return (default: 5)

    Returns:
        Formatted search results with titles, URLs, and snippets
    """
    ...
```

#### Fallback Chain Tool

A unified `web_search` tool that orchestrates the fallback:

```python
@tool
def web_search(query: str, max_results: int = 5) -> str:
    """
    Search the web using the best available provider.

    Attempts providers in order: DuckDuckGo → Brave → Tavily
    Falls back to next provider on failure.

    Args:
        query: The search query string
        max_results: Maximum number of results to return (default: 5)

    Returns:
        Formatted search results with titles, URLs, and snippets
    """
    ...
```

---

### Provider Specifications

#### 1. DuckDuckGo (Primary)

**Package:** `ddgs` ([PyPI](https://pypi.org/project/ddgs/))

```python
from ddgs import DDGS

def _search_duckduckgo(query: str, max_results: int) -> list[dict]:
    with DDGS() as ddgs:
        results = list(ddgs.text(query, max_results=max_results))
    return results
```

**Response Format:**
```python
{
    "title": "Result Title",
    "href": "https://example.com/page",
    "body": "Snippet text describing the result..."
}
```

**Failure Modes:**
- Rate limiting (RateLimitException)
- Network timeout
- Empty results

#### 2. Brave Search (First Fallback)

**API:** [Brave Web Search API](https://api-dashboard.search.brave.com/documentation/services/web-search)

**Endpoint:** `https://api.search.brave.com/res/v1/web/search`

```python
def _search_brave(query: str, max_results: int) -> list[dict]:
    response = httpx.get(
        "https://api.search.brave.com/res/v1/web/search",
        params={"q": query, "count": max_results},
        headers={"X-Subscription-Token": os.getenv("BRAVE_API_KEY")},
    )
    response.raise_for_status()
    data = response.json()
    return data.get("web", {}).get("results", [])
```

**Response Format:**
```python
{
    "title": "Result Title",
    "url": "https://example.com/page",
    "description": "Snippet text..."
}
```

**Failure Modes:**
- Missing API key (skip provider)
- 401 Unauthorized (invalid key)
- 429 Rate Limited
- Network errors

#### 3. Tavily (Final Fallback)

**Package:** `strands-agents-tools` (already includes Tavily tool)

**Reference:** [strands_tools/tavily.py](https://github.com/strands-agents/tools/blob/main/src/strands_tools/tavily.py)

The existing Tavily tool from `strands-agents-tools` will be used directly:

```python
from strands_tools import tavily_search

# Already a Strands tool, can be called directly
result = tavily_search(query=query, max_results=max_results)
```

**Failure Modes:**
- Missing API key (skip provider)
- 401 Unauthorized
- Rate limited (1,000/month free tier)

---

### Environment Variables

```bash
# .env

# =============================================================================
# Web Search Provider API Keys (optional)
# =============================================================================

# Brave Search API (fallback 1)
# Get key at: https://api.search.brave.com/
# Free tier: 2,000 queries/month
# BRAVE_API_KEY=your_brave_api_key_here

# Tavily API (fallback 2)
# Get key at: https://tavily.com/
# Free tier: 1,000 queries/month
# TAVILY_API_KEY=your_tavily_api_key_here

# =============================================================================
# Web Search Session Limits (cost protection)
# =============================================================================

# Maximum searches allowed per workflow session (default: 20)
# Prevents runaway agent loops from exhausting API quotas
WEB_SEARCH_SESSION_LIMIT=20

# Threshold at which to warn agents about remaining searches (default: 15)
# Helps agents plan their remaining queries
WEB_SEARCH_WARNING_THRESHOLD=15
```

**Notes:**
- DuckDuckGo requires no API key
- If no API keys are configured, the system operates in DuckDuckGo-only mode
- Session limits apply regardless of which provider is used
- Limits reset at the start of each workflow execution

---

### Error Handling Strategy

```python
def web_search(query: str, max_results: int = 5) -> str:
    errors = []

    # Try DuckDuckGo first (no API key required)
    try:
        results = _search_duckduckgo(query, max_results)
        if results:
            return _format_results(results, "DuckDuckGo")
    except Exception as e:
        errors.append(f"DuckDuckGo: {e}")

    # Try Brave if API key is configured
    if os.getenv("BRAVE_API_KEY"):
        try:
            results = _search_brave(query, max_results)
            if results:
                return _format_results(results, "Brave")
        except Exception as e:
            errors.append(f"Brave: {e}")

    # Try Tavily if API key is configured
    if os.getenv("TAVILY_API_KEY"):
        try:
            results = _search_tavily(query, max_results)
            if results:
                return _format_results(results, "Tavily")
        except Exception as e:
            errors.append(f"Tavily: {e}")

    # All providers failed
    return f"Web search unavailable. Errors: {'; '.join(errors)}"
```

---

### Output Format

Consistent output format across all providers:

```
Search results for: {query}
(Source: {provider})

1. {title}
   URL: {url}
   {snippet}

2. {title}
   URL: {url}
   {snippet}

...
```

---

### Directory Structure

```
haytham/
├── agents/
│   └── utils/
│       ├── __init__.py
│       ├── web_search.py          # Main fallback chain tool (UPDATED)
│       ├── duckduckgo_search.py   # DuckDuckGo provider (NEW)
│       └── brave_search.py        # Brave provider (NEW)
```

**Note:** Tavily is already available via `strands-agents-tools`, no new file needed.

---

### Dependencies

Add to `pyproject.toml`:

```toml
dependencies = [
    # ... existing deps ...
    "ddgs>=6.1.0",  # DuckDuckGo search
    # httpx already included
    # strands-agents-tools already includes tavily
]
```

---

### Integration with Existing Agents

No changes required to agent prompts. The `web_search` tool maintains the same interface:

```python
# Agents continue to use the same tool signature
web_search(query="AI product validation market trends 2024", max_results=5)
```

The fallback chain is transparent to the calling agents.

---

### Configuration Updates

Update `haytham/config.py` to use the new tool:

```python
# Tool profiles remain unchanged
# The web_search tool now internally handles fallback
```

Update `.env.example`:

```bash
# Web Search Configuration (optional)
# At least one of these is recommended for reliable web search

# Brave Search API - https://api.search.brave.com/
# BRAVE_API_KEY=

# Tavily API - https://tavily.com/
# TAVILY_API_KEY=
```

---

### Success Criteria

| Metric | Target | Measurement |
|--------|--------|-------------|
| Search success rate | >95% | Log analysis |
| Fallback usage | <20% of searches | Provider tracking |
| Average latency | <5 seconds | Response time logging |
| Zero 403 errors | 100% | Error log monitoring |

---

### Rollout Plan

#### Phase 1: Implementation (Day 1-2)
1. Add `ddgs` dependency
2. Implement `duckduckgo_search.py` as Strands tool
3. Implement `brave_search.py` as Strands tool
4. Update `web_search.py` with fallback chain
5. Update `.env.example` with new variables

#### Phase 2: Testing (Day 2)
1. Unit tests for each provider
2. Integration test for fallback chain
3. Test with missing API keys (graceful degradation)
4. Load test to verify rate limit handling

#### Phase 3: Deployment (Day 3)
1. Update documentation
2. Add API keys to deployment environment
3. Monitor logs for fallback usage
4. Verify market_intelligence and competitor_analysis agents work

---

## Consequences

### Positive

1. **Resilience** — Multiple providers ensure search availability
2. **No breaking changes** — Same tool interface for agents
3. **Cost optimization** — Free DuckDuckGo used first, paid APIs only as fallback
4. **Graceful degradation** — Works without any API keys (DuckDuckGo only)
5. **Observability** — Provider logged in results for debugging
6. **Cost protection** — Session limits prevent runaway agent loops from exhausting quotas
7. **Agent awareness** — Warning threshold helps agents plan remaining queries

### Negative

1. **Complexity** — Three providers to maintain
2. **Latency** — Failed attempts add latency before fallback
3. **Cost** — Fallback providers have costs at scale
4. **Dependencies** — Additional packages to maintain
5. **Session limit friction** — Agents may hit limits on complex research tasks

### Risks

1. **All providers fail** — Unlikely but possible during outages
   - **Mitigation:** Agents designed to work with training data as final fallback

2. **Runaway agent loops** — Uncontrolled loops could exhaust API quotas
   - **Mitigation:** Hard session limit (default 20) with warning threshold (default 15)
   - **Mitigation:** Counter resets only at workflow start, not per-agent

3. **API key exposure** — Keys in .env could leak
   - **Mitigation:** Use secrets management in production

4. **Session limit too restrictive** — Complex research may need more searches
   - **Mitigation:** Configurable via environment variable
   - **Mitigation:** Agents can combine related queries to maximize value

---

## Alternatives Considered

### Alternative A: Single Provider (Tavily Only)

Switch entirely to Tavily API.

**Rejected because:**
- Requires API key even for development
- 1,000/month free tier may be limiting
- Single point of failure

### Alternative B: SerpAPI

Use SerpAPI as primary provider.

**Rejected because:**
- No free tier ($50/month minimum)
- Overkill for our use case
- Single point of failure

### Alternative C: Disable Web Search

Make web search optional, rely on training data.

**Rejected because:**
- Significantly reduces value of market research
- Competitors analysis would be stale
- Users expect current data

### Alternative D: Self-Hosted Search

Deploy own search infrastructure (Meilisearch, Elasticsearch).

**Rejected because:**
- Massive scope increase
- Requires maintaining search index
- Doesn't help with web search use case

---

## References

- [ddgs PyPI package](https://pypi.org/project/ddgs/)
- [Brave Web Search API Documentation](https://api-dashboard.search.brave.com/documentation/services/web-search)
- [Tavily Documentation](https://docs.tavily.com/)
- [Strands Tools - Tavily](https://github.com/strands-agents/tools/blob/main/src/strands_tools/tavily.py)
- [Strands Custom Tools Guide](https://strandsagents.com/latest/documentation/docs/user-guide/concepts/tools/custom-tools/)
