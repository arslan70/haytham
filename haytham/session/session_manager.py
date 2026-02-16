"""Session management for single-project, meta-recursive Haytham.

This module provides session management for the simplified single-session architecture.
It replaces both ProjectManager and CheckpointManager with a unified, simpler API.

The system goal is stored in project.yaml as the single source of truth.
"""

import json
import logging
import shutil
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, ClassVar

from haytham.agents.output_utils import extract_output_content
from haytham.config import (
    DEFAULT_WORKFLOW_PHASE,
    METADATA_FILES,
    StageStatus,
    WorkflowPhase,
)
from haytham.project.project_state import ProjectStateManager
from haytham.workflow.stage_registry import (
    STAGES,
    WorkflowType,
    get_stage_by_slug,
    get_stage_registry,
)

logger = logging.getLogger(__name__)


class SessionManager:
    """Manages the single active session for the meta-recursive system.

    The SessionManager handles:
    - Single session creation and management (no project_id or session_id)
    - Stage checkpoint saving and loading (using stage slugs)
    - Agent output persistence
    - Session resume and recovery
    - Session archival

    Directory Structure:
        session/                          # Singular - ONE persistent project
        ├── project.yaml                  # System goal and project state
        ├── session_manifest.md
        ├── preferences.json
        ├── idea-refinement/
        │   ├── checkpoint.md
        │   ├── concept_expansion.md
        │   └── user_feedback.md
        ├── market-analysis/
        │   ├── checkpoint.md
        │   ├── market_intelligence.md
        │   ├── competitor_analysis.md
        │   └── user_feedback.md
        ├── mvp-specification/            # MVP spec (after workflow completes)
        │   └── mvp_spec.md
        └── ...
        outputs/                          # Final requirements documents
        └── requirements_{timestamp}.md

    Note: Archive functionality has been removed. The system operates with a
    single persistent project that remains active for MVP specification.
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

    def __init__(self, base_dir: str = "."):
        """Initialize the SessionManager.

        Args:
            base_dir: Base directory for session and outputs (default: ".")
        """
        self.base_dir = Path(base_dir)
        self.session_dir = self.base_dir / "session"
        self.archive_dir = self.base_dir / "archive"  # Kept for backwards compat
        self.outputs_dir = self.base_dir / "outputs"

        # Ensure directories exist
        self.session_dir.mkdir(parents=True, exist_ok=True)
        # Note: archive_dir creation removed - no longer archiving sessions
        self.outputs_dir.mkdir(parents=True, exist_ok=True)

        # Initialize ProjectStateManager for system goal management
        self.project_state = ProjectStateManager(self.session_dir)

    def has_system_goal(self) -> bool:
        """Check if a system goal has been set.

        Returns:
            True if a system goal exists in project.yaml, False otherwise
        """
        return self.project_state.has_system_goal()

    def get_system_goal(self) -> str | None:
        """Get the system goal from project state.

        Returns:
            The system goal string, or None if not set
        """
        return self.project_state.get_system_goal()

    def set_system_goal(self, goal: str) -> None:
        """Set the system goal in project state.

        Args:
            goal: The system goal string provided by the user
        """
        self.project_state.set_system_goal(goal)

    def has_active_session(self) -> bool:
        """Check if an incomplete session exists.

        Returns:
            True if an incomplete session exists, False otherwise
        """
        manifest_path = self.session_dir / "session_manifest.md"
        if not manifest_path.exists():
            return False

        try:
            session = self._parse_manifest(manifest_path.read_text())
            return session.get("status") == "in_progress"
        except (OSError, ValueError, KeyError) as e:
            logger.warning("Failed to read session manifest: %s", e)
            return False

    def create_session(self) -> dict[str, Any]:
        """Create a new session (clears any existing session directory).

        Preserves project.yaml which contains the system goal.
        Creates stage directories using slugs (idea-refinement/, market-analysis/, etc.)

        Returns:
            Dict containing session metadata
        """
        # Preserve project.yaml before clearing session directory
        project_yaml_path = self.session_dir / "project.yaml"
        project_yaml_content = None
        if project_yaml_path.exists():
            project_yaml_content = project_yaml_path.read_text()

        # Clear existing session directory
        if self.session_dir.exists():
            shutil.rmtree(self.session_dir)
        self.session_dir.mkdir(parents=True, exist_ok=True)

        # Restore project.yaml if it existed
        if project_yaml_content is not None:
            project_yaml_path.write_text(project_yaml_content)

        # Re-initialize ProjectStateManager after directory recreation
        self.project_state = ProjectStateManager(self.session_dir)

        # Create stage directories using slugs
        for stage in STAGES:
            stage_dir = self.session_dir / stage.slug
            stage_dir.mkdir(exist_ok=True)

        # Get system goal from project state (may be None if not set yet)
        system_goal = self.project_state.get_system_goal()

        # Create session manifest
        now = datetime.now(UTC).isoformat().replace("+00:00", "Z")
        self._create_manifest(now, system_goal)

        # Create empty preferences file
        preferences_path = self.session_dir / "preferences.json"
        preferences_path.write_text(json.dumps({}, indent=2))

        return {
            "status": "in_progress",
            "created": now,
            "system_goal": system_goal,  # May be None if not set yet
        }

    def load_session(self) -> dict[str, Any] | None:
        """Load current session state from manifest.

        Returns:
            Dict containing session state, or None if no session exists
        """
        manifest_path = self.session_dir / "session_manifest.md"
        if not manifest_path.exists():
            return None

        try:
            return self._parse_manifest(manifest_path.read_text())
        except (OSError, ValueError, KeyError) as e:
            logger.warning("Failed to parse session manifest: %s", e)
            return None

    def clear_workflow_stages(self, workflow_type: str) -> None:
        """Clear all stage directories for a specific workflow.

        Preserves project.yaml but clears stage outputs for re-running.
        Used when a user wants to refine their idea and re-run validation.

        Args:
            workflow_type: Type of workflow to clear (e.g., "idea-validation")
        """
        try:
            wf_type = WorkflowType(workflow_type)
            stages = get_stage_registry().get_workflow_stage_slugs(wf_type)
        except ValueError:
            logger.warning("Unknown workflow type for clearing: %s", workflow_type)
            stages = []
        for stage_slug in stages:
            stage_dir = self.session_dir / stage_slug
            if stage_dir.exists():
                shutil.rmtree(stage_dir)

        # Clear workflow lock
        lock_file = self.session_dir / f".{workflow_type}.locked"
        if lock_file.exists():
            lock_file.unlink()

        # Remove workflow run records for this workflow type
        self._clear_workflow_runs(workflow_type)

        logger.info(f"Cleared stages for workflow '{workflow_type}'")

    def _clear_workflow_runs(self, workflow_type: str) -> None:
        """Clear workflow run records for a specific workflow type.

        Args:
            workflow_type: Type of workflow to clear runs for
        """
        workflow_runs_file = self.session_dir / "workflow_runs.json"
        if not workflow_runs_file.exists():
            return

        try:
            runs = json.loads(workflow_runs_file.read_text())
            # Filter out runs for this workflow type
            filtered_runs = [r for r in runs if r.get("workflow_type") != workflow_type]
            workflow_runs_file.write_text(json.dumps(filtered_runs, indent=2))
        except json.JSONDecodeError:
            pass

    def save_checkpoint(
        self,
        stage_slug: str,
        status: str,
        agents: list[dict[str, Any]],
        started: str | None = None,
        completed: str | None = None,
        duration: float | None = None,
        retry_count: int = 0,
        execution_mode: str = "single",
        errors: list[str] | None = None,
    ) -> None:
        """Save a stage checkpoint.

        Args:
            stage_slug: Stage slug (e.g., "idea-refinement")
            status: Stage status (pending, in_progress, completed, failed, skipped)
            agents: List of agent execution details
            started: ISO 8601 timestamp when stage started
            completed: ISO 8601 timestamp when stage completed
            duration: Stage duration in seconds
            retry_count: Number of retry attempts
            execution_mode: Execution mode (single, parallel, sequential_interactive)
            errors: List of error messages (if any)

        Raises:
            ValueError: If stage_slug is invalid or status is invalid
            FileNotFoundError: If session directory does not exist
        """
        # Validate stage slug
        try:
            stage = get_stage_by_slug(stage_slug)
        except ValueError as e:
            raise ValueError(f"Invalid stage_slug: {stage_slug}") from e

        # Validate status using enum
        valid_statuses = StageStatus.values()
        if status not in valid_statuses:
            raise ValueError(f"status must be one of {valid_statuses}, got: {status}")

        if not self.session_dir.exists():
            raise FileNotFoundError(f"Session directory not found: {self.session_dir}")

        stage_dir = self.session_dir / stage_slug
        stage_dir.mkdir(exist_ok=True)

        # Create checkpoint content
        checkpoint_content = self._format_checkpoint(
            stage_slug=stage_slug,
            stage_name=stage.display_name,
            status=status,
            started=started,
            completed=completed,
            duration=duration,
            retry_count=retry_count,
            execution_mode=execution_mode,
            agents=agents,
            errors=errors or [],
        )

        # Write checkpoint file
        checkpoint_path = stage_dir / "checkpoint.md"
        checkpoint_path.write_text(checkpoint_content)

        # Update session manifest
        self._update_manifest(stage_slug, status, started, completed, duration)

    def save_agent_output(
        self,
        stage_slug: str,
        agent_name: str,
        output_content: str,
        status: str = "completed",
        duration: float | None = None,
        model: str | None = None,
        input_tokens: int | None = None,
        output_tokens: int | None = None,
        tools_used: list[str] | None = None,
        error_type: str | None = None,
        error_message: str | None = None,
        stack_trace: str | None = None,
    ) -> None:
        """Save agent output to a markdown file.

        Args:
            stage_slug: Stage slug (e.g., "idea-refinement")
            agent_name: Name of the agent
            output_content: The agent's output content
            status: Agent status (completed, failed)
            duration: Execution duration in seconds
            model: Model identifier used
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            tools_used: List of tools used by the agent
            error_type: Error type (if failed)
            error_message: Error message (if failed)
            stack_trace: Stack trace (if failed)

        Raises:
            ValueError: If stage_slug is invalid
            FileNotFoundError: If stage directory does not exist
        """
        # Validate stage slug
        try:
            stage = get_stage_by_slug(stage_slug)
        except ValueError as e:
            raise ValueError(f"Invalid stage_slug: {stage_slug}") from e

        stage_dir = self.session_dir / stage_slug

        if not stage_dir.exists():
            raise FileNotFoundError(f"Stage directory not found: {stage_dir}")

        # Create agent output content
        now = datetime.now(UTC).isoformat().replace("+00:00", "Z")
        agent_output = self._format_agent_output(
            agent_name=agent_name,
            stage_slug=stage_slug,
            stage_name=stage.display_name,
            executed=now,
            duration=duration,
            status=status,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            tools_used=tools_used or [],
            output_content=output_content,
            error_type=error_type,
            error_message=error_message,
            stack_trace=stack_trace,
        )

        # Write agent output file
        output_path = stage_dir / f"{agent_name}.md"
        output_path.write_text(agent_output)

    def save_user_feedback(
        self,
        stage_slug: str,
        feedback: dict[str, Any],
    ) -> None:
        """Save user feedback for a stage.

        Args:
            stage_slug: Stage slug (e.g., "idea-refinement")
            feedback: Dict containing feedback data with keys:
                - reviewed: bool
                - approved: bool
                - comments: str (optional)
                - requested_changes: list[str] (optional)
                - action: str (optional, default: "approved")
                - retry_count: int (optional, default: 0)

        Raises:
            ValueError: If stage_slug is invalid
            FileNotFoundError: If stage directory does not exist
        """
        # Validate stage slug
        try:
            stage = get_stage_by_slug(stage_slug)
        except ValueError as e:
            raise ValueError(f"Invalid stage_slug: {stage_slug}") from e

        stage_dir = self.session_dir / stage_slug

        if not stage_dir.exists():
            raise FileNotFoundError(f"Stage directory not found: {stage_dir}")

        # Extract feedback fields with defaults
        reviewed = feedback.get("reviewed", True)
        approved = feedback.get("approved", False)
        comments = feedback.get("comments", "")
        requested_changes = feedback.get("requested_changes", [])
        action = feedback.get("action", "approved" if approved else "pending")
        retry_count = feedback.get("retry_count", 0)

        # Create user feedback content
        now = datetime.now(UTC).isoformat().replace("+00:00", "Z")
        feedback_content = self._format_user_feedback(
            stage_name=stage.display_name,
            reviewed=reviewed,
            approved=approved,
            timestamp=now,
            comments=comments,
            requested_changes=requested_changes,
            action=action,
            retry_count=retry_count,
        )

        # Write user feedback file
        feedback_path = stage_dir / "user_feedback.md"
        feedback_path.write_text(feedback_content)

    def get_stage_outputs(self, stage_slugs: list[str] | None = None) -> dict[str, dict[str, str]]:
        """Load agent outputs from specified stages.

        Args:
            stage_slugs: List of stage slugs to load (None = all completed stages)

        Returns:
            Dict mapping stage_slug to dict of agent_name -> output_content
        """
        if not self.session_dir.exists():
            return {}

        # If no stage_slugs specified, load all completed stages
        if stage_slugs is None:
            session_state = self.load_session()
            if session_state:
                stage_slugs = session_state.get("completed_stages", [])
            else:
                stage_slugs = []

        outputs = {}

        for stage_slug in stage_slugs:
            # Validate stage slug exists
            try:
                get_stage_by_slug(stage_slug)
            except ValueError:
                continue

            stage_dir = self.session_dir / stage_slug

            if not stage_dir.exists():
                continue

            stage_outputs = {}

            # Load all .md files except metadata files
            for output_file in stage_dir.glob("*.md"):
                if output_file.name in METADATA_FILES:
                    continue

                agent_name = output_file.stem
                content = output_file.read_text()

                # Extract just the output content (skip metadata)
                output_content = extract_output_content(content)
                stage_outputs[agent_name] = output_content

            if stage_outputs:
                outputs[stage_slug] = stage_outputs

        return outputs

    def get_approved_stages(self) -> list[str]:
        """Get list of stages that have been approved by the user.

        A stage is considered approved if:
        1. It has a stage directory
        2. It has a user_feedback.md file
        3. The feedback file shows Approved: true

        Returns:
            List of approved stage slugs in workflow order
        """
        if not self.session_dir.exists():
            return []

        approved_stages = []

        # Check each stage directory in workflow order
        for stage in STAGES:
            stage_dir = self.session_dir / stage.slug
            feedback_file = stage_dir / "user_feedback.md"

            # Check if directory and feedback file exist
            if stage_dir.exists() and feedback_file.exists():
                try:
                    feedback_content = feedback_file.read_text()
                    # Look for "- Approved: true" line
                    if "- Approved: true" in feedback_content:
                        approved_stages.append(stage.slug)
                except OSError as e:
                    logger.debug("Cannot read feedback for %s: %s", stage.slug, e)

        return approved_stages

    def get_next_stage(self) -> str | None:
        """Get the next stage to execute.

        Returns:
            Next stage slug to execute, or None if all stages complete
        """
        approved = set(self.get_approved_stages())

        for stage in STAGES:
            if stage.slug not in approved:
                return stage.slug

        return None  # All stages complete

    def archive_session(self, status: str = "completed") -> str:
        """DEPRECATED: Archive functionality is no longer used.

        The system now operates with a single persistent project.
        Sessions are not archived - they remain active for MVP specification
        and future iterations.

        This method is kept for backwards compatibility but does nothing.

        Args:
            status: Status to include in archive name (ignored)

        Returns:
            Empty string (no archive created)
        """
        logger.warning(
            "archive_session() is deprecated. Sessions are no longer archived. "
            "The project remains active for MVP specification."
        )
        return ""

    def save_final_output(self, requirements_content: str) -> str:
        """Save final requirements document to outputs directory.

        Args:
            requirements_content: The generated requirements.md content

        Returns:
            Path to the saved requirements file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = self.outputs_dir / f"requirements_{timestamp}.md"
        output_path.write_text(requirements_content)

        # Also save as latest
        latest_path = self.outputs_dir / "latest_requirements.md"
        latest_path.write_text(requirements_content)

        return str(output_path)

    def save_preferences(self, preferences: dict[str, Any]) -> None:
        """Save user preferences to session.

        Args:
            preferences: Dict of user preferences
        """
        preferences_path = self.session_dir / "preferences.json"

        # Load existing preferences and merge
        existing = {}
        if preferences_path.exists():
            try:
                existing = json.loads(preferences_path.read_text())
            except (OSError, json.JSONDecodeError) as e:
                logger.warning("Failed to load preferences, starting fresh: %s", e)

        existing.update(preferences)
        existing["updated_at"] = datetime.now(UTC).isoformat().replace("+00:00", "Z")

        preferences_path.write_text(json.dumps(existing, indent=2))

    def load_preferences(self) -> dict[str, Any]:
        """Load user preferences from session.

        Returns:
            Dict of user preferences
        """
        preferences_path = self.session_dir / "preferences.json"
        if not preferences_path.exists():
            return {}

        try:
            return json.loads(preferences_path.read_text())
        except (OSError, json.JSONDecodeError) as e:
            logger.warning("Failed to read preferences: %s", e)
            return {}

    def has_mvp_spec(self) -> bool:
        """Check if an MVP specification has been created and accepted.

        Returns:
            True if MVP spec exists and was accepted, False otherwise
        """
        mvp_spec_path = self.get_mvp_spec_path()
        accepted_marker = self.session_dir / "mvp-specification" / ".accepted"
        return mvp_spec_path is not None and accepted_marker.exists()

    def get_mvp_spec_path(self) -> Path | None:
        """Get the path to the MVP specification file.

        Returns:
            Path to MVP spec if it exists, None otherwise
        """
        mvp_dir = self.session_dir / "mvp-specification"
        # Check for both possible filenames
        for filename in ["mvp_specification.md", "mvp_spec.md"]:
            mvp_spec_path = mvp_dir / filename
            if mvp_spec_path.exists():
                return mvp_spec_path
        return None

    def get_mvp_spec_content(self) -> str | None:
        """Get the content of the MVP specification.

        Returns:
            Content of mvp_spec.md if it exists, None otherwise
        """
        mvp_spec_path = self.get_mvp_spec_path()
        if mvp_spec_path:
            try:
                return mvp_spec_path.read_text(encoding="utf-8")
            except OSError as e:
                logger.warning("Failed to read MVP spec at %s: %s", mvp_spec_path, e)
                return None
        return None

    def mark_mvp_spec_accepted(self) -> None:
        """Mark the MVP specification as accepted.

        Creates a marker file to indicate the MVP spec has been accepted.
        """
        mvp_spec_dir = self.session_dir / "mvp-specification"
        mvp_spec_dir.mkdir(parents=True, exist_ok=True)
        accepted_marker = mvp_spec_dir / ".accepted"
        accepted_marker.write_text(datetime.now(UTC).isoformat().replace("+00:00", "Z"))

    def is_mvp_spec_accepted(self) -> bool:
        """Check if the MVP specification has been accepted.

        Returns:
            True if MVP spec has been accepted, False otherwise
        """
        accepted_marker = self.session_dir / "mvp-specification" / ".accepted"
        return accepted_marker.exists()

    def is_technical_design_complete(self) -> bool:
        """Check if the Technical Design workflow (Phase 3: HOW) is complete.

        Returns:
            True if Technical Design workflow is complete, False otherwise
        """
        return self.is_workflow_locked("technical-design") or self.is_workflow_complete(
            "technical-design"
        )

    def has_backlog_tasks_generated(self) -> bool:
        """Check if Backlog.md tasks have been generated.

        Returns:
            True if Backlog tasks have been generated, False otherwise
        """
        backlog_marker = self.session_dir / ".backlog_generated"
        return backlog_marker.exists()

    def mark_backlog_tasks_generated(self, task_count: int = 0) -> None:
        """Mark that Backlog.md tasks have been generated.

        Creates a marker file to track task generation.

        Args:
            task_count: Number of tasks created
        """
        backlog_marker = self.session_dir / ".backlog_generated"
        marker_data = {
            "generated_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            "task_count": task_count,
        }
        backlog_marker.write_text(json.dumps(marker_data, indent=2))

    # =========================================================================
    # ADR-004: Multi-Phase Workflow Support
    # =========================================================================

    # =========================================================================
    # Workflow Locking (Feedback Mechanism Support)
    # =========================================================================

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

        # Check workflow run status
        workflow_runs_file = self.session_dir / "workflow_runs.json"
        if not workflow_runs_file.exists():
            return "not_started"

        # Map legacy names for lookup
        aliases = self.WORKFLOW_ALIASES.get(workflow_type, [workflow_type])

        try:
            runs = json.loads(workflow_runs_file.read_text())

            # Find the most recent run for this workflow type
            for run in reversed(runs):
                if run.get("workflow_type") in aliases:
                    status = run.get("status", "not_started")
                    if status == "completed":
                        # Completed but not locked = feedback phase
                        return "feedback"
                    elif status == "running":
                        return "running"
                    elif status == "accepted":
                        return "accepted"

            return "not_started"
        except json.JSONDecodeError:
            return "not_started"

    def _update_workflow_run_status(self, workflow_type: str, new_status: str) -> None:
        """Update the status of the most recent workflow run.

        Internal helper to update workflow run status (e.g., to "accepted").

        Args:
            workflow_type: Type of workflow to update
            new_status: New status to set
        """
        workflow_runs_file = self.session_dir / "workflow_runs.json"
        if not workflow_runs_file.exists():
            return

        try:
            runs = json.loads(workflow_runs_file.read_text())

            # Find and update the most recent completed run of this type
            for run in reversed(runs):
                if run.get("workflow_type") == workflow_type:
                    run["status"] = new_status
                    run["status_updated_at"] = datetime.now(UTC).isoformat().replace("+00:00", "Z")
                    workflow_runs_file.write_text(json.dumps(runs, indent=2))
                    return

        except json.JSONDecodeError:
            pass

    # =========================================================================

    def get_workflow_phase(self) -> str:
        """Get the current workflow phase.

        Workflow phases (from ADR-005):
        - "discovery": Workflow 1 - Discovery & Validation (Product Owner role)
        - "architect": Workflow 2 - Technical Translation (Software Architect role)
        - "implementation": Workflow 3 - Implementation (Coding Agent role)

        Returns:
            Current workflow phase string, defaults to DEFAULT_WORKFLOW_PHASE
        """
        phase_file = self.session_dir / ".workflow_phase"
        if phase_file.exists():
            try:
                data = json.loads(phase_file.read_text())
                return data.get("phase", DEFAULT_WORKFLOW_PHASE)
            except (json.JSONDecodeError, KeyError):
                pass
        return DEFAULT_WORKFLOW_PHASE

    def set_workflow_phase(self, phase: str) -> None:
        """Set the current workflow phase.

        Args:
            phase: One of "discovery", "architect", "implementation"

        Raises:
            ValueError: If phase is not valid
        """
        valid_phases = WorkflowPhase.values()
        if phase not in valid_phases:
            raise ValueError(f"Invalid workflow phase: {phase}. Must be one of {valid_phases}")

        phase_file = self.session_dir / ".workflow_phase"
        data = {
            "phase": phase,
            "updated_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        }
        phase_file.write_text(json.dumps(data, indent=2))

    def get_phase(self) -> str:
        """Get the current phase in the four-phase workflow.

        Phases (from ADR-016):
        - "WHY": Phase 1 - Idea Validation (is the idea worth pursuing?)
        - "WHAT": Phase 2 - MVP Specification (what should we build?)
        - "HOW": Phase 3 - Technical Design (how should we build it?)
        - "STORIES": Phase 4 - Story Generation (what are the tasks?)

        Returns:
            Current phase name as string
        """
        # Check phases in order - return the first incomplete phase
        if not self.is_workflow_locked("idea-validation"):
            return "WHY"
        if not self.is_workflow_locked("mvp-specification"):
            return "WHAT"
        if not self.is_workflow_locked("technical-design"):
            return "HOW"
        return "STORIES"

    def load_stage_output(self, stage_slug: str) -> str | None:
        """Load the combined output from a completed stage.

        This method reads all agent output files from a stage directory
        and combines them into a single string. Used for passing upstream
        context to subsequent workflows (e.g., mvp_scope to Workflow 2).

        Args:
            stage_slug: Stage slug (e.g., "mvp-scope", "validation-summary")

        Returns:
            Combined agent outputs as string, or None if stage not found
        """
        stage_dir = self.session_dir / stage_slug
        if not stage_dir.exists():
            return None

        outputs = []
        # Sort to ensure consistent ordering
        for agent_file in sorted(stage_dir.glob("*.md")):
            # Skip metadata files
            if agent_file.name in METADATA_FILES:
                continue

            try:
                content = agent_file.read_text()
                # Extract just the output content (skip metadata headers)
                output_content = extract_output_content(content)
                if output_content.strip():
                    outputs.append(output_content)
            except (OSError, ValueError) as e:
                logger.debug("Skipping unreadable agent file %s: %s", agent_file, e)
                continue

        return "\n\n---\n\n".join(outputs) if outputs else None

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
        workflow_runs_file = self.session_dir / "workflow_runs.json"

        # Load existing runs
        if workflow_runs_file.exists():
            try:
                runs = json.loads(workflow_runs_file.read_text())
            except json.JSONDecodeError:
                runs = []
        else:
            runs = []

        # Create new run record
        run_record = {
            "run_id": str(uuid.uuid4()),
            "workflow_type": workflow_type,
            "status": "completed",
            "completed_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            "summary": summary or {},
        }

        runs.append(run_record)
        workflow_runs_file.write_text(json.dumps(runs, indent=2))

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
        workflow_runs_file = self.session_dir / "workflow_runs.json"
        if not workflow_runs_file.exists():
            return False

        # Map legacy names to new names for lookup
        aliases = self.WORKFLOW_ALIASES.get(workflow_type, [workflow_type])

        try:
            runs = json.loads(workflow_runs_file.read_text())
            return any(
                r.get("workflow_type") in aliases and r.get("status") == "completed" for r in runs
            )
        except json.JSONDecodeError:
            return False

    def get_workflow_status(self, workflow_type: str) -> str:
        """Get the status of a specific workflow.

        Args:
            workflow_type: Type of workflow ("idea-validation", "mvp-specification", etc.)

        Returns:
            Status string: "not_started", "in_progress", "completed"
        """
        workflow_runs_file = self.session_dir / "workflow_runs.json"
        if not workflow_runs_file.exists():
            return "not_started"

        # Map legacy names to new names for lookup
        aliases = self.WORKFLOW_ALIASES.get(workflow_type, [workflow_type])

        try:
            runs = json.loads(workflow_runs_file.read_text())
            # Find the most recent run for this workflow type
            for run in reversed(runs):
                if run.get("workflow_type") in aliases:
                    status = run.get("status", "not_started")
                    if status == "completed":
                        return "completed"
                    elif status == "running":
                        return "in_progress"
            return "not_started"
        except json.JSONDecodeError:
            return "not_started"

    def get_current_workflow(self) -> str | None:
        """Get the workflow currently in progress.

        Returns:
            Workflow type string if a workflow is in progress, None otherwise
        """
        workflow_runs_file = self.session_dir / "workflow_runs.json"
        if not workflow_runs_file.exists():
            return None

        try:
            runs = json.loads(workflow_runs_file.read_text())
            # Find the most recent running workflow
            for run in reversed(runs):
                if run.get("status") == "running":
                    return run.get("workflow_type")
            return None
        except json.JSONDecodeError:
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
        workflow_runs_file = self.session_dir / "workflow_runs.json"

        # Load existing runs
        if workflow_runs_file.exists():
            try:
                runs = json.loads(workflow_runs_file.read_text())
            except json.JSONDecodeError:
                runs = []
        else:
            runs = []

        # Create new run record
        run_record = {
            "run_id": str(uuid.uuid4()),
            "workflow_type": workflow_type,
            "status": "running",
            "started_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            "trigger": {
                "type": trigger_type,
            },
        }

        runs.append(run_record)
        workflow_runs_file.write_text(json.dumps(runs, indent=2))

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
        workflow_runs_file = self.session_dir / "workflow_runs.json"
        if not workflow_runs_file.exists():
            return None

        try:
            runs = json.loads(workflow_runs_file.read_text())

            # Find and update the running workflow of this type
            for run in reversed(runs):
                if run.get("workflow_type") == workflow_type and run.get("status") == "running":
                    run["status"] = "completed"
                    run["completed_at"] = datetime.now(UTC).isoformat().replace("+00:00", "Z")
                    if summary:
                        run["summary"] = summary

                    workflow_runs_file.write_text(json.dumps(runs, indent=2))
                    return run

            return None
        except json.JSONDecodeError:
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
        workflow_runs_file = self.session_dir / "workflow_runs.json"
        if not workflow_runs_file.exists():
            return None

        try:
            runs = json.loads(workflow_runs_file.read_text())

            # Find and update the running workflow of this type
            for run in reversed(runs):
                if run.get("workflow_type") == workflow_type and run.get("status") == "running":
                    run["status"] = "failed"
                    run["failed_at"] = datetime.now(UTC).isoformat().replace("+00:00", "Z")
                    run["error"] = error_message

                    workflow_runs_file.write_text(json.dumps(runs, indent=2))
                    return run

            return None
        except json.JSONDecodeError:
            return None

    # Private helper methods

    def _create_manifest(self, created: str, system_goal: str | None = None) -> None:
        """Create initial session_manifest.md.

        Args:
            created: ISO 8601 timestamp
            system_goal: The system goal string (may be None if not set yet)
        """
        from haytham.session.formatting import create_manifest

        content = create_manifest(
            stages=[(s.slug, s.display_name) for s in STAGES],
            created=created,
            system_goal=system_goal,
        )

        manifest_path = self.session_dir / "session_manifest.md"
        manifest_path.write_text(content)

    def _update_manifest(
        self,
        stage_slug: str,
        status: str,
        started: str | None,
        completed: str | None,
        duration: float | None,
    ) -> None:
        """Update session_manifest.md with stage status."""
        from haytham.session.formatting import update_manifest

        manifest_path = self.session_dir / "session_manifest.md"

        if not manifest_path.exists():
            return

        stage = get_stage_by_slug(stage_slug)
        content = manifest_path.read_text()

        updated = update_manifest(
            manifest_content=content,
            stage_slug=stage_slug,
            stage_display_name=stage.display_name,
            status=status,
            started=started,
            completed=completed,
            duration=duration,
            total_stages=len(STAGES),
            stages_list=[(s.slug, s.display_name) for s in STAGES],
        )

        manifest_path.write_text(updated)

    def _parse_manifest(self, content: str) -> dict[str, Any]:
        """Parse session_manifest.md content."""
        from haytham.session.formatting import parse_manifest

        return parse_manifest(
            content,
            valid_stage_slugs={s.slug for s in STAGES},
        )

    def _format_checkpoint(
        self,
        stage_slug: str,
        stage_name: str,
        status: str,
        started: str | None,
        completed: str | None,
        duration: float | None,
        retry_count: int,
        execution_mode: str,
        agents: list[dict[str, Any]],
        errors: list[str],
    ) -> str:
        """Format checkpoint.md content."""
        from haytham.session.formatting import format_checkpoint

        # Compute prev/next stage info from STAGES
        stage_index = None
        for i, stage in enumerate(STAGES):
            if stage.slug == stage_slug:
                stage_index = i
                break

        prev_stage_name = (
            STAGES[stage_index - 1].display_name if stage_index and stage_index > 0 else "None"
        )

        next_stage_slug = "-"
        next_stage_name = "None"
        if stage_index is not None and stage_index < len(STAGES) - 1:
            next_stage_slug = STAGES[stage_index + 1].slug
            next_stage_name = STAGES[stage_index + 1].display_name

        return format_checkpoint(
            stage_slug=stage_slug,
            stage_name=stage_name,
            status=status,
            started=started,
            completed=completed,
            duration=duration,
            retry_count=retry_count,
            execution_mode=execution_mode,
            agents=agents,
            errors=errors,
            prev_stage_name=prev_stage_name,
            next_stage_slug=next_stage_slug,
            next_stage_name=next_stage_name,
        )

    def _format_agent_output(
        self,
        agent_name: str,
        stage_slug: str,
        stage_name: str,
        executed: str,
        duration: float | None,
        status: str,
        model: str | None,
        input_tokens: int | None,
        output_tokens: int | None,
        tools_used: list[str],
        output_content: str,
        error_type: str | None,
        error_message: str | None,
        stack_trace: str | None,
    ) -> str:
        """Format agent output markdown content."""
        from haytham.session.formatting import format_agent_output

        return format_agent_output(
            agent_name=agent_name,
            context_label=f"{stage_slug} - {stage_name}",
            executed=executed,
            duration=duration,
            status=status,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            tools_used=tools_used,
            output_content=output_content,
            error_type=error_type,
            error_message=error_message,
            stack_trace=stack_trace,
        )

    def _format_user_feedback(
        self,
        stage_name: str,
        reviewed: bool,
        approved: bool,
        timestamp: str,
        comments: str,
        requested_changes: list[str],
        action: str,
        retry_count: int,
    ) -> str:
        """Format user_feedback.md content."""
        from haytham.session.formatting import format_user_feedback

        return format_user_feedback(
            context_name=stage_name,
            reviewed=reviewed,
            approved=approved,
            timestamp=timestamp,
            comments=comments,
            requested_changes=requested_changes,
            action=action,
            retry_count=retry_count,
        )
