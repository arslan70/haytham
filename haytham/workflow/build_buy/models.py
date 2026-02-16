"""Data models for build vs. buy analysis."""

from dataclasses import dataclass, field
from enum import Enum


class RecommendationType(Enum):
    """Recommendation type for a component."""

    BUILD = "BUILD"
    BUY = "BUY"
    HYBRID = "HYBRID"


@dataclass
class ServiceOption:
    """A service option for a BUY or HYBRID recommendation."""

    name: str
    tier: str  # "recommended" or "alternative"
    pricing: str
    integration_effort: str
    docs_url: str = ""
    best_for: str = ""


@dataclass
class BuildBuyRecommendation:
    """Build vs. buy recommendation for a component."""

    recommendation: RecommendationType
    confidence: str  # "high", "medium", "low"
    rationale: str
    services: list[ServiceOption] = field(default_factory=list)
    build_guidance: str = ""
    if_you_must_build: str = ""


@dataclass
class ComponentAnalysis:
    """Analysis result for a single component/story."""

    component_name: str
    story_title: str
    story_order: int
    category: str  # e.g., "authentication", "payments", "storage"
    recommendation: BuildBuyRecommendation
    original_effort: str = ""  # Original estimate if building
    new_effort: str = ""  # Estimated effort with recommendation

    @property
    def time_saved(self) -> str:
        """Estimate time saved by following recommendation."""
        if self.recommendation.recommendation == RecommendationType.BUY:
            return "60-80%"
        elif self.recommendation.recommendation == RecommendationType.HYBRID:
            return "30-50%"
        return "0%"


@dataclass
class BuildBuySummary:
    """Summary of all build vs. buy recommendations."""

    total_components: int
    buy_count: int
    build_count: int
    hybrid_count: int
    estimated_monthly_cost: str
    estimated_time_saved: str
    components: list[ComponentAnalysis] = field(default_factory=list)

    @property
    def buy_percentage(self) -> float:
        """Percentage of components recommended to buy."""
        if self.total_components == 0:
            return 0.0
        return (self.buy_count / self.total_components) * 100

    @property
    def build_percentage(self) -> float:
        """Percentage of components recommended to build."""
        if self.total_components == 0:
            return 0.0
        return (self.build_count / self.total_components) * 100

    @property
    def hybrid_percentage(self) -> float:
        """Percentage of hybrid recommendations."""
        if self.total_components == 0:
            return 0.0
        return (self.hybrid_count / self.total_components) * 100


# =============================================================================
# Capability-based Analysis Models (Stage 7)
# =============================================================================


@dataclass
class CapabilityAnalysis:
    """Analysis result for a single capability."""

    capability_name: str
    capability_type: str  # "functional" or "non_functional"
    recommendation: BuildBuyRecommendation
    story_guidance: str  # "INTEGRATION-focused" or "IMPLEMENTATION-focused"
    architecture_implications: list[str] = field(default_factory=list)

    @property
    def is_buy_or_hybrid(self) -> bool:
        """Check if this capability should use external services."""
        return self.recommendation.recommendation in (
            RecommendationType.BUY,
            RecommendationType.HYBRID,
        )


@dataclass
class CapabilityBuildBuySummary:
    """Summary of build vs buy analysis for capabilities."""

    total_capabilities: int
    buy_count: int
    build_count: int
    hybrid_count: int
    capabilities: list[CapabilityAnalysis] = field(default_factory=list)
    integration_services: list[str] = field(default_factory=list)  # Services that need setup
    suggested_story_order: str = ""  # e.g., "Integration stories before feature stories"

    @property
    def buy_percentage(self) -> float:
        """Percentage of capabilities recommended to buy."""
        if self.total_capabilities == 0:
            return 0.0
        return (self.buy_count / self.total_capabilities) * 100

    @property
    def build_percentage(self) -> float:
        """Percentage of capabilities recommended to build."""
        if self.total_capabilities == 0:
            return 0.0
        return (self.build_count / self.total_capabilities) * 100

    @property
    def hybrid_percentage(self) -> float:
        """Percentage of hybrid recommendations."""
        if self.total_capabilities == 0:
            return 0.0
        return (self.hybrid_count / self.total_capabilities) * 100


# =============================================================================
# Decision Matrix Models
# =============================================================================


# Decision matrix dimension scores
@dataclass
class DimensionScores:
    """Scores for build/buy decision matrix dimensions."""

    complexity: float  # 1 = simple, 5 = security-critical
    time_to_build: float  # 1 = hours, 5 = weeks
    maintenance: float  # 1 = minimal, 5 = constant updates
    cost_at_scale: float  # 1 = expensive services, 5 = cheap/free
    lock_in_risk: float  # 1 = low, 5 = high
    differentiation: float  # 1 = core to product, 5 = commodity

    def compute_recommendation(self) -> RecommendationType:
        """Compute recommendation from dimension scores."""
        # Weights reflect importance for solo founders
        weights = {
            "complexity": 1.5,  # Security complexity matters most
            "time_to_build": 1.3,  # Time is precious for solos
            "maintenance": 1.2,  # Ongoing burden is costly
            "cost_at_scale": 0.8,  # Less important early
            "lock_in_risk": 0.7,  # Acceptable tradeoff
            "differentiation": 1.5,  # Don't outsource your moat
        }

        scores = {
            "complexity": self.complexity,
            "time_to_build": self.time_to_build,
            "maintenance": self.maintenance,
            "cost_at_scale": self.cost_at_scale,
            "lock_in_risk": self.lock_in_risk,
            "differentiation": self.differentiation,
        }

        weighted_score = sum(scores[dim] * weights[dim] for dim in scores) / sum(weights.values())

        if weighted_score >= 3.5:
            return RecommendationType.BUY
        elif weighted_score <= 2.0:
            return RecommendationType.BUILD
        else:
            return RecommendationType.HYBRID
