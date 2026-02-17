"""Tests for SessionManager - single-session management for meta-recursive system.

Tests cover:
- has_active_session() returns correct bool
- create_session() creates correct directory structure in session/
- load_session() parses manifest correctly
- save_checkpoint() updates manifest
- get_approved_stages() returns correct stages
- get_next_stage() returns correct next stage
"""

import json
import shutil

import pytest

from haytham.session.session_manager import SessionManager


@pytest.fixture
def temp_dir(tmp_path):
    """Create a temporary directory for testing."""
    return tmp_path


@pytest.fixture
def session_manager(temp_dir):
    """Create a SessionManager with a temporary base directory."""
    return SessionManager(base_dir=str(temp_dir))


class TestHasActiveSession:
    """Tests for has_active_session() method."""

    def test_no_session_returns_false(self, session_manager):
        """has_active_session returns False when no session exists."""
        assert session_manager.has_active_session() is False

    def test_active_session_returns_true(self, session_manager):
        """has_active_session returns True when in_progress session exists."""
        session_manager.create_session()
        assert session_manager.has_active_session() is True

    def test_completed_session_returns_false(self, session_manager):
        """has_active_session returns False when session is completed."""
        session_manager.create_session()
        # Manually update manifest to completed status
        manifest_path = session_manager.session_dir / "session_manifest.md"
        content = manifest_path.read_text()
        content = content.replace("- Status: in_progress", "- Status: completed")
        manifest_path.write_text(content)
        assert session_manager.has_active_session() is False

    def test_corrupted_manifest_returns_false(self, session_manager):
        """has_active_session returns False when manifest is corrupted."""
        session_manager.session_dir.mkdir(parents=True, exist_ok=True)
        manifest_path = session_manager.session_dir / "session_manifest.md"
        manifest_path.write_text("invalid content")
        assert session_manager.has_active_session() is False


class TestCreateSession:
    """Tests for create_session() method."""

    def test_creates_session_directory(self, session_manager):
        """create_session creates the session directory."""
        session_manager.create_session()
        assert session_manager.session_dir.exists()

    def test_creates_stage_directories(self, session_manager):
        """create_session creates stage directories using slugs."""
        session_manager.create_session()
        expected_dirs = [
            "idea-analysis",
            "market-context",
            "risk-assessment",
            "pivot-strategy",
            "validation-summary",
            "mvp-scope",
            "capability-model",
            "system-traits",
            "build-buy-analysis",
            "architecture-decisions",
            "story-generation",
            "story-validation",
            "dependency-ordering",
        ]
        for dir_name in expected_dirs:
            assert (session_manager.session_dir / dir_name).exists()

    def test_creates_session_manifest(self, session_manager):
        """create_session creates session_manifest.md."""
        session_manager.create_session()
        manifest_path = session_manager.session_dir / "session_manifest.md"
        assert manifest_path.exists()
        content = manifest_path.read_text()
        assert "Status: in_progress" in content

    def test_creates_preferences_file(self, session_manager):
        """create_session creates empty preferences.json."""
        session_manager.create_session()
        prefs_path = session_manager.session_dir / "preferences.json"
        assert prefs_path.exists()
        assert json.loads(prefs_path.read_text()) == {}

    def test_returns_session_metadata(self, session_manager):
        """create_session returns correct metadata dict."""
        result = session_manager.create_session()
        assert result["status"] == "in_progress"
        assert "created" in result
        # system_goal is None initially until set via set_system_goal()
        assert "system_goal" in result

    def test_clears_existing_session(self, session_manager):
        """create_session clears existing session directory."""
        # Create first session with some content
        session_manager.create_session()
        test_file = session_manager.session_dir / "test_file.txt"
        test_file.write_text("test content")

        # Create new session
        session_manager.create_session()

        # Old file should be gone
        assert not test_file.exists()

    def test_preserves_project_yaml(self, session_manager):
        """create_session preserves project.yaml with system goal."""
        # Set system goal first (creates project.yaml)
        session_manager.set_system_goal("Build a SaaS that validates startup ideas")

        # Verify project.yaml exists with system goal
        assert session_manager.has_system_goal()
        assert session_manager.get_system_goal() == "Build a SaaS that validates startup ideas"

        # Create new session (should preserve project.yaml)
        session_manager.create_session()

        # System goal should still be available
        assert session_manager.has_system_goal()
        assert session_manager.get_system_goal() == "Build a SaaS that validates startup ideas"


