"""Idea-validation phase orchestration (WHY).

Functions used by the report-synthesis and market-context stage configs.
"""

import json
import logging
import re
from datetime import UTC, datetime
from typing import Any

from burr.core import State

from haytham.agents.tools.competitor_recording import (
    clear_competitor_accumulator,
    get_competitor_data,
)
from haytham.workflow.agent_runner import run_agent, save_stage_output
from haytham.workflow.stages.concept_anchor import get_anchor_context_string

logger = logging.getLogger(__name__)

# Regex patterns for observability logging in market-context sequential pipeline.
# Formerly imported from validators that were removed in ADR-026.
_REVENUE_EVIDENCE_RE = re.compile(
    r"\*\*Revenue Evidence Tag:\*\*\s*\[?(Priced|Freemium-Dominant|No-Pricing-Found)\]?",
    re.IGNORECASE,
)
_JTBD_MATCH_RE = re.compile(
    r"\*\*JTBD Match:\*\*\s*\[?(Direct|Adjacent|Unrelated)\]?",
    re.IGNORECASE,
)
_SWITCHING_COST_RE = re.compile(
    r"\*\*Switching [Cc]ost:\*\*\s*\[?(Low|Medium|High)\]?",
    re.IGNORECASE,
)

# Regex to extract the JTBD section from market intelligence output.
# Matches "### 2. Jobs-to-be-Done Analysis" through the next "###" heading or end.
_JTBD_SECTION_RE = re.compile(
    r"###\s*2\.\s*Jobs-to-be-Done Analysis\s*\n(.*?)(?=\n###\s|\Z)",
    re.DOTALL,
)


def extract_recommendation_processor(output: str, state: State) -> dict[str, Any]:
    """Post-processor to extract recommendation from report-synthesis output.

    The report-synthesis agent uses a structured output model (ValidationReport)
    with a typed ``recommendation`` field (GO/PIVOT/NO-GO). The stage executor
    stores JSON in state when structured output is configured. This processor
    extracts the recommendation and persists ``recommendation.json`` for fast
    retrieval by the UI and entry validators.

    Returns:
        Dict with ``recommendation`` key (e.g. ``{"recommendation": "GO"}``).
    """
    result: dict[str, Any] = {}

    # Primary path: parse JSON (structured output stages store JSON in state)
    try:
        data = json.loads(output)
        rec = data.get("recommendation", "").upper().strip()
        if rec in ("GO", "NO-GO", "PIVOT"):
            logger.info(f"Recommendation from structured output: {rec}")
            result["recommendation"] = rec

            # Persist recommendation.json for fast retrieval by views
            session_manager = state.get("session_manager")
            if session_manager and hasattr(session_manager, "session_dir"):
                try:
                    meta_path = session_manager.session_dir / "recommendation.json"
                    meta_path.write_text(json.dumps({"recommendation": rec}))
                except OSError:
                    pass  # Non-critical

            return result
    except (json.JSONDecodeError, TypeError, AttributeError):
        pass

    # Fallback: regex from markdown (legacy sessions or non-JSON output)
    output_upper = output.upper()
    match = re.search(r"RECOMMENDATION:\s*(GO|NO-GO|PIVOT)", output_upper)
    if match:
        rec = match.group(1)
        logger.info(f"Recommendation from markdown regex: {rec}")
        return {"recommendation": rec}

    logger.warning("Could not extract recommendation from report synthesis output")
    return {}


def save_final_output(session_manager: Any, output: str) -> None:
    """Additional save operation for report synthesis.

    Saves the rendered output as the latest requirements document.
    Note: recommendation.json is written by extract_recommendation_processor
    which has access to the raw JSON output.
    """
    session_manager.save_final_output(output)


# =============================================================================
# Market Context — Sequential execution with JTBD handoff
# =============================================================================


def _extract_jtbd_section(market_intelligence_output: str) -> str:
    """Extract the Jobs-to-be-Done section from market intelligence output.

    Looks for ``### 2. Jobs-to-be-Done Analysis`` and returns everything up to
    the next ``###`` heading.  Returns empty string if not found (competitor
    agent still works, just without JTBD anchoring).
    """
    match = _JTBD_SECTION_RE.search(market_intelligence_output)
    if match:
        return match.group(1).strip()
    return ""


def extract_competitor_data_processor(output: str, state: State) -> dict[str, Any]:
    """Post-processor: extract structured competitor data from accumulator.

    Reads the module-level accumulator populated by the recording tools
    during the competitor_analysis agent run.  Falls back silently if the
    accumulator is empty (agent didn't call the tools, or old session).
    """
    data = get_competitor_data()
    # Always return all keys — Burr validates that declared write keys are present
    updates: dict[str, Any] = {
        "revenue_evidence_tag": "",
        "switching_cost": "",
        "competitor_jtbd_matches": [],
    }

    mp = data.get("market_positioning", {})
    if mp.get("revenue_evidence_tag"):
        updates["revenue_evidence_tag"] = mp["revenue_evidence_tag"]
    if mp.get("switching_cost"):
        updates["switching_cost"] = mp["switching_cost"]

    competitors = data.get("competitors", [])
    if competitors:
        updates["competitor_jtbd_matches"] = [
            c["jtbd_match"] for c in competitors if c.get("jtbd_match")
        ]

    return updates


