"""Unit tests for pipeline state management.

Tests the Session 1 deliverables:
- Pydantic models for state schema
- PipelineStateManager for YAML persistence
- StateQueries for read operations
- StateUpdater for write operations with auto-save
- ID generation utilities

Reference: ADR-001c: System State Model

Note: This file is named pipeline_state_tests.py to avoid gitignore pattern test_*.py
Run with: pytest tests/pipeline_state_tests.py -v
"""

import tempfile
from pathlib import Path

import pytest
import yaml

from haytham.project.id_generator import (
    next_decision_id,
    next_entity_id,
    next_story_id,
    next_task_id,
)
from haytham.project.project_state import PipelineStateManager
from haytham.project.state_models import (
    Ambiguity,
    Decision,
    Entity,
    EntityAttribute,
    EntityRelationship,
    PipelineState,
    Story,
    Task,
)
from haytham.project.state_queries import StateQueries
from haytham.project.state_updater import StateUpdater

# ========== Fixtures ==========


@pytest.fixture
def temp_session_dir():
    """Create a temporary session directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def temp_project_yaml(temp_session_dir):
    """Create a temporary project.yaml with minimal content."""
    project_file = temp_session_dir / "project.yaml"
    data = {
        "system_goal": "Test Notes App",
        "created_at": "2026-01-04T10:00:00Z",
        "updated_at": "2026-01-04T10:00:00Z",
        "status": "in_progress",
        "current_phase": 5,
        "enriched_data": {
            "concept": {"problem": "Testing"},
            "market": None,
            "niche": None,
            "validation": None,
        },
    }
    with open(project_file, "w") as f:
        yaml.dump(data, f)
    return project_file


@pytest.fixture
def empty_pipeline_state():
    """Empty pipeline state for testing."""
    return PipelineState()


@pytest.fixture
def notes_app_state():
    """Pre-populated state with Notes App data for testing.

    This is the canonical test fixture matching the implementation plan's
    Notes App test case.
    """
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
                EntityAttribute(name="name", type="String"),
                EntityAttribute(name="created_at", type="DateTime"),
            ],
            relationships=[
                EntityRelationship(type="has_many", target="E-002", foreign_key="user_id")
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
                EntityAttribute(name="user_id", type="UUID", foreign_key="E-001"),
                EntityAttribute(name="created_at", type="DateTime"),
                EntityAttribute(name="updated_at", type="DateTime"),
            ],
            relationships=[EntityRelationship(type="belongs_to", target="E-001")],
        ),
    ]

    # Stories
    state.stories = [
        Story(
            id="S-001",
            title="Create Note",
            priority="P0",
            status="pending",
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
            status="pending",
            user_story="As a user, I want to see all my notes so that I can find what I need",
            acceptance_criteria=[
                "Given I am logged in, when I view the notes page, then I see a list of my notes",
                "Notes are sorted by last updated, newest first",
            ],
            depends_on=["E-001", "E-002"],
        ),
        Story(
            id="S-003",
            title="Search Notes",
            priority="P0",
            status="pending",
            user_story="As a user, I want to search my notes so I can find what I need",
            acceptance_criteria=[
                "Given I am on the notes page, when I type in the search box, then matching notes are shown"
            ],
            depends_on=["E-002"],
            ambiguities=[
                Ambiguity(
                    question="Should search include note content or just titles?",
                    classification="decision_required",
                    options=["Title only", "Title and content", "Full-text search"],
                    default="Title and content",
                )
            ],
        ),
        Story(
            id="S-004",
            title="Delete Note",
            priority="P0",
            status="pending",
            user_story="As a user, I want to delete a note so I can remove unwanted content",
            acceptance_criteria=[
                "Given I am viewing a note, when I click Delete, then I see a confirmation dialog",
                "When I confirm deletion, then the note is permanently removed",
            ],
            depends_on=["E-002"],
        ),
    ]

    return state


# ========== Pydantic Model Tests ==========


class TestPydanticModels:
    """Test Pydantic model validation and serialization."""

    def test_entity_defaults(self):
        """Entity has correct default values."""
        entity = Entity(name="Test")
        assert entity.id == ""
        assert entity.status == "planned"
        assert entity.attributes == []
        assert entity.relationships == []

    def test_story_defaults(self):
        """Story has correct default values."""
        story = Story(title="Test", user_story="As a user...")
        assert story.id == ""
        assert story.priority == "P0"
        assert story.status == "pending"
        assert story.tasks == []

    def test_task_defaults(self):
        """Task has correct default values."""
        task = Task(story_id="S-001", title="Test Task")
        assert task.id == ""
        assert task.status == "pending"
        assert task.description == ""

    def test_pipeline_state_defaults(self):
        """PipelineState has correct default values."""
        state = PipelineState()
        assert state.schema_version == "1.0"
        assert state.entities == []
        assert state.stories == []
        assert state.tasks == []
        assert state.decisions == []
        assert state.current.chunk == "ready"

    def test_entity_with_attributes(self):
        """Entity can have attributes with all fields."""
        entity = Entity(
            id="E-001",
            name="User",
            attributes=[
                EntityAttribute(name="id", type="UUID", primary_key=True),
                EntityAttribute(name="email", type="String", unique=True),
            ],
        )
        assert len(entity.attributes) == 2
        assert entity.attributes[0].primary_key is True
        assert entity.attributes[1].unique is True


# ========== PipelineStateManager Tests ==========


class TestPipelineStateManager:
    """Test PipelineStateManager CRUD operations."""

    def test_load_raises_if_no_project_yaml(self, temp_session_dir):
        """Loading from non-existent project.yaml raises FileNotFoundError."""
        manager = PipelineStateManager(temp_session_dir)
        with pytest.raises(FileNotFoundError):
            manager.load_pipeline_state()

    def test_load_empty_pipeline_state(self, temp_project_yaml):
        """Loading project.yaml without pipeline section returns empty state."""
        manager = PipelineStateManager(temp_project_yaml.parent)
        state = manager.load_pipeline_state()
        assert state.entities == []
        assert state.stories == []
        assert state.schema_version == "1.0"

    def test_save_creates_pipeline_section(self, temp_project_yaml):
        """Saving pipeline state creates pipeline section in project.yaml."""
        manager = PipelineStateManager(temp_project_yaml.parent)
        state = PipelineState()
        state.entities.append(Entity(id="E-001", name="User"))
        manager.save_pipeline_state(state)

        # Verify pipeline section exists
        with open(temp_project_yaml) as f:
            data = yaml.safe_load(f)
        assert "pipeline" in data
        assert data["pipeline"]["entities"][0]["name"] == "User"

    def test_save_preserves_existing_fields(self, temp_project_yaml):
        """Saving pipeline state doesn't overwrite system_goal, status, etc."""
        manager = PipelineStateManager(temp_project_yaml.parent)
        state = PipelineState()
        state.entities.append(Entity(id="E-001", name="User"))
        manager.save_pipeline_state(state)

        # Verify existing fields preserved
        with open(temp_project_yaml) as f:
            data = yaml.safe_load(f)
        assert data["system_goal"] == "Test Notes App"
        assert data["status"] == "in_progress"
        assert data["current_phase"] == 5
        assert data["enriched_data"]["concept"]["problem"] == "Testing"

    def test_round_trip_with_all_fields(self, temp_project_yaml, notes_app_state):
        """State survives save/load round trip with all fields intact."""
        manager = PipelineStateManager(temp_project_yaml.parent)
        manager.save_pipeline_state(notes_app_state)

        loaded = manager.load_pipeline_state()
        assert len(loaded.entities) == 2
        assert len(loaded.stories) == 4
        assert loaded.entities[0].name == "User"
        assert loaded.stories[2].ambiguities[0].question.startswith("Should search")

    def test_has_pipeline_state(self, temp_project_yaml):
        """has_pipeline_state returns correct value."""
        manager = PipelineStateManager(temp_project_yaml.parent)
        assert manager.has_pipeline_state() is False

        manager.save_pipeline_state(PipelineState())
        assert manager.has_pipeline_state() is True

    def test_initialize_pipeline_state(self, temp_project_yaml):
        """initialize_pipeline_state creates empty state if none exists."""
        manager = PipelineStateManager(temp_project_yaml.parent)
        state = manager.initialize_pipeline_state()
        assert state.schema_version == "1.0"
        assert manager.has_pipeline_state() is True


