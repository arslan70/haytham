"""Centralized configuration for Haytham.

This module provides a single source of truth for all configuration constants,
eliminating hardcoded values scattered across the codebase.

Design Principles:
- All timeout, token, and retry configurations in one place
- Agent configurations defined declaratively
- Tool profiles for common tool combinations
- Enums for type-safe status values
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

# =============================================================================
# Enums for Type Safety
# =============================================================================


class StageStatus(Enum):
    """Valid status values for workflow stages."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    REQUIRES_RETRY = "requires_retry"

    @classmethod
    def values(cls) -> list[str]:
        """Return all valid status values as strings."""
        return [status.value for status in cls]


class WorkflowPhase(Enum):
    """Valid workflow phases for multi-phase execution."""

    DISCOVERY = "discovery"
    ARCHITECT = "architect"
    IMPLEMENTATION = "implementation"

    @classmethod
    def values(cls) -> list[str]:
        """Return all valid phase values as strings."""
        return [phase.value for phase in cls]


class ModelTier(Enum):
    """Model tier for cost/quality routing."""

    HEAVY = "heavy"  # Capable model for synthesis and structured output
    LIGHT = "light"  # Cheaper model for extraction/summarization
    REASONING = "reasoning"  # Strongest model for cross-referencing and conditional logic


# =============================================================================
# Timeout Configuration
# =============================================================================


@dataclass(frozen=True)
class TimeoutConfig:
    """Timeout configuration for Bedrock model calls."""

    read_timeout: float
    connect_timeout: float
    streaming: bool = True

    def to_dict(self) -> dict[str, Any]:
        """Convert to dict for function kwargs."""
        return {
            "read_timeout": self.read_timeout,
            "connect_timeout": self.connect_timeout,
            "streaming": self.streaming,
        }


# Timeout profiles
TIMEOUT_STANDARD = TimeoutConfig(read_timeout=300.0, connect_timeout=60.0)
TIMEOUT_EXTENDED = TimeoutConfig(read_timeout=600.0, connect_timeout=60.0)
TIMEOUT_FILE_OPS = TimeoutConfig(read_timeout=600.0, connect_timeout=60.0, streaming=False)


# =============================================================================
# Token Limits
# =============================================================================

# Token limit for agents using the think tool (cognitive cycles consume extra tokens)
# 550 words ≈ 825 tokens, adding buffer for thinking overhead
TOKENS_THINKING = 2000

# Token limit for medium-complexity outputs (~500 words target)
TOKENS_MEDIUM = 1000

# Token limit for scorecard-style structured outputs (validation summary).
# ScorerOutput has 3 knockouts + N counter-signals + 6 dimensions + metadata;
# the JSON easily exceeds 2000 tokens, causing Strands structured output failure.
TOKENS_SCORECARD = 4000

# Token limit for large structured outputs (build vs buy analysis, etc.)
TOKENS_LARGE = 4000

# Default token limit (~500 words target)
TOKENS_DEFAULT = 1000


# =============================================================================
# Retry Configuration
# =============================================================================

# Bedrock retry settings
BEDROCK_MAX_RETRIES = 5
BEDROCK_RETRY_MODE = "standard"


# =============================================================================
# Content Extraction Limits
# =============================================================================

# Default number of lines to extract from sections
DEFAULT_SECTION_LINES = 4

# Default max characters when extracting content
DEFAULT_SECTION_CHARS = 150

# Default number of list items to extract
DEFAULT_EXTRACT_ITEMS = 3

# Default max characters per extracted item
DEFAULT_ITEM_CHARS = 50


# =============================================================================
# Session Configuration
# =============================================================================

# Files to skip when reading agent outputs
METADATA_FILES = ["checkpoint.md", "user_feedback.md"]

# Default workflow phase when not specified
DEFAULT_WORKFLOW_PHASE = "discovery"


# =============================================================================
# Tool Profiles
# =============================================================================


