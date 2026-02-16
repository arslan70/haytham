"""Idea-validation phase orchestration (WHY).

Functions used by the risk-assessment, validation-summary, and market-context
stage configs.
"""

import json
import logging
import re
from datetime import datetime
from typing import Any

from burr.core import State

from haytham.agents.tools.competitor_recording import (
    clear_competitor_accumulator,
    get_competitor_data,
)
from haytham.workflow.validators.dim8_inputs import _SWITCHING_COST_RE
from haytham.workflow.validators.jtbd_match import _JTBD_MATCH_RE
from haytham.workflow.validators.revenue_evidence import _REVENUE_TAG_RE as _REVENUE_EVIDENCE_RE

logger = logging.getLogger(__name__)

# Regex to extract the JTBD section from market intelligence output.
# Matches "### 2. Jobs-to-be-Done Analysis" through the next "###" heading or end.
_JTBD_SECTION_RE = re.compile(
    r"###\s*2\.\s*Jobs-to-be-Done Analysis\s*\n(.*?)(?=\n###\s|\Z)",
    re.DOTALL,
)


def extract_risk_level_processor(output: str, state: State) -> dict[str, Any]:
    """Post-processor to extract risk level from agent's structured output.

    The startup_validator agent now includes an explicit overall_risk_level field
    in its ValidationOutput model. This processor extracts that value from the
    formatted markdown output.

    This is an agentic approach: instead of inferring risk from keyword counting,
    we trust the agent's direct assessment based on its analysis.
    """
    output_upper = output.upper()

    # Look for the explicit "Overall Risk Level:" line from ValidationOutput
    # This is set directly by the agent in its structured output
    match = re.search(r"OVERALL RISK LEVEL:\s*(HIGH|MEDIUM|LOW)", output_upper)
    if match:
        risk_level = match.group(1)
        logger.info(f"Risk level from agent assessment: {risk_level}")
        return {"risk_level": risk_level}

    # Fallback: Check for legacy format (for backward compatibility with existing sessions)
    if "RISK LEVEL: HIGH" in output_upper or "OVERALL RISK: HIGH" in output_upper:
        risk_level = "HIGH"
    elif "RISK LEVEL: LOW" in output_upper or "OVERALL RISK: LOW" in output_upper:
        risk_level = "LOW"
    elif "RISK LEVEL: MEDIUM" in output_upper or "OVERALL RISK: MEDIUM" in output_upper:
        risk_level = "MEDIUM"
    else:
        # Default to MEDIUM if no explicit assessment found
        risk_level = "MEDIUM"
        logger.warning("No explicit risk level found in output, defaulting to MEDIUM")

    logger.info(f"Risk level determined: {risk_level}")
    return {"risk_level": risk_level}


_CONFIDENCE_EXTERNAL_RATIO_RE = re.compile(
    r"external\s+validation:\*?\*?\s*(\d+)/(\d+)",
    re.IGNORECASE,
)

_CONTRADICTED_CRITICAL_RE = re.compile(
    r"\|\s*C\d+\s*\|[^|]*\|[^|]*\|[^|]*\|\s*critical\s*\|\s*contradicted\s*\|",
    re.IGNORECASE,
)


def _apply_confidence_rubric(
    ext_supported: int,
    ext_total: int,
    contradicted_critical: int,
    risk_level: str,
) -> str:
    """Deterministic confidence rubric — delegates to canonical implementation.

    Wraps ``_compute_confidence_hint`` from ``recommendation.py`` with
    scalar arguments and a ``MEDIUM`` default (instead of ``None``).
    """
    from haytham.agents.tools.recommendation import _compute_confidence_hint

    result = _compute_confidence_hint(
        {
            "external_supported": ext_supported,
            "external_total": ext_total,
            "contradicted_critical": contradicted_critical,
            "risk_level": risk_level,
        }
    )
    return result or "MEDIUM"


def _count_contradicted_critical(risk_assessment: str) -> int:
    """Count contradicted critical-severity claims in risk assessment output.

    Parses the markdown table format:
    | ID | Claim | Type | Origin | Severity | Validation | Reasoning |
    """
    return len(_CONTRADICTED_CRITICAL_RE.findall(risk_assessment))


