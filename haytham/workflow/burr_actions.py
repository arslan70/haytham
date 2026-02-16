"""Burr Actions for Haytham Validation Workflow.

Each action represents a stage in the validation workflow.
Actions integrate with the existing agent factory and session manager.

The @action decorator specifies:
- reads: State keys this action needs to read
- writes: State keys this action will write to
"""

import json
import logging
import re
from typing import Any

from burr.core import State, action

logger = logging.getLogger(__name__)

# Compiled regex for TL;DR extraction (ADR-022)
_TLDR_PATTERN = re.compile(r"##\s*TL;?DR\s*\n(.*?)(?=\n##|\Z)", re.IGNORECASE | re.DOTALL)


# =============================================================================
# Context Builder Helpers (will move to context_builder.py in Task 3)
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
