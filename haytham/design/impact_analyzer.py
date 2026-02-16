"""Impact Analyzer for Design Evolution.

Analyzes interpreted stories to determine what system changes are required,
including new entities, capabilities, and architectural decisions.

Reference: ADR-001e: System Design Evolution - Stage 1 Impact Analysis
"""

from dataclasses import dataclass, field

from haytham.interpretation.story_interpreter import InterpretedStory, ParsedStory
from haytham.project.state_models import PipelineState, Story
from haytham.project.state_queries import StateQueries


@dataclass
class ProposedEntity:
    """An entity that needs to be created."""

    name: str
    reason: str
    suggested_attributes: list[str] = field(default_factory=list)
    from_story_id: str = ""


@dataclass
class ProposedCapability:
    """A capability that needs to be added."""

    name: str
    description: str
    provides: list[str] = field(default_factory=list)
    from_story_id: str = ""


@dataclass
class ProposedDecision:
    """A design decision that needs to be made."""

    topic: str
    question: str
    options: list[dict] = field(default_factory=list)  # [{id, choice, implications}]
    recommendation: str = ""
    rationale: str = ""
    auto_resolvable: bool = False
    from_story_id: str = ""


@dataclass
class ImpactAnalysisResult:
    """Result of impact analysis for a story."""

    story_id: str
    new_entities: list[ProposedEntity] = field(default_factory=list)
    entity_modifications: list[dict] = field(default_factory=list)
    new_capabilities: list[ProposedCapability] = field(default_factory=list)
    new_decisions: list[ProposedDecision] = field(default_factory=list)
    existing_entities_used: list[str] = field(default_factory=list)

    @property
    def requires_new_entities(self) -> bool:
        return len(self.new_entities) > 0

    @property
    def requires_decisions(self) -> bool:
        return any(not d.auto_resolvable for d in self.new_decisions)


# ========== Capability Templates ==========

CAPABILITY_PATTERNS = {
    "create": {
        "name_template": "Create {entity}",
        "description_template": "Users can create new {entity} records",
        "provides": [
            "Create new {entity}",
            "Validate {entity} data",
            "Persist {entity} to database",
        ],
    },
    "read": {
        "name_template": "{entity} Retrieval",
        "description_template": "Users can view {entity} data",
        "provides": ["Get single {entity} by ID", "List all {entity}"],
    },
    "update": {
        "name_template": "Update {entity}",
        "description_template": "Users can modify existing {entity} records",
        "provides": ["Update {entity} fields", "Validate changes"],
    },
    "delete": {
        "name_template": "Delete {entity}",
        "description_template": "Users can remove {entity} records",
        "provides": ["Delete {entity} by ID", "Handle cascade/cleanup"],
    },
    "search": {
        "name_template": "{entity} Search",
        "description_template": "Users can search {entity} by keyword",
        "provides": ["Search {entity} by query", "Return matching results"],
    },
}


