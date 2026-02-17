"""Centralized Stage Registry for Workflow Management.

This module provides a single source of truth for all stage metadata,
eliminating scattered mappings and hardcoded dictionaries throughout the codebase.

Design Principles:
- Single Responsibility: Only manages stage metadata and lookups
- Open/Closed: New stages can be added via configuration, not code changes
- DRY: Centralizes all stage-related mappings in one place

Workflow Types (ADR-016: Four-Phase Architecture):
- IDEA_VALIDATION: Phase 1 (WHY) - Stages 1-4 (+ optional pivot) - Business validation
- MVP_SPECIFICATION: Phase 2 (WHAT) - Stages 5-6 - Define what to build first
- BUILD_BUY_ANALYSIS: Phase 3a (HOW) - Stage 7 - Build vs Buy decisions
- ARCHITECTURE_DECISIONS: Phase 3b (HOW) - Stage 8 - Architecture decisions
- STORY_GENERATION: Phase 4 (STORIES) - Stages 9-11 - Implementation tasks
"""

from dataclasses import dataclass, field
from enum import Enum


class WorkflowType(Enum):
    """Workflow types for grouping stages.

    The system is split into focused workflows with decision gates (ADR-016):
    - IDEA_VALIDATION: Phase 1 (WHY) - Quick validation of business viability
    - MVP_SPECIFICATION: Phase 2 (WHAT) - Define what to build first
    - BUILD_BUY_ANALYSIS: Phase 3a (HOW) - Build vs Buy decisions
    - ARCHITECTURE_DECISIONS: Phase 3b (HOW) - Architecture decisions
    - STORY_GENERATION: Phase 4 (STORIES) - Generate implementation tasks
    """

    IDEA_VALIDATION = "idea-validation"
    MVP_SPECIFICATION = "mvp-specification"
    BUILD_BUY_ANALYSIS = "build-buy-analysis"
    ARCHITECTURE_DECISIONS = "architecture-decisions"
    STORY_GENERATION = "story-generation"

    @classmethod
    def values(cls) -> list[str]:
        """Return all valid workflow type values as strings."""
        return [wf.value for wf in cls]


@dataclass(frozen=True)
class StageMetadata:
    """Immutable metadata for a workflow stage.

    This is the single source of truth for all stage configuration.
    Consolidates information previously scattered across stage_config.py
    and multiple dictionaries throughout the codebase.
    """

    # Identifiers
    slug: str  # e.g., "idea-analysis" (kebab-case, used in URLs/files)
    action_name: str  # e.g., "idea_analysis" (Burr action name)

    # Display information
    display_name: str  # e.g., "Idea Analysis"
    display_index: int | str  # e.g., 1 or "3b" for optional stages
    description: str  # User-facing explanation of what this stage does

    # State keys (for Burr state management)
    state_key: str  # e.g., "idea_analysis" (where output is stored)
    status_key: str  # e.g., "idea_analysis_status"

    # Workflow membership
    workflow_type: WorkflowType  # Which workflow/phase this stage belongs to

    # Query template for LLM prompt
    query_template: str  # Template with {system_goal} placeholder

    # Agent information
    agent_names: list[str] = field(default_factory=list)  # Agents to run

    # Execution configuration
    is_optional: bool = False  # e.g., pivot-strategy is optional
    execution_mode: str = "single"  # single, parallel

    # Context requirements
    required_context: list[str] = field(default_factory=list)  # Slugs of required prior stages


# =============================================================================
# Stage Definitions - Single Source of Truth
# =============================================================================

