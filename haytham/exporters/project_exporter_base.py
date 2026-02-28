"""Abstract base class for project-level exporters."""

from abc import ABC, abstractmethod

from haytham.exporters.project_model import ExportableProject


class ProjectExporter(ABC):
    """Base class for project-level exporters (OpenSpec, Spec Kit)."""

    format_name: str = "Unknown"
    file_extension: str = "zip"
    mime_type: str = "application/zip"

    @abstractmethod
    def export_tree(self, project: ExportableProject) -> dict[str, str]:
        """Produce a directory tree as {relative_path: content}."""
        ...

    def get_filename(self) -> str:
        """Generate download filename."""
        return f"{self.format_name.lower().replace(' ', '-')}.{self.file_extension}"
