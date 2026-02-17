"""Service catalog loader for build vs. buy analysis."""

from dataclasses import dataclass, field
from pathlib import Path

import yaml

from .models import RecommendationType, ServiceOption


@dataclass
class CategoryInfo:
    """Information about a service category."""

    name: str
    default_recommendation: RecommendationType
    keywords: list[str]
    rationale: str
    services: list[ServiceOption]
    if_you_must_build: str = ""


@dataclass
class BuildCategory:
    """Category of components that should be built."""

    name: str
    keywords: list[str]
    rationale: str


@dataclass
class ServiceCatalog:
    """Loaded service catalog with lookup capabilities."""

    categories: dict[str, CategoryInfo] = field(default_factory=dict)
    build_categories: list[BuildCategory] = field(default_factory=list)

    def find_category(self, text: str) -> CategoryInfo | None:
        """
        Find matching category based on text content.

        Args:
            text: Text to search for keywords (e.g., story title + description)

        Returns:
            Matching CategoryInfo or None
        """
        text_lower = text.lower()

        # Check each category's keywords
        for _category_name, category_info in self.categories.items():
            for keyword in category_info.keywords:
                if keyword.lower() in text_lower:
                    return category_info

        return None

    def is_build_category(self, text: str) -> tuple[bool, BuildCategory | None]:
        """
        Check if text matches a build category.

        Args:
            text: Text to search for keywords

        Returns:
            Tuple of (is_build, matching_category)
        """
        text_lower = text.lower()

        for build_cat in self.build_categories:
            for keyword in build_cat.keywords:
                if keyword.lower() in text_lower:
                    return True, build_cat

        return False, None

    def get_all_categories(self) -> list[str]:
        """Get list of all category names."""
        return list(self.categories.keys())


def load_service_catalog(catalog_path: Path | None = None) -> ServiceCatalog:
    """
    Load service catalog from YAML file.

    Args:
        catalog_path: Path to catalog YAML. Defaults to bundled catalog.

    Returns:
        Loaded ServiceCatalog
    """
    if catalog_path is None:
        catalog_path = Path(__file__).parent / "service_catalog.yaml"

    if not catalog_path.exists():
        raise FileNotFoundError(f"Service catalog not found: {catalog_path}")

    with open(catalog_path) as f:
        data = yaml.safe_load(f)

    catalog = ServiceCatalog()

    # Load buy categories
    for category_name, category_data in data.get("categories", {}).items():
        # Parse recommendation type
        rec_str = category_data.get("default_recommendation", "BUY")
        if rec_str == "BUY":
            rec_type = RecommendationType.BUY
        elif rec_str == "BUILD":
            rec_type = RecommendationType.BUILD
        else:
            rec_type = RecommendationType.HYBRID

        # Parse services
        services = []
        for svc_data in category_data.get("services", []):
            service = ServiceOption(
                name=svc_data.get("name", ""),
                tier=svc_data.get("tier", "alternative"),
                pricing=svc_data.get("pricing", ""),
                integration_effort=svc_data.get("integration_effort", ""),
                docs_url=svc_data.get("docs", ""),
                best_for=svc_data.get("best_for", ""),
            )
            services.append(service)

        category_info = CategoryInfo(
            name=category_name,
            default_recommendation=rec_type,
            keywords=category_data.get("keywords", []),
            rationale=category_data.get("rationale", ""),
            services=services,
            if_you_must_build=category_data.get("if_you_must_build", ""),
        )
        catalog.categories[category_name] = category_info

    # Load build categories
    for build_data in data.get("build_categories", []):
        build_cat = BuildCategory(
            name=build_data.get("name", ""),
            keywords=build_data.get("keywords", []),
            rationale=build_data.get("rationale", ""),
        )
        catalog.build_categories.append(build_cat)

    return catalog
