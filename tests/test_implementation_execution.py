"""Unit tests for implementation execution components.

Tests the Session 7 deliverables:
- Task status updates (pending → in_progress → completed/failed)
- Entity status updates when models are created
- Story completion when all tasks finish
- Notes App test: All tasks complete, entities implemented

Reference: ADR-001g: Implementation Execution

Run with: pytest tests/test_implementation_execution.py -v
"""

import pytest

from haytham.execution.task_executor import (
    StoryExecutionResult,
    TaskExecutionResult,
    TaskExecutor,
    TaskStatus,
    create_execution_prompt,
)
from haytham.project.state_models import (
    BackendStack,
    Entity,
    EntityAttribute,
    FrontendStack,
    PipelineState,
    Stack,
    Story,
    Task,
)
from haytham.project.state_queries import StateQueries

# ========== Fixtures ==========


@pytest.fixture
def notes_app_state_with_tasks():
    """Pre-populated state with Notes App stories and tasks."""
    state = PipelineState()

    # Entities
    state.entities = [
        Entity(
            id="E-001",
            name="User",
            status="planned",
            attributes=[
                EntityAttribute(name="id", type="UUID", primary_key=True),
                EntityAttribute(name="email", type="String", unique=True),
            ],
        ),
        Entity(
            id="E-002",
            name="Note",
            status="planned",
            attributes=[
                EntityAttribute(name="id", type="UUID", primary_key=True),
                EntityAttribute(name="title", type="String"),
                EntityAttribute(name="content", type="Text"),
            ],
        ),
    ]

    # Stories (marked as implementing)
    state.stories = [
        Story(
            id="S-001",
            title="Create Note",
            priority="P0",
            status="implementing",
            user_story="As a user, I want to create a new note",
            acceptance_criteria=["Given I am logged in, when I save, the note is persisted"],
            depends_on=["E-001", "E-002"],
            tasks=["T-001", "T-002", "T-003", "T-004"],
        ),
        Story(
            id="S-003",
            title="Search Notes",
            priority="P0",
            status="implementing",
            user_story="As a user, I want to search my notes",
            acceptance_criteria=["When I search, matching notes are shown"],
            depends_on=["E-002"],
            tasks=["T-005", "T-006", "T-007"],
        ),
    ]

    # Tasks for S-001 (Create Note)
    state.tasks = [
        Task(
            id="T-001",
            story_id="S-001",
            title="Define Note model",
            status="pending",
            description="Create database model for Note entity",
        ),
        Task(
            id="T-002",
            story_id="S-001",
            title="Add Note API endpoints",
            status="pending",
            description="Create POST /api/notes endpoint",
        ),
        Task(
            id="T-003",
            story_id="S-001",
            title="Add Note form component",
            status="pending",
            description="Create form for new notes",
        ),
        Task(
            id="T-004",
            story_id="S-001",
            title="Write Note creation tests",
            status="pending",
            description="Unit tests for Note creation",
        ),
        # Tasks for S-003 (Search Notes)
        Task(
            id="T-005",
            story_id="S-003",
            title="Add search endpoint",
            status="pending",
            description="Create GET /api/notes/search endpoint",
        ),
        Task(
            id="T-006",
            story_id="S-003",
            title="Add search component",
            status="pending",
            description="Create search bar component",
        ),
        Task(
            id="T-007",
            story_id="S-003",
            title="Write search tests",
            status="pending",
            description="Unit tests for search",
        ),
    ]

    # Stack
    state.stack = Stack(
        platform="web_application",
        backend=BackendStack(language="python", framework="fastapi"),
        frontend=FrontendStack(language="typescript", framework="react"),
    )

    return state


@pytest.fixture
def executor(notes_app_state_with_tasks):
    """TaskExecutor with mocked save callback."""
    saves = []
    executor = TaskExecutor(
        notes_app_state_with_tasks,
        save_callback=lambda s: saves.append(s),
    )
    executor._saves = saves  # Expose for testing
    return executor


# ========== Task Status Tests ==========