# ========== StateQueries Tests ==========


class TestStateQueries:
    """Test state query operations."""

    def test_get_entity_by_id(self, notes_app_state):
        """Can retrieve entity by E-XXX ID."""
        queries = StateQueries(notes_app_state)
        entity = queries.get_entity("E-001")
        assert entity is not None
        assert entity.name == "User"
        assert queries.get_entity("E-999") is None

    def test_get_entity_by_name(self, notes_app_state):
        """Can retrieve entity by name."""
        queries = StateQueries(notes_app_state)
        entity = queries.get_entity_by_name("Note")
        assert entity is not None
        assert entity.id == "E-002"
        assert queries.get_entity_by_name("Nonexistent") is None

    def test_entity_exists(self, notes_app_state):
        """entity_exists returns correct boolean."""
        queries = StateQueries(notes_app_state)
        assert queries.entity_exists("User") is True
        assert queries.entity_exists("Note") is True
        assert queries.entity_exists("Nonexistent") is False

    def test_get_story_by_id(self, notes_app_state):
        """Can retrieve story by S-XXX ID."""
        queries = StateQueries(notes_app_state)
        story = queries.get_story("S-001")
        assert story is not None
        assert story.title == "Create Note"
        assert queries.get_story("S-999") is None

    def test_get_pending_stories_ordered(self, notes_app_state):
        """Pending stories returned in priority order."""
        # Modify one story to be P1 and one to be completed
        notes_app_state.stories[1].priority = "P1"
        notes_app_state.stories[3].status = "completed"

        queries = StateQueries(notes_app_state)
        pending = queries.get_pending_stories()

        assert len(pending) == 3
        # P0 stories first (S-001, S-003), then P1 (S-002)
        assert pending[0].id == "S-001"
        assert pending[1].id == "S-003"
        assert pending[2].id == "S-002"

    def test_get_story_tasks(self, notes_app_state):
        """Can get tasks for a story."""
        notes_app_state.tasks = [
            Task(id="T-001", story_id="S-001", title="Task 1"),
            Task(id="T-002", story_id="S-001", title="Task 2"),
            Task(id="T-003", story_id="S-002", title="Task 3"),
        ]

        queries = StateQueries(notes_app_state)
        tasks = queries.get_story_tasks("S-001")
        assert len(tasks) == 2
        assert all(t.story_id == "S-001" for t in tasks)

    def test_get_decisions_affecting(self, notes_app_state):
        """Can get decisions affecting a target."""
        notes_app_state.decisions = [
            Decision(
                id="D-001",
                title="Use SQLite",
                rationale="Simple",
                affects=["E-001", "E-002"],
            ),
            Decision(id="D-002", title="Use React", rationale="Popular", affects=["S-001"]),
        ]

        queries = StateQueries(notes_app_state)
        decisions = queries.get_decisions_affecting("E-001")
        assert len(decisions) == 1
        assert decisions[0].id == "D-001"


