"""Build vs. buy analyzer for capabilities (Stage 7).

This module analyzes capabilities from the Capability Model to determine
whether each should be built, bought, or use a hybrid approach.

Unlike the story-based analyzer, this works with:
- Functional capabilities (what users can do)
- Non-functional capabilities (quality attributes)

The output informs:
- Architecture decisions (what services to integrate)
- Story generation (INTEGRATION stories vs IMPLEMENTATION stories)
"""

import json
import logging

from .catalog import ServiceCatalog, load_service_catalog
from .models import (
    BuildBuyRecommendation,
    CapabilityAnalysis,
    CapabilityBuildBuySummary,
    RecommendationType,
)

logger = logging.getLogger(__name__)


class CapabilityBuildBuyAnalyzer:
    """Analyzes capabilities for build vs. buy recommendations.

    This analyzer works with the structured capability model output
    from Stage 6 (capability-model) and produces recommendations that
    inform Stage 8 (architecture_decisions) and Stage 9 (story_generation).
    """

    def __init__(self, catalog: ServiceCatalog | None = None):
        """Initialize analyzer with service catalog.

        Args:
            catalog: Service catalog to use. Loads default if not provided.
        """
        self.catalog = catalog or load_service_catalog()

    def analyze_capability(
        self, capability: dict, capability_type: str = "functional"
    ) -> CapabilityAnalysis | None:
        """Analyze a single capability for build vs. buy recommendation.

        Args:
            capability: Capability dictionary with name, description, etc.
            capability_type: "functional" or "non_functional"

        Returns:
            CapabilityAnalysis or None if analysis fails
        """
        name = capability.get("name", "")
        description = capability.get("description", "")
        acceptance_criteria = capability.get("acceptance_criteria", [])
        rationale = capability.get("rationale", "")

        if not name:
            logger.warning("Capability missing name, skipping")
            return None

        # Combine all text for keyword matching
        criteria_text = " ".join(acceptance_criteria) if acceptance_criteria else ""
        search_text = f"{name} {description} {criteria_text} {rationale}"

        # First check if this is a build category (core business logic, etc.)
        is_build, build_cat = self.catalog.is_build_category(search_text)
        if is_build and build_cat:
            recommendation = BuildBuyRecommendation(
                recommendation=RecommendationType.BUILD,
                confidence="high",
                rationale=build_cat.rationale,
                services=[],
                build_guidance="This is core to your product. Build it yourself.",
            )
            return CapabilityAnalysis(
                capability_name=name,
                capability_type=capability_type,
                recommendation=recommendation,
                story_guidance="IMPLEMENTATION-focused",
                architecture_implications=[
                    "Custom implementation required",
                    "Consider patterns from similar products",
                    "Plan for comprehensive testing",
                ],
            )

        # Check buy/hybrid categories
        category_info = self.catalog.find_category(search_text)
        if category_info:
            recommendation = BuildBuyRecommendation(
                recommendation=category_info.default_recommendation,
                confidence="high",
                rationale=category_info.rationale,
                services=category_info.services,
                if_you_must_build=category_info.if_you_must_build,
            )

            # Generate story guidance based on recommendation
            if category_info.default_recommendation == RecommendationType.BUY:
                story_guidance = "INTEGRATION-focused"
                arch_implications = [
                    f"Integrate with {category_info.services[0].name if category_info.services else 'external service'}",
                    "Add service credentials to environment config",
                    "Implement error handling for service failures",
                ]
            elif category_info.default_recommendation == RecommendationType.HYBRID:
                story_guidance = "INTEGRATION-focused with custom logic"
                arch_implications = [
                    "Use service for foundation",
                    "Build custom layer on top",
                    "Design clean abstraction boundary",
                ]
            else:
                story_guidance = "IMPLEMENTATION-focused"
                arch_implications = ["Custom implementation required"]

            return CapabilityAnalysis(
                capability_name=name,
                capability_type=capability_type,
                recommendation=recommendation,
                story_guidance=story_guidance,
                architecture_implications=arch_implications,
            )

        # No matching category - default to BUILD (core logic)
        recommendation = BuildBuyRecommendation(
            recommendation=RecommendationType.BUILD,
            confidence="medium",
            rationale="No matching service category found. This appears to be custom business logic.",
            services=[],
            build_guidance="Build this capability as part of your core product logic.",
        )
        return CapabilityAnalysis(
            capability_name=name,
            capability_type=capability_type,
            recommendation=recommendation,
            story_guidance="IMPLEMENTATION-focused",
            architecture_implications=["Custom implementation required"],
        )

    def analyze_capabilities(self, capability_model: dict) -> CapabilityBuildBuySummary:
        """Analyze all capabilities from a capability model.

        Args:
            capability_model: Parsed capability model JSON with structure:
                {
                    "capabilities": {
                        "functional": [...],
                        "non_functional": [...]
                    },
                    "summary": {...}
                }

        Returns:
            CapabilityBuildBuySummary with all analyses
        """
        analyses: list[CapabilityAnalysis] = []
        buy_count = 0
        build_count = 0
        hybrid_count = 0
        integration_services: list[str] = []

        capabilities_data = capability_model.get("capabilities", {})

        # Analyze functional capabilities
        for cap in capabilities_data.get("functional", []):
            analysis = self.analyze_capability(cap, "functional")
            if analysis:
                analyses.append(analysis)
                self._update_counts(analysis, buy_count, build_count, hybrid_count)
                if analysis.recommendation.recommendation == RecommendationType.BUY:
                    buy_count += 1
                    # Track services for integration
                    for svc in analysis.recommendation.services:
                        if svc.name not in integration_services:
                            integration_services.append(svc.name)
                elif analysis.recommendation.recommendation == RecommendationType.HYBRID:
                    hybrid_count += 1
                    for svc in analysis.recommendation.services:
                        if svc.name not in integration_services:
                            integration_services.append(svc.name)
                else:
                    build_count += 1

        # Analyze non-functional capabilities
        for cap in capabilities_data.get("non_functional", []):
            analysis = self.analyze_capability(cap, "non_functional")
            if analysis:
                analyses.append(analysis)
                if analysis.recommendation.recommendation == RecommendationType.BUY:
                    buy_count += 1
                    for svc in analysis.recommendation.services:
                        if svc.name not in integration_services:
                            integration_services.append(svc.name)
                elif analysis.recommendation.recommendation == RecommendationType.HYBRID:
                    hybrid_count += 1
                    for svc in analysis.recommendation.services:
                        if svc.name not in integration_services:
                            integration_services.append(svc.name)
                else:
                    build_count += 1

        # Generate story order suggestion
        suggested_order = self._generate_story_order_suggestion(
            buy_count, hybrid_count, build_count
        )

        return CapabilityBuildBuySummary(
            total_capabilities=len(analyses),
            buy_count=buy_count,
            build_count=build_count,
            hybrid_count=hybrid_count,
            capabilities=analyses,
            integration_services=integration_services,
            suggested_story_order=suggested_order,
        )

    def _update_counts(
        self,
        analysis: CapabilityAnalysis,
        buy_count: int,
        build_count: int,
        hybrid_count: int,
    ) -> None:
        """Update recommendation counts (for internal tracking)."""
        # This is handled inline now for accuracy
        pass

    def _generate_story_order_suggestion(
        self, buy_count: int, hybrid_count: int, build_count: int
    ) -> str:
        """Generate suggestion for story ordering based on analysis."""
        if buy_count > 0 or hybrid_count > 0:
            return (
                "1. Integration setup stories (configure external services)\n"
                "2. Foundation stories (core entities and data model)\n"
                "3. Feature stories (business logic using integrations)"
            )
        else:
            return (
                "1. Foundation stories (core entities and data model)\n"
                "2. Infrastructure stories (API, database, auth)\n"
                "3. Feature stories (business logic)"
            )


