"""Data models for story export."""

from dataclasses import dataclass, field

# Single source of truth for layer number → display name mapping.
LAYER_NAMES: dict[int, str] = {
    1: "Bootstrap",
    2: "Entity Models",
    3: "Infrastructure",
    4: "Features",
}


@dataclass
class ExportableStory:
    """Normalized story format for export transformation."""

    # Core fields (always exported)
    id: str  # Generated: STORY-001, STORY-002, etc.
    title: str
    description: str
    acceptance_criteria: list[str] = field(default_factory=list)
    priority: str = "medium"  # high, medium, low
    order: int = 0  # Execution order

    # Metadata (format-dependent)
    labels: list[str] = field(default_factory=list)
    layer: int = 4  # Extracted from labels (1-4)
    story_type: str = "feature"  # bootstrap, entity, infrastructure, feature

    # Dependencies (transformed per format)
    dependencies: list[str] = field(default_factory=list)  # Original: title-based
    dependency_ids: list[str] = field(default_factory=list)  # Transformed: STORY-XXX

    # Optional enrichment
    estimate: str | None = None  # T-shirt size: XS, S, M, L, XL
    epic: str | None = None  # Grouped by layer or capability

    @property
    def layer_name(self) -> str:
        """Get human-readable layer name."""
        return LAYER_NAMES.get(self.layer, "Unknown")

    @property
    def clean_labels(self) -> list[str]:
        """Get labels with colons replaced by dashes (for tools that don't support colons)."""
        return [label.replace(":", "-") for label in self.labels]


@dataclass
class ExportOptions:
    """Options for customizing story export."""

    include_acceptance_criteria: bool = True
    include_dependencies: bool = True
    include_labels: bool = True
    include_estimates: bool = False
    story_id_prefix: str = "STORY"
    filter_layers: list[int] | None = None  # None means all layers

    def should_include_story(self, story: ExportableStory) -> bool:
        """Check if story should be included based on filter options."""
        if self.filter_layers is None:
            return True
        return story.layer in self.filter_layers