_STAGES: list[StageMetadata] = [
    # =========================================================================
    # WORKFLOW 1: IDEA VALIDATION (Stages 1-4 + optional pivot)
    # =========================================================================
    StageMetadata(
        slug="idea-analysis",
        action_name="idea_analysis",
        display_name="Idea Analysis",
        display_index=1,
        description=(
            "We transform your raw idea into a structured startup concept. "
            "This includes identifying the top 3 specific problems it solves, "
            "defining target user segments with budget indicators, crafting a unique value proposition, "
            "and creating an initial Lean Canvas. This foundation feeds into market research next."
        ),
        state_key="idea_analysis",
        status_key="idea_analysis_status",
        workflow_type=WorkflowType.IDEA_VALIDATION,
        query_template=(
            "Analyze this startup idea in depth. Identify the core problems it solves, "
            "target users, and unique value proposition: {system_goal}"
        ),
        agent_names=["concept_expansion"],
        required_context=[],
    ),
    StageMetadata(
        slug="market-context",
        action_name="market_context",
        display_name="Market Context",
        display_index=2,
        description=(
            "Building on your structured concept, we run two agents sequentially. "
            "Market Intelligence researches live market data, applies Jobs-to-be-Done analysis, "
            "and identifies trends. Its JTBD output is then passed to Competitor Analysis, which "
            "uses job-anchored search to find 5-7 real competitors solving the same customer job — "
            "regardless of category. Together they ground your concept in market reality."
        ),
        state_key="market_context",
        status_key="market_context_status",
        workflow_type=WorkflowType.IDEA_VALIDATION,
        query_template=(
            "Conduct comprehensive market research. Analyze market size, trends, and competitive "
            "landscape. Use http_request to fetch live market data."
        ),
        agent_names=["market_intelligence", "competitor_analysis"],
        execution_mode="sequential",
        required_context=["idea-analysis"],
    ),
    StageMetadata(
        slug="risk-assessment",
        action_name="risk_assessment",
        display_name="Risk Assessment",
        display_index=3,
        description=(
            "Using all findings from Idea Analysis and Market Context, we extract 10-15 key claims "
            "and validate each against research evidence. Claims are classified as supported, partial, "
            "unsupported, or contradicted. Risks are prioritized (high/medium/low) with mitigation strategies. "
            "This determines whether to proceed, pivot, or reconsider."
        ),
        state_key="risk_assessment",
        status_key="risk_assessment_status",
        workflow_type=WorkflowType.IDEA_VALIDATION,
        query_template=(
            "Identify and assess risks for this startup concept. "
            "Validate key assumptions and flag potential issues."
        ),
        agent_names=["startup_validator"],
        required_context=["idea-analysis", "market-context"],
    ),
    StageMetadata(
        slug="pivot-strategy",
        action_name="pivot_strategy",
        display_name="Pivot Strategy",
        display_index="3b",
        description=(
            "Only triggered when Risk Assessment identifies high-risk scenarios. "
            "We analyze what's causing the risk and propose alternative approaches, "
            "market pivots, or scope adjustments that could reduce risk while preserving core value."
        ),
        state_key="pivot_strategy",
        status_key="pivot_strategy_status",
        workflow_type=WorkflowType.IDEA_VALIDATION,
        query_template=(
            "Given the high risk assessment, suggest strategic pivot options that could "
            "reduce risk while preserving the core value proposition."
        ),
        agent_names=["pivot_strategy"],
        is_optional=True,
        required_context=["idea-analysis", "market-context", "risk-assessment"],
    ),
    StageMetadata(
        slug="validation-summary",
        action_name="validation_summary",
        display_name="Validation Summary",
        display_index=4,
        description=(
            "We synthesize all prior findings into a decision-ready report. "
            "Includes an executive summary with Go/No-Go verdict, condensed Lean Canvas, "
            "key validation findings, and concrete next steps. "
            "This becomes the foundation for MVP scoping."
        ),
        state_key="validation_summary",
        status_key="validation_summary_status",
        workflow_type=WorkflowType.IDEA_VALIDATION,
        query_template=(
            "Synthesize all findings into a concise validation report. "
            "Include a clear recommendation on whether to proceed with system definition."
        ),
        agent_names=["validation_scorer", "validation_narrator"],
        required_context=["idea-analysis", "market-context", "risk-assessment"],
    ),
    # =========================================================================
    # WORKFLOW 2: MVP SPECIFICATION (Stages 5-6)
    # =========================================================================
    StageMetadata(
        slug="mvp-scope",
        action_name="mvp_scope",
        display_name="MVP Scope",
        display_index=5,
        description=(
            "Taking the validated concept, we define a focused, achievable MVP. "
            "This means identifying 'The One Thing' (core value proposition), "
            "choosing the primary user segment, setting clear in/out-of-scope boundaries, "
            "defining success criteria, and mapping 2-3 core user flows. "
            "This scope constrains the capability model."
        ),
        state_key="mvp_scope",
        status_key="mvp_scope_status",
        workflow_type=WorkflowType.MVP_SPECIFICATION,
        query_template=(
            "Define a focused MVP scope based on the validation summary. Identify: The One Thing "
            "(core value proposition), primary user segment, MVP boundaries (in scope vs out of scope), "
            "success criteria, appetite, and core user flows (max 3). Be ruthless about prioritization."
        ),
        agent_names=["mvp_scope"],
        required_context=[
            "idea-analysis",
            "market-context",
            "risk-assessment",
            "validation-summary",
        ],
    ),
    StageMetadata(
        slug="capability-model",
        action_name="capability_model",
        display_name="Capability Model",
        display_index=6,
        description=(
            "We transform the MVP scope into a structured capability model. "
            "This defines 3-5 functional capabilities (what users can do) and 2-4 non-functional "
            "capabilities (performance, security, usability). Each capability traces back to your "
            "MVP scope and user flows. This becomes the implementation blueprint for development."
        ),
        state_key="capability_model",
        status_key="capability_model_status",
        workflow_type=WorkflowType.MVP_SPECIFICATION,
        query_template=(
            "Transform the MVP scope into a structured capability model. Define functional capabilities "
            "(what users can do) and non-functional capabilities (quality attributes) that serve ONLY "
            "the defined MVP scope. Limit to 3-5 functional and 2-4 non-functional capabilities."
        ),
        agent_names=["capability_model"],
        required_context=[
            "idea-analysis",
            "market-context",
            "risk-assessment",
            "validation-summary",
            "mvp-scope",
        ],
    ),
    StageMetadata(
        slug="system-traits",
        action_name="system_traits",
        display_name="System Traits",
        display_index="6b",
        description=(
            "We classify the type of system being built based on the capability model and MVP scope. "
            "Five traits (interface, auth, deployment, data layer, realtime) are detected to control "
            "which story layers are generated downstream, eliminating irrelevant noise for non-web ideas."
        ),
        state_key="system_traits",
        status_key="system_traits_status",
        workflow_type=WorkflowType.MVP_SPECIFICATION,
        query_template=(
            "Classify the system traits for this startup idea based on the capability model "
            "and MVP scope. Determine: interface type, auth model, deployment targets, "
            "data layer, and realtime requirements."
        ),
        agent_names=["system_traits"],
        required_context=["idea-analysis", "mvp-scope", "capability-model"],
    ),
    # =========================================================================
    # WORKFLOW 3: TECHNICAL DESIGN (Stages 7-8) - Phase 3: HOW
    # =========================================================================
    StageMetadata(
        slug="build-buy-analysis",
        action_name="build_buy_analysis",
        display_name="Build vs Buy Analysis",
        display_index=7,
        description=(
            "Analyze each capability to determine whether to BUILD custom code, "
            "BUY existing services, or use a HYBRID approach. This informs "
            "architecture decisions and story generation approach."
        ),
        state_key="build_buy_analysis",
        status_key="build_buy_analysis_status",
        workflow_type=WorkflowType.BUILD_BUY_ANALYSIS,
        query_template=(
            "Analyze each capability to determine if it should be built from scratch, "
            "bought (using existing services/libraries), or a hybrid approach."
        ),
        agent_names=["build_buy_analyzer"],
        required_context=["mvp-scope", "capability-model"],
    ),
    StageMetadata(
        slug="architecture-decisions",
        action_name="architecture_decisions",
        display_name="Architecture Decisions",
        display_index=8,
        description=(
            "Make key technical decisions (DEC-*) based on Build vs Buy analysis. "
            "Define component structure, technology choices, and integration patterns. "
            "These decisions guide story generation for both BUILD and BUY capabilities."
        ),
        state_key="architecture_decisions",
        status_key="architecture_decisions_status",
        workflow_type=WorkflowType.ARCHITECTURE_DECISIONS,
        query_template=(
            "Based on the build vs buy analysis, make key architecture decisions including "
            "technology stack, integration patterns, and deployment approach."
        ),
        agent_names=["architecture_decisions"],
        required_context=["mvp-scope", "capability-model", "build-buy-analysis"],
    ),
    # =========================================================================
    # WORKFLOW 4: STORY GENERATION (Stages 9-11) - Phase 4: STORIES
    # =========================================================================
    StageMetadata(
        slug="story-generation",
        action_name="story_generation",
        display_name="Story Generation",
        display_index=9,
        description=(
            "Generate user stories for each capability based on Build vs Buy decisions. "
            "BUILD capabilities get implementation stories, BUY capabilities get integration stories. "
            "Each story references its capability with implements:CAP-* labels."
        ),
        state_key="story_generation",
        status_key="story_generation_status",
        workflow_type=WorkflowType.STORY_GENERATION,
        query_template=(
            "Generate user stories for each capability based on Build vs Buy decisions. "
            "BUILD capabilities get implementation stories, BUY capabilities get integration stories."
        ),
        agent_names=["story_generation"],
        required_context=["capability-model", "build-buy-analysis", "architecture-decisions"],
    ),
    StageMetadata(
        slug="story-validation",
        action_name="story_validation",
        display_name="Story Validation",
        display_index=10,
        description=(
            "Validate generated stories against capability requirements. "
            "Ensure each capability is covered by at least one story, "
            "and that stories meet INVEST criteria."
        ),
        state_key="story_validation",
        status_key="story_validation_status",
        workflow_type=WorkflowType.STORY_GENERATION,
        query_template=(
            "Validate generated stories against capability requirements. "
            "Ensure each capability is covered by at least one story."
        ),
        agent_names=["story_validation"],
        required_context=["capability-model", "story-generation"],
    ),
    StageMetadata(
        slug="dependency-ordering",
        action_name="dependency_ordering",
        display_name="Dependency Ordering",
        display_index=11,
        description=(
            "Order stories by dependencies to create an implementation roadmap. "
            "Infrastructure stories first, then core features, then enhancements. "
            "Output is ready for implementation by a coding agent."
        ),
        state_key="dependency_ordering",
        status_key="dependency_ordering_status",
        workflow_type=WorkflowType.STORY_GENERATION,
        query_template=(
            "Order stories by dependencies to create an implementation roadmap. "
            "Infrastructure first, then core features, then enhancements."
        ),
        agent_names=["dependency_ordering"],
        required_context=["story-generation", "story-validation"],
    ),
]


