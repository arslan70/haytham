"""Unit tests for MVP spec parser, validator, and state initializer.

Tests the Session 2 deliverables:
- MVPSpecParser for parsing enhanced MVP specifications
- MVP spec validation rules
- State initialization from parsed specs

Reference: ADR-001a: MVP Spec Enhancement

Run with: pytest tests/test_mvp_spec_parser.py -v
"""

import tempfile
from pathlib import Path

import pytest
import yaml

from haytham.project.mvp_spec_parser import MVPSpecParser, ParsedMVPSpec
from haytham.project.mvp_spec_validator import (
    validate_mvp_spec,
)
from haytham.project.project_state import PipelineStateManager
from haytham.project.state_initializer import (
    StateInitializationError,
    initialize_from_mvp_spec_text,
    initialize_pipeline_state,
)
from haytham.project.state_models import (
    Entity,
    EntityAttribute,
    EntityRelationship,
    Story,
)

# ========== Fixtures ==========


@pytest.fixture
def notes_app_mvp_spec():
    """Load the Notes App MVP spec fixture."""
    fixture_path = Path(__file__).parent / "fixtures" / "notes_app_mvp_spec.md"
    with open(fixture_path) as f:
        return f.read()


@pytest.fixture
def temp_session_dir():
    """Create a temporary session directory with project.yaml."""
    with tempfile.TemporaryDirectory() as tmpdir:
        session_dir = Path(tmpdir)
        # Create minimal project.yaml
        project_file = session_dir / "project.yaml"
        data = {
            "system_goal": "Simple Notes App",
            "status": "in_progress",
            "current_phase": 5,
        }
        with open(project_file, "w") as f:
            yaml.dump(data, f)
        yield session_dir


@pytest.fixture
def parser():
    """Create MVPSpecParser instance."""
    return MVPSpecParser()


# ========== MVPSpecParser Tests ==========