# ========== StateUpdater Tests ==========


class TestStateUpdater:
    """Test state update operations."""

    def test_add_entity_assigns_id(self, empty_pipeline_state):
        """Adding entity without ID assigns next sequential ID."""
        saves = []
        updater = StateUpdater(empty_pipeline_state, lambda s: saves.append(s))

        entity = updater.add_entity(Entity(name="User"))
        assert entity.id == "E-001"
        assert len(saves) == 1

        entity2 = updater.add_entity(Entity(name="Note"))
        assert entity2.id == "E-002"

    def test_add_entity_preserves_id(self, empty_pipeline_state):
        """Adding entity with ID preserves it."""
        updater = StateUpdater(empty_pipeline_state, lambda s: None)

        entity = updater.add_entity(Entity(id="E-100", name="User"))
        assert entity.id == "E-100"

    def test_update_entity_status(self, notes_app_state):
        """Can update entity status."""
        saves = []
        updater = StateUpdater(notes_app_state, lambda s: saves.append(s))

        result = updater.update_entity_status("E-001", "implemented", "backend/models/user.py")
        assert result is True
        assert notes_app_state.entities[0].status == "implemented"
        assert notes_app_state.entities[0].file_path == "backend/models/user.py"
        assert len(saves) == 1

    def test_add_story_assigns_id(self, empty_pipeline_state):
        """Adding story without ID assigns next sequential ID."""
        updater = StateUpdater(empty_pipeline_state, lambda s: None)

        story = updater.add_story(Story(title="Test", user_story="As a user..."))
        assert story.id == "S-001"

    def test_add_task_updates_story(self, notes_app_state):
        """Adding task also updates story's task list."""
        updater = StateUpdater(notes_app_state, lambda s: None)

        task = updater.add_task(Task(id="T-001", story_id="S-001", title="Implement model"))
        assert task.id == "T-001"
        assert "T-001" in notes_app_state.stories[0].tasks

    def test_add_task_assigns_id(self, notes_app_state):
        """Adding task without ID assigns next sequential ID."""
        updater = StateUpdater(notes_app_state, lambda s: None)

        task = updater.add_task(Task(story_id="S-001", title="Task 1"))
        assert task.id == "T-001"

        task2 = updater.add_task(Task(story_id="S-001", title="Task 2"))
        assert task2.id == "T-002"

    def test_add_decision_sets_timestamp(self, empty_pipeline_state):
        """Adding decision sets made_at timestamp if not set."""
        updater = StateUpdater(empty_pipeline_state, lambda s: None)

        decision = updater.add_decision(Decision(title="Use SQLite", rationale="Simple"))
        assert decision.id == "D-001"
        assert decision.made_at is not None

    def test_set_current(self, empty_pipeline_state):
        """Can set current processing context."""
        saves = []
        updater = StateUpdater(empty_pipeline_state, lambda s: saves.append(s))

        updater.set_current("S-001", "story-interpretation")
        assert empty_pipeline_state.current.story == "S-001"
        assert empty_pipeline_state.current.chunk == "story-interpretation"
        assert len(saves) == 1

    def test_clear_current(self, notes_app_state):
        """Can clear current processing context."""
        notes_app_state.current.story = "S-001"
        notes_app_state.current.chunk = "task-generation"

        updater = StateUpdater(notes_app_state, lambda s: None)
        updater.clear_current()

        assert notes_app_state.current.story is None
        assert notes_app_state.current.chunk == "ready"

    def test_add_story_ambiguity(self, notes_app_state):
        """Can add ambiguity to a story."""
        updater = StateUpdater(notes_app_state, lambda s: None)

        result = updater.add_story_ambiguity(
            "S-001",
            Ambiguity(
                question="Max note length?",
                classification="auto_resolvable",
                default="10000 characters",
            ),
        )
        assert result is True
        assert len(notes_app_state.stories[0].ambiguities) == 1

    def test_resolve_ambiguity(self, notes_app_state):
        """Can resolve an ambiguity."""
        updater = StateUpdater(notes_app_state, lambda s: None)

        # S-003 already has an ambiguity
        result = updater.resolve_ambiguity(
            "S-003",
            "Should search include note content or just titles?",
            "Title and content",
        )
        assert result is True
        assert notes_app_state.stories[2].ambiguities[0].resolved is True
        assert notes_app_state.stories[2].ambiguities[0].resolution == "Title and content"


