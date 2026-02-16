"""Backlog.md integration for Haytham.

Provides Python wrappers for the Backlog.md CLI tool, enabling
programmatic task management through human-readable markdown files.

Components:
- BacklogCLI: CLI wrapper for backlog commands
- BacklogTask: Data class representing a task
"""

from .cli import BacklogCLI, BacklogTask

__all__ = [
    "BacklogCLI",
    "BacklogTask",
]
