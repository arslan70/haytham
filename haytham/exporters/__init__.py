"""Story and project exporters for various formats."""

from .base import BaseExporter
from .csv_exporter import CSVExporter
from .jira_exporter import JiraExporter
from .linear_exporter import LinearExporter
from .markdown_exporter import MarkdownExporter
from .models import ExportableStory, ExportOptions
from .openspec_exporter import OpenSpecExporter
from .project_exporter_base import ProjectExporter
from .scaffold_exporter import ScaffoldExporter
from .speckit_exporter import SpecKitExporter
from .transformer import (
    get_layer_summary,
    get_stories_by_layer,
    load_stories_from_file,
    load_stories_from_json,
)

__all__ = [
    "ExportableStory",
    "ExportOptions",
    "BaseExporter",
    "ProjectExporter",
    "LinearExporter",
    "JiraExporter",
    "MarkdownExporter",
    "CSVExporter",
    "OpenSpecExporter",
    "ScaffoldExporter",
    "SpecKitExporter",
    "load_stories_from_json",
    "load_stories_from_file",
    "get_stories_by_layer",
    "get_layer_summary",
]

# Story-level exporters (single-file output)
STORY_EXPORTERS: dict[str, type[BaseExporter]] = {
    "linear": LinearExporter,
    "jira": JiraExporter,
    "markdown": MarkdownExporter,
    "csv": CSVExporter,
}

# Project-level exporters (directory tree output)
PROJECT_EXPORTERS: dict[str, type[ProjectExporter]] = {
    "openspec": OpenSpecExporter,
    "speckit": SpecKitExporter,
    "scaffold": ScaffoldExporter,
}


def get_exporter(format_name: str, options: ExportOptions | None = None) -> BaseExporter:
    """Get a story-level exporter instance by format name."""
    format_lower = format_name.lower()
    if format_lower not in STORY_EXPORTERS:
        available = ", ".join(STORY_EXPORTERS.keys())
        raise ValueError(f"Unknown export format: {format_name}. Available: {available}")
    return STORY_EXPORTERS[format_lower](options)
