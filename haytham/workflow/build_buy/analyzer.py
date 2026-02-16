"""Build vs. buy analyzer for stories and components."""

from .catalog import ServiceCatalog, load_service_catalog
from .models import (
    BuildBuyRecommendation,
    BuildBuySummary,
    ComponentAnalysis,
    RecommendationType,
)


class BuildBuyAnalyzer:
    """Analyzes stories and components for build vs. buy recommendations."""

    def __init__(self, catalog: ServiceCatalog | None = None):
        """
        Initialize analyzer with service catalog.

        Args:
            catalog: Service catalog to use. Loads default if not provided.
        """
        self.catalog = catalog or load_service_catalog()

    def analyze_story(self, story: dict) -> ComponentAnalysis | None:
        """
        Analyze a single story for build vs. buy recommendation.

        Args:
            story: Story dictionary with title, description, labels, etc.

        Returns:
            ComponentAnalysis or None if no recommendation applies
        """
        title = story.get("title", "")
        description = story.get("description", "")
        labels = story.get("labels", [])
        order = story.get("order", 0)

        # Combine text for keyword matching
        search_text = f"{title} {description} {' '.join(labels)}"

        # First check if this is a build category
        is_build, build_cat = self.catalog.is_build_category(search_text)
        if is_build and build_cat:
            recommendation = BuildBuyRecommendation(
                recommendation=RecommendationType.BUILD,
                confidence="high",
                rationale=build_cat.rationale,
                services=[],
                build_guidance="This is core to your product. Build it yourself.",
            )
            return ComponentAnalysis(
                component_name=build_cat.name.replace("_", " ").title(),
                story_title=title,
                story_order=order,
                category=build_cat.name,
                recommendation=recommendation,
                original_effort=self._estimate_effort_from_story(story),
                new_effort=self._estimate_effort_from_story(story),
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

            # Estimate new effort based on recommendation
            original_effort = self._estimate_effort_from_story(story)
            if category_info.default_recommendation == RecommendationType.BUY:
                # Use recommended service's integration effort
                new_effort = (
                    category_info.services[0].integration_effort
                    if category_info.services
                    else "2-4 hours"
                )
            elif category_info.default_recommendation == RecommendationType.HYBRID:
                new_effort = "4-8 hours (integration + customization)"
            else:
                new_effort = original_effort

            return ComponentAnalysis(
                component_name=category_info.name.replace("_", " ").title(),
                story_title=title,
                story_order=order,
                category=category_info.name,
                recommendation=recommendation,
                original_effort=original_effort,
                new_effort=new_effort,
            )

        # No matching category - default to BUILD
        return None

    def _estimate_effort_from_story(self, story: dict) -> str:
        """Estimate effort from story type/labels."""
        labels = story.get("labels", [])
        for label in labels:
            if label.startswith("type:"):
                story_type = label.split(":")[1]
                # Default effort by type
                type_efforts = {
                    "bootstrap": "4-8 hours",
                    "entity": "2-4 hours",
                    "infrastructure": "4-8 hours",
                    "feature": "6-12 hours",
                }
                return type_efforts.get(story_type, "4-8 hours")
        return "4-8 hours"

    def analyze_stories(self, stories: list[dict]) -> BuildBuySummary:
        """
        Analyze all stories and generate summary.

        Args:
            stories: List of story dictionaries

        Returns:
            BuildBuySummary with all analyses
        """
        components: list[ComponentAnalysis] = []
        buy_count = 0
        build_count = 0
        hybrid_count = 0

        for story in stories:
            analysis = self.analyze_story(story)
            if analysis:
                components.append(analysis)
                if analysis.recommendation.recommendation == RecommendationType.BUY:
                    buy_count += 1
                elif analysis.recommendation.recommendation == RecommendationType.BUILD:
                    build_count += 1
                else:
                    hybrid_count += 1

        # Estimate monthly cost based on BUY recommendations
        # Most services have free tiers that cover MVP scale
        monthly_cost = self._estimate_monthly_cost(components)

        # Estimate time saved
        time_saved = self._estimate_time_saved(buy_count, hybrid_count, len(components))

        return BuildBuySummary(
            total_components=len(components),
            buy_count=buy_count,
            build_count=build_count,
            hybrid_count=hybrid_count,
            estimated_monthly_cost=monthly_cost,
            estimated_time_saved=time_saved,
            components=components,
        )

    def _estimate_monthly_cost(self, components: list[ComponentAnalysis]) -> str:
        """Estimate monthly cost at MVP scale."""
        buy_components = [
            c for c in components if c.recommendation.recommendation == RecommendationType.BUY
        ]

        if not buy_components:
            return "$0 (all custom)"

        # Most services have free tiers that cover MVP scale
        # Estimate $10-30 per service at early growth stage
        min_cost = len(buy_components) * 0  # Free tiers
        max_cost = len(buy_components) * 30  # Basic paid tiers

        if max_cost == 0:
            return "$0 (free tiers)"
        elif min_cost == 0:
            return f"$0-{max_cost} (free tiers available)"
        else:
            return f"${min_cost}-{max_cost}"

    def _estimate_time_saved(self, buy_count: int, hybrid_count: int, total: int) -> str:
        """Estimate total time saved by following recommendations."""
        if total == 0:
            return "0 hours"

        # Rough estimates:
        # BUY saves ~6-8 hours per component on average
        # HYBRID saves ~3-4 hours per component on average
        min_hours = buy_count * 6 + hybrid_count * 3
        max_hours = buy_count * 10 + hybrid_count * 6

        if min_hours == 0:
            return "0 hours"
        return f"{min_hours}-{max_hours} hours"


def analyze_stories(stories: list[dict]) -> BuildBuySummary:
    """
    Convenience function to analyze stories.

    Args:
        stories: List of story dictionaries

    Returns:
        BuildBuySummary with recommendations
    """
    analyzer = BuildBuyAnalyzer()
    return analyzer.analyze_stories(stories)
