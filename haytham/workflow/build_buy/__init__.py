"""Build vs. Buy analysis module for technical component recommendations."""

from .analyzer import BuildBuyAnalyzer, analyze_stories
from .capability_analyzer import CapabilityBuildBuyAnalyzer, analyze_capabilities
from .catalog import ServiceCatalog, load_service_catalog
from .models import (
    BuildBuyRecommendation,
    BuildBuySummary,
    CapabilityAnalysis,
    CapabilityBuildBuySummary,
    ComponentAnalysis,
    RecommendationType,
    ServiceOption,
)

__all__ = [
    # Core types
    "RecommendationType",
    "ServiceOption",
    "BuildBuyRecommendation",
    # Story-based analysis (legacy)
    "ComponentAnalysis",
    "BuildBuySummary",
    "BuildBuyAnalyzer",
    "analyze_stories",
    # Capability-based analysis (Stage 7)
    "CapabilityAnalysis",
    "CapabilityBuildBuySummary",
    "CapabilityBuildBuyAnalyzer",
    "analyze_capabilities",
    # Catalog
    "ServiceCatalog",
    "load_service_catalog",
]