class TestTaskStatus:
    """Test task status transitions."""

    def test_start_task_sets_in_progress(self, executor, notes_app_state_with_tasks):
        """start_task marks task as in_progress."""
        executor.start_task("T-001")

        queries = StateQueries(notes_app_state_with_tasks)
        task = queries.get_task("T-001")
        assert task.status == "in_progress"

    def test_complete_task_sets_completed(self, executor, notes_app_state_with_tasks):
        """complete_task marks task as completed."""
        executor.complete_task("T-001", file_path="src/models/note.py")

        queries = StateQueries(notes_app_state_with_tasks)
        task = queries.get_task("T-001")
        assert task.status == "completed"
        assert task.file_path == "src/models/note.py"

    def test_fail_task_sets_failed(self, executor, notes_app_state_with_tasks):
        """fail_task marks task as failed."""
        result = executor.fail_task("T-001", "Test failure", retry_count=3)

        assert result.status == TaskStatus.FAILED
        assert result.error_message == "Test failure"
        assert result.retry_count == 3

        queries = StateQueries(notes_app_state_with_tasks)
        task = queries.get_task("T-001")
        assert task.status == "failed"

    def test_complete_task_returns_result(self, executor):
        """complete_task returns TaskExecutionResult."""
        result = executor.complete_task("T-001", file_path="src/models/note.py")

        assert isinstance(result, TaskExecutionResult)
        assert result.task_id == "T-001"
        assert result.status == TaskStatus.COMPLETED
        assert result.succeeded is True
        assert result.failed is False


# ========== Task Queue Tests ==========


class TestTaskQueue:
    """Test task queuing and retrieval."""

    def test_get_next_pending_task(self, executor, notes_app_state_with_tasks):
        """get_next_pending_task returns first pending task."""
        task = executor.get_next_pending_task()

        assert task is not None
        assert task.id == "T-001"
        assert task.status == "pending"

    def test_get_next_pending_task_none_when_all_complete(
        self, executor, notes_app_state_with_tasks
    ):
        """get_next_pending_task returns None when no pending tasks."""
        # Mark all tasks as completed
        for task in notes_app_state_with_tasks.tasks:
            task.status = "completed"

        result = executor.get_next_pending_task()
        assert result is None

    def test_get_story_pending_tasks(self, executor, notes_app_state_with_tasks):
        """get_story_pending_tasks returns pending tasks for story."""
        tasks = executor.get_story_pending_tasks("S-001")

        assert len(tasks) == 4
        assert all(t.story_id == "S-001" for t in tasks)


# ========== Entity Completion Tests ==========


class TestEntityCompletion:
    """Test entity status updates on task completion."""

    def test_model_task_updates_entity_status(self, executor, notes_app_state_with_tasks):
        """Completing a model task marks entity as implemented."""
        # T-001 is "Define Note model"
        executor.complete_task("T-001", file_path="src/models/note.py")

        queries = StateQueries(notes_app_state_with_tasks)
        # E-002 (Note) should be marked as implemented
        entity = queries.get_entity("E-002")
        assert entity.status == "implemented"
        assert entity.file_path == "src/models/note.py"

    def test_non_model_task_does_not_update_entity(self, executor, notes_app_state_with_tasks):
        """Completing a non-model task doesn't change entity status."""
        # T-003 is "Add Note form component"
        executor.complete_task("T-003", file_path="src/components/NoteForm.tsx")

        queries = StateQueries(notes_app_state_with_tasks)
        entity = queries.get_entity("E-002")
        assert entity.status == "planned"  # Still planned


# ========== Story Completion Tests ==========


class TestStoryCompletion:
    """Test story status updates when all tasks complete."""

    def test_story_completed_when_all_tasks_done(self, executor, notes_app_state_with_tasks):
        """Story marked as completed when all tasks finish."""
        # Complete all S-001 tasks
        executor.complete_task("T-001", "src/models/note.py")
        executor.complete_task("T-002", "src/api/notes.py")
        executor.complete_task("T-003", "src/components/NoteForm.tsx")
        executor.complete_task("T-004", "tests/test_notes.py")

        queries = StateQueries(notes_app_state_with_tasks)
        story = queries.get_story("S-001")
        assert story.status == "completed"

    def test_story_not_completed_when_tasks_pending(self, executor, notes_app_state_with_tasks):
        """Story stays implementing while tasks pending."""
        # Complete only some tasks
        executor.complete_task("T-001", "src/models/note.py")
        executor.complete_task("T-002", "src/api/notes.py")

        queries = StateQueries(notes_app_state_with_tasks)
        story = queries.get_story("S-001")
        assert story.status == "implementing"


