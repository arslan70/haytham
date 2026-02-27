"""Tests for path traversal prevention in ProjectManager."""

import pytest

from haytham.project.project_manager import ProjectManager


@pytest.fixture
def pm(tmp_path):
    return ProjectManager(base_dir=tmp_path)


def test_delete_project_rejects_path_traversal(pm):
    """Path traversal in project_id must raise ValueError."""
    with pytest.raises(ValueError, match="Invalid project ID"):
        pm.delete_project("../../etc")


def test_delete_project_rejects_absolute_path(pm):
    """Absolute paths in project_id must raise ValueError."""
    with pytest.raises(ValueError, match="Invalid project ID"):
        pm.delete_project("/etc/passwd")


def test_delete_project_accepts_valid_id(pm, tmp_path):
    """Normal project IDs should work."""
    project_dir = tmp_path / "my_project"
    project_dir.mkdir()
    pm.delete_project("my_project")
    assert not project_dir.exists()