class ToolProfile(Enum):
    """Named profiles for common tool combinations."""

    NONE = "none"
    THINKING = "thinking"
    WEB_RESEARCH = "web_research"
    RISK_CLASSIFICATION = "risk_classification"  # For startup_validator
    RECOMMENDATION = "recommendation"  # For validation_summary
    BUILD_BUY = "build_buy"  # For build_buy_advisor (legacy)
    BUILD_BUY_WEB = "build_buy_web"  # For build_buy_analyzer with web search
    COMPETITOR_RESEARCH = "competitor_research"  # For competitor_analysis with recording tools
    STORY_GENERATION = "story_generation"  # For story generator with validation tools
    PDF_REPORT = "pdf_report"  # For PDF report generation


def get_tools_for_profile(profile: ToolProfile) -> list:
    """Get tool instances for a given profile.

    Args:
        profile: The tool profile to use

    Returns:
        List of tool instances

    Note:
        Import happens lazily to avoid circular imports and
        to only import tools when actually needed.
    """
    if profile == ToolProfile.NONE:
        return []

    if profile == ToolProfile.THINKING:
        from strands_tools import think

        return [think]

    if profile == ToolProfile.WEB_RESEARCH:
        from strands_tools import current_time, file_read, file_write, http_request

        from haytham.agents.utils.web_search import web_search

        return [file_read, file_write, http_request, current_time, web_search]

    if profile == ToolProfile.COMPETITOR_RESEARCH:
        from strands_tools import current_time, file_read, file_write, http_request

        from haytham.agents.tools.competitor_recording import (
            record_competitor,
            record_market_positioning,
            record_sentiment,
        )
        from haytham.agents.utils.web_search import web_search

        return [
            file_read,
            file_write,
            http_request,
            current_time,
            web_search,
            record_competitor,
            record_sentiment,
            record_market_positioning,
        ]

    if profile == ToolProfile.RISK_CLASSIFICATION:
        from haytham.agents.tools.risk_classification import classify_risk_level

        return [classify_risk_level]

    if profile == ToolProfile.RECOMMENDATION:
        from haytham.agents.tools.recommendation import (
            compute_verdict,
            record_counter_signal,
            record_dimension_score,
            record_knockout,
            set_risk_and_evidence,
        )

        return [
            record_knockout,
            record_dimension_score,
            record_counter_signal,
            set_risk_and_evidence,
            compute_verdict,
        ]

    if profile == ToolProfile.BUILD_BUY:
        from haytham.agents.tools.build_buy import (
            estimate_integration_effort,
            evaluate_build_buy_decision,
            search_service_catalog,
        )

        return [search_service_catalog, evaluate_build_buy_decision, estimate_integration_effort]

    if profile == ToolProfile.BUILD_BUY_WEB:
        from haytham.agents.utils.web_search import web_search

        # Build vs Buy analyzer with web search for current pricing/features
        return [web_search]

    if profile == ToolProfile.STORY_GENERATION:
        # Story generation validation tools are provided via custom tool handlers
        # in the agent execution, not as strands tools
        return []

    if profile == ToolProfile.PDF_REPORT:
        from haytham.agents.tools.pdf_report import generate_pdf_tool

        return [generate_pdf_tool]

    return []


# =============================================================================
# Agent Configuration
# =============================================================================


@dataclass
class AgentConfig:
    """Configuration for a specialist agent.

    Attributes:
        name: Agent name (used for logging and identification)
        prompt_key: Key for loading prompt from worker_* directory
        max_tokens: Maximum tokens for response generation
        timeout_config: Timeout configuration to use
        tool_profile: Tools to provide to the agent
        streaming: Whether to enable streaming (overrides timeout_config if set)
        use_file_ops_model: If True, uses create_bedrock_model_for_file_operations
        structured_output_model: Optional Pydantic model for structured output
        custom_system_prompt: Optional inline system prompt (overrides prompt_key)
    """

    name: str
    prompt_key: str
    max_tokens: int = TOKENS_DEFAULT
    timeout_config: TimeoutConfig = field(default_factory=lambda: TIMEOUT_STANDARD)
    tool_profile: ToolProfile = ToolProfile.NONE
    model_tier: ModelTier = ModelTier.LIGHT
    streaming: bool | None = None
    use_file_ops_model: bool = False
    structured_output_model: type | None = None
    structured_output_model_path: str | None = None
    custom_system_prompt: str | None = None


