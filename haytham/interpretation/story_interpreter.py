"""Story Interpretation Engine for the Story-to-Implementation Pipeline.

Processes user stories through a structured analysis pipeline to produce
interpreted specifications with explicit ambiguities and assumptions.

Reference: ADR-001d: Story Interpretation Engine
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime

from haytham.project.state_models import Ambiguity, PipelineState, Story
from haytham.project.state_queries import StateQueries
from haytham.project.state_updater import StateUpdater

from .ambiguity_detector import AmbiguityDetector
from .consistency_checker import ConsistencyChecker, ConsistencyReport


@dataclass
class ParsedStory:
    """Parsed components of a user story."""

    story_id: str
    actor: str = ""
    action: str = ""
    object: str = ""
    outcome: str = ""
    verb_type: str = ""  # create, read, update, delete

    @classmethod
    def from_story(cls, story: Story) -> "ParsedStory":
        """Parse a story into structured components."""
        parsed = cls(story_id=story.id)

        user_story = story.user_story.lower()

        # Extract actor (As a <role>)
        if "as a " in user_story:
            actor_start = user_story.find("as a ") + 5
            actor_end = user_story.find(",", actor_start)
            if actor_end == -1:
                actor_end = user_story.find(" i want", actor_start)
            if actor_end > actor_start:
                parsed.actor = user_story[actor_start:actor_end].strip()

        # Extract action and object (I want to <verb> <object>)
        if "i want to " in user_story:
            want_start = user_story.find("i want to ") + 10
            want_end = user_story.find(" so that", want_start)
            if want_end == -1:
                want_end = len(user_story)
            action_text = user_story[want_start:want_end].strip()

            # First word is typically the verb
            parts = action_text.split(" ", 1)
            parsed.action = parts[0]
            parsed.object = parts[1] if len(parts) > 1 else ""

            # Classify verb type
            parsed.verb_type = cls._classify_verb(parsed.action)

        # Extract outcome (so that <benefit>)
        if "so that " in user_story:
            outcome_start = user_story.find("so that ") + 8
            parsed.outcome = user_story[outcome_start:].strip()

        return parsed

    @staticmethod
    def _classify_verb(verb: str) -> str:
        """Classify verb into CRUD category."""
        create_verbs = ["create", "add", "make", "write", "new"]
        read_verbs = ["view", "see", "list", "show", "search", "find", "read", "get"]
        update_verbs = ["edit", "update", "modify", "change"]
        delete_verbs = ["delete", "remove", "trash", "archive"]

        verb_lower = verb.lower()
        if verb_lower in create_verbs:
            return "create"
        elif verb_lower in read_verbs:
            return "read"
        elif verb_lower in update_verbs:
            return "update"
        elif verb_lower in delete_verbs:
            return "delete"
        return "unknown"


@dataclass
class InterpretedStory:
    """Result of story interpretation."""

    story_id: str
    interpreted_at: datetime
    original: Story
    parsed: ParsedStory
    consistency: ConsistencyReport
    auto_resolved_ambiguities: list[Ambiguity] = field(default_factory=list)
    pending_ambiguities: list[Ambiguity] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)
    status: str = "ready"  # ready, blocked, error

    @property
    def is_blocked(self) -> bool:
        """Story is blocked by pending user decisions."""
        return len(self.pending_ambiguities) > 0

    @property
    def all_ambiguities(self) -> list[Ambiguity]:
        """All ambiguities (resolved and pending)."""
        return self.auto_resolved_ambiguities + self.pending_ambiguities


class StoryInterpreter:
    """Main story interpretation engine.

    Processes stories through the interpretation pipeline:
    1. Parse story components
    2. Detect ambiguities
    3. Classify and resolve
    4. Check consistency
    5. Generate interpreted story

    Reference: ADR-001d: Story Interpretation Engine
    """

    def __init__(self, state: PipelineState, save_callback=None):
        """Initialize interpreter with state.

        Args:
            state: Current pipeline state
            save_callback: Optional callback to save state after updates
        """
        self.state = state
        self.queries = StateQueries(state)
        self.updater = StateUpdater(state, save_callback or (lambda s: None))
        self.ambiguity_detector = AmbiguityDetector()
        self.consistency_checker = ConsistencyChecker(state)

    def interpret(self, story: Story) -> InterpretedStory:
        """Interpret a single story.

        Args:
            story: Story to interpret

        Returns:
            InterpretedStory with parsed components and ambiguities
        """
        # Stage 1: Parse story
        parsed = ParsedStory.from_story(story)

        # Stage 2: Detect ambiguities
        detected = self.ambiguity_detector.detect(story)

        # Stage 3: Classify and resolve
        auto, pending = self.ambiguity_detector.classify(detected)

        # Convert to Ambiguity models
        auto_resolved = []
        for amb in auto:
            ambiguity = amb.to_ambiguity("auto_resolvable")
            if amb.default:
                ambiguity.resolved = True
                ambiguity.resolution = amb.default
            auto_resolved.append(ambiguity)

        pending_ambiguities = [amb.to_ambiguity("decision_required") for amb in pending]

        # Stage 4: Consistency check
        consistency = self.consistency_checker.check(story)

        # Stage 5: Collect assumptions
        assumptions = self._collect_assumptions(parsed, auto_resolved)

        # Determine status
        if pending_ambiguities:
            status = "blocked"
        elif not consistency.passed:
            status = "error"
        else:
            status = "ready"

        return InterpretedStory(
            story_id=story.id,
            interpreted_at=datetime.now(UTC),
            original=story,
            parsed=parsed,
            consistency=consistency,
            auto_resolved_ambiguities=auto_resolved,
            pending_ambiguities=pending_ambiguities,
            assumptions=assumptions,
            status=status,
        )

    def interpret_and_update(self, story_id: str) -> InterpretedStory | None:
        """Interpret a story and update state with ambiguities.

        Args:
            story_id: ID of story to interpret (S-XXX)

        Returns:
            InterpretedStory or None if story not found
        """
        story = self.queries.get_story(story_id)
        if not story:
            return None

        # Interpret
        result = self.interpret(story)

        # Update story with ambiguities
        for amb in result.all_ambiguities:
            # Only add if not already present
            existing_questions = [a.question for a in story.ambiguities]
            if amb.question not in existing_questions:
                self.updater.add_story_ambiguity(story_id, amb)

        # Update story status to interpreting
        self.updater.update_story_status(story_id, "interpreting")

        return result

    def apply_user_decisions(self, story_id: str, decisions: dict[str, str]) -> bool:
        """Apply user decisions to pending ambiguities.

        Args:
            story_id: Story ID (S-XXX)
            decisions: Dict of {question: resolution}

        Returns:
            True if all decisions applied successfully
        """
        story = self.queries.get_story(story_id)
        if not story:
            return False

        for question, resolution in decisions.items():
            self.updater.resolve_ambiguity(story_id, question, resolution)

        # Check if all ambiguities are now resolved
        story = self.queries.get_story(story_id)  # Reload
        all_resolved = all(amb.resolved for amb in story.ambiguities)

        if all_resolved:
            self.updater.update_story_status(story_id, "interpreted")

        return True

    def interpret_all_pending(self) -> list[InterpretedStory]:
        """Interpret all pending stories.

        Returns:
            List of InterpretedStory results
        """
        results = []
        for story in self.queries.get_pending_stories():
            result = self.interpret(story)
            results.append(result)
        return results

    def _collect_assumptions(
        self, parsed: ParsedStory, auto_resolved: list[Ambiguity]
    ) -> list[str]:
        """Collect assumptions made during interpretation."""
        assumptions = []

        # Add assumptions from auto-resolved ambiguities
        for amb in auto_resolved:
            if amb.resolved and amb.resolution:
                assumptions.append(f"Assumed: {amb.question} → {amb.resolution}")

        # Add implicit assumptions based on parsing
        if parsed.actor:
            assumptions.append(f"User must be logged in as '{parsed.actor}'")

        return assumptions


def interpret_story(story: Story, state: PipelineState) -> InterpretedStory:
    """Convenience function to interpret a single story.

    Args:
        story: Story to interpret
        state: Pipeline state

    Returns:
        InterpretedStory result
    """
    interpreter = StoryInterpreter(state)
    return interpreter.interpret(story)
