"""Unit tests for design evolution components.

Tests the Session 5 deliverables:
- Impact analysis for stories
- Conflict detection
- Decision generation
- Entity registration as "planned"
- Notes App test: S-001 should register E-002 (Note) as planned

Reference: ADR-001e: System Design Evolution

Note: This file is named design_evolution_tests.py to avoid gitignore pattern test_*.py
Run with: pytest tests/design_evolution_tests.py -v
"""

import pytest

from haytham.design.design_evolution import (
    DesignEvolutionEngine,
    DesignEvolutionResult,
    evolve_story_design,
)
from haytham.design.impact_analyzer import (
    ImpactAnalysisResult,
    ImpactAnalyzer,
)
from haytham.project.state_models import (
    Decision,
    Entity,
    EntityAttribute,
    PipelineState,
    Story,
)
from haytham.project.state_queries import StateQueries

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
            ],
            depends_on=["E-002"],
        ),
    ]

    return state


@pytest.fixture
def empty_state():
    """Empty pipeline state."""
    return PipelineState()


@pytest.fixture
def create_note_story(notes_app_state):
    """Create Note story from Notes App."""
    return notes_app_state.stories[0]


@pytest.fixture
def search_story(notes_app_state):
    """Search Notes story from Notes App."""
    return notes_app_state.stories[2]


# ========== Impact Analyzer Tests ==========


class TestImpactAnalyzer:
    """Test impact analysis."""

    def test_analyze_returns_result(self, notes_app_state, create_note_story):
        """Analyzer returns ImpactAnalysisResult."""
        analyzer = ImpactAnalyzer(notes_app_state)
        result = analyzer.analyze(create_note_story)
        assert isinstance(result, ImpactAnalysisResult)
        assert result.story_id == "S-001"

    def test_analyze_identifies_existing_entities(self, notes_app_state, create_note_story):
        """Analyzer identifies existing entities used."""
        analyzer = ImpactAnalyzer(notes_app_state)
        result = analyzer.analyze(create_note_story)

        # S-001 depends on E-001 and E-002
        assert "E-001" in result.existing_entities_used
        assert "E-002" in result.existing_entities_used

    def test_analyze_proposes_capability(self, notes_app_state, create_note_story):
        """Analyzer proposes capability based on verb type."""
        analyzer = ImpactAnalyzer(notes_app_state)
        result = analyzer.analyze(create_note_story)

        # Create story should propose "Create X" capability
        assert len(result.new_capabilities) >= 1
        cap_names = [c.name for c in result.new_capabilities]
        assert any("Create" in name for name in cap_names)

    def test_analyze_storage_decision_for_create(self, notes_app_state, create_note_story):
        """Analyzer proposes storage decision for create story."""
        analyzer = ImpactAnalyzer(notes_app_state)
        result = analyzer.analyze(create_note_story)

        # Should propose storage approach decision (if no decisions exist)
        storage_decisions = [d for d in result.new_decisions if "storage" in d.topic]
        assert len(storage_decisions) >= 1

    def test_analyze_search_decision(self, notes_app_state, search_story):
        """Analyzer proposes search implementation decision."""
        analyzer = ImpactAnalyzer(notes_app_state)
        result = analyzer.analyze(search_story)

        # Should propose search implementation decision
        search_decisions = [d for d in result.new_decisions if "search" in d.topic]
        assert len(search_decisions) >= 1
        assert search_decisions[0].auto_resolvable is True

    def test_analyze_missing_entity(self, empty_state):
        """Analyzer identifies missing entity dependency."""
        story = Story(
            id="S-TEST",
            title="Test Story",
            user_story="As a user, I want to do something",
            depends_on=["E-999"],  # Doesn't exist
        )
        analyzer = ImpactAnalyzer(empty_state)
        result = analyzer.analyze(story)

        assert len(result.new_entities) >= 1
        assert result.requires_new_entities


# ========== Design Evolution Engine Tests ==========


class TestDesignEvolutionEngine:
    """Test design evolution engine."""

    def test_evolve_returns_result(self, notes_app_state, create_note_story):
        """Evolve returns DesignEvolutionResult."""
        engine = DesignEvolutionEngine(notes_app_state)
        result = engine.evolve(create_note_story)

        assert isinstance(result, DesignEvolutionResult)
        assert result.story_id == "S-001"

    def test_evolve_no_conflicts_for_simple_story(self, notes_app_state, create_note_story):
        """Simple CRUD story has no conflicts."""
        engine = DesignEvolutionEngine(notes_app_state)
        result = engine.evolve(create_note_story)

        assert result.has_conflicts is False
        assert result.status != "blocked_on_conflicts"

    def test_evolve_generates_decisions(self, notes_app_state, create_note_story):
        """Evolve generates auto-resolvable decisions."""
        engine = DesignEvolutionEngine(notes_app_state)
        result = engine.evolve(create_note_story)

        # Should have decisions from auto-resolvable proposals
        # Note: decisions_made is populated only for auto-resolvable ones
        assert result.impact is not None
        auto_decisions = [d for d in result.impact.new_decisions if d.auto_resolvable]
        assert len(auto_decisions) >= 1

    def test_evolve_and_apply_updates_state(self, notes_app_state, create_note_story):
        """evolve_and_apply updates state with decisions."""
        saves = []
        engine = DesignEvolutionEngine(notes_app_state, lambda s: saves.append(s))

        result = engine.evolve_and_apply(create_note_story, auto_approve=True)

        assert result.status == "ready"
        assert len(saves) >= 1  # State was saved

        # Story status should be updated to "designed"
        queries = StateQueries(notes_app_state)
        story = queries.get_story("S-001")
        assert story.status == "designed"

    def test_evolve_registers_decisions(self, notes_app_state, create_note_story):
        """Applied evolution registers decisions in state."""
        engine = DesignEvolutionEngine(notes_app_state, lambda s: None)
        engine.evolve_and_apply(create_note_story, auto_approve=True)

        queries = StateQueries(notes_app_state)
        decisions = queries.get_decisions()
        assert len(decisions) >= 1