class TestMVPSpecParser:
    """Test MVP specification parsing."""

    def test_parse_extracts_entities(self, parser, notes_app_mvp_spec):
        """Parser extracts User and Note entities from Notes App spec."""
        result = parser.parse(notes_app_mvp_spec)

        assert len(result.entities) == 2

        # Check User entity
        user = next((e for e in result.entities if e.name == "User"), None)
        assert user is not None
        assert user.id == "E-001"
        assert user.status == "planned"

        # Check Note entity
        note = next((e for e in result.entities if e.name == "Note"), None)
        assert note is not None
        assert note.id == "E-002"

    def test_parse_extracts_entity_attributes(self, parser, notes_app_mvp_spec):
        """Parser extracts entity attributes with correct types."""
        result = parser.parse(notes_app_mvp_spec)

        user = next((e for e in result.entities if e.name == "User"), None)
        assert user is not None

        # Check for expected attributes
        attr_names = [a.name for a in user.attributes]
        assert "id" in attr_names
        assert "email" in attr_names
        assert "name" in attr_names

        # Check types and constraints
        id_attr = next((a for a in user.attributes if a.name == "id"), None)
        assert id_attr is not None
        assert id_attr.type == "UUID"
        assert id_attr.primary_key

        email_attr = next((a for a in user.attributes if a.name == "email"), None)
        assert email_attr is not None
        assert email_attr.unique

    def test_parse_extracts_entity_relationships(self, parser, notes_app_mvp_spec):
        """Parser extracts entity relationships."""
        result = parser.parse(notes_app_mvp_spec)

        user = next((e for e in result.entities if e.name == "User"), None)
        assert user is not None
        assert len(user.relationships) == 1
        assert user.relationships[0].type == "has_many"
        assert user.relationships[0].target == "E-002"

        note = next((e for e in result.entities if e.name == "Note"), None)
        assert note is not None
        assert len(note.relationships) == 1
        assert note.relationships[0].type == "belongs_to"
        assert note.relationships[0].target == "E-001"

    def test_parse_extracts_stories(self, parser, notes_app_mvp_spec):
        """Parser extracts all 4 stories from Notes App spec."""
        result = parser.parse(notes_app_mvp_spec)

        assert len(result.stories) == 4

        story_ids = [s.id for s in result.stories]
        assert story_ids == ["S-001", "S-002", "S-003", "S-004"]

        story_titles = [s.title for s in result.stories]
        assert "Create Note" in story_titles
        assert "List Notes" in story_titles
        assert "Search Notes" in story_titles
        assert "Delete Note" in story_titles

    def test_parse_extracts_story_dependencies(self, parser, notes_app_mvp_spec):
        """Parser extracts story dependencies correctly."""
        result = parser.parse(notes_app_mvp_spec)

        # S-001 depends on E-001, E-002
        s001 = next((s for s in result.stories if s.id == "S-001"), None)
        assert s001 is not None
        assert "E-001" in s001.depends_on
        assert "E-002" in s001.depends_on

        # S-003 depends on E-002 and S-002
        s003 = next((s for s in result.stories if s.id == "S-003"), None)
        assert s003 is not None
        assert "E-002" in s003.depends_on
        assert "S-002" in s003.depends_on

    def test_parse_extracts_acceptance_criteria(self, parser, notes_app_mvp_spec):
        """Parser extracts acceptance criteria for stories."""
        result = parser.parse(notes_app_mvp_spec)

        s001 = next((s for s in result.stories if s.id == "S-001"), None)
        assert s001 is not None
        assert len(s001.acceptance_criteria) >= 2

    def test_parse_extracts_uncertainties(self, parser, notes_app_mvp_spec):
        """Parser extracts uncertainty registry."""
        result = parser.parse(notes_app_mvp_spec)

        assert len(result.uncertainties) == 2

        # Check first ambiguity is attached to S-003
        s003 = next((s for s in result.stories if s.id == "S-003"), None)
        assert s003 is not None
        assert len(s003.ambiguities) >= 1
        assert s003.ambiguities[0].classification == "decision_required"

    def test_parse_extracts_ambiguity_options(self, parser, notes_app_mvp_spec):
        """Parser extracts ambiguity options."""
        result = parser.parse(notes_app_mvp_spec)

        s003 = next((s for s in result.stories if s.id == "S-003"), None)
        assert s003 is not None
        assert len(s003.ambiguities) >= 1

        amb = s003.ambiguities[0]
        assert len(amb.options) >= 2

    def test_has_pipeline_data(self, parser, notes_app_mvp_spec):
        """Parser detects pipeline data complete marker."""
        assert parser.has_pipeline_data(notes_app_mvp_spec)

    def test_validate_completeness_passes(self, parser, notes_app_mvp_spec):
        """Validate completeness passes for valid spec."""
        missing = parser.validate_completeness(notes_app_mvp_spec)
        assert len(missing) == 0

    def test_validate_completeness_fails_for_missing_sections(self, parser):
        """Validate completeness fails when sections are missing."""
        incomplete_spec = "# Just a title\n\nNo domain model here."
        missing = parser.validate_completeness(incomplete_spec)
        assert "DOMAIN MODEL section" in missing
        assert "STORY DEPENDENCY GRAPH section" in missing
        assert "PIPELINE_DATA_COMPLETE marker" in missing


# ========== MVP Spec Validator Tests ==========


