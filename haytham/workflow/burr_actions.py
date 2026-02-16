"""Burr Actions for Haytham Validation Workflow.

Each action represents a stage in the validation workflow.
Actions integrate with the existing agent factory and session manager.

The @action decorator specifies:
- reads: State keys this action needs to read
- writes: State keys this action will write to
"""

import json
import logging
import time
from datetime import datetime
from typing import Any

from burr.core import State, action

logger = logging.getLogger(__name__)


# =============================================================================
# Error Handling Helpers
# =============================================================================


def _is_token_limit_error(error: Exception) -> bool:
    """Check if an error is a token limit error from Bedrock.

    Args:
        error: The exception to check

    Returns:
        True if this is a token limit error
    """
    error_str = str(error).lower()

    # Check for common token limit indicators from AWS Bedrock
    token_limit_indicators = [
        "token",
        "maxtoken",
        "max_token",
        "context length",
        "too long",
        "exceeds the max",
        "input is too long",
        "validationexception",
        "input too large",
    ]

    return any(indicator in error_str for indicator in token_limit_indicators)


def _get_user_friendly_error(error: Exception, agent_name: str) -> str:
    """Get a user-friendly error message for display.

    Args:
        error: The exception that occurred
        agent_name: Name of the agent that failed

    Returns:
        User-friendly error message
    """
    if _is_token_limit_error(error):
        return (
            f"Token limit exceeded in {agent_name}. "
            "Your idea description may be too long. Try shortening it, "
            "or reduce the DEFAULT_MAX_TOKENS setting in .env if outputs are being truncated."
        )

    # For other errors, return the original message
    return str(error)


# =============================================================================
# Agent Execution Helpers
# =============================================================================


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
    import re

    # Look for ## TL;DR or ## TLDR section (case insensitive)
    tldr_pattern = r"##\s*TL;?DR\s*\n(.*?)(?=\n##|\Z)"
    match = re.search(tldr_pattern, content, re.IGNORECASE | re.DOTALL)

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


def run_agent(
    agent_name: str,
    query: str,
    context: dict[str, Any],
    session_manager: Any = None,
    use_context_tools: bool = False,
    trace_attributes: dict[str, Any] | None = None,
    output_as_json: bool = False,
) -> dict[str, Any]:
    """Execute an agent using the existing agent factory.

    Timing, lifecycle logging, and OTEL span annotation are handled by
    HaythamAgentHooks (registered on every agent via agent_factory.py).
    This function focuses on context building, output extraction, and
    error classification.

    Args:
        agent_name: Name of the agent to run (e.g., "concept_expansion")
        query: Query string for the agent
        context: Context dict with previous stage outputs
        session_manager: Optional SessionManager for file operations
        use_context_tools: If True, set up context store for context retrieval tools
                          instead of pre-building context summary
        trace_attributes: Optional attributes for OpenTelemetry tracing
        output_as_json: If True, return JSON from Pydantic structured outputs
                       instead of rendering markdown

    Returns:
        Dict with agent output and metadata
    """
    start_time = time.time()

    try:
        from haytham.agents.factory.agent_factory import create_agent_by_name

        agent = create_agent_by_name(agent_name, trace_attributes=trace_attributes)

        if agent is None:
            raise ValueError(f"Agent factory returned None for {agent_name}")

        # Build full query
        full_query = query

        if use_context_tools:
            from haytham.agents.tools.context_retrieval import (
                clear_context_store,
                set_context_store,
            )

            set_context_store(context)
            full_query += "\n\nUse the context retrieval tools to access relevant information from previous stages."
        else:
            context_summary = _build_context_summary(context)
            if context_summary:
                full_query += f"\n\n## Context from Previous Stages:\n{context_summary}"

        logger.info(f"Running agent {agent_name} with query length: {len(full_query)}")

        try:
            result = agent(full_query)
            output_text = _extract_agent_output(result, output_as_json=output_as_json)
            execution_time = time.time() - start_time

            if not output_text or not output_text.strip():
                logger.error(f"Agent {agent_name} returned empty output")
                return {
                    "output": f"Error: Agent {agent_name} produced no output. This may indicate a structured output parsing failure or token limit issue.",
                    "agent_name": agent_name,
                    "status": "failed",
                    "error": "Empty output",
                    "execution_time": execution_time,
                }

            return {
                "output": output_text,
                "agent_name": agent_name,
                "status": "completed",
                "execution_time": execution_time,
            }
        finally:
            if use_context_tools:
                clear_context_store()

    except Exception as e:
        execution_time = time.time() - start_time
        user_error = _get_user_friendly_error(e, agent_name)
        is_token_error = _is_token_limit_error(e)

        # Classify and log — HaythamAgentHooks handles generic lifecycle logging,
        # but error classification is business logic that stays here.
        if is_token_error:
            logger.error(
                f"Agent {agent_name} token limit error: {e}",
                extra={"agent": agent_name, "error_type": "token_limit"},
            )
        else:
            logger.error(
                f"Agent {agent_name} failed: {e}",
                exc_info=True,
                extra={"agent": agent_name, "error_type": type(e).__name__},
            )

        return {
            "output": f"Error executing {agent_name}: {user_error}",
            "agent_name": agent_name,
            "status": "failed",
            "error": user_error,
            "error_type": "token_limit" if is_token_error else type(e).__name__,
            "original_error": str(e),
            "execution_time": execution_time,
        }