class StageRegistry:
    """Registry for stage metadata with efficient lookups.

    Provides a clean API to access stage information without
    scattering hardcoded mappings throughout the codebase.

    Usage:
        registry = StageRegistry()

        # Get stage by slug
        stage = registry.get_by_slug("idea-analysis")

        # Get stage by action name
        stage = registry.get_by_action("idea_analysis")

        # Get all stages in order
        for stage in registry.all_stages():
            print(stage.display_name)

        # Get ordered list of slugs (excluding optional)
        slugs = registry.get_stage_order(include_optional=False)
    """

    def __init__(self, stages: list[StageMetadata] | None = None):
        """Initialize the registry.

        Args:
            stages: Optional custom stage list. Uses default if not provided.
        """
        self._stages = stages or _STAGES

        # Build lookup indices for O(1) access
        self._by_slug: dict[str, StageMetadata] = {s.slug: s for s in self._stages}
        self._by_action: dict[str, StageMetadata] = {s.action_name: s for s in self._stages}

    # =========================================================================
    # Lookup Methods
    # =========================================================================

    def get_by_slug(self, slug: str) -> StageMetadata:
        """Get stage metadata by slug.

        Args:
            slug: Stage slug (e.g., "idea-analysis")

        Returns:
            StageMetadata for the stage

        Raises:
            ValueError: If slug not found
        """
        if slug not in self._by_slug:
            raise ValueError(
                f"Unknown stage slug: {slug}. Valid slugs: {list(self._by_slug.keys())}"
            )
        return self._by_slug[slug]

    def get_by_action(self, action_name: str) -> StageMetadata:
        """Get stage metadata by Burr action name.

        Args:
            action_name: Action name (e.g., "idea_analysis")

        Returns:
            StageMetadata for the stage

        Raises:
            ValueError: If action name not found
        """
        if action_name not in self._by_action:
            raise ValueError(
                f"Unknown action: {action_name}. Valid actions: {list(self._by_action.keys())}"
            )
        return self._by_action[action_name]

    def get_by_slug_safe(self, slug: str) -> StageMetadata | None:
        """Get stage metadata by slug, returning None if not found."""
        return self._by_slug.get(slug)

    def get_by_action_safe(self, action_name: str) -> StageMetadata | None:
        """Get stage metadata by action name, returning None if not found."""
        return self._by_action.get(action_name)

    # =========================================================================
    # Collection Methods
    # =========================================================================

    def all_stages(self, include_optional: bool = True) -> list[StageMetadata]:
        """Get all stages in workflow order.

        Args:
            include_optional: Whether to include optional stages (e.g., pivot-strategy)

        Returns:
            List of StageMetadata in execution order
        """
        if include_optional:
            return list(self._stages)
        return [s for s in self._stages if not s.is_optional]

    def get_stage_order(self, include_optional: bool = True) -> list[str]:
        """Get ordered list of stage slugs.

        Args:
            include_optional: Whether to include optional stages

        Returns:
            List of stage slugs in execution order
        """
        return [s.slug for s in self.all_stages(include_optional)]

    # =========================================================================
    # Validation Helpers
    # =========================================================================

    # =========================================================================
    # Workflow-Based Methods
    # =========================================================================

    def get_stages_for_workflow(
        self, workflow_type: WorkflowType, include_optional: bool = True
    ) -> list[StageMetadata]:
        """Get all stages belonging to a specific workflow.

        Args:
            workflow_type: The workflow type to filter by
            include_optional: Whether to include optional stages

        Returns:
            List of StageMetadata for the specified workflow
        """
        stages = [s for s in self._stages if s.workflow_type == workflow_type]
        if not include_optional:
            stages = [s for s in stages if not s.is_optional]
        return stages

    def get_workflow_stage_slugs(
        self, workflow_type: WorkflowType, include_optional: bool = True
    ) -> list[str]:
        """Get ordered list of stage slugs for a specific workflow.

        Args:
            workflow_type: The workflow type to filter by
            include_optional: Whether to include optional stages

        Returns:
            List of stage slugs in execution order for the workflow
        """
        return [s.slug for s in self.get_stages_for_workflow(workflow_type, include_optional)]

    def get_workflow_for_stage(self, slug: str) -> WorkflowType:
        """Get the workflow type for a given stage slug.

        Args:
            slug: Stage slug (e.g., "idea-analysis")

        Returns:
            WorkflowType that the stage belongs to

        Raises:
            ValueError: If slug not found
        """
        stage = self.get_by_slug(slug)
        return stage.workflow_type

    def get_first_stage_of_workflow(self, workflow_type: WorkflowType) -> StageMetadata | None:
        """Get the first stage of a workflow.

        Args:
            workflow_type: The workflow type

        Returns:
            First StageMetadata or None if workflow has no stages
        """
        stages = self.get_stages_for_workflow(workflow_type, include_optional=False)
        return stages[0] if stages else None

    def get_last_stage_of_workflow(self, workflow_type: WorkflowType) -> StageMetadata | None:
        """Get the last non-optional stage of a workflow.

        Args:
            workflow_type: The workflow type

        Returns:
            Last non-optional StageMetadata or None if workflow has no stages
        """
        stages = self.get_stages_for_workflow(workflow_type, include_optional=False)
        return stages[-1] if stages else None

    def is_last_stage_of_workflow(self, slug: str) -> bool:
        """Check if a stage is the last stage of its workflow.

        Args:
            slug: Stage slug to check

        Returns:
            True if this is the last non-optional stage of its workflow
        """
        stage = self.get_by_slug_safe(slug)
        if not stage:
            return False
        last_stage = self.get_last_stage_of_workflow(stage.workflow_type)
        return last_stage is not None and last_stage.slug == slug

    def __len__(self) -> int:
        """Return number of stages."""
        return len(self._stages)

    def __iter__(self):
        """Iterate over stages."""
        return iter(self._stages)

    # =========================================================================
    # Query Formatting
    # =========================================================================

    def format_query(self, slug: str, **kwargs) -> str:
        """Format query template with provided arguments.

        Args:
            slug: Stage slug (e.g., "idea-analysis")
            **kwargs: Template variables (e.g., system_goal="...")

        Returns:
            Formatted query string

        Raises:
            ValueError: If slug not found
            KeyError: If required template variables missing
        """
        stage = self.get_by_slug(slug)
        try:
            return stage.query_template.format(**kwargs)
        except KeyError as e:
            raise KeyError(
                f"Missing required template variable for stage '{slug}': {e}. "
                f"Template: {stage.query_template}"
            ) from e