class TestLoadSession:
    """Tests for load_session() method."""

    def test_no_session_returns_none(self, session_manager):
        """load_session returns None when no session exists."""
        # Remove session_manifest.md if it exists (session_dir created by __init__)
        manifest_path = session_manager.session_dir / "session_manifest.md"
        if manifest_path.exists():
            manifest_path.unlink()
        assert session_manager.load_session() is None

    def test_loads_session_metadata(self, session_manager):
        """load_session correctly parses session metadata."""
        session_manager.create_session()
        session = session_manager.load_session()

        assert session is not None
        assert session["status"] == "in_progress"
        # system_goal is None initially until set via set_system_goal()
        assert "system_goal" in session

    def test_loads_stage_statuses(self, session_manager):
        """load_session correctly parses stage statuses."""
        session_manager.create_session()
        session = session_manager.load_session()

        # All stages should be pending initially
        for slug in [
            "idea-analysis",
            "market-context",
            "risk-assessment",
            "validation-summary",
            "mvp-scope",
        ]:
            assert session["stage_statuses"].get(slug) == "pending"


class TestSaveCheckpoint:
    """Tests for save_checkpoint() method."""

    def test_creates_checkpoint_file(self, session_manager):
        """save_checkpoint creates checkpoint.md in stage directory."""
        session_manager.create_session()
        session_manager.save_checkpoint(
            stage_slug="idea-analysis",
            status="completed",
            agents=[{"agent_name": "concept_expansion", "status": "completed"}],
            started="2024-01-15T10:00:00Z",
            completed="2024-01-15T10:03:00Z",
            duration=180.0,
        )

        checkpoint_path = session_manager.session_dir / "idea-analysis" / "checkpoint.md"
        assert checkpoint_path.exists()
        content = checkpoint_path.read_text()
        assert "Stage: idea-analysis" in content
        assert "Status: completed" in content

    def test_updates_manifest(self, session_manager):
        """save_checkpoint updates session_manifest.md."""
        session_manager.create_session()
        session_manager.save_checkpoint(
            stage_slug="idea-analysis",
            status="completed",
            agents=[{"agent_name": "concept_expansion", "status": "completed"}],
            started="2024-01-15T10:00:00Z",
            completed="2024-01-15T10:03:00Z",
            duration=180.0,
        )

        manifest_path = session_manager.session_dir / "session_manifest.md"
        content = manifest_path.read_text()
        assert "| idea-analysis | Idea Analysis | completed |" in content

    def test_invalid_stage_raises(self, session_manager):
        """save_checkpoint raises ValueError for invalid stage slug."""
        session_manager.create_session()
        with pytest.raises(ValueError, match="Invalid stage_slug"):
            session_manager.save_checkpoint(
                stage_slug="invalid-stage", status="completed", agents=[]
            )

    def test_invalid_status_raises(self, session_manager):
        """save_checkpoint raises ValueError for invalid status."""
        session_manager.create_session()
        with pytest.raises(ValueError, match="status must be one of"):
            session_manager.save_checkpoint(stage_slug="idea-analysis", status="invalid", agents=[])

    def test_no_session_raises(self, session_manager):
        """save_checkpoint raises FileNotFoundError when no session exists."""
        # Remove session directory
        if session_manager.session_dir.exists():
            shutil.rmtree(session_manager.session_dir)

        with pytest.raises(FileNotFoundError):
            session_manager.save_checkpoint(
                stage_slug="idea-analysis", status="completed", agents=[]
            )


class TestGetApprovedStages:
    """Tests for get_approved_stages() method."""

    def test_no_session_returns_empty(self, session_manager):
        """get_approved_stages returns empty list when no session exists."""
        # Remove session directory completely to simulate no session
        if session_manager.session_dir.exists():
            shutil.rmtree(session_manager.session_dir)
        assert session_manager.get_approved_stages() == []

    def test_no_approvals_returns_empty(self, session_manager):
        """get_approved_stages returns empty list when no stages approved."""
        session_manager.create_session()
        assert session_manager.get_approved_stages() == []

    def test_returns_approved_stages(self, session_manager):
        """get_approved_stages returns list of approved stage slugs."""
        session_manager.create_session()

        # Create user feedback with approval for idea-analysis
        session_manager.save_user_feedback(
            stage_slug="idea-analysis",
            feedback={"reviewed": True, "approved": True, "action": "approved"},
        )

        approved = session_manager.get_approved_stages()
        assert approved == ["idea-analysis"]

    def test_returns_sorted_stages(self, session_manager):
        """get_approved_stages returns stages in workflow order."""
        session_manager.create_session()

        # Approve stages (risk-assessment first, then idea-analysis)
        session_manager.save_user_feedback(
            stage_slug="risk-assessment",
            feedback={"reviewed": True, "approved": True},
        )
        session_manager.save_user_feedback(
            stage_slug="idea-analysis",
            feedback={"reviewed": True, "approved": True},
        )

        approved = session_manager.get_approved_stages()
        # Should be in workflow order, not approval order
        assert approved == ["idea-analysis", "risk-assessment"]


