"""Unit tests for Backlog.md CLI wrapper.

Tests the BacklogCLI class and its task management methods.
Uses mocking to simulate CLI commands without requiring actual Backlog.md installation.

Run with: pytest tests/backlog_cli_tests.py -v
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from haytham.backlog.cli import BacklogCLI

# ========== Fixtures ==========


@pytest.fixture
def cli():
    """BacklogCLI instance with a temporary project directory."""
    return BacklogCLI("/tmp/test-project")


@pytest.fixture
def mock_run():
    """Mock subprocess.run for CLI commands."""
    with patch("subprocess.run") as mock:
        yield mock


# ========== Initialization Tests ==========


class TestBacklogCLIInit:
    """Test CLI initialization methods."""

    def test_init_with_path(self):
        """CLI initializes with project directory."""
        cli = BacklogCLI("/path/to/project")
        assert cli.project_dir == Path("/path/to/project")

    def test_init_with_custom_command(self):
        """CLI accepts custom backlog command path."""
        cli = BacklogCLI("/project", backlog_cmd="/usr/local/bin/backlog")
        assert cli.backlog_cmd == "/usr/local/bin/backlog"

    def test_is_initialized_true(self, cli):
        """is_initialized returns True when backlog folder exists."""
        with patch.object(Path, "exists", return_value=True):
            assert cli.is_initialized() is True

    def test_is_initialized_false(self, cli):
        """is_initialized returns False when backlog folder missing."""
        with patch.object(Path, "exists", return_value=False):
            assert cli.is_initialized() is False


# ========== Task Creation Tests ==========


class TestTaskCreation:
    """Test task creation methods."""

    def test_create_task_simple(self, cli, mock_run):
        """create_task creates a simple task."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="Created task-1: Test task",
        )

        task_id = cli.create_task("Test task")

        assert task_id == "task-1"
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert args[:3] == ["backlog", "task", "create"]
        assert "Test task" in args

    def test_create_task_with_options(self, cli, mock_run):
        """create_task includes all options."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="Created task-5: Full task",
        )

        task_id = cli.create_task(
            "Full task",
            description="A detailed description",
            priority="high",
            labels=["backend", "api"],
            acceptance_criteria=["Must work", "Must be tested"],
            dependencies=["task-1", "task-2"],
        )

        assert task_id == "task-5"
        args = mock_run.call_args[0][0]
        assert "-d" in args
        assert "A detailed description" in args
        assert "--priority" in args
        assert "high" in args
        assert "-l" in args
        assert "backend,api" in args
        assert "--ac" in args
        assert "--dep" in args

    def test_create_task_returns_none_on_failure(self, cli, mock_run):
        """create_task returns None on failure."""
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="Error",
        )

        task_id = cli.create_task("Failing task")

        assert task_id is None

    def test_create_draft(self, cli, mock_run):
        """create_draft creates a draft task."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="Created draft 1.1: Draft task",
        )

        draft_id = cli.create_draft("Draft task")

        assert draft_id == "draft-1.1"
        args = mock_run.call_args[0][0]
        assert "--draft" in args

    def test_promote_draft(self, cli, mock_run):
        """promote_draft promotes a draft to backlog."""
        mock_run.return_value = MagicMock(returncode=0)

        result = cli.promote_draft("draft-1.1")

        assert result is True
        args = mock_run.call_args[0][0]
        assert args[:3] == ["backlog", "draft", "promote"]
        assert "1.1" in args


# ========== Task Update Tests ==========


class TestTaskUpdates:
    """Test task update methods."""

    def test_update_status(self, cli, mock_run):
        """update_status changes task status."""
        mock_run.return_value = MagicMock(returncode=0)

        result = cli.update_status("task-5", "In Progress")

        assert result is True
        args = mock_run.call_args[0][0]
        assert "5" in args
        assert "-s" in args
        assert "In Progress" in args

    def test_check_acceptance_criteria(self, cli, mock_run):
        """check_acceptance_criteria marks criterion as done."""
        mock_run.return_value = MagicMock(returncode=0)

        result = cli.check_acceptance_criteria("task-3", 1)

        assert result is True
        args = mock_run.call_args[0][0]
        assert "--check-ac" in args
        assert "1" in args

    def test_add_notes(self, cli, mock_run):
        """add_notes adds notes to task."""
        mock_run.return_value = MagicMock(returncode=0)

        result = cli.add_notes("task-7", "Implementation complete")

        assert result is True
        args = mock_run.call_args[0][0]
        assert "--notes" in args
        assert "Implementation complete" in args

    def test_append_notes(self, cli, mock_run):
        """append_notes appends to existing notes."""
        mock_run.return_value = MagicMock(returncode=0)

        result = cli.append_notes("task-7", "Additional notes")

        assert result is True
        args = mock_run.call_args[0][0]
        assert "--append-notes" in args

    def test_archive_task(self, cli, mock_run):
        """archive_task archives a task."""
        mock_run.return_value = MagicMock(returncode=0)

        result = cli.archive_task("task-10")

        assert result is True
        args = mock_run.call_args[0][0]
        assert args[:3] == ["backlog", "task", "archive"]