# Agent configurations - single source of truth for all agent settings
AGENT_CONFIGS: dict[str, AgentConfig] = {
    # Thinking tool agents (extended tokens for cognitive cycles)
    "concept_expansion": AgentConfig(
        name="concept_expansion_agent",
        prompt_key="worker_concept_expansion",
        max_tokens=TOKENS_THINKING,
        timeout_config=TIMEOUT_STANDARD,
        tool_profile=ToolProfile.THINKING,
        model_tier=ModelTier.HEAVY,
    ),
    "mvp_specification": AgentConfig(
        name="mvp_specification_agent",
        prompt_key="worker_mvp_specification",
        max_tokens=TOKENS_LARGE,
        timeout_config=TIMEOUT_STANDARD,
        tool_profile=ToolProfile.THINKING,
        model_tier=ModelTier.HEAVY,
    ),
    "capability_model": AgentConfig(
        name="capability_model_agent",
        prompt_key="worker_capability_model",
        max_tokens=TOKENS_LARGE,
        timeout_config=TIMEOUT_STANDARD,
        tool_profile=ToolProfile.THINKING,
        model_tier=ModelTier.HEAVY,
    ),
    # Web research agents (file + http tools, extended timeouts)
    "market_intelligence": AgentConfig(
        name="market_intelligence_agent",
        prompt_key="worker_market_intelligence",
        max_tokens=TOKENS_MEDIUM,
        use_file_ops_model=True,
        tool_profile=ToolProfile.WEB_RESEARCH,
        model_tier=ModelTier.HEAVY,
    ),
    "competitor_analysis": AgentConfig(
        name="competitor_analysis_agent",
        prompt_key="worker_competitor_analysis",
        max_tokens=TOKENS_THINKING,  # 550-word structured output + markdown ≈ 1200 tokens
        use_file_ops_model=True,
        tool_profile=ToolProfile.COMPETITOR_RESEARCH,
        model_tier=ModelTier.HEAVY,
    ),
    # Standard agents (no special tools or timeouts)
    "pivot_strategy": AgentConfig(
        name="pivot_strategy_agent",
        prompt_key="worker_pivot_strategy",
        model_tier=ModelTier.REASONING,
    ),
    "validation_scorer": AgentConfig(
        name="validation_scorer_agent",
        prompt_key="worker_validation_scorer",
        max_tokens=TOKENS_SCORECARD,
        tool_profile=ToolProfile.RECOMMENDATION,
        model_tier=ModelTier.REASONING,
        structured_output_model_path="haytham.agents.worker_validation_summary.validation_summary_models:ScorerOutput",
    ),
    "validation_narrator": AgentConfig(
        name="validation_narrator_agent",
        prompt_key="worker_validation_narrator",
        max_tokens=TOKENS_MEDIUM,
        tool_profile=ToolProfile.NONE,
        structured_output_model_path="haytham.agents.worker_validation_summary.validation_summary_models:NarrativeFields",
    ),
    "mvp_scope": AgentConfig(
        name="mvp_scope_agent",
        prompt_key="worker_mvp_scope",
        max_tokens=TOKENS_DEFAULT,
    ),
    # MVP Scope sub-agents (chain: core → boundaries → flows)
    "mvp_scope_core": AgentConfig(
        name="mvp_scope_core_agent",
        prompt_key="worker_mvp_scope_core",
        max_tokens=TOKENS_DEFAULT,
    ),
    "mvp_scope_boundaries": AgentConfig(
        name="mvp_scope_boundaries_agent",
        prompt_key="worker_mvp_scope_boundaries",
        max_tokens=TOKENS_DEFAULT,
    ),
    "mvp_scope_flows": AgentConfig(
        name="mvp_scope_flows_agent",
        prompt_key="worker_mvp_scope_flows",
        max_tokens=TOKENS_DEFAULT,
    ),
    # Risk assessment agent - produces markdown output with risk classification
    "startup_validator": AgentConfig(
        name="startup_validator_agent",
        prompt_key="worker_startup_validator",
        max_tokens=2000,  # Increased for detailed validation output
        timeout_config=TIMEOUT_EXTENDED,
        tool_profile=ToolProfile.RISK_CLASSIFICATION,
        model_tier=ModelTier.REASONING,
        # Removed structured_output_model - markdown is more reliable
        # Risk level is extracted by post-processor from text output
    ),
    # Input validation agent (lightweight, fast classification)
    "idea_gatekeeper": AgentConfig(
        name="idea_gatekeeper_agent",
        prompt_key="worker_idea_gatekeeper",
        max_tokens=500,  # Small output - just JSON classification
        timeout_config=TIMEOUT_STANDARD,
        tool_profile=ToolProfile.NONE,
    ),
    # Idea discovery agent (Lean Canvas gap analysis, pre-workflow)
    "idea_discovery": AgentConfig(
        name="idea_discovery_agent",
        prompt_key="worker_idea_discovery",
        max_tokens=800,
        timeout_config=TIMEOUT_STANDARD,
        tool_profile=ToolProfile.NONE,
        structured_output_model_path="haytham.agents.worker_idea_discovery.discovery_models:IdeaDiscoveryOutput",
    ),
    # System traits classification agent (lightweight, no tools)
    "system_traits": AgentConfig(
        name="system_traits_agent",
        prompt_key="worker_system_traits",
        max_tokens=TOKENS_MEDIUM,
        timeout_config=TIMEOUT_STANDARD,
        tool_profile=ToolProfile.NONE,
        structured_output_model_path="haytham.agents.worker_system_traits.system_traits_models:SystemTraitsOutput",
    ),
    # Build vs Buy advisor with catalog search and evaluation tools (legacy)
    "build_buy_advisor": AgentConfig(
        name="build_buy_advisor_agent",
        prompt_key="worker_build_buy_advisor",
        max_tokens=TOKENS_MEDIUM,
        timeout_config=TIMEOUT_EXTENDED,
        tool_profile=ToolProfile.BUILD_BUY,
    ),
    # Build vs Buy analyzer with structured output and web search
    "build_buy_analyzer": AgentConfig(
        name="build_buy_analyzer_agent",
        prompt_key="worker_build_buy_advisor",
        max_tokens=TOKENS_LARGE,  # Larger output for structured response
        timeout_config=TIMEOUT_EXTENDED,
        tool_profile=ToolProfile.BUILD_BUY_WEB,
        model_tier=ModelTier.HEAVY,
        structured_output_model_path="haytham.agents.worker_build_buy_advisor.build_buy_models:BuildBuyAnalysisOutput",
    ),
    # Concept Anchor Extractor (ADR-022) - extracts invariants to prevent concept drift
    "anchor_extractor": AgentConfig(
        name="anchor_extractor_agent",
        prompt_key="worker_anchor_extractor",
        max_tokens=TOKENS_THINKING,  # Structured output: ConceptAnchor JSON (~1200 tokens)
        timeout_config=TIMEOUT_STANDARD,
        tool_profile=ToolProfile.NONE,
        structured_output_model_path="haytham.workflow.anchor_schema:ConceptAnchor",
    ),
    # Phase Verifier (ADR-022) - independent reviewer for phase-boundary verification
    "phase_verifier": AgentConfig(
        name="phase_verifier_agent",
        prompt_key="worker_phase_verifier",
        max_tokens=TOKENS_LARGE,  # Needs room for detailed verification output
        timeout_config=TIMEOUT_EXTENDED,
        tool_profile=ToolProfile.NONE,
        structured_output_model_path="haytham.workflow.verifiers.schemas:PhaseVerification",
    ),
}


# =============================================================================
# Output Formatter Configuration
# =============================================================================

# Common agent preamble patterns to skip when extracting content
AGENT_PREAMBLE_PATTERNS = [
    "i'll analyze",
    "i will analyze",
    "let me analyze",
    "i'll examine",
    "i will examine",
    "let me examine",
    "i'll help",
    "i will help",
    "based on",
    "looking at",
    "here's my analysis",
    "here is my analysis",
    "analyzing",
    "examining",
]
