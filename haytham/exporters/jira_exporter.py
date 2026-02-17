"""Export stories to Jira-compatible CSV format."""

import csv
import io

from .base import BaseExporter
from .models import ExportableStory


class JiraExporter(BaseExporter):
    """Export stories to Jira-compatible CSV format.

    Jira's external import expects columns:
    - Summary (title)
    - Description (supports wiki markup)
    - Issue Type (Story, Task, Bug, Epic)
    - Priority (High, Medium, Low)
    - Labels (space-separated)
    - Linked Issues (for dependencies)
    """

    format_name = "Jira"
    file_extension = "csv"
    mime_type = "text/csv"

    # Map story types to Jira issue types
    ISSUE_TYPE_MAP = {
        "bootstrap": "Task",
        "entity": "Task",
        "infrastructure": "Task",
        "feature": "Story",
    }

    # Map priority to Jira priority
    PRIORITY_MAP = {
        "high": "High",
        "medium": "Medium",
        "low": "Low",
    }

    def export(self, stories: list[ExportableStory]) -> str:
        """Transform stories to Jira CSV format."""
        filtered_stories = self.filter_stories(stories)
        output = io.StringIO()
        writer = csv.writer(output, quoting=csv.QUOTE_ALL)

        # Jira CSV headers
        writer.writerow(
            [
                "Summary",
                "Description",
                "Issue Type",
                "Priority",
                "Labels",
                "Linked Issues",
            ]
        )

        for story in filtered_stories:
            description = self._build_description(story)
            issue_type = self.ISSUE_TYPE_MAP.get(story.story_type, "Story")
            priority = self.PRIORITY_MAP.get(story.priority, "Medium")
            labels = self._build_labels(story)
            linked_issues = self._build_linked_issues(story)

            writer.writerow(
                [
                    story.title,
                    description,
                    issue_type,
                    priority,
                    labels,
                    linked_issues,
                ]
            )

        return output.getvalue()

    def _build_description(self, story: ExportableStory) -> str:
        """Build Jira description with wiki markup."""
        parts = [story.description]

        if self.options.include_acceptance_criteria and story.acceptance_criteria:
            parts.append("\n\nh3. Acceptance Criteria\n")
            for ac in story.acceptance_criteria:
                parts.append(f"* {ac}\n")

        # Add metadata
        parts.append(f"\n\n----\n*Layer:* {story.layer_name}\n")
        parts.append(f"*Order:* {story.order}\n")
        parts.append(f"*ID:* {story.id}\n")

        return "".join(parts)

    def _build_labels(self, story: ExportableStory) -> str:
        """Build space-separated labels for Jira."""
        if not self.options.include_labels:
            return ""

        # Jira labels are space-separated and can't have spaces in them
        labels = []
        for label in story.labels:
            # Replace special characters
            clean_label = label.replace(":", "_").replace(" ", "_")
            labels.append(clean_label)

        # Add layer label
        labels.append(f"layer_{story.layer}")

        return " ".join(labels)

    def _build_linked_issues(self, story: ExportableStory) -> str:
        """Build linked issues string for Jira."""
        if not self.options.include_dependencies or not story.dependency_ids:
            return ""

        # Format: "blocks STORY-001, blocks STORY-002"
        links = [f"is blocked by {dep_id}" for dep_id in story.dependency_ids]
        return ", ".join(links)
