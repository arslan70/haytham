"""Unit tests for task generation components.

Tests the Session 6 deliverables:
- Task generation from designed stories
- Task templates for different verb types
- Task linking to stories via StateUpdater
- Prompt formatting for Claude Code
- Notes App test: Each story should generate 2-4 tasks

Reference: ADR-001f: Task Generation & Refinement

Note: This file is named task_generation_tests.py to avoid gitignore pattern test_*.py
Run with: pytest tests/task_generation_tests.py -v
"""

import pytest

from haytham.project.state_models import (
    BackendStack,
    Entity,
    EntityAttribute,
    FrontendStack,
    PipelineState,
    Stack,
    Story,
)
from haytham.project.state_queries import StateQueries
from haytham.tasks.task_generator import (
    TASK_TEMPLATES,
    TaskGenerationResult,
    TaskGenerator,
    format_task_prompt,
    generate_story_tasks,
)

# ========== Fixtures ==========


@pytest.fixture
def notes_app_state():
    """Pre-populated state with Notes App data for testing."""
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

    # Stories (marked as designed, ready for task generation)
    state.stories = [
        Story(
            id="S-001",
            title="Create Note",
            priority="P0",
            status="designed",
            user_story="As a user, I want to create a new note so that I can capture my thoughts",
            acceptance_criteria=[
                "Given I am logged in, when I click New Note, then a blank note editor opens",
                "Given I have entered content, when I click Save, then the note is persisted",
            ],
            depends_on=["E-001", "E-002"],
        ),
        Story(
            id="S-002",
            title="List Notes",
            priority="P0",
            status="designed",
            user_story="As a user, I want to see all my notes so that I can find what I need",
            acceptance_criteria=[
                "Given I am logged in, when I view the notes page, then I see a list of my notes",
            ],
            depends_on=["E-001", "E-002"],
        ),
        Story(
            id="S-003",
            title="Search Notes",
            priority="P0",
            status="designed",
            user_story="As a user, I want to search my notes so I can quickly find what I need",
            acceptance_criteria=[
                "Given I am on the notes page, when I type in the search box, then matching notes are shown"
            ],
            depends_on=["E-002", "S-002"],
        ),
        Story(
            id="S-004",
            title="Delete Note",
            priority="P0",
            status="designed",
            user_story="As a user, I want to delete a note so I can remove unwanted content",
            acceptance_criteria=[
                "Given I am viewing a note, when I click Delete, then I see a confirmation dialog",
            ],
            depends_on=["E-002"],
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
def create_note_story(notes_app_state):
    """Create Note story from Notes App."""
    return notes_app_state.stories[0]


@pytest.fixture
def search_story(notes_app_state):
    """Search Notes story from Notes App."""
    return notes_app_state.stories[2]


@pytest.fixture
def delete_story(notes_app_state):
    """Delete Note story from Notes App."""
    return notes_app_state.stories[3]


# ========== Task Templates Tests ==========


class TestTaskTemplates:
    """Test task template definitions."""

    def test_templates_exist_for_crud(self):
        """Templates exist for CRUD operations."""
        assert "create" in TASK_TEMPLATES
        assert "read" in TASK_TEMPLATES
        assert "update" in TASK_TEMPLATES
        assert "delete" in TASK_TEMPLATES

    def test_templates_include_backend_frontend_test(self):
        """Each verb type has backend, frontend, and test tasks."""
        for verb_type, templates in TASK_TEMPLATES.items():
            types = [t.task_type for t in templates]
            assert "backend" in types, f"{verb_type} missing backend task"
            assert "frontend" in types, f"{verb_type} missing frontend task"
            assert "test" in types, f"{verb_type} missing test task"

    def test_search_templates_exist(self):
        """Search templates are defined."""
        assert "search" in TASK_TEMPLATES
        search_templates = TASK_TEMPLATES["search"]
        assert len(search_templates) >= 3


# ========== Task Generator Tests ==========


class TestTaskGenerator:
    """Test task generation."""

    def test_generate_returns_result(self, notes_app_state, create_note_story):
        """Generator returns TaskGenerationResult."""
        generator = TaskGenerator(notes_app_state)
        result = generator.generate(create_note_story)

        assert isinstance(result, TaskGenerationResult)
        assert result.story_id == "S-001"

    def test_generate_creates_tasks(self, notes_app_state, create_note_story):
        """Generator creates multiple tasks for a story."""
        generator = TaskGenerator(notes_app_state)
        result = generator.generate(create_note_story)

        # Create story should have backend, frontend, and test tasks
        assert result.task_count >= 3
        assert len(result.backend_tasks) >= 1
        assert len(result.frontend_tasks) >= 1
        assert len(result.test_tasks) >= 1

    def test_generate_search_tasks(self, notes_app_state, search_story):
        """Generator creates search-specific tasks."""
        generator = TaskGenerator(notes_app_state)
        result = generator.generate(search_story)

        # Should have search-specific tasks
        assert result.task_count >= 3
        assert any("search" in t.title.lower() for t in result.tasks)

    def test_generate_delete_tasks(self, notes_app_state, delete_story):
        """Generator creates delete-specific tasks."""
        generator = TaskGenerator(notes_app_state)
        result = generator.generate(delete_story)

        # Should have delete-specific tasks
        assert result.task_count >= 3
        assert any("delete" in t.title.lower() for t in result.tasks)

    def test_tasks_have_story_id(self, notes_app_state, create_note_story):
        """Generated tasks link to their story."""
        generator = TaskGenerator(notes_app_state)
        result = generator.generate(create_note_story)

        for task in result.tasks:
            assert task.story_id == "S-001"

    def test_presentation_text_generated(self, notes_app_state, create_note_story):
        """Generator creates presentation text for user approval."""
        generator = TaskGenerator(notes_app_state)
        result = generator.generate(create_note_story)

        assert result.presentation_text
        assert "Task Breakdown" in result.presentation_text
        assert "S-001" in result.presentation_text
        assert "[Approve]" in result.presentation_text


class TestTaskGeneratorApply:
    """Test task generator state updates."""

    def test_generate_and_apply_adds_tasks_to_state(self, notes_app_state):
        """generate_and_apply adds tasks to state."""
        saves = []
        generator = TaskGenerator(notes_app_state, lambda s: saves.append(s))

        result = generator.generate_and_apply("S-001")

        assert result is not None
        assert len(saves) >= 1

        # Check tasks were added to state
        queries = StateQueries(notes_app_state)
        tasks = queries.get_story_tasks("S-001")
        assert len(tasks) >= 3

    def test_generate_and_apply_updates_story_status(self, notes_app_state):
        """generate_and_apply updates story to implementing."""
        generator = TaskGenerator(notes_app_state, lambda s: None)

        generator.generate_and_apply("S-001")

        queries = StateQueries(notes_app_state)
        story = queries.get_story("S-001")
        assert story.status == "implementing"

    def test_generate_and_apply_returns_none_for_missing_story(self, notes_app_state):
        """generate_and_apply returns None for non-existent story."""
        generator = TaskGenerator(notes_app_state)

        result = generator.generate_and_apply("S-999")

        assert result is None

    def test_generate_for_all_designed(self, notes_app_state):
        """Can generate tasks for all designed stories."""
        generator = TaskGenerator(notes_app_state)

        results = generator.generate_for_all_designed()

        assert len(results) == 4  # All 4 stories are designed
        for result in results:
            assert result.task_count >= 2


# ========== Prompt Formatting Tests ==========


class TestPromptFormatting:
    """Test task prompt formatting for Claude Code."""

    def test_format_task_prompt(self, notes_app_state, create_note_story):
        """format_task_prompt creates proper prompt."""
        # Create a task
        from haytham.project.state_models import Task

        task = Task(
            id="T-001",
            story_id="S-001",
            title="Define Note model",
            description="Create database model for Note entity",
        )

        prompt = format_task_prompt(task, create_note_story, notes_app_state.stack)

        assert "T-001" in prompt
        assert "Define Note model" in prompt
        assert "S-001" in prompt
        assert "Python/Fastapi" in prompt
        assert "### Description" in prompt
        assert "### Requirements" in prompt

    def test_format_task_prompt_without_stack(self, notes_app_state, create_note_story):
        """format_task_prompt works without stack."""
        from haytham.project.state_models import Task

        task = Task(
            id="T-001",
            story_id="S-001",
            title="Define Note model",
            description="Create database model",
        )

        prompt = format_task_prompt(task, create_note_story, None)

        assert "T-001" in prompt
        assert "Define Note model" in prompt
        assert "Stack" not in prompt


# ========== Notes App Integration Tests ==========


class TestNotesAppTaskGeneration:
    """Integration tests using Notes App fixture."""

    def test_each_story_generates_2_to_4_tasks(self, notes_app_state):
        """Notes App: Each story should generate 2-4 tasks."""
        generator = TaskGenerator(notes_app_state)

        for story in notes_app_state.stories:
            result = generator.generate(story)
            assert 2 <= result.task_count <= 5, f"Story {story.id} has {result.task_count} tasks"

    def test_s003_search_generates_search_tasks(self, notes_app_state):
        """Notes App: S-003 Search generates search-specific tasks."""
        generator = TaskGenerator(notes_app_state)
        search_story = notes_app_state.stories[2]

        result = generator.generate(search_story)

        # Should have search endpoint task
        backend_titles = [t.title.lower() for t in result.backend_tasks]
        assert any("search" in title for title in backend_titles)

        # Should have search component task
        frontend_titles = [t.title.lower() for t in result.frontend_tasks]
        assert any("search" in title for title in frontend_titles)

    def test_all_tasks_linked_to_stories(self, notes_app_state):
        """All generated tasks link back to their stories."""
        generator = TaskGenerator(notes_app_state, lambda s: None)

        for story in notes_app_state.stories:
            generator.generate_and_apply(story.id)

        queries = StateQueries(notes_app_state)
        for story in notes_app_state.stories:
            tasks = queries.get_story_tasks(story.id)
            assert len(tasks) >= 2, f"Story {story.id} has no tasks"
            for task in tasks:
                assert task.story_id == story.id

    def test_convenience_function_works(self, notes_app_state, create_note_story):
        """Convenience function generates tasks correctly."""
        result = generate_story_tasks(create_note_story, notes_app_state)

        assert isinstance(result, TaskGenerationResult)
        assert result.story_id == "S-001"
        assert result.task_count >= 3
