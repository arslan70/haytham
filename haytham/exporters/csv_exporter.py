"""Export stories to generic CSV format."""

import csv
import io

from .base import BaseExporter
from .models import ExportableStory


class CSVExporter(BaseExporter):
    """Export stories to generic CSV format.

    Produces a universal CSV format suitable for:
    - Spreadsheet review
    - Custom imports to other tools
    - Data analysis
    """

    format_name = "CSV"
    file_extension = "csv"
    mime_type = "text/csv"

    def export(self, stories: list[ExportableStory]) -> str:
        """Transform stories to generic CSV format."""
        filtered_stories = self.filter_stories(stories)
        output = io.StringIO()
        writer = csv.writer(output, quoting=csv.QUOTE_ALL)

        # CSV headers
        headers = [
            "ID",
            "Title",
            "Description",
            "Priority",
            "Type",
            "Layer",
            "Layer Name",
            "Order",
        ]

        if self.options.include_acceptance_criteria:
            headers.append("Acceptance Criteria")

        if self.options.include_dependencies:
            headers.extend(["Dependencies", "Dependency IDs"])

        if self.options.include_labels:
            headers.append("Labels")

        if self.options.include_estimates:
            headers.append("Estimate")

        writer.writerow(headers)

        for story in filtered_stories:
            row = [
                story.id,
                story.title,
                story.description,
                story.priority.capitalize(),
                story.story_type,
                story.layer,
                story.layer_name,
                story.order,
            ]

            if self.options.include_acceptance_criteria:
                # Join acceptance criteria with numbered list
                ac_text = "; ".join(
                    f"{i + 1}. {ac}" for i, ac in enumerate(story.acceptance_criteria)
                )
                row.append(ac_text)

            if self.options.include_dependencies:
                row.append("|".join(story.dependencies))
                row.append("|".join(story.dependency_ids))

            if self.options.include_labels:
                row.append("|".join(story.labels))

            if self.options.include_estimates:
                row.append(story.estimate or "")

            writer.writerow(row)

        return output.getvalue()