def extract_recommendation_processor(output: str, state: State) -> dict[str, Any]:
    """Post-processor to extract recommendation from validation summary JSON.

    The validation-summary stage has output_model=ValidationSummaryOutput,
    so the output stored in state is JSON. This processor extracts the
    recommendation directly from JSON, avoiding the regex-from-markdown
    round-trip in entry_conditions.py.

    Also extracts composite_score from the Stage-Gate scorecard if present,
    and computes authoritative confidence from evidence quality metrics.

    Returns:
        Dict with ``recommendation`` key (e.g. ``{"recommendation": "GO"}``),
        and optionally ``composite_score`` and ``computed_confidence``.
    """
    result: dict[str, Any] = {}

    # Primary path: parse JSON (output_model stages store JSON in state)
    try:
        data = json.loads(output)
        rec = data.get("recommendation", "").upper().strip()
        if rec in ("GO", "NO-GO", "PIVOT"):
            logger.info(f"Recommendation from structured output: {rec}")
            result["recommendation"] = rec

        # Extract composite_score from Stage-Gate scorecard
        assessment = data.get("go_no_go_assessment", {})
        if isinstance(assessment, dict) and "composite_score" in assessment:
            result["composite_score"] = assessment["composite_score"]

        if "recommendation" in result:
            # Persist recommendation.json for fast retrieval by views
            session_manager = state.get("session_manager")
            if session_manager and hasattr(session_manager, "session_dir"):
                try:
                    meta_path = session_manager.session_dir / "recommendation.json"
                    meta_path.write_text(json.dumps({"recommendation": rec}))
                except OSError:
                    pass  # Non-critical

            # Compute authoritative confidence from evidence quality
            risk_assessment = state.get("risk_assessment", "")
            risk_level = state.get("risk_level", "MEDIUM")

            if risk_assessment:
                ext_match = _CONFIDENCE_EXTERNAL_RATIO_RE.search(risk_assessment)
                ext_supported = int(ext_match.group(1)) if ext_match else 0
                ext_total = int(ext_match.group(2)) if ext_match else 0
                contradicted_critical = _count_contradicted_critical(risk_assessment)

                computed = _apply_confidence_rubric(
                    ext_supported,
                    ext_total,
                    contradicted_critical,
                    risk_level,
                )
                result["computed_confidence"] = computed

                agent_confidence = data.get("confidence", "").upper().strip()
                if agent_confidence and agent_confidence != computed:
                    logger.warning(
                        f"Confidence override: agent={agent_confidence} → computed={computed}"
                    )

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

    logger.warning("Could not extract recommendation from validation summary output")
    return {}