# ========== ID Generator Tests ==========


class TestIDGenerator:
    """Test ID generation utilities."""

    def test_next_story_id_empty(self, empty_pipeline_state):
        """First story ID is S-001."""
        assert next_story_id(empty_pipeline_state) == "S-001"

    def test_next_story_id_sequential(self, notes_app_state):
        """Story IDs are sequential."""
        # notes_app_state has S-001 through S-004
        assert next_story_id(notes_app_state) == "S-005"

    def test_next_entity_id_sequential(self, notes_app_state):
        """Entity IDs are sequential."""
        # notes_app_state has E-001 and E-002
        assert next_entity_id(notes_app_state) == "E-003"

    def test_next_task_id_empty(self, empty_pipeline_state):
        """First task ID is T-001."""
        assert next_task_id(empty_pipeline_state) == "T-001"

    def test_next_decision_id_empty(self, empty_pipeline_state):
        """First decision ID is D-001."""
        assert next_decision_id(empty_pipeline_state) == "D-001"

    def test_id_handles_gaps(self, empty_pipeline_state):
        """ID generation handles gaps in sequence."""
        empty_pipeline_state.stories = [
            Story(id="S-001", title="A", user_story="..."),
            Story(id="S-005", title="B", user_story="..."),  # Gap
        ]
        # Should use max + 1, not fill gaps
        assert next_story_id(empty_pipeline_state) == "S-006"


# ========== Notes App Fixture Tests ==========


class TestNotesAppFixture:
    """Test the Notes App fixture matches expected structure."""

    def test_notes_app_has_four_stories(self, notes_app_state):
        """Notes App fixture has exactly 4 stories."""
        assert len(notes_app_state.stories) == 4

    def test_notes_app_has_two_entities(self, notes_app_state):
        """Notes App fixture has exactly 2 entities."""
        assert len(notes_app_state.entities) == 2

    def test_notes_app_story_ids(self, notes_app_state):
        """Notes App stories have correct IDs."""
        ids = [s.id for s in notes_app_state.stories]
        assert ids == ["S-001", "S-002", "S-003", "S-004"]

    def test_notes_app_entity_ids(self, notes_app_state):
        """Notes App entities have correct IDs."""
        ids = [e.id for e in notes_app_state.entities]
        assert ids == ["E-001", "E-002"]

    def test_notes_app_search_has_ambiguity(self, notes_app_state):
        """Search story (S-003) has at least one ambiguity."""
        queries = StateQueries(notes_app_state)
        story = queries.get_story("S-003")
        assert len(story.ambiguities) >= 1
        assert story.ambiguities[0].classification == "decision_required"

    def test_notes_app_user_has_relationship(self, notes_app_state):
        """User entity has has_many relationship to Note."""
        queries = StateQueries(notes_app_state)
        user = queries.get_entity("E-001")
        assert len(user.relationships) == 1
        assert user.relationships[0].type == "has_many"
        assert user.relationships[0].target == "E-002"
