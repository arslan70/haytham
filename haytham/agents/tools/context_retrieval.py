"""Context retrieval tools for accessing previous stage outputs.

These tools allow agents to selectively request context from previous
stages, rather than having all context pre-loaded. This enables more
intelligent context selection based on the agent's current task.
"""

import json

from strands import tool

# Global context store - set by workflow before agent execution
_context_store: dict[str, str] = {}


def set_context_store(context: dict[str, str]) -> None:
    """Set the context store with available stage outputs.

    Called by the workflow before agent execution to make
    previous stage outputs available to the context retrieval tools.

    Args:
        context: Dict mapping stage keys to their output content
    """
    global _context_store
    _context_store = context.copy()


def clear_context_store() -> None:
    """Clear the context store after agent execution."""
    global _context_store
    _context_store = {}


@tool
def list_available_context() -> str:
    """List all available context from previous stages.

    Use this tool to see what prior stage outputs are available
    before deciding what context to retrieve.

    Returns:
        JSON with available context keys and content previews
    """
    available = []

    for key, content in _context_store.items():
        if content and isinstance(content, str):
            # Get preview of content
            preview = content[:200].replace("\n", " ").strip()
            if len(content) > 200:
                preview += "..."

            available.append(
                {
                    "key": key,
                    "length": len(content),
                    "preview": preview,
                }
            )

    return json.dumps(
        {
            "available_contexts": len(available),
            "contexts": available,
        },
        indent=2,
    )


@tool
def get_context_by_key(context_key: str, max_chars: int = 2000) -> str:
    """Retrieve context from a previous stage by its key.

    Use this tool after list_available_context to fetch specific
    context that's relevant to your current task.

    Args:
        context_key: The key of the context to retrieve (e.g., "idea_analysis", "market_context")
        max_chars: Maximum characters to return (default 2000)

    Returns:
        The context content, or error message if not found
    """
    if context_key not in _context_store:
        available_keys = list(_context_store.keys())
        return json.dumps(
            {
                "error": f"Context key '{context_key}' not found",
                "available_keys": available_keys,
            }
        )

    content = _context_store[context_key]
    if not content:
        return json.dumps(
            {
                "error": f"Context '{context_key}' is empty",
            }
        )

    # Truncate if needed
    if len(content) > max_chars:
        content = (
            content[:max_chars]
            + f"\n\n[...truncated, {len(_context_store[context_key]) - max_chars} more chars]"
        )

    return json.dumps(
        {
            "key": context_key,
            "content": content,
            "truncated": len(_context_store[context_key]) > max_chars,
        },
        indent=2,
    )


@tool
def search_context(query: str, max_results: int = 3) -> str:
    """Search across all available context for relevant information.

    Use this tool to find specific information across all previous
    stage outputs without retrieving everything.

    Args:
        query: Keywords to search for (case-insensitive)
        max_results: Maximum number of matching excerpts to return

    Returns:
        JSON with matching excerpts and their source contexts
    """
    query_lower = query.lower()
    keywords = query_lower.split()
    results = []

    for key, content in _context_store.items():
        if not content or not isinstance(content, str):
            continue

        content_lower = content.lower()

        # Check if any keywords match
        if any(kw in content_lower for kw in keywords):
            # Find matching lines
            lines = content.split("\n")
            for i, line in enumerate(lines):
                line_lower = line.lower()
                if any(kw in line_lower for kw in keywords):
                    # Get context around the match
                    start = max(0, i - 1)
                    end = min(len(lines), i + 2)
                    excerpt = "\n".join(lines[start:end]).strip()

                    results.append(
                        {
                            "source": key,
                            "line_number": i + 1,
                            "excerpt": excerpt[:300],
                        }
                    )

                    if len(results) >= max_results:
                        break

        if len(results) >= max_results:
            break

    return json.dumps(
        {
            "query": query,
            "results_found": len(results),
            "results": results,
        },
        indent=2,
    )


@tool
def get_context_summary(context_key: str) -> str:
    """Get a summary of a previous stage's output.

    Use this tool to get a quick overview of a stage's output
    without retrieving the full content.

    Args:
        context_key: The key of the context to summarize

    Returns:
        JSON with key statistics and first/last sections
    """
    if context_key not in _context_store:
        return json.dumps(
            {
                "error": f"Context key '{context_key}' not found",
            }
        )

    content = _context_store[context_key]
    if not content:
        return json.dumps(
            {
                "error": f"Context '{context_key}' is empty",
            }
        )

    lines = content.split("\n")
    sections = [line for line in lines if line.startswith("#")]

    # Get first paragraph (non-header content)
    first_para = ""
    for line in lines:
        if line.strip() and not line.startswith("#"):
            first_para = line.strip()[:200]
            break

    return json.dumps(
        {
            "key": context_key,
            "total_chars": len(content),
            "total_lines": len(lines),
            "sections": sections[:10],  # First 10 section headers
            "first_paragraph": first_para,
        },
        indent=2,
    )
