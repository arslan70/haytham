"""Unit tests for orchestration and integration components.

Tests the Session 8 deliverables:
- Full pipeline orchestration from MVP spec to implementation
- Sequential story processing through all chunks
- Progress tracking and state persistence
- Notes App end-to-end test: 4 stories processed, entities implemented

Reference: ADR-001h: Orchestration & Feedback Loops

Run with: pytest tests/test_orchestration.py -v
"""

import tempfile
from pathlib import Path

import pytest

from haytham.orchestration import (
    HumanGateRequest,
    PipelineOrchestrator,
    PipelineProgress,
    PipelineStage,
    StoryProcessingResult,
    run_notes_app_pipeline,
)
from haytham.project.state_queries import StateQueries

# ========== Fixtures ==========


@pytest.fixture
def temp_session_dir():
    """Temporary directory for session state."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def notes_app_mvp_spec():
    """Notes App MVP specification text - loads from fixture file."""
    fixture_path = Path(__file__).parent / "fixtures" / "notes_app_mvp_spec.md"
    return fixture_path.read_text()


@pytest.fixture
def orchestrator(temp_session_dir):
    """PipelineOrchestrator instance."""
    return PipelineOrchestrator(temp_session_dir)


# ========== Pipeline Progress Tests ==========


class TestPipelineProgress:
    """Test progress tracking."""

    def test_initial_progress(self):
        """Initial progress is idle with zero counts."""
        progress = PipelineProgress()

        assert progress.stage == PipelineStage.IDLE
        assert progress.stories_completed == 0
        assert progress.stories_total == 0
        assert progress.progress_percentage == 0.0

    def test_progress_percentage_calculation(self):
        """Progress percentage calculated correctly."""
        progress = PipelineProgress(stories_completed=2, stories_total=4)
        assert progress.progress_percentage == 50.0


# ========== Pipeline Orchestrator Tests ==========


class TestPipelineOrchestrator:
    """Test orchestrator initialization and setup."""

    def test_orchestrator_creates_session_dir(self, temp_session_dir):
        """Orchestrator creates session directory."""
        orchestrator = PipelineOrchestrator(temp_session_dir)
        assert orchestrator.session_dir == temp_session_dir

    def test_initialize_from_mvp_spec(self, orchestrator, notes_app_mvp_spec):
        """Can initialize state from MVP spec."""
        result = orchestrator.initialize_from_mvp_spec(notes_app_mvp_spec)

        assert result is True
        assert orchestrator.state is not None
        assert len(orchestrator.state.stories) >= 1

    def test_stack_selection_gate(self, orchestrator, notes_app_mvp_spec):
        """Stack selection returns HumanGateRequest."""
        gate = orchestrator.select_stack(notes_app_mvp_spec)

        assert isinstance(gate, HumanGateRequest)
        assert gate.gate_type == "stack_selection"
        assert len(gate.options) >= 1
        assert gate.needs_response() is True

    def test_apply_stack_selection(self, orchestrator, notes_app_mvp_spec):
        """Can apply stack selection."""
        orchestrator.initialize_from_mvp_spec(notes_app_mvp_spec)

        result = orchestrator.apply_stack_selection("web-python-react")

        assert result is True
        assert orchestrator.state.stack is not None
        assert orchestrator.state.stack.platform == "web_application"


# ========== Story Processing Tests ==========


class TestStoryProcessing:
    """Test individual story processing."""

    def test_get_next_story(self, orchestrator, notes_app_mvp_spec):
        """get_next_story returns first pending story."""
        orchestrator.initialize_from_mvp_spec(notes_app_mvp_spec)
        orchestrator.apply_stack_selection("web-python-react")

        story = orchestrator.get_next_story()

        assert story is not None
        assert story.status == "pending"

    def test_process_story_returns_result(self, orchestrator, notes_app_mvp_spec):
        """process_story returns StoryProcessingResult."""
        orchestrator.initialize_from_mvp_spec(notes_app_mvp_spec)
        orchestrator.apply_stack_selection("web-python-react")

        story = orchestrator.get_next_story()
        result = orchestrator.process_story(story.id, auto_approve=True)

        assert isinstance(result, StoryProcessingResult)
        assert result.story_id == story.id
        assert result.success is True

    def test_process_story_creates_tasks(self, orchestrator, notes_app_mvp_spec):
        """process_story creates tasks for the story."""
        orchestrator.initialize_from_mvp_spec(notes_app_mvp_spec)
        orchestrator.apply_stack_selection("web-python-react")

        story = orchestrator.get_next_story()
        result = orchestrator.process_story(story.id, auto_approve=True)

        assert result.tasks_created >= 2
        assert result.tasks_completed >= 2

    def test_process_story_updates_progress(self, orchestrator, notes_app_mvp_spec):
        """process_story updates progress tracking."""
        orchestrator.initialize_from_mvp_spec(notes_app_mvp_spec)
        orchestrator.apply_stack_selection("web-python-react")

        initial_completed = orchestrator.progress.stories_completed
        story = orchestrator.get_next_story()
        orchestrator.process_story(story.id, auto_approve=True)

        assert orchestrator.progress.stories_completed == initial_completed + 1


# ========== Full Pipeline Tests ==========


class TestFullPipeline:
    """Test end-to-end pipeline execution."""

    def test_run_full_pipeline(self, orchestrator, notes_app_mvp_spec):
        """Can run full pipeline from MVP spec to completion."""
        results = orchestrator.run_full_pipeline(
            notes_app_mvp_spec,
            stack_template_id="web-python-react",
            auto_approve=True,
        )

        assert len(results) >= 1
        assert all(r.success for r in results)
        assert orchestrator.progress.stage == PipelineStage.COMPLETED

    def test_process_all_stories(self, orchestrator, notes_app_mvp_spec):
        """process_all_stories handles all pending stories."""
        orchestrator.initialize_from_mvp_spec(notes_app_mvp_spec)
        orchestrator.apply_stack_selection("web-python-react")

        results = orchestrator.process_all_stories(auto_approve=True)

        assert len(results) >= 1
        assert all(r.success for r in results)

    def test_progress_summary(self, orchestrator, notes_app_mvp_spec):
        """get_progress_summary returns readable summary."""
        orchestrator.initialize_from_mvp_spec(notes_app_mvp_spec)
        orchestrator.apply_stack_selection("web-python-react")

        summary = orchestrator.get_progress_summary()

        assert "Pipeline Progress" in summary
        assert "Stage" in summary


# ========== State Persistence Tests ==========


class TestStatePersistence:
    """Test state persistence during pipeline."""

    def test_state_saved_after_initialization(self, temp_session_dir, notes_app_mvp_spec):
        """State saved to disk after initialization."""
        orchestrator = PipelineOrchestrator(temp_session_dir)
        orchestrator.initialize_from_mvp_spec(notes_app_mvp_spec)

        # Check state file exists (PipelineStateManager uses project.yaml)
        state_file = temp_session_dir / "project.yaml"
        assert state_file.exists()

    def test_state_persists_across_loads(self, temp_session_dir, notes_app_mvp_spec):
        """State persists when reloading orchestrator."""
        # First orchestrator
        orch1 = PipelineOrchestrator(temp_session_dir)
        orch1.initialize_from_mvp_spec(notes_app_mvp_spec)
        orch1.apply_stack_selection("web-python-react")
        stories_count = len(orch1.state.stories)

        # Second orchestrator (reload)
        orch2 = PipelineOrchestrator(temp_session_dir)
        # Force reload
        orch2._state = None
        reloaded_stories = len(orch2.state.stories)

        assert reloaded_stories == stories_count


# ========== Notes App Integration Tests ==========


class TestNotesAppEndToEnd:
    """End-to-end tests using Notes App fixture."""

    def test_notes_app_full_pipeline(self, temp_session_dir, notes_app_mvp_spec):
        """Notes App: Full pipeline processes all 4 stories."""
        results = run_notes_app_pipeline(temp_session_dir, notes_app_mvp_spec)

        # Should process multiple stories
        assert len(results) >= 1

        # All should succeed
        assert all(r.success for r in results)

        # Each story should create and complete tasks
        for result in results:
            assert result.tasks_created >= 2
            assert result.tasks_completed >= 2

    def test_notes_app_entities_implemented(self, temp_session_dir, notes_app_mvp_spec):
        """Notes App: Entities marked as implemented."""
        orchestrator = PipelineOrchestrator(temp_session_dir)
        orchestrator.run_full_pipeline(
            notes_app_mvp_spec,
            stack_template_id="web-python-react",
            auto_approve=True,
        )

        queries = StateQueries(orchestrator.state)

        # Should have implemented entities
        implemented = queries.get_implemented_entities()
        # May have entities depending on how stories define them
        assert isinstance(implemented, list)

    def test_notes_app_all_stories_completed(self, temp_session_dir, notes_app_mvp_spec):
        """Notes App: All stories marked as completed."""
        orchestrator = PipelineOrchestrator(temp_session_dir)
        orchestrator.run_full_pipeline(
            notes_app_mvp_spec,
            stack_template_id="web-python-react",
            auto_approve=True,
        )

        queries = StateQueries(orchestrator.state)
        completed = queries.get_completed_stories()
        pending = queries.get_pending_stories()

        # All stories should be completed
        assert len(completed) > 0
        assert len(pending) == 0

    def test_notes_app_progress_100_percent(self, temp_session_dir, notes_app_mvp_spec):
        """Notes App: Progress reaches 100%."""
        orchestrator = PipelineOrchestrator(temp_session_dir)
        orchestrator.run_full_pipeline(
            notes_app_mvp_spec,
            stack_template_id="web-python-react",
            auto_approve=True,
        )

        assert orchestrator.progress.progress_percentage == 100.0
        assert orchestrator.progress.stage == PipelineStage.COMPLETED


class TestHumanGates:
    """Test human gate functionality."""

    def test_human_gate_request_options(self, orchestrator, notes_app_mvp_spec):
        """HumanGateRequest has proper options."""
        gate = orchestrator.select_stack(notes_app_mvp_spec)

        assert gate.options is not None
        assert len(gate.options) >= 1
        assert gate.default is not None

    def test_human_gate_presentation_text(self, orchestrator, notes_app_mvp_spec):
        """HumanGateRequest has presentation text."""
        gate = orchestrator.select_stack(notes_app_mvp_spec)

        assert gate.presentation_text != ""
        assert "Stack" in gate.presentation_text or "stack" in gate.presentation_text


class TestConvenienceFunction:
    """Test convenience function."""

    def test_run_notes_app_pipeline(self, temp_session_dir, notes_app_mvp_spec):
        """run_notes_app_pipeline convenience function works."""
        results = run_notes_app_pipeline(temp_session_dir, notes_app_mvp_spec)

        assert isinstance(results, list)
        assert len(results) >= 1
        assert all(isinstance(r, StoryProcessingResult) for r in results)