def save_final_output(session_manager: Any, output: str) -> None:
    """Additional save operation for validation summary.

    Saves the rendered markdown as the latest requirements document.
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


def _extract_jtbd_matches(competitor_analysis_output: str) -> list[str]:
    """Extract all JTBD Match tags from competitor analysis output."""
    return [m.group(1).strip() for m in _JTBD_MATCH_RE.finditer(competitor_analysis_output)]


def _extract_switching_cost(competitor_analysis_output: str) -> str:
    """Extract Switching Cost tag from competitor analysis Section 4.

    Returns the tag value (e.g. "High", "Low") or empty string if not found.
    """
    match = _SWITCHING_COST_RE.search(competitor_analysis_output)
    return match.group(1).strip() if match else ""


def _extract_revenue_evidence_tag(competitor_analysis_output: str) -> str:
    """Extract Revenue Evidence Tag from competitor analysis output.

    Returns the tag value (e.g. "Priced", "No-Pricing-Found") or empty string
    if not found.
    """
    match = _REVENUE_EVIDENCE_RE.search(competitor_analysis_output)
    return match.group(1).strip() if match else ""


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
    from haytham.workflow.burr_actions import run_agent, save_stage_output
    from haytham.workflow.stages.concept_anchor import get_anchor_context_string

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
        rev_tag = _extract_revenue_evidence_tag(ca_output)
        if rev_tag:
            logger.info(f"Revenue Evidence Tag: {rev_tag}")
        else:
            logger.warning("No Revenue Evidence Tag found in competitor analysis output")

        jtbd_matches = _extract_jtbd_matches(ca_output)
        if jtbd_matches:
            logger.info(f"JTBD Matches: {jtbd_matches}")

        switching_cost = _extract_switching_cost(ca_output)
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
                completed=datetime.utcnow().isoformat() + "Z",
                execution_mode="sequential",
            )
        except Exception as e:
            logger.error(f"Failed to save final market-context checkpoint: {e}")

    logger.info(
        f"Market context sequential completed: mi={mi_status}, ca={ca_status}, "
        f"jtbd={'yes' if jtbd_section else 'no'}, combined={len(combined.strip())} chars"
    )
    return combined.strip(), status


# =============================================================================
# Validation Summary — Scorer + Narrator sequential execution
# =============================================================================


def run_validation_summary_sequential(state: State) -> tuple[str, str]:
    """Run validation-summary as sequential: scorer → narrator → merge.

    The scorer handles all analytical work (knockouts, scores, counter-signals,
    recommendation tool call). The narrator generates prose (executive summary,
    lean canvas, findings, next steps). A deterministic merge function combines
    both into the unchanged ValidationSummaryOutput schema.

    Returns:
        Tuple of (merged_json, status) for stage_executor compatibility.
    """
    from haytham.agents.worker_validation_summary.validation_summary_models import (
        ValidationSummaryOutput,
        merge_scorer_narrator,
    )
    from haytham.workflow.burr_actions import run_agent, save_stage_output
    from haytham.workflow.stages.concept_anchor import get_anchor_context_string

    system_goal = state.get("system_goal", "")
    idea_analysis = state.get("idea_analysis", "")
    market_context = state.get("market_context", "")
    risk_assessment = state.get("risk_assessment", "")
    pivot_strategy = state.get("pivot_strategy", "")
    session_manager = state.get("session_manager")

    # Build shared context
    context: dict[str, Any] = {"system_goal": system_goal}
    if idea_analysis:
        context["idea_analysis"] = idea_analysis
    if market_context:
        context["market_context"] = market_context
    if risk_assessment:
        context["risk_assessment"] = risk_assessment
    if pivot_strategy:
        context["pivot_strategy"] = pivot_strategy

    anchor_str = get_anchor_context_string(state)
    if anchor_str:
        context["concept_anchor"] = anchor_str

    # --- 1. Run validation_scorer ---
    from haytham.agents.tools.recommendation import clear_scorecard

    # Build scorer query with FULL upstream context inline.
    # The scorer's job is cross-referencing specific evidence (market sizes,
    # competitor traction, claim validation results). The generic
    # _build_context_summary() truncates each stage to ~200 chars, which
    # strips all the data the scorer needs to cite. Pass full text instead.
    from haytham.workflow.anchor_schema import FounderPersona

    founder_persona = FounderPersona()
    scorer_sections = [
        "Evaluate all upstream findings using the Stage-Gate scorecard. "
        "Record knockouts, dimension scores, counter-signals, risk/evidence, "
        "then call compute_verdict.",
        "\n## Context from Previous Stages:",
        f"\n**ORIGINAL IDEA (Source of Truth - read carefully for explicit constraints):**\n{system_goal}",
    ]
    if anchor_str:
        scorer_sections.append(f"\n**Concept Anchor (source: concept_anchor):**\n{anchor_str}")
    scorer_sections.append(f"\n{founder_persona.to_context()}")
    if idea_analysis:
        scorer_sections.append(f"\n**Idea Analysis (source: idea_analysis):**\n{idea_analysis}")
    if market_context:
        scorer_sections.append(f"\n**Market Context (source: market_context):**\n{market_context}")
    if risk_assessment:
        scorer_sections.append(
            f"\n**Risk Assessment (source: risk_assessment):**\n{risk_assessment}"
        )
    if pivot_strategy:
        scorer_sections.append(f"\n**Pivot Strategy (source: pivot_strategy):**\n{pivot_strategy}")

    scorer_query = "\n".join(scorer_sections)

    clear_scorecard()
    try:
        # Pass empty context — full text is already in scorer_query
        scorer_result = run_agent(
            "validation_scorer",
            scorer_query,
            {},
            session_manager,
            output_as_json=True,
        )
    finally:
        clear_scorecard()
    scorer_output = scorer_result.get("output", "")
    scorer_status = scorer_result.get("status", "failed")

    # Save scorer output for observability
    if session_manager and scorer_output:
        save_stage_output(
            session_manager,
            "validation-summary",
            "validation_scorer",
            scorer_output,
            status="in_progress",
        )

    if scorer_status != "completed":
        logger.error(f"Validation scorer failed: {scorer_result.get('error', 'unknown')}")
        return scorer_output or "Error: Scorer agent failed", "failed"

    # Parse scorer JSON
    try:
        scorer_data = json.loads(scorer_output)
    except json.JSONDecodeError:
        logger.error("Validation scorer output is not valid JSON")
        return scorer_output, "failed"

    # Validate critical scorer fields
    missing = [f for f in ("composite_score", "verdict", "recommendation") if f not in scorer_data]
    if missing:
        logger.error(f"Scorer output missing critical fields: {missing}")
        return scorer_output, "failed"

    # --- 2. Run validation_narrator with scorer output as context ---
    narrator_context = dict(context)
    narrator_context["scorer_output"] = scorer_output

    narrator_query = (
        "Generate the human-readable validation summary from the scorer's "
        "analytical output. Include executive summary, lean canvas, "
        "validation findings, and next steps."
    )
    narrator_result = run_agent(
        "validation_narrator",
        narrator_query,
        narrator_context,
        session_manager,
        output_as_json=True,
    )
    narrator_output = narrator_result.get("output", "")
    narrator_status = narrator_result.get("status", "failed")

    # Save narrator output for observability
    if session_manager and narrator_output:
        save_stage_output(
            session_manager,
            "validation-summary",
            "validation_narrator",
            narrator_output,
            status="in_progress",
        )

    if narrator_status != "completed":
        logger.warning(f"Validation narrator failed: {narrator_result.get('error', 'unknown')}")
        return scorer_output, "partial"

    # Parse narrator JSON
    try:
        narrator_data = json.loads(narrator_output)
    except json.JSONDecodeError:
        logger.error("Validation narrator output is not valid JSON")
        return scorer_output, "partial"

    # --- 3. Merge scorer + narrator into ValidationSummaryOutput ---
    try:
        merged = merge_scorer_narrator(scorer_data, narrator_data)
        # Validate the merged dict parses as ValidationSummaryOutput
        ValidationSummaryOutput.model_validate(merged)
        merged_json = json.dumps(merged)
    except Exception as e:
        logger.error(f"Failed to merge scorer+narrator outputs: {e}")
        return scorer_output, "partial"

    logger.info(
        f"Validation summary sequential completed: "
        f"scorer={scorer_status}, narrator={narrator_status}, "
        f"merged={len(merged_json)} chars"
    )
    return merged_json, "completed"