def analyze_capabilities(capability_model: dict | str) -> CapabilityBuildBuySummary:
    """Convenience function to analyze capabilities.

    Args:
        capability_model: Capability model dict or JSON string

    Returns:
        CapabilityBuildBuySummary with recommendations
    """
    if isinstance(capability_model, str):
        # Parse JSON, extracting from markdown code blocks if needed
        json_str = _extract_json_from_output(capability_model)
        capability_model = json.loads(json_str)

    analyzer = CapabilityBuildBuyAnalyzer()
    return analyzer.analyze_capabilities(capability_model)


def _extract_json_from_output(output: str) -> str:
    """Extract JSON from output that may contain markdown code blocks.

    Note: Returns the raw JSON *string* (not parsed dict) for backward compat.
    """
    from haytham.agents.output_utils import extract_json_from_text

    parsed = extract_json_from_text(output)
    if parsed is not None:
        return json.dumps(parsed)
    return output


def format_capability_analysis_as_markdown(summary: CapabilityBuildBuySummary) -> str:
    """Format capability analysis as markdown for stage output.

    Args:
        summary: The capability build/buy summary

    Returns:
        Formatted markdown string
    """
    lines = [
        "# Build vs Buy Analysis\n",
        "## Summary\n",
        f"- **Total Capabilities Analyzed:** {summary.total_capabilities}",
        f"- **BUY:** {summary.buy_count} ({summary.buy_percentage:.0f}%)",
        f"- **BUILD:** {summary.build_count} ({summary.build_percentage:.0f}%)",
        f"- **HYBRID:** {summary.hybrid_count} ({summary.hybrid_percentage:.0f}%)",
        "",
    ]

    if summary.integration_services:
        lines.extend(
            [
                "## Services to Integrate\n",
                *[f"- {svc}" for svc in summary.integration_services],
                "",
            ]
        )

    if summary.suggested_story_order:
        lines.extend(
            [
                "## Suggested Story Order\n",
                summary.suggested_story_order,
                "",
            ]
        )

    # Group by recommendation type
    buy_caps = [
        c for c in summary.capabilities if c.recommendation.recommendation == RecommendationType.BUY
    ]
    hybrid_caps = [
        c
        for c in summary.capabilities
        if c.recommendation.recommendation == RecommendationType.HYBRID
    ]
    build_caps = [
        c
        for c in summary.capabilities
        if c.recommendation.recommendation == RecommendationType.BUILD
    ]

    if buy_caps:
        lines.extend(
            [
                "## Recommended to BUY\n",
                "*Use existing services to save time and reduce risk*\n",
            ]
        )
        for cap in buy_caps:
            lines.extend(_format_capability_section(cap))

    if hybrid_caps:
        lines.extend(
            [
                "## HYBRID Approach\n",
                "*Buy the foundation, build custom logic*\n",
            ]
        )
        for cap in hybrid_caps:
            lines.extend(_format_capability_section(cap))

    if build_caps:
        lines.extend(
            [
                "## Recommended to BUILD\n",
                "*Core to your product - build it yourself*\n",
            ]
        )
        for cap in build_caps:
            lines.extend(_format_capability_section(cap))

    return "\n".join(lines)


def _format_capability_section(cap: CapabilityAnalysis) -> list[str]:
    """Format a single capability analysis as markdown lines."""
    rec = cap.recommendation
    emoji = {"BUY": "🛒", "HYBRID": "🔀", "BUILD": "🔧"}.get(rec.recommendation.value, "❓")

    lines = [
        f"### {emoji} {cap.capability_name}\n",
        f"**Type:** {cap.capability_type.replace('_', ' ').title()}",
        f"**Story Guidance:** {cap.story_guidance}",
        f"**Rationale:** {rec.rationale}",
        "",
    ]

    if cap.architecture_implications:
        lines.append("**Architecture Implications:**")
        for impl in cap.architecture_implications:
            lines.append(f"- {impl}")
        lines.append("")

    if rec.services:
        lines.append("**Recommended Services:**")
        for svc in rec.services:
            tier_badge = "⭐ " if svc.tier == "recommended" else ""
            lines.append(f"- {tier_badge}{svc.name} ({svc.pricing})")
        lines.append("")

    if rec.if_you_must_build:
        lines.extend(
            [
                "**If you must build:**",
                rec.if_you_must_build,
                "",
            ]
        )

    return lines
