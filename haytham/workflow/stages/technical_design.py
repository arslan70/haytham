"""Technical-design phase orchestration (HOW).

Functions used by build-buy-analysis and architecture-decisions stage configs.
"""

import json
import logging

from burr.core import State

logger = logging.getLogger(__name__)


def run_architecture_decisions(state: State) -> tuple[str, str]:
    """Run architecture decisions stage using the workflow_2 implementation.

    This stage makes key technical decisions based on build vs buy analysis.
    Creates decisions that:
    - Cover ALL capabilities (functional and non-functional)
    - Implement Build/Buy recommendations
    - Specify HOW to use the recommended services
    """
    from haytham.phases.workflow_2.actions import (
        ARCHITECTURE_DECISIONS_PROMPT,
        extract_json_from_response,
        run_architect_agent,
    )

    # Get context from state
    system_goal = state.get("system_goal", "")
    mvp_scope = state.get("mvp_scope", "")
    capability_model = state.get("capability_model", "")
    build_buy_raw = state.get("build_buy_analysis", "")

    # Parse build_buy_analysis — may be JSON (from output_model) or markdown (legacy)
    try:
        bb_data = json.loads(build_buy_raw)
        # Extract a prompt-friendly summary from structured data
        stack_lines = []
        for svc in bb_data.get("recommended_stack", []):
            name = svc.get("name", "?")
            cat = svc.get("category", "?")
            rec = svc.get("recommendation", "BUY")
            stack_lines.append(f"- {name} ({cat}): {rec}")
        build_buy_analysis = (
            f"System Summary: {bb_data.get('system_summary', '')}\n"
            f"Stack Rationale: {bb_data.get('stack_rationale', '')}\n"
            f"Recommended Stack:\n" + "\n".join(stack_lines)
        )
    except (json.JSONDecodeError, TypeError):
        build_buy_analysis = build_buy_raw  # backward compat with markdown

    # Build context for the prompt - use correct field names matching the template
    # Don't over-truncate - the agent needs full context for complete coverage
    context = {
        "system_goal": system_goal,
        "mvp_scope": mvp_scope[:3000] if mvp_scope else "",
        "build_buy_analysis": build_buy_analysis[:4000] if build_buy_analysis else "",
        "capabilities": capability_model[:4000] if capability_model else "[]",
        "existing_decisions": "[]",
    }

    # Run the agent
    result = run_architect_agent(
        agent_name="architecture_decisions",
        prompt_template=ARCHITECTURE_DECISIONS_PROMPT,
        context=context,
    )

    if result["status"] == "failed":
        return f"Error: {result.get('error', 'Unknown error')}", "failed"

    # Parse the response
    parsed = extract_json_from_response(result["output"])

    if not parsed or "decisions" not in parsed:
        # Return raw output if parsing fails
        return result["output"], "completed"

    # Build output summary
    output_md = "# Architecture Decisions\n\n"
    output_md += f"**Summary:** {parsed.get('summary', 'N/A')}\n\n"
    output_md += f"**Decisions Created:** {len(parsed.get('decisions', []))}\n\n"

    # Add coverage check summary if present
    coverage = parsed.get("coverage_check", {})
    if coverage:
        func_covered = coverage.get("functional_capabilities_covered", [])
        nf_covered = coverage.get("non_functional_capabilities_covered", [])
        uncovered = coverage.get("uncovered_capabilities", [])

        output_md += "## Coverage Summary\n\n"
        output_md += f"- **Functional Capabilities Covered:** {', '.join(func_covered) if func_covered else 'None'}\n"
        output_md += f"- **Non-Functional Capabilities Covered:** {', '.join(nf_covered) if nf_covered else 'None'}\n"
        if uncovered:
            output_md += f"- **Uncovered Capabilities:** {', '.join(uncovered)}\n"
        else:
            output_md += "- **All capabilities covered**\n"
        output_md += "\n---\n\n"

    # Output each decision
    for i, dec in enumerate(parsed.get("decisions", []), 1):
        dec_id = dec.get("id", f"DEC-{i:03d}")
        output_md += f"## {i}. {dec_id}: {dec.get('name', 'Unnamed')}\n\n"
        output_md += f"**Description:** {dec.get('description', 'N/A')}\n\n"
        output_md += f"**Rationale:** {dec.get('rationale', 'N/A')}\n\n"

        serves = dec.get("serves_capabilities", [])
        if serves:
            output_md += f"**Serves Capabilities:** {', '.join(serves)}\n\n"

        implements = dec.get("implements_recommendation", "")
        if implements:
            output_md += f"**Implements:** {implements}\n\n"

        alternatives = dec.get("alternatives_considered", [])
        if alternatives:
            output_md += "**Alternatives Considered:**\n"
            for alt in alternatives:
                output_md += f"- {alt}\n"
            output_md += "\n"

        output_md += "---\n\n"

    return output_md, "completed"


def analyze_capabilities_for_build_buy(state: State) -> tuple[str, str]:
    """Analyze capabilities for build vs buy recommendations.

    Uses the build_buy_analyzer LLM agent with structured output to provide:
    1. Infrastructure overview - high-level requirements
    2. Recommended stack - services with rationale
    3. Alternatives - other options with pros/cons
    """
    from haytham.agents.factory.agent_factory import create_agent_by_name
    from haytham.agents.worker_build_buy_advisor.build_buy_models import (
        BuildBuyAnalysisOutput,
        format_build_buy_analysis,
    )

    # Get capability model and system goal from state
    capability_model = state.get("capability_model", "")
    mvp_scope = state.get("mvp_scope", "")
    system_goal = state.get("system_goal", "")

    if not capability_model:
        return "Error: No capability model found in state", "failed"

    try:
        # Create the agent with structured output
        agent = create_agent_by_name("build_buy_analyzer")

        # Build the query with context
        query = f"""Analyze the following startup and its capabilities to provide build vs buy recommendations.

## System Goal
{system_goal}

## MVP Scope
{mvp_scope}

## Capability Model
{capability_model}

Based on this information:
1. Identify the high-level infrastructure requirements
2. Recommend a stack of services/build decisions with clear rationale
3. Provide alternatives for key BUY recommendations

Focus on MVP stage - favor services with generous free tiers and quick integration."""

        # Run the agent
        result = agent(query)

        from haytham.agents.output_utils import extract_text_from_result

        # Check for structured_output attribute (Strands structured output)
        # Return JSON for Burr state; executor renders markdown for disk via output_model
        if hasattr(result, "structured_output") and result.structured_output is not None:
            if isinstance(result.structured_output, BuildBuyAnalysisOutput):
                return result.structured_output.model_dump_json(), "completed"
            # If it's a dict, try to validate and return as JSON
            if isinstance(result.structured_output, dict):
                try:
                    validated = BuildBuyAnalysisOutput.model_validate(result.structured_output)
                    return validated.model_dump_json(), "completed"
                except (ValueError, TypeError):
                    output = format_build_buy_analysis(result.structured_output)
                    return output, "completed"

        # Fallback: extract text from agent result
        return extract_text_from_result(result), "completed"

    except Exception as e:
        logger.error(f"Build/Buy analysis failed: {e}", exc_info=True)
        return f"Error analyzing capabilities: {str(e)}", "failed"