def run_parallel_agents(
    agent_configs: list[dict[str, str]],
    context: dict[str, Any],
    session_manager: Any = None,
    use_context_tools: bool = False,
) -> dict[str, Any]:
    """Execute multiple agents in parallel.

    Args:
        agent_configs: List of dicts with 'name' and 'query' keys
        context: Shared context for all agents
        session_manager: Optional SessionManager for file operations
        use_context_tools: If True, set up context store for context retrieval tools

    Returns:
        Dict mapping agent_name -> result
    """
    import concurrent.futures

    def run_single(config):
        return run_agent(
            agent_name=config["name"],
            query=config["query"],
            context=context,
            session_manager=session_manager,
            use_context_tools=use_context_tools,
        )

    results = {}

    try:
        # Use ThreadPoolExecutor for parallel execution
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            futures = {
                executor.submit(run_single, config): config["name"] for config in agent_configs
            }

            for future in concurrent.futures.as_completed(futures):
                agent_name = futures[future]
                try:
                    results[agent_name] = future.result()
                except Exception as e:
                    user_error = _get_user_friendly_error(e, agent_name)
                    is_token_error = _is_token_limit_error(e)
                    logger.error(
                        f"Parallel agent {agent_name} failed: {e}",
                        extra={
                            "agent": agent_name,
                            "error_type": "token_limit" if is_token_error else type(e).__name__,
                        },
                    )
                    results[agent_name] = {
                        "output": f"Error: {user_error}",
                        "agent_name": agent_name,
                        "status": "failed",
                        "error": user_error,
                        "error_type": "token_limit" if is_token_error else type(e).__name__,
                        "original_error": str(e),
                    }

    except Exception as e:
        logger.error(f"Parallel execution failed: {e}")
        # Fallback to sequential
        for config in agent_configs:
            results[config["name"]] = run_agent(
                agent_name=config["name"],
                query=config["query"],
                context=context,
                session_manager=session_manager,
                use_context_tools=use_context_tools,
            )

    return results


def _format_pydantic_model_as_markdown(model: Any) -> str:
    """Format a Pydantic model as human-readable markdown.

    Prefers the model's own ``to_markdown()`` method (all output models
    should implement it). Falls back to a generic ``model_dump()`` renderer.

    Args:
        model: A Pydantic BaseModel instance

    Returns:
        Formatted markdown string
    """
    from pydantic import BaseModel

    if not isinstance(model, BaseModel):
        return ""

    # Primary: use the model's own to_markdown()
    if hasattr(model, "to_markdown") and callable(model.to_markdown):
        try:
            result = model.to_markdown()
            if result and result.strip():
                return result
        except Exception:
            pass  # Fall through to generic rendering

    # Generic fallback: render model_dump() as markdown
    try:
        data = model.model_dump()
        lines: list[str] = ["# Structured Output\n"]
        for key, value in data.items():
            if isinstance(value, list):
                lines.append(f"## {key.replace('_', ' ').title()}\n")
                for i, item in enumerate(value, 1):
                    if isinstance(item, dict):
                        lines.append(f"### Item {i}")
                        for k, v in item.items():
                            lines.append(f"- **{k}:** {v}")
                        lines.append("")
                    else:
                        lines.append(f"- {item}")
            elif isinstance(value, dict):
                lines.append(f"## {key.replace('_', ' ').title()}\n")
                for k, v in value.items():
                    lines.append(f"- **{k}:** {v}")
                lines.append("")
            else:
                lines.append(f"**{key.replace('_', ' ').title()}:** {value}\n")
    except Exception:
        return str(model)

    return "\n".join(lines)


