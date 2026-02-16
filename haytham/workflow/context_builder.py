"""Context-building helpers for stage handoff.

Pure functions that build concise context summaries from previous stage outputs
for downstream agents. Extracted from burr_actions.py (ADR-024).

Key functions:
    _build_context_summary   -- Main entry point, builds context from stage outputs.
    render_validation_summary_from_json -- Public, used by mvp_scope_swarm and mvp_specification.
"""

import json
import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

# Compiled regex for TL;DR extraction (ADR-022)
_TLDR_PATTERN = re.compile(r"##\s*TL;?DR\s*\n(.*?)(?=\n##|\Z)", re.IGNORECASE | re.DOTALL)


def _extract_tldr(content: str, max_words: int = 300) -> str | None:
    """Extract TL;DR section from stage output.

    ADR-022: Agents should output a ## TL;DR section at the top of their output.
    This function extracts that section for context handoff.

    Args:
        content: Full stage output content
        max_words: Maximum words to extract (default 300 per ADR-022)

    Returns:
        TL;DR content if found, None otherwise
    """
    match = _TLDR_PATTERN.search(content)

    if match:
        tldr_content = match.group(1).strip()
        # Limit to max_words
        words = tldr_content.split()
        if len(words) > max_words:
            tldr_content = " ".join(words[:max_words]) + "..."
        return tldr_content

    return None


def _extract_first_paragraph(content: str, max_chars: int = 200) -> str:
    """Fallback: Extract first meaningful paragraph when no TL;DR exists.

    Args:
        content: Full stage output content
        max_chars: Maximum characters to extract

    Returns:
        First paragraph content, truncated if needed
    """
    lines = [
        line.strip() for line in content.split("\n") if line.strip() and not line.startswith("#")
    ]
    if lines:
        return lines[0][:max_chars]
    return ""


def _render_risk_assessment_context(data: dict) -> str:
    """Render risk_assessment JSON into concise context for downstream agents."""
    summary = data.get("summary", {})
    lines = [f"Risk Level: {data.get('overall_risk_level', 'UNKNOWN').upper()}"]
    if summary:
        lines.append(
            f"Claims: {summary.get('supported', 0)} supported, "
            f"{summary.get('partial', 0)} partial, "
            f"{summary.get('unsupported', 0)} unsupported"
        )
    risks = data.get("risks", [])
    high_risks = [r for r in risks if r.get("level", "").lower() == "high"]
    medium_risks = [r for r in risks if r.get("level", "").lower() == "medium"]
    if high_risks:
        descs = [r.get("description", "")[:80] for r in high_risks]
        lines.append(f"High Risks: {'; '.join(descs)}")
    if medium_risks:
        descs = [r.get("description", "")[:80] for r in medium_risks]
        lines.append(f"Medium Risks: {'; '.join(descs)}")
    return "\n".join(lines)


def render_validation_summary_from_json(data: dict) -> str:
    """Render validation_summary JSON into context for downstream agents.

    Shared renderer used by _build_context_summary(), run_mvp_scope_chain(),
    and build_mvp_scope_context() to avoid triplicated parsing logic.
    """
    lines = [
        f"Recommendation: {data.get('recommendation', 'UNKNOWN').upper()} "
        f"(Confidence: {data.get('confidence', 'UNKNOWN').upper()})"
    ]
    summary = data.get("executive_summary", "")
    if summary:
        lines.append(summary)
    assessment = data.get("go_no_go_assessment", {})
    if assessment.get("strengths"):
        lines.append(f"Strengths: {', '.join(assessment['strengths'])}")
    if assessment.get("weaknesses"):
        lines.append(f"Weaknesses: {', '.join(assessment['weaknesses'])}")
    if assessment.get("guidance"):
        lines.append(f"Guidance: {assessment['guidance']}")
    return "\n".join(lines)


def _render_validation_summary_context(data: dict) -> str:
    """Render validation_summary JSON for _build_context_summary()."""
    return render_validation_summary_from_json(data)


