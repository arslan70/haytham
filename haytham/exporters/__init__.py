"""Story exporters for various project management tools."""

from .base import BaseExporter
from .csv_exporter import CSVExporter
from .jira_exporter import JiraExporter
from .linear_exporter import LinearExporter
from .markdown_exporter import MarkdownExporter
from .models import ExportableStory, ExportOptions
from .transformer import (
    get_layer_summary,
    get_stories_by_layer,
    load_stories_from_file,
    load_stories_from_json,
)

__all__ = [
    # Models
    "ExportableStory",
    "ExportOptions",
    # Base
    "BaseExporter",
    # Exporters
    "LinearExporter",
    "JiraExporter",
    "MarkdownExporter",
    "CSVExporter",
    # Transformer functions
    "load_stories_from_json",
    "load_stories_from_file",
    "get_stories_by_layer",
    "get_layer_summary",
]

# Registry of available exporters
EXPORTERS = {
    "linear": LinearExporter,
    "jira": JiraExporter,
    "markdown": MarkdownExporter,
    "csv": CSVExporter,
}


def get_exporter(format_name: str, options: ExportOptions | None = None) -> BaseExporter:
    """
    Get an exporter instance by format name.

    Args:
        format_name: One of 'linear', 'jira', 'markdown', 'csv'
        options: Export options

    Returns:
        Exporter instance

    Raises:
        ValueError: If format_name is not recognized
    """
    format_lower = format_name.lower()
    if format_lower not in EXPORTERS:
        available = ", ".join(EXPORTERS.keys())
        raise ValueError(f"Unknown export format: {format_name}. Available: {available}")

    return EXPORTERS[format_lower](options)
