"""Backlog.md CLI wrapper for Python integration.

Provides a typed interface to backlog.md commands for task management.
All commands are executed via subprocess calls to the backlog CLI.

Prerequisites:
    npm i -g backlog.md
    # or
    brew install backlog-md

Reference: https://github.com/MrLesk/Backlog.md
"""

import logging
import re
import subprocess

logger = logging.getLogger(__name__)
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal


@dataclass
class BacklogTask:
    """Represents a Backlog.md task.

    Attributes:
        id: Task identifier (e.g., "task-1")
        title: Task title
        status: Current status ("To Do", "In Progress", "Done")
        priority: Priority level ("low", "medium", "high")
        description: Detailed task description
        labels: List of labels for categorization
        acceptance_criteria: List of acceptance criteria
        dependencies: List of dependency task IDs
        parent_id: Parent task ID for subtasks
        notes: Implementation notes
        is_draft: Whether task is in draft status
    """

    id: str
    title: str
    status: str = "To Do"
    priority: str = "medium"
    description: str = ""
    labels: list[str] = field(default_factory=list)
    acceptance_criteria: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    parent_id: str | None = None
    notes: str = ""
    is_draft: bool = False


class BacklogCLIError(Exception):
    """Error from Backlog.md CLI execution."""

    def __init__(self, message: str, returncode: int = 1, stderr: str = ""):
        super().__init__(message)
        self.returncode = returncode
        self.stderr = stderr