def _render_build_buy_context(data: dict) -> str:
    """Render build_buy_analysis JSON into concise context for downstream agents."""
    lines = []
    stack = data.get("recommended_stack", [])
    if stack:
        names = [f"{s.get('name', '?')} ({s.get('category', '?')})" for s in stack[:6]]
        lines.append(f"Recommended Stack: {', '.join(names)}")
    effort = data.get("total_integration_effort", "")
    if effort:
        lines.append(f"Integration Effort: {effort}")
    return "\n".join(lines)


def _render_story_generation_context(data: dict) -> str:
    """Render story_generation JSON into concise context for downstream agents."""
    stories = data.get("stories", [])
    if not stories:
        return f"Stories: {len(stories)} total"
    layers = sorted({s.get("layer", 0) for s in stories})
    cap_ids = set()
    for s in stories:
        cap_ids.update(s.get("implements", []))
    lines = [
        f"Stories: {len(stories)} total across layers {min(layers)}-{max(layers)}",
    ]
    if cap_ids:
        lines.append(f"Coverage: {', '.join(sorted(cap_ids))}")
    return "\n".join(lines)


_JSON_CONTEXT_RENDERERS: dict[str, Any] = {
    "risk_assessment": _render_risk_assessment_context,
    "validation_summary": _render_validation_summary_context,
    "build_buy_analysis": _render_build_buy_context,
    "story_generation": _render_story_generation_context,
}


def _try_render_json_context(key: str, content: str) -> str | None:
    """Try to parse content as JSON and render via stage-specific renderer.

    Returns rendered string on success, None on failure (caller falls back).
    """
    renderer = _JSON_CONTEXT_RENDERERS.get(key)
    if not renderer:
        return None
    try:
        data = json.loads(content)
        return renderer(data)
    except (json.JSONDecodeError, TypeError, KeyError, AttributeError):
        return None


def _build_context_summary(context: dict[str, Any], max_chars: int = 200) -> str:
    """Build a concise context summary from previous stage outputs.

    ADR-022: Uses TL;DR sections when available, falls back to first-line
    truncation for backward compatibility. Always includes concept anchor.

    When stage output is JSON (from output_model split), uses stage-specific
    renderers to extract the most useful fields for downstream agents.

    Args:
        context: Dict with previous stage outputs
        max_chars: Maximum characters per context item (for fallback)

    Returns:
        Concise summary string
    """
    summaries = []

    # System goal - ALWAYS include FULL text (this is the source of truth)
    # Never truncate the original idea - it contains critical user constraints
    if context.get("system_goal"):
        summaries.append(
            f"**ORIGINAL IDEA (Source of Truth - read carefully for explicit constraints):**\n{context['system_goal']}"
        )

    # ADR-022: Include concept anchor if available (non-truncatable)
    if context.get("concept_anchor"):
        summaries.append(f"\n{context['concept_anchor']}")

    # Stage outputs - prefer JSON rendering, then TL;DR, then first paragraph
    stage_keys = [
        ("idea_analysis", "Idea Analysis"),
        ("market_context", "Market Context"),
        ("risk_assessment", "Risk Assessment"),
        ("validation_summary", "Validation Summary"),
        ("mvp_scope", "MVP Scope"),
        ("capability_model", "Capability Model"),
        ("system_traits", "System Traits"),
    ]

    for key, label in stage_keys:
        content = context.get(key)
        if not content:
            continue

        # Try JSON rendering first (for stages with output_model)
        json_rendered = _try_render_json_context(key, content)
        if json_rendered:
            summaries.append(f"**{label}:**\n{json_rendered}")
            continue

        # Try TL;DR next (ADR-022)
        tldr = _extract_tldr(content)
        if tldr:
            summaries.append(f"**{label} (TL;DR):**\n{tldr}")
        else:
            # Fallback to first paragraph
            preview = _extract_first_paragraph(content, max_chars)
            if preview:
                summaries.append(f"**{label}:** {preview}")

    return "\n\n".join(summaries)