# ========== Simulated Execution Tests ==========


class TestSimulatedExecution:
    """Test simulated execution for testing."""

    def test_execute_task_simulated_success(self, executor, notes_app_state_with_tasks):
        """Simulated execution with success."""
        result = executor.execute_task_simulated(
            "T-001", success=True, file_path="src/models/note.py"
        )

        assert result.succeeded is True
        assert result.file_path == "src/models/note.py"

        queries = StateQueries(notes_app_state_with_tasks)
        task = queries.get_task("T-001")
        assert task.status == "completed"

    def test_execute_task_simulated_failure(self, executor, notes_app_state_with_tasks):
        """Simulated execution with failure."""
        result = executor.execute_task_simulated("T-001", success=False)

        assert result.failed is True
        assert result.error_message == "Simulated failure"

    def test_execute_story_tasks_all_success(self, executor, notes_app_state_with_tasks):
        """Execute all story tasks with simulated success."""
        result = executor.execute_story_tasks("S-001", simulate_success=True)

        assert isinstance(result, StoryExecutionResult)
        assert result.story_id == "S-001"
        assert result.completed_count == 4
        assert result.failed_count == 0
        assert result.all_completed is True


# ========== Prompt Generation Tests ==========


class TestPromptGeneration:
    """Test execution prompt generation."""

    def test_get_task_prompt(self, executor, notes_app_state_with_tasks):
        """get_task_prompt generates valid prompt."""
        prompt = executor.get_task_prompt("T-005")

        assert prompt is not None
        assert "T-005" in prompt
        assert "search" in prompt.lower()
        assert "S-003" in prompt

    def test_get_task_prompt_missing_task(self, executor):
        """get_task_prompt returns None for missing task."""
        prompt = executor.get_task_prompt("T-999")
        assert prompt is None

    def test_create_execution_prompt(self, notes_app_state_with_tasks):
        """create_execution_prompt generates full prompt."""
        task = notes_app_state_with_tasks.tasks[4]  # T-005
        story = notes_app_state_with_tasks.stories[1]  # S-003

        prompt = create_execution_prompt(task, story, notes_app_state_with_tasks)

        assert "T-005" in prompt
        assert "Instructions" in prompt
        assert "unit tests" in prompt.lower()


# ========== Notes App Integration Tests ==========


class TestNotesAppExecution:
    """Integration tests using Notes App fixture."""

    def test_all_tasks_complete_and_entities_implemented(self, notes_app_state_with_tasks):
        """Notes App: All tasks complete, entities implemented."""
        saves = []
        executor = TaskExecutor(notes_app_state_with_tasks, lambda s: saves.append(s))

        # Execute all S-001 tasks
        executor.execute_story_tasks("S-001", simulate_success=True)

        queries = StateQueries(notes_app_state_with_tasks)

        # Story should be completed
        story = queries.get_story("S-001")
        assert story.status == "completed"

        # Entity E-002 (Note) should be implemented (from model task)
        entity = queries.get_entity("E-002")
        assert entity.status == "implemented"

        # All tasks should be completed
        tasks = queries.get_story_tasks("S-001")
        assert all(t.status == "completed" for t in tasks)

    def test_multiple_stories_can_execute(self, notes_app_state_with_tasks):
        """Can execute tasks for multiple stories."""
        executor = TaskExecutor(notes_app_state_with_tasks, lambda s: None)

        result1 = executor.execute_story_tasks("S-001", simulate_success=True)
        result2 = executor.execute_story_tasks("S-003", simulate_success=True)

        assert result1.all_completed is True
        assert result2.all_completed is True

        queries = StateQueries(notes_app_state_with_tasks)
        assert queries.get_story("S-001").status == "completed"
        assert queries.get_story("S-003").status == "completed"
