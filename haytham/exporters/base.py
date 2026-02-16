"""Base exporter class for all story exporters."""

from abc import ABC, abstractmethod

from .models import ExportableStory, ExportOptions


class BaseExporter(ABC):
    """Base class for all story exporters."""

    format_name: str = "Unknown"
    file_extension: str = "txt"
    mime_type: str = "text/plain"

    def __init__(self, options: ExportOptions | None = None):
        """Initialize exporter with options."""
        self.options = options or ExportOptions()

    @abstractmethod
    def export(self, stories: list[ExportableStory]) -> str:
        """
        Transform stories to export format string.

        Args:
            stories: List of exportable stories

        Returns:
            Formatted string content
        """
        pass

    def export_bytes(self, stories: list[ExportableStory]) -> bytes:
        """
        Export stories as bytes.

        Args:
            stories: List of exportable stories

        Returns:
            UTF-8 encoded bytes
        """
        content = self.export(stories)
        return content.encode("utf-8")

    def get_filename(self, project_name: str = "project") -> str:
        """
        Generate export filename.

        Args:
            project_name: Name of the project

        Returns:
            Filename with appropriate extension
        """
        safe_name = project_name.lower().replace(" ", "-").replace("_", "-")
        # Remove any non-alphanumeric characters except dashes
        safe_name = "".join(c for c in safe_name if c.isalnum() or c == "-")
        return f"{safe_name}-stories.{self.file_extension}"

    def filter_stories(self, stories: list[ExportableStory]) -> list[ExportableStory]:
        """
        Filter stories based on export options.

        Args:
            stories: All stories

        Returns:
            Filtered list of stories
        """
        return [s for s in stories if self.options.should_include_story(s)]