class TestEntityRegistration:
    """Test entity registration as planned."""

    def test_register_entity_as_planned(self, notes_app_state):
        """Can register entity as planned."""
        engine = DesignEvolutionEngine(notes_app_state, lambda s: None)

        # E-002 should already be planned
        result = engine.register_entity_as_planned("E-002")
        assert result is True

    def test_register_all_story_entities(self, notes_app_state, create_note_story):
        """Can register all entities from story dependencies."""
        engine = DesignEvolutionEngine(notes_app_state, lambda s: None)

        registered = engine.register_all_story_entities(create_note_story)

        # Should include E-001 and E-002
        assert "E-001" in registered
        assert "E-002" in registered

    def test_s001_registers_e002_as_planned(self, notes_app_state):
        """Notes App: S-001 should verify E-002 (Note) is planned."""
        engine = DesignEvolutionEngine(notes_app_state, lambda s: None)
        story = notes_app_state.stories[0]  # S-001

        # Verify E-002 is in dependencies
        assert "E-002" in story.depends_on

        # Register entities
        registered = engine.register_all_story_entities(story)

        # E-002 should be registered
        assert "E-002" in registered

        # Verify E-002 status is planned
        queries = StateQueries(notes_app_state)
        entity = queries.get_entity("E-002")
        assert entity is not None
        assert entity.status == "planned"


# ========== Conflict Detection Tests ==========


class TestConflictDetection:
    """Test conflict detection."""

    def test_no_conflicts_for_new_story(self, notes_app_state, create_note_story):
        """No conflicts when there are no existing decisions."""
        engine = DesignEvolutionEngine(notes_app_state)
        result = engine.evolve(create_note_story)

        assert result.has_conflicts is False

    def test_conflict_detection_with_existing_decision(self, notes_app_state):
        """Conflict detected when decision topic matches existing."""
        # Add an existing decision
        notes_app_state.decisions.append(
            Decision(
                id="D-001",
                title="search_implementation",  # Same topic as search story proposes
                rationale="Already decided",
                affects=["S-003"],
            )
        )

        engine = DesignEvolutionEngine(notes_app_state)
        search_story = notes_app_state.stories[2]  # S-003

        result = engine.evolve(search_story)

        # Should detect conflict
        assert result.has_conflicts is True
        assert result.status == "blocked_on_conflicts"


# ========== Integration Tests ==========


class TestNotesAppDesignEvolution:
    """Integration tests using Notes App fixture."""

    def test_all_stories_evolve_without_conflicts(self, notes_app_state):
        """All Notes App stories evolve without conflicts."""
        engine = DesignEvolutionEngine(notes_app_state, lambda s: None)

        for story in notes_app_state.stories:
            result = engine.evolve(story)
            assert not result.has_conflicts, f"Story {story.id} has conflicts"

    def test_create_note_story_full_evolution(self, notes_app_state):
        """Full evolution of Create Note story."""
        saves = []
        engine = DesignEvolutionEngine(notes_app_state, lambda s: saves.append(s))

        story = notes_app_state.stories[0]  # S-001: Create Note
        result = engine.evolve_and_apply(story, auto_approve=True)

        # Should complete successfully
        assert result.status == "ready"

        # Should have registered entities
        assert "E-001" in result.impact.existing_entities_used
        assert "E-002" in result.impact.existing_entities_used

        # Story should be marked as designed
        queries = StateQueries(notes_app_state)
        updated_story = queries.get_story("S-001")
        assert updated_story.status == "designed"

    def test_search_story_proposes_search_decision(self, notes_app_state):
        """Search story proposes auto-resolvable search decision."""
        engine = DesignEvolutionEngine(notes_app_state)
        story = notes_app_state.stories[2]  # S-003: Search Notes

        result = engine.evolve(story)

        # Should have search decision
        search_decisions = [d for d in result.impact.new_decisions if "search" in d.topic]
        assert len(search_decisions) >= 1
        assert search_decisions[0].recommendation == "A"  # LIKE queries

    def test_evolve_convenience_function(self, notes_app_state):
        """Convenience function works correctly."""
        story = notes_app_state.stories[0]
        result = evolve_story_design(story, notes_app_state)

        assert isinstance(result, DesignEvolutionResult)
        assert result.story_id == "S-001"