def _extract_agent_output(result: Any, output_as_json: bool = False) -> str:
    """Extract text output from various agent result formats.

    Thin wrapper around :func:`haytham.agents.output_utils.extract_text_from_result`
    kept for backward compatibility with existing import sites.
    """
    from haytham.agents.output_utils import extract_text_from_result

    return extract_text_from_result(result, output_as_json=output_as_json)


def _format_tool_use_output(tool_use: dict) -> str:
    """Format tool use output as readable markdown."""
    if not isinstance(tool_use, dict):
        return str(tool_use)

    tool_name = tool_use.get("name", "Unknown Tool")
    tool_input = tool_use.get("input", {})

    # Handle ValidationOutput specifically
    if tool_name == "ValidationOutput" and isinstance(tool_input, dict):
        return _format_validation_output(tool_input)

    # Handle ValidationSummaryOutput specifically
    if tool_name == "ValidationSummaryOutput" and isinstance(tool_input, dict):
        return _format_validation_summary_output(tool_input)

    # Generic tool output formatting
    return _format_dict_as_markdown(tool_input)


def _format_validation_summary_output(data: dict) -> str:
    """Format ValidationSummaryOutput tool response as markdown."""
    lines = ["# Validation Summary\n"]

    # Executive Summary
    if "executive_summary" in data:
        lines.append("## Executive Summary\n")
        lines.append(data["executive_summary"])
        lines.append("")

    # Validation Findings
    if "validation_findings" in data:
        findings = data["validation_findings"]
        lines.append("---\n")
        lines.append("## Validation Findings\n")

        if "market_opportunity" in findings:
            lines.append("### Market Opportunity\n")
            lines.append(findings["market_opportunity"])
            lines.append("")

        if "competition" in findings:
            lines.append("### Competition\n")
            lines.append(findings["competition"])
            lines.append("")

        if "critical_risks" in findings:
            lines.append("### Critical Risks\n")
            for risk in findings["critical_risks"]:
                lines.append(f"- {risk}")
            lines.append("")

    # Go/No-Go Assessment
    if "go_no_go_assessment" in data:
        assessment = data["go_no_go_assessment"]
        lines.append("---\n")
        lines.append("## Go/No-Go Assessment\n")

        if "strengths" in assessment:
            lines.append("### Strengths\n")
            for s in assessment["strengths"]:
                lines.append(f"- {s}")
            lines.append("")

        if "weaknesses" in assessment:
            lines.append("### Weaknesses\n")
            for w in assessment["weaknesses"]:
                lines.append(f"- {w}")
            lines.append("")

        if "counter_signals" in assessment and assessment["counter_signals"]:
            lines.append("### Counter-Signals Reconciliation\n")
            for cs in assessment["counter_signals"]:
                dims = ", ".join(cs.get("affected_dimensions", []))
                lines.append(
                    f"- **{cs.get('signal', '')}** (source: {cs.get('source', '?')}, affects: {dims})"
                )
                # Prefer structured fields; fall back to legacy reconciliation
                if (
                    cs.get("evidence_cited")
                    or cs.get("why_score_holds")
                    or cs.get("what_would_change_score")
                ):
                    if cs.get("evidence_cited"):
                        lines.append(f"  - *Evidence cited:* {cs['evidence_cited']}")
                    if cs.get("why_score_holds"):
                        lines.append(f"  - *Why score holds:* {cs['why_score_holds']}")
                    if cs.get("what_would_change_score"):
                        lines.append(
                            f"  - *What would change score:* {cs['what_would_change_score']}"
                        )
                elif cs.get("reconciliation"):
                    lines.append(f"  - *Reconciliation:* {cs['reconciliation']}")
            lines.append("")

        if "guidance" in assessment:
            lines.append("### Guidance\n")
            lines.append(assessment["guidance"])
            lines.append("")

    # Next Steps
    if "next_steps" in data:
        lines.append("---\n")
        lines.append("## Next Steps\n")
        for i, step in enumerate(data["next_steps"], 1):
            lines.append(f"{i}. {step}")

    return "\n".join(lines)