# =============================================================================
# Module-level singleton for convenience
# =============================================================================

_registry: StageRegistry | None = None


def get_stage_registry() -> StageRegistry:
    """Get the global stage registry singleton.

    Returns:
        The shared StageRegistry instance
    """
    global _registry
    if _registry is None:
        _registry = StageRegistry()
    return _registry


# =============================================================================
# Convenience functions (for backwards compatibility during migration)
# =============================================================================


def get_stage_by_slug(slug: str) -> StageMetadata:
    """Get stage metadata by slug."""
    return get_stage_registry().get_by_slug(slug)


def get_stage_by_action(action_name: str) -> StageMetadata:
    """Get stage metadata by action name."""
    return get_stage_registry().get_by_action(action_name)


def get_all_stage_slugs(include_optional: bool = True) -> list[str]:
    """Get ordered list of all stage slugs."""
    return get_stage_registry().get_stage_order(include_optional)


def get_stage_index(slug: str) -> int:
    """Get the 0-based index of a stage in the global stage order.

    Args:
        slug: The stage slug to look up

    Returns:
        The index of the stage

    Raises:
        ValueError: If the slug is not found
    """
    for i, stage in enumerate(get_stage_registry().all_stages(include_optional=True)):
        if stage.slug == slug:
            return i
    raise ValueError(f"Unknown stage: {slug}")


def format_query(slug: str, **kwargs) -> str:
    """Format query template with provided arguments."""
    return get_stage_registry().format_query(slug, **kwargs)


# Computed once at import time for backward compatibility.
# Callers that iterate all stages can use this instead of
# get_stage_registry().all_stages() for brevity.
STAGES: list[StageMetadata] = get_stage_registry().all_stages(include_optional=True)
