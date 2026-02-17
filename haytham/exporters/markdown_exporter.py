"""Export stories to Markdown format."""

from .base import BaseExporter
from .models import LAYER_NAMES, ExportableStory
from .transformer import get_stories_by_layer


class MarkdownExporter(BaseExporter):
    """Export stories to human-readable Markdown format.

    Produces a well-structured document grouped by layer with
    all story details, acceptance criteria, and dependencies.
    """

    format_name = "Markdown"
    file_extension = "md"
    mime_type = "text/markdown"

    def export(self, stories: list[ExportableStory]) -> str:
        """Transform stories to Markdown format."""
        filtered_stories = self.filter_stories(stories)
        lines = []

        # Header
        lines.append("# Generated Stories\n")
        lines.append(f"Total: {len(filtered_stories)} stories\n\n")

        # Summary table
        lines.append("## Summary\n")
        lines.append("| Layer | Stories | Priority Distribution |")
        lines.append("|-------|---------|----------------------|")

        layers = get_stories_by_layer(filtered_stories)
        for layer_num in sorted(layers.keys()):
            layer_stories = layers[layer_num]
            layer_name = LAYER_NAMES.get(layer_num, f"Layer {layer_num}")
            high = sum(1 for s in layer_stories if s.priority == "high")
            med = sum(1 for s in layer_stories if s.priority == "medium")
            low = sum(1 for s in layer_stories if s.priority == "low")
            lines.append(
                f"| {layer_name} | {len(layer_stories)} | High: {high}, Medium: {med}, Low: {low} |"
            )

        lines.append("\n")

        # Stories by layer
        for layer_num in sorted(layers.keys()):
            layer_stories = layers[layer_num]
            layer_name = LAYER_NAMES.get(layer_num, f"Layer {layer_num}")

            lines.append(f"## Layer {layer_num}: {layer_name} ({len(layer_stories)} stories)\n")

            for story in sorted(layer_stories, key=lambda s: s.order):
                lines.extend(self._format_story(story))
                lines.append("\n---\n")

        return "\n".join(lines)

    def _format_story(self, story: ExportableStory) -> list[str]:
        """Format a single story as Markdown."""
        lines = []

        # Story header
        lines.append(f"### {story.id}: {story.title}\n")

        # Metadata line
        meta_parts = [
            f"**Priority:** {story.priority.capitalize()}",
            f"**Type:** {story.story_type.capitalize()}",
        ]
        if story.estimate:
            meta_parts.append(f"**Estimate:** {story.estimate}")
        lines.append(" | ".join(meta_parts) + "\n")

        # Description
        lines.append(f"\n{story.description}\n")

        # Acceptance Criteria
        if self.options.include_acceptance_criteria and story.acceptance_criteria:
            lines.append("\n**Acceptance Criteria:**\n")
            for ac in story.acceptance_criteria:
                lines.append(f"- [ ] {ac}")
            lines.append("")

        # Dependencies
        if self.options.include_dependencies:
            if story.dependency_ids:
                deps = ", ".join(story.dependency_ids)
                lines.append(f"\n**Dependencies:** {deps}\n")
            else:
                lines.append("\n**Dependencies:** None\n")

        # Labels
        if self.options.include_labels and story.labels:
            labels_str = ", ".join(f"`{label}`" for label in story.labels)
            lines.append(f"\n**Labels:** {labels_str}\n")

        return lines
