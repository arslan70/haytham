"""Unit tests for story interpretation components.

Tests the Session 4 deliverables:
- Ambiguity detection from user stories
- Ambiguity classification (auto-resolvable vs decision-required)
- Consistency checking against system state
- Story interpretation pipeline
- Notes App test: S-003 (Search) should detect "search scope" ambiguity

Reference: ADR-001d: Story Interpretation Engine

Run with: pytest tests/test_story_interpretation.py -v
"""

import pytest

from haytham.interpretation.ambiguity_detector import (
    AmbiguityDetector,
    detect_story_ambiguities,
)
from haytham.interpretation.consistency_checker import (
    ConsistencyChecker,
)
from haytham.interpretation.story_interpreter import (
    InterpretedStory,
    ParsedStory,
    StoryInterpreter,
)
from haytham.project.state_models import (
    Ambiguity,
    Entity,
    EntityAttribute,
    PipelineState,
    Story,
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


@pytest.fixture
def create_note_story():
    """Create Note story for testing."""
    return Story(
        id="S-001",
        title="Create Note",
        priority="P0",
        status="pending",
        user_story="As a user, I want to create a new note so that I can capture my thoughts",
        acceptance_criteria=[
            "Given I have entered a title, when I click Save, then the note is persisted",
        ],
    )


@pytest.fixture
def search_story():
    """Search Notes story for testing - should detect search scope ambiguity."""
    return Story(
        id="S-003",
        title="Search Notes",
        priority="P0",
        status="pending",
        user_story="As a user, I want to search my notes so I can quickly find what I need",
        acceptance_criteria=[
            "Given I am on the notes page, when I type in the search box, then matching notes are shown"
        ],
    )


@pytest.fixture
def delete_story():
    """Delete Note story for testing."""
    return Story(
        id="S-004",
        title="Delete Note",
        priority="P0",
        status="pending",
        user_story="As a user, I want to delete a note so I can remove unwanted content",
        acceptance_criteria=[
            "Given I am viewing a note, when I click Delete, then I see a confirmation dialog",
        ],
    )


# ========== Parser Tests ==========


class TestParsedStory:
    """Test story parsing."""

    def test_parse_actor(self, create_note_story):
        """Parser extracts actor from 'As a <role>'."""
        parsed = ParsedStory.from_story(create_note_story)
        assert parsed.actor == "user"

    def test_parse_action(self, create_note_story):
        """Parser extracts action verb."""
        parsed = ParsedStory.from_story(create_note_story)
        assert parsed.action == "create"

    def test_parse_object(self, create_note_story):
        """Parser extracts action object."""
        parsed = ParsedStory.from_story(create_note_story)
        assert "note" in parsed.object.lower()

    def test_parse_outcome(self, create_note_story):
        """Parser extracts outcome from 'so that <benefit>'."""
        parsed = ParsedStory.from_story(create_note_story)
        assert "capture" in parsed.outcome or "thoughts" in parsed.outcome

    def test_classify_verb_create(self, create_note_story):
        """Parser classifies create verb."""
        parsed = ParsedStory.from_story(create_note_story)
        assert parsed.verb_type == "create"

    def test_classify_verb_read(self, search_story):
        """Parser classifies search as read verb."""
        parsed = ParsedStory.from_story(search_story)
        assert parsed.verb_type == "read"

    def test_classify_verb_delete(self, delete_story):
        """Parser classifies delete verb."""
        parsed = ParsedStory.from_story(delete_story)
        assert parsed.verb_type == "delete"


# ========== Ambiguity Detector Tests ==========


class TestAmbiguityDetector:
    """Test ambiguity detection."""

    def test_search_story_detects_scope_ambiguity(self, search_story):
        """Search story should detect search scope ambiguity."""
        detector = AmbiguityDetector()
        ambiguities = detector.detect(search_story)

        # Should detect at least the search scope ambiguity
        search_ambiguities = [a for a in ambiguities if "search" in a.question.lower()]
        assert len(search_ambiguities) >= 1

        # Check the main search scope ambiguity
        scope_amb = next((a for a in ambiguities if "fields" in a.question.lower()), None)
        assert scope_amb is not None
        assert scope_amb.category == "scope"
        assert "Title only" in scope_amb.options
        assert "Title and content" in scope_amb.options

    def test_delete_story_detects_confirmation_ambiguity(self, delete_story):
        """Delete story should detect confirmation ambiguity."""
        detector = AmbiguityDetector()
        ambiguities = detector.detect(delete_story)

        # Should detect delete-related ambiguities
        delete_ambiguities = [a for a in ambiguities if "delete" in a.question.lower()]
        assert len(delete_ambiguities) >= 1

    def test_create_story_detects_content_ambiguity(self, create_note_story):
        """Create story should detect content length ambiguity."""
        detector = AmbiguityDetector()
        ambiguities = detector.detect(create_note_story)

        # Should detect create-related ambiguities
        assert len(ambiguities) >= 1

    def test_classify_search_scope_as_decision_required(self, search_story):
        """Search scope ambiguity should be classified as decision_required."""
        detector = AmbiguityDetector()
        ambiguities = detector.detect(search_story)
        auto, required = detector.classify(ambiguities)

        # Search scope should be in required (not auto-resolvable)
        scope_in_required = any("fields" in a.question.lower() for a in required)
        assert scope_in_required, "Search scope should require user decision"

    def test_classify_search_ui_as_auto_resolvable(self, search_story):
        """Search UI (instant vs submit) should be auto-resolvable."""
        detector = AmbiguityDetector()
        ambiguities = detector.detect(search_story)
        auto, required = detector.classify(ambiguities)

        # Search UI should be auto-resolvable
        ui_in_auto = any("instant" in a.question.lower() for a in auto)
        assert ui_in_auto, "Search UI should be auto-resolvable"


class TestDetectStoryAmbiguities:
    """Test the convenience function."""

    def test_detect_story_ambiguities_returns_ambiguity_models(self, search_story):
        """detect_story_ambiguities returns Ambiguity model instances."""
        ambiguities = detect_story_ambiguities(search_story)
        assert all(isinstance(a, Ambiguity) for a in ambiguities)

    def test_auto_resolved_ambiguities_have_resolution(self, search_story):
        """Auto-resolved ambiguities should have resolution set."""
        ambiguities = detect_story_ambiguities(search_story)
        auto_resolved = [a for a in ambiguities if a.classification == "auto_resolvable"]

        for amb in auto_resolved:
            assert amb.resolved is True
            assert amb.resolution is not None


# ========== Consistency Checker Tests ==========


class TestConsistencyChecker:
    """Test consistency checking."""

    def test_check_passes_for_valid_story(self, notes_app_state):
        """Consistency check passes when entities exist."""
        checker = ConsistencyChecker(notes_app_state)
        story = notes_app_state.stories[0]  # S-001: Create Note

        report = checker.check(story)

        assert report.passed is True
        assert report.passed_count >= 2  # At least E-001 and E-002

    def test_check_fails_for_missing_entity(self, notes_app_state):
        """Consistency check fails when entity doesn't exist."""
        checker = ConsistencyChecker(notes_app_state)

        # Create story with non-existent entity
        bad_story = Story(
            id="S-999",
            title="Bad Story",
            user_story="As a user...",
            depends_on=["E-999"],  # Doesn't exist
        )

        report = checker.check(bad_story)

        assert report.passed is False
        assert "E-999" in str(report.prerequisites_needed)

    def test_check_passes_for_story_dependencies(self, notes_app_state):
        """Consistency check passes when story dependencies exist."""
        checker = ConsistencyChecker(notes_app_state)
        story = notes_app_state.stories[2]  # S-003: Search Notes (depends on S-002)

        report = checker.check(story)

        # Should pass because S-002 exists
        story_check = next((c for c in report.checks if c.check_type == "story_exists"), None)
        assert story_check is not None
        assert story_check.passed is True


# ========== Story Interpreter Tests ==========


class TestStoryInterpreter:
    """Test the main story interpreter."""

    def test_interpret_returns_interpreted_story(self, notes_app_state):
        """Interpreter returns InterpretedStory."""
        interpreter = StoryInterpreter(notes_app_state)
        story = notes_app_state.stories[0]

        result = interpreter.interpret(story)

        assert isinstance(result, InterpretedStory)
        assert result.story_id == "S-001"

    def test_interpret_parses_story(self, notes_app_state):
        """Interpreter parses story components."""
        interpreter = StoryInterpreter(notes_app_state)
        story = notes_app_state.stories[0]

        result = interpreter.interpret(story)

        assert result.parsed.actor == "user"
        assert result.parsed.action == "create"

    def test_interpret_detects_ambiguities(self, notes_app_state):
        """Interpreter detects ambiguities."""
        interpreter = StoryInterpreter(notes_app_state)
        story = notes_app_state.stories[2]  # S-003: Search

        result = interpreter.interpret(story)

        assert len(result.all_ambiguities) >= 1

    def test_interpret_checks_consistency(self, notes_app_state):
        """Interpreter includes consistency report."""
        interpreter = StoryInterpreter(notes_app_state)
        story = notes_app_state.stories[0]

        result = interpreter.interpret(story)

        assert result.consistency is not None
        assert result.consistency.story_id == "S-001"

    def test_interpret_blocked_when_pending_ambiguities(self, notes_app_state):
        """Interpreter sets status to blocked when pending ambiguities exist."""
        interpreter = StoryInterpreter(notes_app_state)
        story = notes_app_state.stories[2]  # S-003: Search has decision_required

        result = interpreter.interpret(story)

        # Should be blocked due to search scope ambiguity
        if result.pending_ambiguities:
            assert result.status == "blocked"
            assert result.is_blocked is True

    def test_interpret_collects_assumptions(self, notes_app_state):
        """Interpreter collects assumptions from auto-resolved ambiguities."""
        interpreter = StoryInterpreter(notes_app_state)
        story = notes_app_state.stories[0]

        result = interpreter.interpret(story)

        # Should have assumptions from auto-resolved and implicit
        assert len(result.assumptions) >= 1


class TestStoryInterpreterUpdate:
    """Test interpreter state update methods."""

    def test_interpret_and_update_adds_ambiguities(self, notes_app_state):
        """interpret_and_update adds ambiguities to story."""
        saves = []
        interpreter = StoryInterpreter(notes_app_state, lambda s: saves.append(s))

        interpreter.interpret_and_update("S-003")

        # Check ambiguities were added to state
        story = next(s for s in notes_app_state.stories if s.id == "S-003")
        assert len(story.ambiguities) >= 1
        assert len(saves) >= 1  # State was saved

    def test_apply_user_decisions_resolves_ambiguity(self, notes_app_state):
        """apply_user_decisions resolves pending ambiguities."""
        saves = []
        interpreter = StoryInterpreter(notes_app_state, lambda s: saves.append(s))

        # First, add ambiguities
        interpreter.interpret_and_update("S-003")

        # Apply decision
        story = next(s for s in notes_app_state.stories if s.id == "S-003")
        if story.ambiguities:
            question = story.ambiguities[0].question
            interpreter.apply_user_decisions("S-003", {question: "Title and content"})

            # Verify resolution
            story = next(s for s in notes_app_state.stories if s.id == "S-003")
            resolved_amb = next((a for a in story.ambiguities if a.question == question), None)
            assert resolved_amb is not None
            assert resolved_amb.resolved is True
            assert resolved_amb.resolution == "Title and content"


# ========== Notes App Integration Tests ==========


class TestNotesAppInterpretation:
    """Integration tests using Notes App fixture."""

    def test_search_story_detects_scope_ambiguity(self, notes_app_state):
        """Notes App: S-003 Search should detect search scope ambiguity."""
        interpreter = StoryInterpreter(notes_app_state)
        search_story = next(s for s in notes_app_state.stories if s.id == "S-003")

        result = interpreter.interpret(search_story)

        # Should have search scope as decision_required
        scope_amb = next(
            (a for a in result.pending_ambiguities if "fields" in a.question.lower()),
            None,
        )
        assert scope_amb is not None, "Search scope ambiguity should be detected"
        assert scope_amb.classification == "decision_required"

    def test_all_stories_pass_consistency(self, notes_app_state):
        """All Notes App stories pass consistency checks."""
        interpreter = StoryInterpreter(notes_app_state)

        for story in notes_app_state.stories:
            result = interpreter.interpret(story)
            assert result.consistency.passed, f"Story {story.id} failed consistency"

    def test_interpret_all_pending(self, notes_app_state):
        """Can interpret all pending stories."""
        interpreter = StoryInterpreter(notes_app_state)

        results = interpreter.interpret_all_pending()

        assert len(results) == 4  # All 4 Notes App stories
        for result in results:
            assert result.parsed.actor == "user"