def _format_validation_output(data: dict) -> str:
    """Format ValidationOutput tool response as markdown."""
    lines = ["# Risk Assessment Report\n"]

    # Summary section
    summary = data.get("summary", {})
    if summary:
        lines.append("## Summary\n")
        lines.append(f"- **Total Claims Analyzed:** {summary.get('total_claims', 'N/A')}")
        lines.append(f"- **Supported:** {summary.get('supported', 0)}")
        lines.append(f"- **Partial:** {summary.get('partial', 0)}")
        lines.append(f"- **Unsupported:** {summary.get('unsupported', 0)}")
        lines.append(f"- **High Risks:** {summary.get('high_risks', 0)}")
        lines.append(f"- **Medium Risks:** {summary.get('medium_risks', 0)}")
        lines.append("")

    # Risks section
    risks = data.get("risks", [])
    if risks:
        lines.append("## Identified Risks\n")
        for risk in risks:
            level = risk.get("level", "unknown").upper()
            desc = risk.get("description", "No description")
            mitigation = risk.get("mitigation", "No mitigation suggested")
            lines.append(f"### Risk ({level})")
            lines.append(f"**Description:** {desc}\n")
            lines.append(f"**Mitigation:** {mitigation}\n")

    # Claims section
    claims = data.get("claims", [])
    if claims:
        lines.append("## Claims Analysis\n")
        for claim in claims[:5]:  # Limit to first 5 claims
            text = claim.get("text", "")
            validation = claim.get("validation", "unknown")
            reasoning = claim.get("reasoning", "")
            lines.append(f"- **{validation.upper()}:** {text}")
            if reasoning:
                lines.append(f"  - *{reasoning}*")
        if len(claims) > 5:
            lines.append(f"\n*...and {len(claims) - 5} more claims*")

    return "\n".join(lines)


def _format_dict_as_markdown(data: dict) -> str:
    """Format a dictionary as readable markdown."""
    if not isinstance(data, dict):
        return str(data)

    lines = []
    for key, value in data.items():
        if isinstance(value, dict):
            lines.append(f"## {key.replace('_', ' ').title()}\n")
            for k, v in value.items():
                lines.append(f"- **{k.replace('_', ' ').title()}:** {v}")
        elif isinstance(value, list):
            lines.append(f"## {key.replace('_', ' ').title()}\n")
            for item in value[:10]:  # Limit list items
                if isinstance(item, dict):
                    # Format dict item
                    item_str = ", ".join(f"{k}: {v}" for k, v in list(item.items())[:3])
                    lines.append(f"- {item_str}")
                else:
                    lines.append(f"- {item}")
        else:
            lines.append(f"**{key.replace('_', ' ').title()}:** {value}")

    return "\n".join(lines) if lines else str(data)


def save_stage_output(
    session_manager: Any,
    stage_slug: str,
    agent_name: str,
    output: str,
    status: str = "completed",
) -> None:
    """Save agent output to session directory."""
    if session_manager is None:
        logger.warning(f"No session manager, skipping save for {stage_slug}/{agent_name}")
        return

    # Save output file first - this is the critical artifact
    try:
        stage_dir = session_manager.session_dir / stage_slug
        stage_dir.mkdir(parents=True, exist_ok=True)

        output_file = stage_dir / f"{agent_name}.md"
        output_file.write_text(output, encoding="utf-8")

        logger.info(f"Saved output to {output_file}")
    except Exception as e:
        logger.error(f"Failed to save stage output file: {e}")

    # Save checkpoint separately - non-critical, don't block on failure
    try:
        session_manager.save_checkpoint(
            stage_slug=stage_slug,
            status=status,
            agents=[{"agent_name": agent_name, "status": status, "output_length": len(output)}],
            completed=datetime.utcnow().isoformat() + "Z",
        )
    except Exception as e:
        logger.error(f"Failed to save checkpoint for {stage_slug}: {e}")


# =============================================================================
# Stage Actions (using StageExecutor)
# =============================================================================

# Import stage executor for clean delegation
from .stage_executor import execute_stage


