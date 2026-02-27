"""Assembled stage execution configurations.

This module is the single place where ``StageExecutionConfig`` instances are
wired together from the domain-specific modules.  It is imported by
:mod:`haytham.workflow.stage_executor` at the module level.
"""

from typing import TYPE_CHECKING

from haytham.agents.worker_build_buy_advisor.build_buy_models import (
    BuildBuyAnalysisOutput as _BuildBuyAnalysisOutput,
)
from haytham.agents.worker_report_synthesis.report_synthesis_models import (
    ValidationReport as _ValidationReport,
)
from haytham.agents.worker_story_generator.story_generation_models import (
    StoryGenerationHybridOutput as _StoryGenerationHybridOutput,
)
from haytham.agents.worker_system_traits.system_traits_models import (
    SystemTraitsOutput as _SystemTraitsOutput,
)
from haytham.workflow.stage_executor import StageExecutionConfig
from haytham.workflow.validators.report_guardrails import (
    validate_no_judgment_language,
    validate_regulated_domain_safety,
    validate_som_arithmetic,
)
from haytham.workflow.validators.story_coherence import validate_story_coherence

from .concept_anchor import extract_anchor_post_processor
from .idea_validation import (
    extract_competitor_data_processor,
    extract_recommendation_processor,
    run_market_context_sequential,
    run_report_synthesis,
    run_research_brief,
    save_final_output,
)
from .mvp_scope_swarm import run_mvp_scope_swarm
from .mvp_specification import (
    build_capability_model_context,
    build_system_traits_context,
    create_capability_model_agent,
    create_system_traits_agent,
    extract_system_traits_processor,
    store_capabilities_in_state,
)
from .story_pipeline import (
    create_backlog_drafts_after_ordering,
    run_dependency_ordering,
    run_story_generation,
    run_story_validation,
)
from .technical_design import (
    analyze_capabilities_for_build_buy,
    run_architecture_decisions,
)

if TYPE_CHECKING:
    from burr.core import State


# =============================================================================
# ADR-022: Post-validators for story coherence
# =============================================================================


def story_coherence_validator(output: str, state: "State") -> list[str]:
    """Validate story generation output for framework conflicts.

    ADR-022 Part 4: Detects multiple frontend/backend frameworks that would
    indicate inconsistent architecture decisions.
    """
    report = validate_story_coherence(output)

    warnings = []
    for error in report.errors:
        warnings.append(error)
    for warning in report.warnings:
        warnings.append(warning)

    return warnings


STAGE_CONFIGS: dict[str, StageExecutionConfig] = {
    "idea-analysis": StageExecutionConfig(
        stage_slug="idea-analysis",
        # query_template inherited from StageMetadata in registry
        # ADR-022: Extract concept anchor after idea analysis to prevent concept drift
        # The post_processor extracts the anchor and saves it to disk in one step
        post_processor=extract_anchor_post_processor,
    ),
    "market-context": StageExecutionConfig(
        stage_slug="market-context",
        programmatic_executor=run_market_context_sequential,
        post_processor=extract_competitor_data_processor,
    ),
    "research-brief": StageExecutionConfig(
        stage_slug="research-brief",
        programmatic_executor=run_research_brief,
        post_validators=[validate_no_judgment_language],
    ),
    "report-synthesis": StageExecutionConfig(
        stage_slug="report-synthesis",
        programmatic_executor=run_report_synthesis,
        post_processor=extract_recommendation_processor,
        additional_save=save_final_output,
        post_validators=[validate_som_arithmetic, validate_regulated_domain_safety],
        output_model=_ValidationReport,
    ),
    "mvp-scope": StageExecutionConfig(
        stage_slug="mvp-scope",
        programmatic_executor=run_mvp_scope_swarm,
    ),
    "capability-model": StageExecutionConfig(
        stage_slug="capability-model",
        query_template=(
            "Transform the MVP scope into a structured capability model. "
            "Define functional capabilities (what users can do) and non-functional capabilities "
            "(quality attributes) that serve ONLY the defined MVP scope. "
            "Limit to 3-5 functional and 2-4 non-functional capabilities. "
            "Output as JSON per the format specified in your instructions."
        ),
        custom_agent_factory=create_capability_model_agent,
        custom_context_builder=build_capability_model_context,
        additional_save=store_capabilities_in_state,
        # ADR-022: Enable context retrieval tools for deep context access
        use_context_tools=True,
    ),
    "system-traits": StageExecutionConfig(
        stage_slug="system-traits",
        # query_template inherited from StageMetadata in registry
        custom_agent_factory=create_system_traits_agent,
        custom_context_builder=build_system_traits_context,
        post_processor=extract_system_traits_processor,
        output_model=_SystemTraitsOutput,
        # ADR-022: Enable context retrieval tools for deep context access
        use_context_tools=True,
    ),
    "build-buy-analysis": StageExecutionConfig(
        stage_slug="build-buy-analysis",
        programmatic_executor=analyze_capabilities_for_build_buy,
        output_model=_BuildBuyAnalysisOutput,
    ),
    "architecture-decisions": StageExecutionConfig(
        stage_slug="architecture-decisions",
        programmatic_executor=run_architecture_decisions,
    ),
    "story-generation": StageExecutionConfig(
        stage_slug="story-generation",
        programmatic_executor=run_story_generation,
        # ADR-022 Part 4: Validate story count against appetite limits
        post_validators=[story_coherence_validator],
        output_model=_StoryGenerationHybridOutput,
    ),
    "story-validation": StageExecutionConfig(
        stage_slug="story-validation",
        programmatic_executor=run_story_validation,
    ),
    "dependency-ordering": StageExecutionConfig(
        stage_slug="dependency-ordering",
        programmatic_executor=run_dependency_ordering,
        additional_save=create_backlog_drafts_after_ordering,
    ),
}