class TestGetNextStage:
    """Tests for get_next_stage() method."""

    def test_new_session_returns_first_stage(self, session_manager):
        """get_next_stage returns first stage for new session."""
        session_manager.create_session()
        assert session_manager.get_next_stage() == "idea-analysis"

    def test_returns_next_unapproved_stage(self, session_manager):
        """get_next_stage returns first unapproved stage."""
        session_manager.create_session()

        # Approve idea-analysis
        session_manager.save_user_feedback(
            stage_slug="idea-analysis",
            feedback={"reviewed": True, "approved": True},
        )

        assert session_manager.get_next_stage() == "market-context"

    def test_all_complete_returns_none(self, session_manager):
        """get_next_stage returns None when all stages complete."""
        session_manager.create_session()

        # Approve all stages
        from haytham.phases.stage_config import STAGES

        for stage in STAGES:
            session_manager.save_user_feedback(
                stage_slug=stage.slug,
                feedback={"reviewed": True, "approved": True},
            )

        assert session_manager.get_next_stage() is None


class TestSaveAndLoadPreferences:
    """Tests for save_preferences() and load_preferences() methods."""

    def test_save_and_load_preferences(self, session_manager):
        """Preferences can be saved and loaded correctly."""
        session_manager.create_session()

        prefs = {"target_niche": "Solo founders", "risk_tolerance": "medium"}
        session_manager.save_preferences(prefs)

        loaded = session_manager.load_preferences()
        assert loaded["target_niche"] == "Solo founders"
        assert loaded["risk_tolerance"] == "medium"
        assert "updated_at" in loaded

    def test_load_empty_preferences(self, session_manager):
        """load_preferences returns empty dict when no preferences exist."""
        # Remove any existing preferences
        prefs_path = session_manager.session_dir / "preferences.json"
        if prefs_path.exists():
            prefs_path.unlink()
        assert session_manager.load_preferences() == {}


class TestSaveAgentOutput:
    """Tests for save_agent_output() method."""

    def test_saves_agent_output_file(self, session_manager):
        """save_agent_output creates agent output markdown file."""
        session_manager.create_session()

        session_manager.save_agent_output(
            stage_slug="idea-analysis",
            agent_name="concept_expansion",
            output_content="# Concept Analysis\n\nThis is the analysis.",
            status="completed",
            duration=45.5,
        )

        output_path = session_manager.session_dir / "idea-analysis" / "concept_expansion.md"
        assert output_path.exists()
        content = output_path.read_text()
        assert "Agent: concept_expansion" in content
        assert "# Concept Analysis" in content


class TestGetStageOutputs:
    """Tests for get_stage_outputs() method."""

    def test_loads_stage_outputs(self, session_manager):
        """get_stage_outputs loads agent outputs from specified stages."""
        session_manager.create_session()

        # Save some agent outputs
        session_manager.save_agent_output(
            stage_slug="idea-analysis",
            agent_name="concept_expansion",
            output_content="Concept output content",
        )

        outputs = session_manager.get_stage_outputs(["idea-analysis"])
        assert "idea-analysis" in outputs
        assert "concept_expansion" in outputs["idea-analysis"]
        assert "Concept output content" in outputs["idea-analysis"]["concept_expansion"]

    def test_no_session_returns_empty(self, session_manager):
        """get_stage_outputs returns empty dict when no session exists."""
        # Remove session directory
        if session_manager.session_dir.exists():
            shutil.rmtree(session_manager.session_dir)

        assert session_manager.get_stage_outputs(["idea-analysis"]) == {}


