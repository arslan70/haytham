"""Project management system for Haytham.

This module provides project CRUD operations, session management, and version tracking
for the phased workflow architecture.
"""

import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml


class ProjectManager:
    """Manages projects, sessions, and version tracking for Haytham.

    A project represents one startup idea with multiple sessions (iterations/refinements).
    Each session produces a version of requirements.md.

    Directory Structure:
        projects/{project_id}/
        ├── project.yaml                 # Project config and state
        ├── sessions/
        │   └── {session_id}/           # Session-specific data
        ├── outputs/
        │   ├── latest_requirements.md
        │   ├── requirements_v1.md
        │   └── requirements_v2.md
        └── history/
            └── changelog.md
    """

    def __init__(self, base_dir: str = "projects"):
        """Initialize the ProjectManager.

        Args:
            base_dir: Base directory for all projects (default: "projects")
        """
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def create_project(
        self,
        user_id: str,
        startup_idea: str,
        project_name: str | None = None,
        execution_mode: str = "mvp",
    ) -> dict[str, Any]:
        """Create a new project for a startup idea.

        Args:
            user_id: Unique identifier for the user
            startup_idea: The raw startup idea description
            project_name: Optional human-readable project name (used as folder name)
            execution_mode: "mvp" or "full" (default: "mvp")

        Returns:
            Dict containing project metadata including project_id

        Raises:
            ValueError: If execution_mode is not "mvp" or "full"
        """
        if execution_mode not in ["mvp", "full"]:
            raise ValueError(f"execution_mode must be 'mvp' or 'full', got: {execution_mode}")

        # Use project_name as folder name, fallback to UUID if not provided
        if project_name:
            # Ensure project_name is safe for filesystem
            safe_name = project_name.strip().replace(" ", "_").lower()
            safe_name = "".join(c if c.isalnum() or c == "_" else "_" for c in safe_name)

            # Check if folder already exists, append number if needed
            project_id = safe_name
            counter = 1
            while (self.base_dir / project_id).exists():
                project_id = f"{safe_name}_{counter}"
                counter += 1
        else:
            # Fallback to UUID
            project_id = str(uuid.uuid4())

        # Create project directory structure
        project_dir = self.base_dir / project_id
        project_dir.mkdir(parents=True, exist_ok=True)
        (project_dir / "sessions").mkdir(exist_ok=True)
        (project_dir / "outputs").mkdir(exist_ok=True)
        (project_dir / "history").mkdir(exist_ok=True)

        # Initialize project configuration
        now = datetime.now(UTC).isoformat().replace("+00:00", "Z")
        project_config = {
            "project_id": project_id,
            "user_id": user_id,
            "project_name": project_id,  # Use project_id as display name (already human-readable)
            "startup_idea": startup_idea,
            "execution_mode": execution_mode,
            "created_at": now,
            "updated_at": now,
            "status": "active",
            "sessions": [],
            "current_version": 0,
            "metrics": {
                "total_sessions": 0,
                "completed_sessions": 0,
                "total_duration_seconds": 0,
                "total_tokens": 0,
                "total_cost": 0.0,
            },
            "user_preferences": {
                "target_niche": None,
                "business_model": None,
                "pricing_strategy": None,
                "go_to_market_approach": None,
                "risk_tolerance": None,
                "target_region": None,
            },
        }

        # Save project configuration
        self._save_project_config(project_id, project_config)

        # Initialize changelog
        changelog_path = project_dir / "history" / "changelog.md"
        changelog_path.write_text(
            f"# Project Changelog\n\n"
            f"## Project Created\n"
            f"- **Date**: {now}\n"
            f"- **User**: {user_id}\n"
            f"- **Idea**: {startup_idea}\n"
            f"- **Mode**: {execution_mode}\n\n"
        )

        return project_config

    def start_session(
        self, project_id: str, workflow_type: str = "idea_validation"
    ) -> dict[str, Any]:
        """Start a new session within a project.

        Args:
            project_id: The project identifier
            workflow_type: Type of workflow (default: "idea_validation")

        Returns:
            Dict containing session metadata including session_id

        Raises:
            FileNotFoundError: If project does not exist
        """
        # Load project configuration
        project_config = self._load_project_config(project_id)

        # Generate unique session ID
        session_id = str(uuid.uuid4())

        # Create session directory structure
        session_dir = self.base_dir / project_id / "sessions" / session_id
        session_dir.mkdir(parents=True, exist_ok=True)

        # Initialize session metadata
        now = datetime.now(UTC).isoformat().replace("+00:00", "Z")
        session_metadata = {
            "session_id": session_id,
            "project_id": project_id,
            "user_id": project_config["user_id"],
            "workflow_type": workflow_type,
            "execution_mode": project_config["execution_mode"],
            "created_at": now,
            "updated_at": now,
            "status": "in_progress",
            "current_phase": 0,
            "completed_phases": [],
            "metrics": {"total_duration_seconds": 0, "total_tokens": 0, "total_cost": 0.0},
        }

        # Update project configuration
        project_config["sessions"].append(
            {"session_id": session_id, "started_at": now, "status": "in_progress"}
        )
        project_config["metrics"]["total_sessions"] += 1
        project_config["updated_at"] = now

        # Track latest session for quick resume
        project_config["latest_session"] = {
            "session_id": session_id,
            "started_at": now,
            "status": "in_progress",
            "current_phase": 0,
            "execution_mode": project_config["execution_mode"],
        }

        self._save_project_config(project_id, project_config)

        # Create session manifest
        self._create_session_manifest(project_id, session_id, session_metadata)

        return session_metadata

    def complete_session(
        self,
        project_id: str,
        session_id: str,
        requirements_content: str,
        metrics: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Complete a session and save the generated requirements.

        Args:
            project_id: The project identifier
            session_id: The session identifier
            requirements_content: The generated requirements.md content
            metrics: Optional session metrics (duration, tokens, cost)

        Returns:
            Dict containing completion metadata including version number

        Raises:
            FileNotFoundError: If project or session does not exist
        """
        # Load project configuration
        project_config = self._load_project_config(project_id)

        # Update version number
        project_config["current_version"] += 1
        version = project_config["current_version"]

        # Save requirements to outputs directory
        outputs_dir = self.base_dir / project_id / "outputs"

        # Save versioned requirements
        versioned_path = outputs_dir / f"requirements_v{version}.md"
        versioned_path.write_text(requirements_content)

        # Update latest requirements
        latest_path = outputs_dir / "latest_requirements.md"
        latest_path.write_text(requirements_content)

        # Update session status
        now = datetime.now(UTC).isoformat().replace("+00:00", "Z")
        for session in project_config["sessions"]:
            if session["session_id"] == session_id:
                session["status"] = "completed"
                session["completed_at"] = now
                session["version"] = version
                break

        # Update project metrics
        if metrics:
            project_config["metrics"]["total_duration_seconds"] += metrics.get(
                "duration_seconds", 0
            )
            project_config["metrics"]["total_tokens"] += metrics.get("tokens", 0)
            project_config["metrics"]["total_cost"] += metrics.get("cost", 0.0)

        project_config["metrics"]["completed_sessions"] += 1
        project_config["updated_at"] = now

        # Update latest_session status
        if project_config.get("latest_session", {}).get("session_id") == session_id:
            project_config["latest_session"]["status"] = "completed"
            project_config["latest_session"]["completed_at"] = now
            project_config["latest_session"]["version"] = version

        self._save_project_config(project_id, project_config)

        # Update changelog
        self._append_to_changelog(
            project_id,
            f"## Session Completed - Version {version}\n"
            f"- **Date**: {now}\n"
            f"- **Session ID**: {session_id}\n"
            f"- **Output**: requirements_v{version}.md\n\n",
        )

        return {
            "project_id": project_id,
            "session_id": session_id,
            "version": version,
            "completed_at": now,
            "output_path": str(versioned_path),
        }

    def list_user_projects(self, user_id: str, status: str | None = None) -> list[dict[str, Any]]:
        """List all projects for a user.

        Args:
            user_id: The user identifier
            status: Optional filter by status ("active", "archived", "completed")

        Returns:
            List of project metadata dictionaries
        """
        projects = []

        # Iterate through all project directories
        if not self.base_dir.exists():
            return projects

        for project_dir in self.base_dir.iterdir():
            if not project_dir.is_dir():
                continue

            try:
                project_config = self._load_project_config(project_dir.name)

                # Filter by user_id
                if project_config["user_id"] != user_id:
                    continue

                # Filter by status if specified
                if status and project_config.get("status") != status:
                    continue

                projects.append(project_config)

            except (FileNotFoundError, yaml.YAMLError):
                # Skip invalid project directories
                continue

        # Sort by updated_at (most recent first)
        projects.sort(key=lambda p: p.get("updated_at", ""), reverse=True)

        return projects

    def get_project_status(self, project_id: str) -> dict[str, Any]:
        """Get the current status of a project.

        Args:
            project_id: The project identifier

        Returns:
            Dict containing project status and metadata

        Raises:
            FileNotFoundError: If project does not exist
        """
        project_config = self._load_project_config(project_id)

        # Get latest session status
        latest_session = None
        if project_config["sessions"]:
            latest_session = project_config["sessions"][-1]

        return {
            "project_id": project_id,
            "project_name": project_config["project_name"],
            "status": project_config["status"],
            "execution_mode": project_config["execution_mode"],
            "current_version": project_config["current_version"],
            "total_sessions": project_config["metrics"]["total_sessions"],
            "completed_sessions": project_config["metrics"]["completed_sessions"],
            "latest_session": latest_session,
            "created_at": project_config["created_at"],
            "updated_at": project_config["updated_at"],
        }

    def update_user_preferences(self, project_id: str, preferences: dict[str, Any]) -> None:
        """Update user preferences for a project.

        Args:
            project_id: The project identifier
            preferences: Dict of user preferences to update

        Raises:
            FileNotFoundError: If project does not exist
        """
        project_config = self._load_project_config(project_id)

        # Update preferences
        project_config["user_preferences"].update(preferences)
        project_config["updated_at"] = datetime.now(UTC).isoformat().replace("+00:00", "Z")

        self._save_project_config(project_id, project_config)

    def get_user_preferences(self, project_id: str) -> dict[str, Any]:
        """Get user preferences for a project.

        Args:
            project_id: The project identifier

        Returns:
            Dict of user preferences

        Raises:
            FileNotFoundError: If project does not exist
        """
        project_config = self._load_project_config(project_id)
        return project_config["user_preferences"]

    def archive_project(self, project_id: str) -> None:
        """Archive a project (mark as inactive).

        Args:
            project_id: The project identifier

        Raises:
            FileNotFoundError: If project does not exist
        """
        project_config = self._load_project_config(project_id)
        project_config["status"] = "archived"
        project_config["updated_at"] = datetime.now(UTC).isoformat().replace("+00:00", "Z")
        self._save_project_config(project_id, project_config)

    def delete_project(self, project_id: str) -> None:
        """Delete a project and all its data.

        Args:
            project_id: The project identifier

        Raises:
            FileNotFoundError: If project does not exist
        """
        project_dir = self.base_dir / project_id

        if not project_dir.exists():
            raise FileNotFoundError(f"Project not found: {project_id}")

        # Remove entire project directory
        import shutil

        shutil.rmtree(project_dir)

    # Private helper methods

    def _load_project_config(self, project_id: str) -> dict[str, Any]:
        """Load project configuration from project.yaml.

        Args:
            project_id: The project identifier

        Returns:
            Dict containing project configuration

        Raises:
            FileNotFoundError: If project.yaml does not exist
        """
        config_path = self.base_dir / project_id / "project.yaml"

        if not config_path.exists():
            raise FileNotFoundError(f"Project configuration not found: {project_id}")

        with open(config_path) as f:
            return yaml.safe_load(f)

    def _save_project_config(self, project_id: str, config: dict[str, Any]) -> None:
        """Save project configuration to project.yaml.

        Args:
            project_id: The project identifier
            config: Project configuration dictionary
        """
        config_path = self.base_dir / project_id / "project.yaml"

        with open(config_path, "w") as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)

    def _create_session_manifest(
        self, project_id: str, session_id: str, metadata: dict[str, Any]
    ) -> None:
        """Create session_manifest.md for a new session.

        Args:
            project_id: The project identifier
            session_id: The session identifier
            metadata: Session metadata dictionary
        """
        session_dir = self.base_dir / project_id / "sessions" / session_id
        manifest_path = session_dir / "session_manifest.md"

        execution_mode = metadata["execution_mode"]

        content = f"""# Session Manifest

## Metadata
- Session ID: {session_id}
- Project ID: {project_id}
- User ID: {metadata["user_id"]}
- Workflow Type: {metadata["workflow_type"]}
- Execution Mode: {execution_mode}
- Created: {metadata["created_at"]}
- Last Updated: {metadata["updated_at"]}
- Status: {metadata["status"]}

## Phase Status

| Phase | Name | Status | Started | Completed | Duration |
|-------|------|--------|---------|-----------|----------|
| 1 | Concept Expansion | pending | - | - | - |
| 2 | Market Research | pending | - | - | - |
| 3 | Niche Selection | pending | - | - | - |
"""

        if execution_mode == "full":
            content += """| 4 | Product Strategy | pending | - | - | - |
| 5 | Business Planning | pending | - | - | - |
"""

        content += """| 6 | Validation | pending | - | - | - |
| 7 | Final Synthesis | pending | - | - | - |

## Current Phase
- Phase: 0
- Name: Not Started
- Status: pending
- Can Resume: false

## Metrics
- Total Duration: 0s
- Total Tokens: 0
- Total Cost: $0.00
"""

        manifest_path.write_text(content)

    def _append_to_changelog(self, project_id: str, entry: str) -> None:
        """Append an entry to the project changelog.

        Args:
            project_id: The project identifier
            entry: Changelog entry text
        """
        changelog_path = self.base_dir / project_id / "history" / "changelog.md"

        with open(changelog_path, "a") as f:
            f.write(entry)
