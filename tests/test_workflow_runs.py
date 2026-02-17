"""Tests for WorkflowRunTracker thread safety and clear_runs.

Covers:
- Lock attribute exists (C1 structural check)
- clear_runs() removes records by workflow type
- clear_runs() respects alias mapping
- clear_runs() is a no-op when file doesn't exist
"""

import threading

import pytest

from haytham.session.workflow_runs import WorkflowRunTracker


@pytest.fixture
def tracker(tmp_path):
    """Create a WorkflowRunTracker with a temporary session directory."""
    return WorkflowRunTracker(tmp_path)


class TestThreadSafety:
    """C1: Verify thread safety infrastructure."""

    def test_lock_attribute_exists(self, tracker):
        """WorkflowRunTracker has a threading.Lock instance."""
        assert hasattr(tracker, "_lock")
        assert isinstance(tracker._lock, type(threading.Lock()))

    def test_read_write_helpers_exist(self, tracker):
        """_read_runs and _write_runs helpers are available."""
        assert callable(getattr(tracker, "_read_runs", None))
        assert callable(getattr(tracker, "_write_runs", None))

    def test_read_runs_empty_when_no_file(self, tracker):
        """_read_runs returns [] when workflow_runs.json doesn't exist."""
        assert tracker._read_runs() == []

    def test_write_then_read_roundtrip(self, tracker):
        """_write_runs and _read_runs round-trip correctly."""
        runs = [{"run_id": "abc", "workflow_type": "discovery", "status": "completed"}]
        tracker._write_runs(runs)
        assert tracker._read_runs() == runs


class TestClearRuns:
    """C1: Tests for clear_runs() method."""

    def test_clear_runs_removes_matching_type(self, tracker):
        """clear_runs removes records matching the workflow type."""
        tracker.start_workflow_run("idea-validation")
        tracker.start_workflow_run("mvp-specification")

        tracker.clear_runs("idea-validation")

        runs = tracker._read_runs()
        types = [r["workflow_type"] for r in runs]
        assert "idea-validation" not in types
        assert "mvp-specification" in types

    def test_clear_runs_respects_aliases(self, tracker):
        """clear_runs("discovery") also removes "idea-validation" records."""
        tracker.start_workflow_run("idea-validation")
        tracker.start_workflow_run("discovery")
        tracker.start_workflow_run("mvp-specification")

        tracker.clear_runs("discovery")

        runs = tracker._read_runs()
        types = [r["workflow_type"] for r in runs]
        assert "idea-validation" not in types
        assert "discovery" not in types
        assert "mvp-specification" in types

    def test_clear_runs_noop_when_no_file(self, tracker):
        """clear_runs is a no-op when workflow_runs.json doesn't exist."""
        tracker.clear_runs("idea-validation")  # Should not raise

    def test_clear_runs_noop_when_no_matching_type(self, tracker):
        """clear_runs preserves all records when type doesn't match."""
        tracker.start_workflow_run("mvp-specification")

        tracker.clear_runs("story-generation")

        runs = tracker._read_runs()
        assert len(runs) == 1
        assert runs[0]["workflow_type"] == "mvp-specification"