class BacklogCLI:
    """CLI wrapper for backlog.md commands.

    All commands are executed in the project root directory
    where the backlog folder is located.

    Example:
        cli = BacklogCLI("/path/to/project")

        # Initialize backlog
        cli.init("My Project")

        # Create a task
        task_id = cli.create_task(
            "Implement login",
            description="Add user authentication",
            priority="high",
            labels=["backend", "auth"],
            acceptance_criteria=["Users can log in", "Sessions persist"],
        )

        # Update task status
        cli.update_status(task_id, "In Progress")

        # Complete task
        cli.update_status(task_id, "Done")
        cli.add_notes(task_id, "Implemented with JWT tokens")
    """

    def __init__(self, project_dir: Path | str, backlog_cmd: str = "backlog"):
        """Initialize CLI wrapper.

        Args:
            project_dir: Project root directory containing backlog folder
            backlog_cmd: Path to backlog CLI executable
        """
        self.project_dir = Path(project_dir)
        self.backlog_cmd = backlog_cmd

    def _run(
        self,
        args: list[str],
        capture_output: bool = True,
        check: bool = False,
    ) -> subprocess.CompletedProcess:
        """Execute a backlog command.

        Args:
            args: Command arguments (without 'backlog' prefix)
            capture_output: Whether to capture stdout/stderr
            check: Whether to raise on non-zero exit

        Returns:
            CompletedProcess with command results
        """
        cmd = [self.backlog_cmd] + args
        result = subprocess.run(
            cmd,
            cwd=self.project_dir,
            capture_output=capture_output,
            text=True,
        )

        if check and result.returncode != 0:
            raise BacklogCLIError(
                f"Command failed: {' '.join(cmd)}",
                returncode=result.returncode,
                stderr=result.stderr,
            )

        return result

    # === Initialization ===

    def init(self, project_name: str, skip_ai_setup: bool = True) -> bool:
        """Initialize Backlog.md in the project.

        Args:
            project_name: Name for the project
            skip_ai_setup: Skip AI/MCP integration setup

        Returns:
            True if initialization succeeded
        """
        # Try CLI first with --skip-ai-setup flag
        args = ["init", project_name]
        if skip_ai_setup:
            args.append("--skip-ai-setup")

        result = self._run(args)
        if result.returncode == 0:
            return True

        # Fallback: create folder structure manually if CLI is interactive/fails
        # This enables non-interactive initialization for hosted environments
        return self._init_manually(project_name)

    def _init_manually(self, project_name: str) -> bool:
        """Manually create Backlog.md folder structure.

        Creates the required directories and config file when CLI init
        fails (e.g., in non-interactive environments).

        Args:
            project_name: Name for the project

        Returns:
            True if initialization succeeded
        """
        try:
            backlog_dir = self.project_dir / "backlog"

            # Create required directories
            (backlog_dir / "tasks").mkdir(parents=True, exist_ok=True)
            (backlog_dir / "drafts").mkdir(exist_ok=True)
            (backlog_dir / "completed").mkdir(exist_ok=True)
            (backlog_dir / "archive").mkdir(exist_ok=True)
            (backlog_dir / "decisions").mkdir(exist_ok=True)
            (backlog_dir / "docs").mkdir(exist_ok=True)

            # Create config.yml
            config_content = f"""# Backlog.md Configuration
project_name: "{project_name}"
created_at: "{self._get_timestamp()}"

# Task numbering
next_task_id: 1
next_draft_id: 1

# Status workflow
statuses:
  - "To Do"
  - "In Progress"
  - "Done"

# Priority levels
priorities:
  - high
  - medium
  - low
"""
            config_file = backlog_dir / "config.yml"
            config_file.write_text(config_content, encoding="utf-8")

            return True

        except OSError as e:
            logger.warning("Failed to initialize backlog structure: %s", e)
            return False

    def _get_timestamp(self) -> str:
        """Get current timestamp in ISO format."""
        from datetime import datetime

        return datetime.now().isoformat()

    def is_initialized(self) -> bool:
        """Check if Backlog.md is initialized in the project.

        Returns:
            True if backlog folder exists
        """
        return (self.project_dir / "backlog").exists()

    # === Task Creation ===

    def create_task(
        self,
        title: str,
        *,
        description: str = "",
        priority: Literal["low", "medium", "high"] | None = None,
        labels: list[str] | None = None,
        acceptance_criteria: list[str] | None = None,
        dependencies: list[str] | None = None,
        parent_id: int | str | None = None,
        draft: bool = False,
        status: str | None = None,
    ) -> str | None:
        """Create a new task.

        Args:
            title: Task title
            description: Task description
            priority: Priority level (low, medium, high)
            labels: List of labels for categorization
            acceptance_criteria: List of acceptance criteria
            dependencies: List of dependency task IDs
            parent_id: Parent task ID for subtasks
            draft: Create as draft (requires promotion)
            status: Initial status

        Returns:
            Task ID if successful (e.g., "task-1"), None otherwise
        """
        args = ["task", "create", title]

        if description:
            args.extend(["-d", description])
        if priority:
            args.extend(["--priority", priority])
        if labels:
            args.extend(["-l", ",".join(labels)])
        if acceptance_criteria:
            for ac in acceptance_criteria:
                args.extend(["--ac", ac])
        if dependencies:
            # Normalize dependency format
            dep_ids = []
            for dep in dependencies:
                if dep.startswith("task-"):
                    dep_ids.append(dep)
                else:
                    dep_ids.append(f"task-{dep}")
            args.extend(["--dep", ",".join(dep_ids)])
        if parent_id:
            # Extract numeric ID if needed
            if isinstance(parent_id, str) and parent_id.startswith("task-"):
                parent_id = parent_id.replace("task-", "")
            args.extend(["-p", str(parent_id)])
        if draft:
            args.append("--draft")
        if status:
            args.extend(["-s", status])

        result = self._run(args)
        if result.returncode == 0:
            # Parse task ID from output
            # Expected formats:
            # "Created task-N: Title"
            # "Created draft 3.1: Title"
            match = re.search(r"(?:task-|draft\s+)(\d+(?:\.\d+)?)", result.stdout)
            if match:
                task_num = match.group(1)
                if draft:
                    return f"draft-{task_num}"
                return f"task-{task_num}"

            # Fallback: try to find any number
            match = re.search(r"(\d+)", result.stdout)
            if match:
                if draft:
                    return f"draft-{match.group(1)}"
                return f"task-{match.group(1)}"

        return None

    def create_draft(self, title: str, **kwargs) -> str | None:
        """Create a draft task (shorthand for create_task with draft=True).

        Falls back to manual file creation if CLI fails.

        Args:
            title: Task title
            **kwargs: Additional arguments for create_task

        Returns:
            Draft ID if successful, None otherwise
        """
        # Try CLI first
        result = self.create_task(title, draft=True, **kwargs)
        if result:
            return result

        # Fallback: create draft file manually
        return self._create_draft_manually(title, **kwargs)

    def _create_draft_manually(
        self,
        title: str,
        description: str = "",
        priority: str = "medium",
        labels: list[str] | None = None,
        acceptance_criteria: list[str] | None = None,
        dependencies: list[str] | None = None,
        parent_id: str | None = None,
    ) -> str | None:
        """Manually create a draft file when CLI fails.

        Args:
            title: Task title
            description: Task description
            priority: Priority level
            labels: Task labels
            acceptance_criteria: List of acceptance criteria
            dependencies: List of dependency IDs
            parent_id: Parent task ID for subtasks

        Returns:
            Draft ID if successful, None otherwise
        """
        try:
            drafts_dir = self.project_dir / "backlog" / "drafts"
            drafts_dir.mkdir(parents=True, exist_ok=True)

            # Find next draft ID
            draft_id = self._get_next_draft_id()

            # Build markdown content
            labels_str = ", ".join(labels) if labels else ""
            deps_str = ", ".join(dependencies) if dependencies else ""

            ac_lines = ""
            if acceptance_criteria:
                ac_lines = "\n## Acceptance Criteria\n\n"
                for ac in acceptance_criteria:
                    ac_lines += f"- [ ] {ac}\n"

            parent_line = f"parent: {parent_id}\n" if parent_id else ""

            content = f"""---
title: "{title}"
status: "To Do"
priority: {priority}
labels: [{labels_str}]
dependencies: [{deps_str}]
{parent_line}created: "{self._get_timestamp()}"
---

# {title}

{description}
{ac_lines}
## Notes

"""
            # Write draft file
            draft_file = drafts_dir / f"{draft_id}.md"
            draft_file.write_text(content, encoding="utf-8")

            return f"draft-{draft_id}"

        except OSError as e:
            logger.warning("Failed to create draft task: %s", e)
            return None

    def _get_next_draft_id(self) -> str:
        """Get the next available draft ID."""
        drafts_dir = self.project_dir / "backlog" / "drafts"

        # Find existing draft files
        existing = []
        if drafts_dir.exists():
            for f in drafts_dir.glob("*.md"):
                try:
                    # Parse ID from filename (e.g., "1.md", "2.1.md")
                    name = f.stem
                    if name.isdigit():
                        existing.append(int(name))
                except ValueError:
                    pass

        # Return next ID
        next_id = max(existing, default=0) + 1
        return str(next_id)

    def promote_draft(self, draft_id: str) -> bool:
        """Promote a draft task to the backlog.

        Args:
            draft_id: Draft ID (e.g., "draft-1" or "1.1")

        Returns:
            True if successful
        """
        # Normalize draft ID
        numeric_id = draft_id.replace("draft-", "")
        result = self._run(["draft", "promote", numeric_id])
        return result.returncode == 0

    # === Task Updates ===

    def update_status(self, task_id: str, status: str) -> bool:
        """Update task status.

        Args:
            task_id: Task ID (e.g., "task-1" or "1")
            status: New status ("To Do", "In Progress", "Done")

        Returns:
            True if successful
        """
        numeric_id = self._extract_numeric_id(task_id)
        result = self._run(["task", "edit", numeric_id, "-s", status])
        return result.returncode == 0

    def check_acceptance_criteria(self, task_id: str, criteria_index: int) -> bool:
        """Mark an acceptance criterion as complete.

        Args:
            task_id: Task ID
            criteria_index: 1-based index of criterion to check

        Returns:
            True if successful
        """
        numeric_id = self._extract_numeric_id(task_id)
        result = self._run(["task", "edit", numeric_id, "--check-ac", str(criteria_index)])
        return result.returncode == 0

    def uncheck_acceptance_criteria(self, task_id: str, criteria_index: int) -> bool:
        """Unmark an acceptance criterion.

        Args:
            task_id: Task ID
            criteria_index: 1-based index of criterion to uncheck

        Returns:
            True if successful
        """
        numeric_id = self._extract_numeric_id(task_id)
        result = self._run(["task", "edit", numeric_id, "--uncheck-ac", str(criteria_index)])
        return result.returncode == 0

    def add_notes(self, task_id: str, notes: str) -> bool:
        """Add or replace task notes.

        Args:
            task_id: Task ID
            notes: Notes content

        Returns:
            True if successful
        """
        numeric_id = self._extract_numeric_id(task_id)
        result = self._run(["task", "edit", numeric_id, "--notes", notes])
        return result.returncode == 0

    def append_notes(self, task_id: str, notes: str) -> bool:
        """Append to existing notes.

        Args:
            task_id: Task ID
            notes: Notes to append

        Returns:
            True if successful
        """
        numeric_id = self._extract_numeric_id(task_id)
        result = self._run(["task", "edit", numeric_id, "--append-notes", notes])
        return result.returncode == 0

    def add_label(self, task_id: str, label: str) -> bool:
        """Add a label to a task.

        Note: This appends the label to existing labels.

        Args:
            task_id: Task ID
            label: Label to add

        Returns:
            True if successful
        """
        numeric_id = self._extract_numeric_id(task_id)
        result = self._run(["task", "edit", numeric_id, "-l", label])
        return result.returncode == 0

    def add_dependency(self, task_id: str, dependency_id: str) -> bool:
        """Add a dependency to a task.

        Args:
            task_id: Task ID
            dependency_id: Dependency task ID

        Returns:
            True if successful
        """
        numeric_id = self._extract_numeric_id(task_id)
        dep_id = self._extract_numeric_id(dependency_id)
        result = self._run(["task", "edit", numeric_id, "--dep", f"task-{dep_id}"])
        return result.returncode == 0

    def archive_task(self, task_id: str) -> bool:
        """Archive a completed task.

        Args:
            task_id: Task ID

        Returns:
            True if successful
        """
        numeric_id = self._extract_numeric_id(task_id)
        result = self._run(["task", "archive", numeric_id])
        return result.returncode == 0

    # === Task Queries ===

    def get_task(self, task_id: str) -> BacklogTask | None:
        """Get task details.

        Args:
            task_id: Task ID

        Returns:
            BacklogTask if found, None otherwise
        """
        numeric_id = self._extract_numeric_id(task_id)
        result = self._run(["task", numeric_id, "--plain"])
        if result.returncode == 0:
            return self._parse_task_output(result.stdout, f"task-{numeric_id}")
        return None

    def list_tasks(
        self,
        status: str | None = None,
        parent_id: str | None = None,
        assignee: str | None = None,
    ) -> list[BacklogTask]:
        """List tasks with optional filters.

        Args:
            status: Filter by status
            parent_id: Filter by parent task
            assignee: Filter by assignee

        Returns:
            List of matching tasks
        """
        args = ["task", "list"]
        if status:
            args.extend(["-s", status])
        if parent_id:
            args.extend(["-p", parent_id])
        if assignee:
            args.extend(["-a", assignee])

        result = self._run(args)
        if result.returncode == 0:
            return self._parse_task_list(result.stdout)
        return []

    def list_drafts(self) -> list[BacklogTask]:
        """List all draft tasks.

        Returns:
            List of draft tasks
        """
        result = self._run(["draft", "list"])
        if result.returncode == 0:
            return self._parse_draft_list(result.stdout)
        return []

    def search_tasks(
        self,
        query: str,
        status: str | None = None,
        priority: str | None = None,
    ) -> list[BacklogTask]:
        """Search tasks by keyword.

        Args:
            query: Search query
            status: Filter by status
            priority: Filter by priority

        Returns:
            List of matching tasks
        """
        args = ["search", query]
        if status:
            args.extend(["--status", status])
        if priority:
            args.extend(["--priority", priority])

        result = self._run(args)
        if result.returncode == 0:
            return self._parse_task_list(result.stdout)
        return []

    # === Board Operations ===

    def get_board(self) -> str:
        """Get the Kanban board as text.

        Returns:
            Board representation
        """
        result = self._run(["board"])
        return result.stdout if result.returncode == 0 else ""

    def export_board(self, output_file: str | None = None) -> str | None:
        """Export the board as markdown.

        Args:
            output_file: Optional file path to save export

        Returns:
            Markdown content if successful, None otherwise
        """
        args = ["board", "export"]
        if output_file:
            args.append(output_file)

        result = self._run(args)
        if result.returncode == 0:
            return result.stdout
        return None

    def get_overview(self) -> str:
        """Get project overview with statistics.

        Returns:
            Overview text
        """
        result = self._run(["overview"])
        return result.stdout if result.returncode == 0 else ""

    # === Parsing Helpers ===

    def _extract_numeric_id(self, task_id: str) -> str:
        """Extract numeric ID from task identifier.

        Args:
            task_id: Task ID (e.g., "task-1", "1", "draft-1.1")

        Returns:
            Numeric ID portion
        """
        # Remove common prefixes
        cleaned = task_id.replace("task-", "").replace("draft-", "")
        return cleaned

    def _parse_task_output(self, output: str, task_id: str) -> BacklogTask:
        """Parse task details from CLI output.

        Args:
            output: CLI output text
            task_id: Task ID for the result

        Returns:
            Parsed BacklogTask
        """
        lines = output.strip().split("\n")
        task = BacklogTask(id=task_id, title="")

        current_section = None
        acceptance_criteria = []

        for line in lines:
            stripped = line.strip()

            # Parse key-value fields
            if stripped.startswith("Title:"):
                task.title = stripped.replace("Title:", "").strip()
            elif stripped.startswith("Status:"):
                task.status = stripped.replace("Status:", "").strip()
            elif stripped.startswith("Priority:"):
                task.priority = stripped.replace("Priority:", "").strip()
            elif stripped.startswith("Description:"):
                task.description = stripped.replace("Description:", "").strip()
            elif stripped.startswith("Labels:"):
                labels_str = stripped.replace("Labels:", "").strip()
                if labels_str:
                    task.labels = [lbl.strip() for lbl in labels_str.split(",")]
            elif stripped.startswith("Parent:"):
                parent_str = stripped.replace("Parent:", "").strip()
                if parent_str and parent_str != "None":
                    task.parent_id = parent_str
            elif stripped.startswith("Dependencies:"):
                deps_str = stripped.replace("Dependencies:", "").strip()
                if deps_str and deps_str not in ("None", "[]"):
                    task.dependencies = [d.strip() for d in deps_str.split(",")]

            # Detect section headers
            elif "Acceptance Criteria" in stripped:
                current_section = "ac"
            elif "Notes" in stripped:
                current_section = "notes"
            elif stripped.startswith("##") or stripped.startswith("**"):
                current_section = None

            # Parse section content
            elif current_section == "ac" and stripped.startswith("- "):
                # Remove checkbox markers
                criterion = re.sub(r"^-\s*\[.\]\s*", "", stripped)
                criterion = re.sub(r"^-\s*", "", criterion)
                if criterion:
                    acceptance_criteria.append(criterion)
            elif current_section == "notes" and stripped:
                task.notes += stripped + "\n"

        task.acceptance_criteria = acceptance_criteria
        task.notes = task.notes.strip()

        return task

    def _parse_task_list(self, output: str) -> list[BacklogTask]:
        """Parse task list from CLI output.

        Args:
            output: CLI output text

        Returns:
            List of parsed tasks
        """
        tasks = []
        lines = output.strip().split("\n")

        # Look for task entries in various formats
        # Format 1: "task-N: Title [Status] (Priority)"
        # Format 2: Table format with | separators
        for line in lines:
            stripped = line.strip()

            # Skip empty lines and headers
            if not stripped or stripped.startswith("|--") or stripped.startswith("##"):
                continue

            # Try to parse task-N format
            match = re.match(r"(task-\d+):\s*(.+?)(?:\s*\[(.+?)\])?(?:\s*\((.+?)\))?$", stripped)
            if match:
                task = BacklogTask(
                    id=match.group(1),
                    title=match.group(2).strip(),
                    status=match.group(3) or "To Do",
                    priority=match.group(4) or "medium",
                )
                tasks.append(task)
                continue

            # Try table format: | ID | Title | Status | Priority |
            if "|" in stripped:
                parts = [p.strip() for p in stripped.split("|") if p.strip()]
                if len(parts) >= 2 and re.match(r"task-\d+", parts[0]):
                    task = BacklogTask(
                        id=parts[0],
                        title=parts[1] if len(parts) > 1 else "",
                        status=parts[2] if len(parts) > 2 else "To Do",
                        priority=parts[3] if len(parts) > 3 else "medium",
                    )
                    tasks.append(task)

        return tasks

    def _parse_draft_list(self, output: str) -> list[BacklogTask]:
        """Parse draft list from CLI output.

        Args:
            output: CLI output text

        Returns:
            List of draft tasks
        """
        tasks = []
        lines = output.strip().split("\n")

        for line in lines:
            stripped = line.strip()

            # Draft format: "3.1: Title"
            match = re.match(
                r"(\d+(?:\.\d+)?)[:\s]+(.+?)(?:\s*\[(.+?)\])?(?:\s*\((.+?)\))?$", stripped
            )
            if match:
                task = BacklogTask(
                    id=f"draft-{match.group(1)}",
                    title=match.group(2).strip(),
                    status=match.group(3) or "Draft",
                    priority=match.group(4) or "medium",
                    is_draft=True,
                )
                tasks.append(task)

        return tasks