# ========== Task Query Tests ==========


class TestTaskQueries:
    """Test task query methods."""

    def test_get_task(self, cli, mock_run):
        """get_task retrieves task details."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="""Title: Test Task
Status: To Do
Priority: high
Description: A test task
Labels: backend, api
""",
        )

        task = cli.get_task("task-1")

        assert task is not None
        assert task.title == "Test Task"
        assert task.status == "To Do"
        assert task.priority == "high"
        assert "backend" in task.labels

    def test_get_task_returns_none_on_failure(self, cli, mock_run):
        """get_task returns None when task not found."""
        mock_run.return_value = MagicMock(returncode=1)

        task = cli.get_task("task-999")

        assert task is None

    def test_list_tasks(self, cli, mock_run):
        """list_tasks returns list of tasks."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="""task-1: First task [To Do] (high)
task-2: Second task [In Progress] (medium)
""",
        )

        tasks = cli.list_tasks()

        assert len(tasks) == 2
        assert tasks[0].id == "task-1"
        assert tasks[0].title == "First task"
        assert tasks[1].status == "In Progress"

    def test_list_tasks_with_filter(self, cli, mock_run):
        """list_tasks applies status filter."""
        mock_run.return_value = MagicMock(returncode=0, stdout="")

        cli.list_tasks(status="In Progress")

        args = mock_run.call_args[0][0]
        assert "-s" in args
        assert "In Progress" in args

    def test_list_drafts(self, cli, mock_run):
        """list_drafts returns draft tasks."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="""1.1: Draft One
1.2: Draft Two
""",
        )

        drafts = cli.list_drafts()

        assert len(drafts) == 2
        assert drafts[0].id == "draft-1.1"
        assert drafts[0].is_draft is True


# ========== Board Operations Tests ==========


class TestBoardOperations:
    """Test board operation methods."""

    def test_get_board(self, cli, mock_run):
        """get_board returns board text."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="| To Do | In Progress | Done |",
        )

        board = cli.get_board()

        assert "To Do" in board

    def test_export_board(self, cli, mock_run):
        """export_board returns markdown export."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="# Board Export\n...",
        )

        export = cli.export_board()

        assert "Board Export" in export

    def test_get_overview(self, cli, mock_run):
        """get_overview returns project statistics."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="Tasks: 10, Completed: 5",
        )

        overview = cli.get_overview()

        assert "Tasks" in overview


# ========== ID Extraction Tests ==========


class TestIDExtraction:
    """Test ID extraction helper."""

    def test_extract_numeric_id_from_task(self, cli):
        """Extracts numeric ID from task-N format."""
        assert cli._extract_numeric_id("task-5") == "5"

    def test_extract_numeric_id_from_draft(self, cli):
        """Extracts numeric ID from draft-N format."""
        assert cli._extract_numeric_id("draft-1.1") == "1.1"

    def test_extract_numeric_id_plain(self, cli):
        """Returns plain numeric ID unchanged."""
        assert cli._extract_numeric_id("7") == "7"


# ========== Task Parsing Tests ==========


class TestTaskParsing:
    """Test task output parsing."""

    def test_parse_task_with_acceptance_criteria(self, cli):
        """Parses task with acceptance criteria."""
        output = """Title: Create Note
Status: To Do
Priority: high

## Acceptance Criteria
- [ ] Note is saved to database
- [x] User receives confirmation
"""

        task = cli._parse_task_output(output, "task-1")

        assert task.title == "Create Note"
        assert len(task.acceptance_criteria) == 2
        assert "Note is saved to database" in task.acceptance_criteria[0]

    def test_parse_task_list_table_format(self, cli):
        """Parses task list in table format."""
        output = """| task-1 | First | To Do | high |
| task-2 | Second | Done | low |
"""

        tasks = cli._parse_task_list(output)

        assert len(tasks) == 2
        assert tasks[0].id == "task-1"
        assert tasks[1].status == "Done"
