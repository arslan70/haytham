"""Export stories to Linear-compatible CSV format."""

import csv
import io

from .base import BaseExporter
from .models import ExportableStory


class LinearExporter(BaseExporter):
    """Export stories to Linear-compatible CSV format.

    Linear's CSV importer expects columns:
    - Title
    - Description
    - Priority (High, Medium, Low, None)
    - Labels (comma-separated)
    - Parent Issue (for sub-issues)
    """

    format_name = "Linear"
    file_extension = "csv"
    mime_type = "text/csv"

    def export(self, stories: list[ExportableStory]) -> str:
        """Transform stories to Linear CSV format."""
        filtered_stories = self.filter_stories(stories)
        output = io.StringIO()
        writer = csv.writer(output, quoting=csv.QUOTE_ALL)

        # Linear CSV headers
        writer.writerow(["Title", "Description", "Priority", "Labels", "Parent Issue"])

        for story in filtered_stories:
            description = self._build_description(story)
            labels = self._build_labels(story)
            parent = self._get_parent_issue(story)

            writer.writerow(
                [
                    story.title,
                    description,
                    story.priority.capitalize(),
                    labels,
                    parent,
                ]
            )

        return output.getvalue()

    def _build_description(self, story: ExportableStory) -> str:
        """Build Linear description with acceptance criteria."""
        parts = [story.description]

        if self.options.include_acceptance_criteria and story.acceptance_criteria:
            parts.append("\n\n## Acceptance Criteria\n")
            for ac in story.acceptance_criteria:
                parts.append(f"- [ ] {ac}\n")

        if self.options.include_dependencies and story.dependency_ids:
            parts.append(f"\n\n**Dependencies:** {', '.join(story.dependency_ids)}")

        return "".join(parts)

    def _build_labels(self, story: ExportableStory) -> str:
        """Build comma-separated labels for Linear."""
        if not self.options.include_labels:
            return ""

        # Linear doesn't like colons in labels, replace with dashes
        labels = story.clean_labels

        # Add layer as a label
        labels.append(f"layer-{story.layer}")

        return ",".join(labels)

    def _get_parent_issue(self, story: ExportableStory) -> str:
        """Get parent issue (Linear only supports single parent)."""
        if not self.options.include_dependencies:
            return ""

        # Linear only supports single parent, use first dependency
        if story.dependencies:
            return story.dependencies[0]
        return ""