class TestWorkflowLocking:
    """Tests for workflow locking methods (feedback mechanism support)."""

    def test_lock_workflow_creates_lock_file(self, session_manager):
        """lock_workflow creates a .{workflow_type}.locked file."""
        session_manager.session_dir.mkdir(parents=True, exist_ok=True)

        session_manager.lock_workflow("idea-validation")

        lock_file = session_manager.session_dir / ".idea-validation.locked"
        assert lock_file.exists()

        # Verify lock file contains expected data
        lock_data = json.loads(lock_file.read_text())
        assert "locked_at" in lock_data
        assert lock_data["workflow_type"] == "idea-validation"

    def test_is_workflow_locked_returns_false_when_not_locked(self, session_manager):
        """is_workflow_locked returns False when no lock file exists."""
        session_manager.session_dir.mkdir(parents=True, exist_ok=True)

        assert session_manager.is_workflow_locked("idea-validation") is False

    def test_is_workflow_locked_returns_true_when_locked(self, session_manager):
        """is_workflow_locked returns True when lock file exists."""
        session_manager.session_dir.mkdir(parents=True, exist_ok=True)
        session_manager.lock_workflow("idea-validation")

        assert session_manager.is_workflow_locked("idea-validation") is True

    def test_lock_workflow_updates_workflow_run_status(self, session_manager):
        """lock_workflow updates the workflow run status to 'accepted'."""
        session_manager.session_dir.mkdir(parents=True, exist_ok=True)

        # Create a completed workflow run
        session_manager.start_workflow_run("idea-validation")
        session_manager.complete_workflow_run("idea-validation")

        # Lock the workflow
        session_manager.lock_workflow("idea-validation")

        # Check that status was updated
        workflow_runs_file = session_manager.session_dir / "workflow_runs.json"
        runs = json.loads(workflow_runs_file.read_text())

        assert any(
            r.get("workflow_type") == "idea-validation" and r.get("status") == "accepted"
            for r in runs
        )

    def test_get_workflow_feedback_state_not_started(self, session_manager):
        """get_workflow_feedback_state returns 'not_started' for new workflow."""
        session_manager.session_dir.mkdir(parents=True, exist_ok=True)

        state = session_manager.get_workflow_feedback_state("idea-validation")
        assert state == "not_started"

    def test_get_workflow_feedback_state_running(self, session_manager):
        """get_workflow_feedback_state returns 'running' for in-progress workflow."""
        session_manager.session_dir.mkdir(parents=True, exist_ok=True)
        session_manager.start_workflow_run("idea-validation")

        state = session_manager.get_workflow_feedback_state("idea-validation")
        assert state == "running"

    def test_get_workflow_feedback_state_feedback(self, session_manager):
        """get_workflow_feedback_state returns 'feedback' for completed but unlocked workflow."""
        session_manager.session_dir.mkdir(parents=True, exist_ok=True)
        session_manager.start_workflow_run("idea-validation")
        session_manager.complete_workflow_run("idea-validation")

        state = session_manager.get_workflow_feedback_state("idea-validation")
        assert state == "feedback"

    def test_get_workflow_feedback_state_accepted(self, session_manager):
        """get_workflow_feedback_state returns 'accepted' for locked workflow."""
        session_manager.session_dir.mkdir(parents=True, exist_ok=True)
        session_manager.start_workflow_run("idea-validation")
        session_manager.complete_workflow_run("idea-validation")
        session_manager.lock_workflow("idea-validation")

        state = session_manager.get_workflow_feedback_state("idea-validation")
        assert state == "accepted"

    def test_lock_file_takes_precedence_over_run_status(self, session_manager):
        """Lock file presence takes precedence over workflow run status."""
        session_manager.session_dir.mkdir(parents=True, exist_ok=True)

        # Create a completed workflow run (status = "completed")
        session_manager.start_workflow_run("idea-validation")
        session_manager.complete_workflow_run("idea-validation")

        # Manually create lock file without going through lock_workflow
        # (simulates edge case where run status wasn't updated)
        lock_file = session_manager.session_dir / ".idea-validation.locked"
        lock_file.write_text('{"locked_at": "2024-01-01T00:00:00Z"}')

        # Should still return accepted because lock file exists
        state = session_manager.get_workflow_feedback_state("idea-validation")
        assert state == "accepted"

    def test_multiple_workflows_independent_locking(self, session_manager):
        """Each workflow can be locked independently."""
        session_manager.session_dir.mkdir(parents=True, exist_ok=True)

        # Lock only idea-validation
        session_manager.lock_workflow("idea-validation")

        assert session_manager.is_workflow_locked("idea-validation") is True
        assert session_manager.is_workflow_locked("mvp-specification") is False
        assert session_manager.is_workflow_locked("story-generation") is False

    def test_workflow_feedback_state_with_legacy_aliases(self, session_manager):
        """get_workflow_feedback_state handles legacy workflow names."""
        session_manager.session_dir.mkdir(parents=True, exist_ok=True)

        # Start with legacy name "discovery"
        session_manager.start_workflow_run("discovery")
        session_manager.complete_workflow_run("discovery")

        # Query with new name "idea-validation" should find it
        state = session_manager.get_workflow_feedback_state("idea-validation")
        assert state == "feedback"