class TestMVPSpecValidator:
    """Test MVP spec validation rules."""

    def test_validate_passes_for_valid_spec(self, parser, notes_app_mvp_spec):
        """Validation passes for Notes App spec."""
        parsed = parser.parse(notes_app_mvp_spec)
        errors = validate_mvp_spec(parsed)
        assert len(errors) == 0

    def test_validate_catches_missing_entity(self, parser):
        """Validation catches story depending on non-existent entity."""
        parsed = ParsedMVPSpec()
        parsed.entities = [
            Entity(id="E-001", name="User", attributes=[EntityAttribute(name="id", type="UUID")])
        ]
        parsed.stories = [
            Story(
                id="S-001",
                title="Test",
                user_story="As a user...",
                depends_on=["E-001", "E-999"],  # E-999 doesn't exist
            )
        ]

        errors = validate_mvp_spec(parsed)
        assert len(errors) >= 1
        assert any("E-999" in e and "does not exist" in e for e in errors)

    def test_validate_catches_duplicate_entity_id(self):
        """Validation catches duplicate entity IDs."""
        parsed = ParsedMVPSpec()
        parsed.entities = [
            Entity(id="E-001", name="User", attributes=[EntityAttribute(name="id", type="UUID")]),
            Entity(
                id="E-001", name="Note", attributes=[EntityAttribute(name="id", type="UUID")]
            ),  # Duplicate!
        ]

        errors = validate_mvp_spec(parsed)
        assert any("Duplicate entity ID: E-001" in e for e in errors)

    def test_validate_catches_duplicate_story_id(self):
        """Validation catches duplicate story IDs."""
        parsed = ParsedMVPSpec()
        parsed.entities = [
            Entity(id="E-001", name="User", attributes=[EntityAttribute(name="id", type="UUID")])
        ]
        parsed.stories = [
            Story(id="S-001", title="First", user_story="As a user..."),
            Story(id="S-001", title="Second", user_story="As a user..."),  # Duplicate!
        ]

        errors = validate_mvp_spec(parsed)
        assert any("Duplicate story ID: S-001" in e for e in errors)

    def test_validate_catches_circular_dependency(self):
        """Validation catches circular dependencies between stories."""
        parsed = ParsedMVPSpec()
        parsed.entities = [
            Entity(id="E-001", name="User", attributes=[EntityAttribute(name="id", type="UUID")])
        ]
        parsed.stories = [
            Story(id="S-001", title="A", user_story="...", depends_on=["S-002"]),
            Story(id="S-002", title="B", user_story="...", depends_on=["S-003"]),
            Story(id="S-003", title="C", user_story="...", depends_on=["S-001"]),  # Cycle!
        ]

        errors = validate_mvp_spec(parsed)
        assert any("Circular dependency" in e for e in errors)

    def test_validate_catches_missing_entity_name(self):
        """Validation catches entity without name."""
        parsed = ParsedMVPSpec()
        parsed.entities = [
            Entity(id="E-001", name="", attributes=[EntityAttribute(name="id", type="UUID")])
        ]

        errors = validate_mvp_spec(parsed)
        assert any("missing name" in e for e in errors)

    def test_validate_catches_entity_without_attributes(self):
        """Validation catches entity without attributes."""
        parsed = ParsedMVPSpec()
        parsed.entities = [
            Entity(id="E-001", name="User", attributes=[])  # No attributes!
        ]

        errors = validate_mvp_spec(parsed)
        assert any("no attributes" in e for e in errors)

    def test_validate_catches_invalid_relationship_target(self):
        """Validation catches relationship to non-existent entity."""
        parsed = ParsedMVPSpec()
        parsed.entities = [
            Entity(
                id="E-001",
                name="User",
                attributes=[EntityAttribute(name="id", type="UUID")],
                relationships=[
                    EntityRelationship(type="has_many", target="E-999")
                ],  # E-999 doesn't exist
            )
        ]

        errors = validate_mvp_spec(parsed)
        assert any("E-999" in e and "does not exist" in e for e in errors)


# ========== State Initializer Tests ==========