@action(
    reads=["system_goal", "idea_analysis_status", "session_manager", "archetype"],
    writes=[
        "idea_analysis",
        "idea_analysis_status",
        "current_stage",
        "concept_anchor",
        "concept_anchor_str",
    ],
)
def idea_analysis(state: State) -> State:
    """Stage 1: Analyze the startup idea.

    Also extracts the concept anchor (ADR-022) for downstream stages.
    """
    return execute_stage("idea-analysis", state)


@action(
    reads=["system_goal", "idea_analysis", "market_context_status"],
    writes=[
        "market_context",
        "market_context_status",
        "current_stage",
        "revenue_evidence_tag",
        "switching_cost",
        "competitor_jtbd_matches",
    ],
)
def market_context(state: State) -> State:
    """Stage 2: Research market context."""
    return execute_stage("market-context", state)


@action(
    reads=["system_goal", "idea_analysis", "market_context", "risk_assessment_status"],
    writes=["risk_assessment", "risk_level", "risk_assessment_status", "current_stage"],
)
def risk_assessment(state: State) -> State:
    """Stage 3: Assess risks and determine risk level."""
    return execute_stage("risk-assessment", state)


@action(
    reads=[
        "system_goal",
        "idea_analysis",
        "market_context",
        "risk_assessment",
        "pivot_strategy_status",
    ],
    writes=["pivot_strategy", "pivot_strategy_status", "current_stage"],
)
def pivot_strategy(state: State) -> State:
    """Stage 3b: Develop pivot strategy (conditional, for HIGH risk)."""
    return execute_stage("pivot-strategy", state)


@action(
    reads=[
        "system_goal",
        "idea_analysis",
        "market_context",
        "risk_assessment",
        "pivot_strategy",
        "validation_summary_status",
    ],
    writes=["validation_summary", "validation_summary_status", "current_stage"],
)
def validation_summary(state: State) -> State:
    """Stage 4: Generate validation summary."""
    return execute_stage("validation-summary", state)


@action(
    reads=[
        "system_goal",
        "idea_analysis",
        "market_context",
        "risk_assessment",
        "validation_summary",
        "mvp_scope_status",
        "concept_anchor",  # ADR-022: For anchor compliance
        "concept_anchor_str",  # ADR-022: For agent context
        "session_manager",
    ],
    writes=["mvp_scope", "mvp_scope_status", "current_stage"],
)
def mvp_scope(state: State) -> State:
    """Stage 5: Define MVP scope.

    Defines a focused, achievable MVP scope based on the validation summary:
    - The One Thing (core value proposition)
    - Primary user segment
    - MVP boundaries (in scope vs out of scope)
    - Success criteria
    - Core user flows (max 3)
    """
    return execute_stage("mvp-scope", state)


@action(
    reads=[
        "system_goal",
        "idea_analysis",
        "market_context",
        "risk_assessment",
        "validation_summary",
        "mvp_scope",
        "capability_model_status",
        "concept_anchor",  # ADR-022: For anchor compliance
        "concept_anchor_str",  # ADR-022: For agent context
        "session_manager",
    ],
    writes=["capability_model", "capability_model_status", "current_stage"],
)
def capability_model(state: State) -> State:
    """Stage 6: Generate capability model.

    Transforms the MVP scope into a structured capability model that defines
    WHAT the system does: functional capabilities (what users can do) and
    non-functional capabilities (quality attributes) that serve ONLY the
    defined MVP scope.
    """
    return execute_stage("capability-model", state)


@action(
    reads=[
        "system_goal",
        "idea_analysis",
        "mvp_scope",
        "capability_model",
        "system_traits_status",
        "concept_anchor",  # ADR-022: For anchor compliance
        "concept_anchor_str",  # ADR-022: For agent context
        "session_manager",
    ],
    writes=[
        "system_traits",
        "system_traits_status",
        "system_traits_parsed",
        "system_traits_warnings",
        "current_stage",
    ],
)
def system_traits(state: State) -> State:
    """Stage 6b: Classify system traits.

    Detects 5 system traits (interface, auth, deployment, data_layer, realtime)
    based on upstream context. Traits control which story layers are generated
    downstream, eliminating irrelevant noise for non-web ideas.
    """
    return execute_stage("system-traits", state)


