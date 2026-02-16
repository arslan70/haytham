"""Burr Actions for Haytham Validation Workflow.

Each action represents a stage in the validation workflow.
Actions integrate with the existing agent factory and session manager.

The @action decorator specifies:
- reads: State keys this action needs to read
- writes: State keys this action will write to
"""

import logging

from burr.core import State, action

logger = logging.getLogger(__name__)


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