class TestStateInitializer:
    """Test state initialization from parsed MVP spec."""

    def test_initialize_creates_pipeline_state(self, parser, notes_app_mvp_spec, temp_session_dir):
        """Initialize creates pipeline state in project.yaml."""
        parsed = parser.parse(notes_app_mvp_spec)
        manager = PipelineStateManager(temp_session_dir)

        state = initialize_pipeline_state(manager, parsed)

        assert state is not None
        assert len(state.entities) == 2
        assert len(state.stories) == 4
        assert manager.has_pipeline_state()

    def test_initialize_sets_entity_status_to_planned(
        self, parser, notes_app_mvp_spec, temp_session_dir
    ):
        """Initialize sets all entity statuses to planned."""
        parsed = parser.parse(notes_app_mvp_spec)
        manager = PipelineStateManager(temp_session_dir)

        state = initialize_pipeline_state(manager, parsed)

        for entity in state.entities:
            assert entity.status == "planned"

    def test_initialize_sets_story_status_to_pending(
        self, parser, notes_app_mvp_spec, temp_session_dir
    ):
        """Initialize sets all story statuses to pending."""
        parsed = parser.parse(notes_app_mvp_spec)
        manager = PipelineStateManager(temp_session_dir)

        state = initialize_pipeline_state(manager, parsed)

        for story in state.stories:
            assert story.status == "pending"

    def test_initialize_preserves_existing_project_yaml_fields(
        self, parser, notes_app_mvp_spec, temp_session_dir
    ):
        """Initialize preserves system_goal and other fields."""
        parsed = parser.parse(notes_app_mvp_spec)
        manager = PipelineStateManager(temp_session_dir)

        initialize_pipeline_state(manager, parsed)

        # Load raw YAML to check
        with open(temp_session_dir / "project.yaml") as f:
            data = yaml.safe_load(f)

        assert data["system_goal"] == "Simple Notes App"
        assert data["status"] == "in_progress"
        assert "pipeline" in data

    def test_initialize_from_text(self, notes_app_mvp_spec, temp_session_dir):
        """Initialize from MVP spec text directly."""
        state = initialize_from_mvp_spec_text(temp_session_dir, notes_app_mvp_spec)

        assert len(state.entities) == 2
        assert len(state.stories) == 4

    def test_initialize_fails_for_invalid_spec(self, temp_session_dir):
        """Initialize raises error for invalid spec."""
        invalid_spec = """
## DOMAIN MODEL

### E-001: User
**Attributes:**
- id: UUID (primary_key)

## STORY DEPENDENCY GRAPH

### S-001: Test Story
**User Story:** As a user...
**Priority:** P0
**Depends On:** E-999
**Acceptance Criteria:**
- Test criterion

---
PIPELINE_DATA_COMPLETE: true
ENTITY_COUNT: 1
STORY_COUNT: 1
UNCERTAINTY_COUNT: 0
---
"""
        with pytest.raises(StateInitializationError) as exc_info:
            initialize_from_mvp_spec_text(temp_session_dir, invalid_spec)

        assert "E-999" in str(exc_info.value) or "does not exist" in str(exc_info.value)

    def test_initialize_fails_for_missing_sections(self, temp_session_dir):
        """Initialize raises error for missing sections."""
        incomplete_spec = "# Just a title\n\nNo pipeline data."

        with pytest.raises(StateInitializationError) as exc_info:
            initialize_from_mvp_spec_text(temp_session_dir, incomplete_spec)

        assert "missing required sections" in str(exc_info.value)

    def test_initialize_sets_current_chunk(self, parser, notes_app_mvp_spec, temp_session_dir):
        """Initialize sets current.chunk to initialized."""
        parsed = parser.parse(notes_app_mvp_spec)
        manager = PipelineStateManager(temp_session_dir)

        state = initialize_pipeline_state(manager, parsed)

        assert state.current.chunk == "initialized"
        assert state.current.story is None


# ========== Integration Tests ==========


class TestNotesAppEndToEnd:
    """End-to-end tests using Notes App fixture."""

    def test_full_pipeline_parse_validate_initialize(self, notes_app_mvp_spec, temp_session_dir):
        """Full pipeline: parse -> validate -> initialize."""
        # Parse
        parser = MVPSpecParser()
        parsed = parser.parse(notes_app_mvp_spec)

        # Validate
        errors = validate_mvp_spec(parsed)
        assert len(errors) == 0, f"Validation errors: {errors}"

        # Initialize
        manager = PipelineStateManager(temp_session_dir)
        state = initialize_pipeline_state(manager, parsed)

        # Verify final state
        assert len(state.entities) == 2
        assert len(state.stories) == 4
        assert state.entities[0].id == "E-001"
        assert state.stories[0].id == "S-001"

    def test_notes_app_has_correct_structure(self, notes_app_mvp_spec, temp_session_dir):
        """Notes App initializes with correct structure."""
        state = initialize_from_mvp_spec_text(temp_session_dir, notes_app_mvp_spec)

        # Check entities
        entity_names = [e.name for e in state.entities]
        assert "User" in entity_names
        assert "Note" in entity_names

        # Check stories
        story_titles = [s.title for s in state.stories]
        assert "Create Note" in story_titles
        assert "List Notes" in story_titles
        assert "Search Notes" in story_titles
        assert "Delete Note" in story_titles

        # Check ambiguities on S-003
        s003 = next((s for s in state.stories if s.id == "S-003"), None)
        assert s003 is not None
        assert len(s003.ambiguities) >= 1
