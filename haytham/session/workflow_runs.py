"""Workflow run state machine for session management.

Encapsulates workflow lifecycle operations: starting, completing, failing,
locking, and status queries. Operates on workflow_runs.json and .lock files
within the session directory.
"""

import json
import logging
import threading
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import ClassVar

logger = logging.getLogger(__name__)


class WorkflowRunTracker:
    """Tracks workflow run state for a session.

    Args:
        session_dir: Path to the session directory.
    """

    # Canonical mapping of workflow names (including legacy aliases) to lookup keys.
    # Used for workflow_runs.json lookups. Superset of all alias needs.
    WORKFLOW_ALIASES: ClassVar[dict[str, list[str]]] = {
        "discovery": ["discovery", "idea-validation"],
        "idea-validation": ["discovery", "idea-validation"],
        "architect": ["architect", "mvp-specification"],
        "mvp-specification": ["architect", "mvp-specification"],
        "technical-design": ["technical-design"],
        "story-generation": ["story-generation"],
        "implementation": ["implementation"],
    }

    def __init__(self, session_dir: Path) -> None:
        self.session_dir = session_dir
        self._lock = threading.Lock()

    def _get_aliases(self, workflow_type: str) -> list[str]:
        """Return all recognized names for a workflow type.

        Ensures that both legacy ("discovery") and canonical ("idea-validation")
        names match interchangeably when looking up workflow runs.
        """
        return self.WORKFLOW_ALIASES.get(workflow_type, [workflow_type])

    def _read_runs(self) -> list[dict]:
        """Read workflow runs from disk. Caller must hold self._lock."""
        workflow_runs_file = self.session_dir / "workflow_runs.json"
        if not workflow_runs_file.exists():
            return []
        try:
            return json.loads(workflow_runs_file.read_text())
        except json.JSONDecodeError:
            logger.warning("Corrupted workflow_runs.json, returning empty list")
            return []

    def _write_runs(self, runs: list[dict]) -> None:
        """Write workflow runs to disk. Caller must hold self._lock."""
        workflow_runs_file = self.session_dir / "workflow_runs.json"
        workflow_runs_file.write_text(json.dumps(runs, indent=2))

    def lock_workflow(self, workflow_type: str) -> None:
        """Lock a workflow, marking its artifacts as immutable.

        Once locked, a workflow cannot receive further feedback. This is the
        "Accept & Continue" action in the UI. Creates a lock file and updates
        the workflow run status to "accepted".

        Args:
            workflow_type: Type of workflow to lock (e.g., "idea-validation",
                          "mvp-specification", "story-generation")
        """
        # Create lock file with timestamp
        lock_file = self.session_dir / f".{workflow_type}.locked"
        lock_data = {
            "locked_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            "workflow_type": workflow_type,
        }
        lock_file.write_text(json.dumps(lock_data, indent=2))

        # Update workflow run status to "accepted" if there's a completed run
        self._update_workflow_run_status(workflow_type, "accepted")

        logger.info(f"Workflow '{workflow_type}' has been locked")

    def is_workflow_locked(self, workflow_type: str) -> bool:
        """Check if a workflow has been accepted/locked.

        A locked workflow cannot receive further feedback. Users must start
        a new project/iteration to make changes to locked artifacts.

        Args:
            workflow_type: Type of workflow to check

        Returns:
            True if the workflow has been locked, False otherwise
        """
        lock_file = self.session_dir / f".{workflow_type}.locked"
        return lock_file.exists()

    def get_workflow_feedback_state(self, workflow_type: str) -> str:
        """Get the feedback state of a workflow.

        This method determines whether a workflow is available for feedback,
        which is different from the execution status.

        States:
        - "not_started": Workflow has not been run yet
        - "running": Workflow is currently executing
        - "feedback": Workflow complete, awaiting user review (can provide feedback)
        - "accepted": Workflow locked, artifacts immutable (no feedback allowed)

        Args:
            workflow_type: Type of workflow to check

        Returns:
            State string indicating feedback availability
        """
        # Check if locked first (highest priority)
        if self.is_workflow_locked(workflow_type):
            return "accepted"

        aliases = self._get_aliases(workflow_type)

        with self._lock:
            runs = self._read_runs()

        # Find the most recent run for this workflow type
        for run in reversed(runs):
            if run.get("workflow_type") in aliases:
                status = run.get("status", "not_started")
                if status == "completed":
                    return "feedback"
                elif status == "running":
                    return "running"
                elif status == "accepted":
                    return "accepted"

        return "not_started"

    def _update_workflow_run_status(self, workflow_type: str, new_status: str) -> None:
        """Update the status of the most recent workflow run.

        Internal helper to update workflow run status (e.g., to "accepted").
        Acquires self._lock internally.

        Args:
            workflow_type: Type of workflow to update
            new_status: New status to set
        """
        aliases = self._get_aliases(workflow_type)

        with self._lock:
            runs = self._read_runs()
            if not runs:
                return

            for run in reversed(runs):
                if run.get("workflow_type") in aliases:
                    run["status"] = new_status
                    run["status_updated_at"] = datetime.now(UTC).isoformat().replace("+00:00", "Z")
                    self._write_runs(runs)
                    return

    def record_workflow_complete(
        self,
        workflow_type: str,
        summary: dict | None = None,
    ) -> dict:
        """Record workflow completion for handoff to next phase.

        Creates a workflow transition record that captures the completion
        state of a workflow. This is used for audit trail and handoff
        metadata between workflows.

        Args:
            workflow_type: Type of workflow completed ("discovery", "architect")
            summary: Optional summary data to include

        Returns:
            Dict containing the transition record
        """
        run_record = {
            "run_id": str(uuid.uuid4()),
            "workflow_type": workflow_type,
            "status": "completed",
            "completed_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            "summary": summary or {},
        }

        with self._lock:
            runs = self._read_runs()
            runs.append(run_record)
            self._write_runs(runs)

        return run_record

    def is_workflow_complete(self, workflow_type: str) -> bool:
        """Check if a specific workflow has been completed.

        Args:
            workflow_type: Type of workflow to check. Accepts both:
                - New format: "idea-validation", "mvp-specification", "story-generation"
                - Legacy format: "discovery", "architect"

        Returns:
            True if the workflow has a completion record
        """
        aliases = self._get_aliases(workflow_type)

        with self._lock:
            runs = self._read_runs()

        return any(
            r.get("workflow_type") in aliases and r.get("status") == "completed" for r in runs
        )

    def get_workflow_status(self, workflow_type: str) -> str:
        """Get the status of a specific workflow.

        Args:
            workflow_type: Type of workflow ("idea-validation", "mvp-specification", etc.)

        Returns:
            Status string: "not_started", "in_progress", "completed"
        """
        aliases = self._get_aliases(workflow_type)

        with self._lock:
            runs = self._read_runs()

        for run in reversed(runs):
            if run.get("workflow_type") in aliases:
                status = run.get("status", "not_started")
                if status == "completed":
                    return "completed"
                elif status == "running":
                    return "in_progress"
        return "not_started"

    def get_current_workflow(self) -> str | None:
        """Get the workflow currently in progress.

        Returns:
            Workflow type string if a workflow is in progress, None otherwise
        """
        with self._lock:
            runs = self._read_runs()

        for run in reversed(runs):
            if run.get("status") == "running":
                return run.get("workflow_type")
        return None

    def start_workflow_run(
        self,
        workflow_type: str,
        trigger_type: str = "user_initiated",
    ) -> dict:
        """Start a new workflow run and record it.

        Args:
            workflow_type: Type of workflow ("idea-validation", "mvp-specification", etc.)
            trigger_type: What triggered this run ("user_initiated", "auto_continue")

        Returns:
            Dict containing the new run record
        """
        run_record = {
            "run_id": str(uuid.uuid4()),
            "workflow_type": workflow_type,
            "status": "running",
            "started_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            "trigger": {
                "type": trigger_type,
            },
        }

        with self._lock:
            runs = self._read_runs()
            runs.append(run_record)
            self._write_runs(runs)

        return run_record

    def complete_workflow_run(
        self,
        workflow_type: str,
        summary: dict | None = None,
    ) -> dict | None:
        """Mark the current workflow run as completed.

        Args:
            workflow_type: Type of workflow that completed
            summary: Optional summary data to include

        Returns:
            Updated run record, or None if no running workflow found
        """
        aliases = self._get_aliases(workflow_type)

        with self._lock:
            runs = self._read_runs()
            if not runs:
                return None

            for run in reversed(runs):
                if run.get("workflow_type") in aliases and run.get("status") == "running":
                    run["status"] = "completed"
                    run["completed_at"] = datetime.now(UTC).isoformat().replace("+00:00", "Z")
                    if summary:
                        run["summary"] = summary
                    self._write_runs(runs)
                    return run

        return None

    def fail_workflow_run(
        self,
        workflow_type: str,
        error_message: str,
    ) -> dict | None:
        """Mark the current workflow run as failed.

        Args:
            workflow_type: Type of workflow that failed
            error_message: Error message describing the failure

        Returns:
            Updated run record, or None if no running workflow found
        """
        aliases = self._get_aliases(workflow_type)

        with self._lock:
            runs = self._read_runs()
            if not runs:
                return None

            for run in reversed(runs):
                if run.get("workflow_type") in aliases and run.get("status") == "running":
                    run["status"] = "failed"
                    run["failed_at"] = datetime.now(UTC).isoformat().replace("+00:00", "Z")
                    run["error"] = error_message
                    self._write_runs(runs)
                    return run

        return None

    def clear_runs(self, workflow_type: str) -> None:
        """Remove all run records for a specific workflow type.

        Used when clearing a workflow for re-run. Respects alias mapping
        so clearing "discovery" also removes "idea-validation" records.

        Args:
            workflow_type: Type of workflow to clear runs for
        """
        aliases = set(self._get_aliases(workflow_type))

        with self._lock:
            runs = self._read_runs()
            if not runs:
                return
            filtered = [r for r in runs if r.get("workflow_type") not in aliases]
            self._write_runs(filtered)