class ImpactAnalyzer:
    """Analyzes stories to determine required system changes.

    Examines interpreted stories to identify:
    - New entities needed
    - Modifications to existing entities
    - New capabilities required
    - Architectural decisions to be made

    Reference: ADR-001e: Impact Analysis
    """

    def __init__(self, state: PipelineState):
        """Initialize with pipeline state.

        Args:
            state: Current pipeline state for checking existing entities
        """
        self.state = state
        self.queries = StateQueries(state)

    def analyze(self, story: Story | InterpretedStory) -> ImpactAnalysisResult:
        """Analyze a story for system impact.

        Args:
            story: Story or InterpretedStory to analyze

        Returns:
            ImpactAnalysisResult with proposed changes
        """
        # Handle both Story and InterpretedStory
        if isinstance(story, InterpretedStory):
            base_story = story.original
            parsed = story.parsed
        else:
            base_story = story
            parsed = ParsedStory.from_story(story)

        result = ImpactAnalysisResult(story_id=base_story.id)

        # Check entity dependencies
        self._analyze_entity_dependencies(base_story, result)

        # Determine capability from verb type
        self._analyze_capabilities(parsed, result)

        # Generate decisions based on story type
        self._analyze_decisions(parsed, base_story, result)

        return result

    def _analyze_entity_dependencies(self, story: Story, result: ImpactAnalysisResult) -> None:
        """Check entity dependencies and identify missing entities."""
        for dep in story.depends_on:
            if dep.startswith("E-"):
                entity = self.queries.get_entity(dep)
                if entity:
                    result.existing_entities_used.append(dep)
                else:
                    # Entity doesn't exist - propose creation
                    result.new_entities.append(
                        ProposedEntity(
                            name=f"Entity {dep}",
                            reason=f"Story {story.id} depends on {dep} which doesn't exist",
                            from_story_id=story.id,
                        )
                    )

    def _analyze_capabilities(self, parsed: ParsedStory, result: ImpactAnalysisResult) -> None:
        """Determine what capabilities the story requires."""
        verb_type = parsed.verb_type
        entity_name = self._extract_entity_name(parsed.object)

        if verb_type in CAPABILITY_PATTERNS:
            pattern = CAPABILITY_PATTERNS[verb_type]
            capability = ProposedCapability(
                name=pattern["name_template"].format(entity=entity_name),
                description=pattern["description_template"].format(entity=entity_name),
                provides=[p.format(entity=entity_name) for p in pattern["provides"]],
                from_story_id=parsed.story_id,
            )
            result.new_capabilities.append(capability)

    def _analyze_decisions(
        self, parsed: ParsedStory, story: Story, result: ImpactAnalysisResult
    ) -> None:
        """Identify architectural decisions needed."""
        # Decision for search implementation
        if parsed.verb_type == "read" and "search" in parsed.action.lower():
            result.new_decisions.append(
                ProposedDecision(
                    topic="search_implementation",
                    question="How should search be implemented?",
                    options=[
                        {
                            "id": "A",
                            "choice": "SQLite LIKE queries",
                            "implications": "Simple, works for small datasets",
                        },
                        {
                            "id": "B",
                            "choice": "SQLite FTS5",
                            "implications": "Better performance, relevance ranking",
                        },
                    ],
                    recommendation="A",
                    rationale="LIKE queries are sufficient for MVP scale",
                    auto_resolvable=True,
                    from_story_id=story.id,
                )
            )

        # Decision for storage approach (if creating entities)
        if parsed.verb_type == "create" and not self.queries.get_decisions():
            result.new_decisions.append(
                ProposedDecision(
                    topic="storage_approach",
                    question="What database should be used?",
                    options=[
                        {
                            "id": "A",
                            "choice": "SQLite",
                            "implications": "Simple, no setup, good for MVP",
                        },
                        {
                            "id": "B",
                            "choice": "PostgreSQL",
                            "implications": "Production-ready, more setup",
                        },
                    ],
                    recommendation="A",
                    rationale="SQLite is simple and sufficient for MVP",
                    auto_resolvable=True,
                    from_story_id=story.id,
                )
            )

    def _extract_entity_name(self, object_text: str) -> str:
        """Extract entity name from parsed object."""
        # Clean up common words
        cleaned = object_text.lower()
        for word in ["a", "an", "the", "my", "new", "all"]:
            cleaned = cleaned.replace(f"{word} ", "")

        # Capitalize first letter
        if cleaned:
            return cleaned.strip().title()
        return "Item"


def analyze_story_impact(story: Story, state: PipelineState) -> ImpactAnalysisResult:
    """Convenience function to analyze a story's impact.

    Args:
        story: Story to analyze
        state: Pipeline state

    Returns:
        ImpactAnalysisResult
    """
    analyzer = ImpactAnalyzer(state)
    return analyzer.analyze(story)