@action(
    reads=[
        "capability_model",
        "mvp_scope",
        "system_goal",
        "build_buy_analysis_status",
        "concept_anchor",  # ADR-022: For anchor compliance
        "concept_anchor_str",  # ADR-022: For agent context
        "session_manager",
    ],
    writes=["build_buy_analysis", "build_buy_analysis_status", "current_stage"],
)
def build_buy_analysis(state: State) -> State:
    """Stage 7: Analyze capabilities for build vs buy recommendations.

    Analyzes each capability from the Capability Model to determine whether
    to BUILD custom code, BUY existing services, or use a HYBRID approach.

    This stage uses programmatic analysis (keyword matching against service
    catalog) rather than an LLM agent for fast, deterministic results.

    Output informs:
    - Architecture decisions (what services to integrate)
    - Story generation (INTEGRATION vs IMPLEMENTATION stories)
    """
    return execute_stage("build-buy-analysis", state)


@action(
    reads=[
        "capability_model",
        "mvp_scope",
        "build_buy_analysis",
        "system_goal",
        "architecture_decisions_status",
        "concept_anchor",  # ADR-022: For anchor compliance
        "concept_anchor_str",  # ADR-022: For agent context
        "session_manager",
    ],
    writes=["architecture_decisions", "architecture_decisions_status", "current_stage"],
)
def architecture_decisions(state: State) -> State:
    """Stage 8: Make key architecture decisions.

    Based on Build vs Buy analysis, makes technical decisions (DEC-*):
    - Component structure and boundaries
    - Technology choices for BUILD capabilities
    - Integration patterns for BUY capabilities
    - Data flow and storage decisions

    Output guides story generation with technical constraints.
    """
    return execute_stage("architecture-decisions", state)


@action(
    reads=[
        "capability_model",
        "build_buy_analysis",
        "architecture_decisions",
        "system_goal",
        "story_generation_status",
        "concept_anchor",  # ADR-022: For anchor compliance
        "concept_anchor_str",  # ADR-022: For agent context
        "session_manager",
    ],
    writes=["story_generation", "story_generation_status", "current_stage"],
)
def story_generation(state: State) -> State:
    """Stage 9: Generate user stories from capabilities.

    Creates implementation-ready user stories:
    - BUILD capabilities -> implementation stories
    - BUY capabilities -> integration stories
    - Each story tagged with implements:CAP-* labels
    - Stories follow INVEST criteria

    Output is a structured list of stories ready for validation.
    """
    return execute_stage("story-generation", state)


@action(
    reads=["capability_model", "story_generation", "system_goal", "story_validation_status"],
    writes=["story_validation", "story_validation_status", "current_stage"],
)
def story_validation(state: State) -> State:
    """Stage 10: Validate stories against capabilities.

    Ensures story coverage and quality:
    - Each capability covered by at least one story
    - Stories meet INVEST criteria
    - No orphan stories (all trace to capabilities)
    - Acceptance criteria are testable

    Output includes validation report and any gaps identified.
    """
    return execute_stage("story-validation", state)


@action(
    reads=["story_generation", "story_validation", "system_goal", "dependency_ordering_status"],
    writes=["dependency_ordering", "dependency_ordering_status", "current_stage"],
)
def dependency_ordering(state: State) -> State:
    """Stage 11: Order stories by dependencies.

    Creates implementation roadmap:
    - Infrastructure stories first
    - Core features next
    - Enhancements last
    - Dependency graph for parallel execution

    Output is an ordered task list ready for a coding agent.
    """
    return execute_stage("dependency-ordering", state)


# =============================================================================
# Human-in-the-loop Actions
# =============================================================================


@action(reads=["current_stage"], writes=["user_approved", "user_feedback"])
def await_user_approval(state: State, approved: bool = True, feedback: str = "") -> State:
    """Wait for user approval of current stage.

    This action is used to pause workflow for human review.
    In the UI, this would present approval buttons.

    Args:
        approved: Whether user approved the stage
        feedback: Optional feedback from user
    """
    current_stage = state.get("current_stage", "unknown")
    logger.info(f"User approval for {current_stage}: approved={approved}")

    return state.update(
        user_approved=approved,
        user_feedback=feedback,
    )


@action(reads=[], writes=["user_choice"])
def await_user_choice(state: State, choice: str = "") -> State:
    """Wait for user to make a choice (for branching).

    Used when multiple transitions are available and
    the user needs to select which path to take.

    Args:
        choice: The user's selected option
    """
    logger.info(f"User choice received: {choice}")
    return state.update(user_choice=choice)