def run_market_context_sequential(state: State) -> tuple[str, str]:
    """Run market-context as sequential: market_intelligence → competitor_analysis.

    Market intelligence runs first so its JTBD output can be extracted and
    injected into the competitor analysis agent, producing job-anchored
    competitor discovery instead of category-based search.

    Returns:
        Tuple of (combined_output, status) for stage_executor compatibility.
    """
    system_goal = state.get("system_goal", "")
    idea_analysis = state.get("idea_analysis", "")
    session_manager = state.get("session_manager")

    # Build shared context (same keys the parallel executor would build)
    context: dict[str, Any] = {"system_goal": system_goal}
    if idea_analysis:
        context["idea_analysis"] = idea_analysis

    anchor_str = get_anchor_context_string(state)
    if anchor_str:
        context["concept_anchor"] = anchor_str

    # --- 1. Run market_intelligence first ---
    mi_query = (
        "Conduct comprehensive market research. Analyze market size, trends, "
        "and growth opportunities. Use http_request to fetch live market data."
    )
    mi_result = run_agent("market_intelligence", mi_query, context, session_manager)
    mi_output = mi_result.get("output", "")
    mi_status = mi_result.get("status", "failed")

    # Save MI output file to disk (but NOT a final checkpoint — stage isn't done)
    if session_manager and mi_status == "completed":
        save_stage_output(
            session_manager,
            "market-context",
            "market_intelligence",
            mi_output,
            status="in_progress",  # Stage still running — competitor analysis pending
        )

    # --- 2. Extract JTBD section for competitor agent ---
    jtbd_section = _extract_jtbd_section(mi_output) if mi_output else ""
    if jtbd_section:
        logger.info(f"Extracted JTBD section ({len(jtbd_section)} chars) for competitor analysis")
    else:
        logger.warning(
            "No JTBD section found in market intelligence output — competitor agent will use category-based search"
        )

    # --- 3. Run competitor_analysis with JTBD context ---
    ca_query = (
        "Analyze the competitive landscape. Identify key competitors, their "
        "strengths and weaknesses, and opportunities for differentiation."
    )
    # Inject JTBD as additional context so the competitor agent can use it
    ca_context = dict(context)
    if jtbd_section:
        ca_context["jtbd_context"] = jtbd_section

    clear_competitor_accumulator()
    ca_result = run_agent("competitor_analysis", ca_query, ca_context, session_manager)
    ca_output = ca_result.get("output", "")
    ca_status = ca_result.get("status", "failed")

    # Save CA output file to disk (skip checkpoint — final one written below)
    if session_manager and ca_output:
        save_stage_output(
            session_manager,
            "market-context",
            "competitor_analysis",
            ca_output,
            status="in_progress",
        )

    # --- Revenue evidence observability ---
    if ca_output:
        rev_match = _REVENUE_EVIDENCE_RE.search(ca_output)
        rev_tag = rev_match.group(1).strip() if rev_match else ""
        if rev_tag:
            logger.info(f"Revenue Evidence Tag: {rev_tag}")
        else:
            logger.warning("No Revenue Evidence Tag found in competitor analysis output")

        jtbd_matches = [m.group(1).strip() for m in _JTBD_MATCH_RE.finditer(ca_output)]
        if jtbd_matches:
            logger.info(f"JTBD Matches: {jtbd_matches}")

        sc_match = _SWITCHING_COST_RE.search(ca_output)
        switching_cost = sc_match.group(1).strip() if sc_match else ""
        if switching_cost:
            logger.info(f"Switching Cost: {switching_cost}")

    # --- 4. Combine outputs (same format as _execute_parallel) ---
    combined = ""
    combined += "\n\n## Market Intelligence\n\n" + (mi_output or "No output")
    combined += "\n\n## Competitor Analysis\n\n" + (ca_output or "No output")

    all_completed = mi_status == "completed" and ca_status == "completed"
    status = "completed" if all_completed else "partial"

    # --- 5. Write final checkpoint with correct status and all agents ---
    if session_manager:
        try:
            session_manager.save_checkpoint(
                stage_slug="market-context",
                status=status,
                agents=[
                    {
                        "agent_name": "market_intelligence",
                        "status": mi_status,
                        "output_length": len(mi_output),
                    },
                    {
                        "agent_name": "competitor_analysis",
                        "status": ca_status,
                        "output_length": len(ca_output),
                    },
                ],
                completed=datetime.now(UTC).isoformat().replace("+00:00", "Z"),
                execution_mode="sequential",
            )
        except (ValueError, FileNotFoundError, OSError) as e:
            logger.error(f"Failed to save final market-context checkpoint: {e}")

    logger.info(
        f"Market context sequential completed: mi={mi_status}, ca={ca_status}, "
        f"jtbd={'yes' if jtbd_section else 'no'}, combined={len(combined.strip())} chars"
    )
    return combined.strip(), status
