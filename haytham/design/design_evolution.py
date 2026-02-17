"""Design Evolution Engine for the Story-to-Implementation Pipeline.

Maps interpreted stories to system state changes, maintaining global coherence
by detecting conflicts and generating architectural decisions.

Reference: ADR-001e: System Design Evolution
"""

from dataclasses import dataclass, field

from haytham.interpretation.story_interpreter import InterpretedStory
from haytham.project.state_models import Decision, Entity, PipelineState, Story
from haytham.project.state_queries import StateQueries
from haytham.project.state_updater import StateUpdater

from .impact_analyzer import ImpactAnalysisResult, ImpactAnalyzer, ProposedDecision


@dataclass
class ConflictInfo:
    """Information about a detected conflict."""

    conflict_type: str  # decision_contradiction, entity_incompatibility, etc.
    description: str
    existing_id: str  # ID of the conflicting item
    proposed_change: str
    resolution_suggestions: list[str] = field(default_factory=list)


@dataclass
class DesignEvolutionResult:
    """Result of design evolution analysis."""

    story_id: str
    status: str  # ready, blocked_on_conflicts, blocked_on_approval
    impact: ImpactAnalysisResult
    conflicts: list[ConflictInfo] = field(default_factory=list)
    decisions_made: list[Decision] = field(default_factory=list)
    entities_registered: list[str] = field(default_factory=list)  # Entity IDs
    requires_approval: bool = False
    approval_reason: str = ""

    @property
    def is_blocked(self) -> bool:
        return self.status.startswith("blocked")

    @property
    def has_conflicts(self) -> bool:
        return len(self.conflicts) > 0


class DesignEvolutionEngine:
    """Main design evolution engine.

    Processes interpreted stories through:
    1. Impact analysis - determine required changes
    2. Conflict detection - check against existing state
    3. Decision generation - create architectural decisions
    4. State update - register entities and record decisions

    Reference: ADR-001e: System Design Evolution
    """

    def __init__(self, state: PipelineState, save_callback=None):
        """Initialize with pipeline state.

        Args:
            state: Current pipeline state
            save_callback: Optional callback to save state after updates
        """
        self.state = state
        self.queries = StateQueries(state)
        self.updater = StateUpdater(state, save_callback or (lambda s: None))
        self.impact_analyzer = ImpactAnalyzer(state)

    def evolve(self, story: Story | InterpretedStory) -> DesignEvolutionResult:
        """Run design evolution for a story.

        Args:
            story: Story or InterpretedStory to process

        Returns:
            DesignEvolutionResult with analysis and proposed changes
        """
        # Get story ID
        if isinstance(story, InterpretedStory):
            story_id = story.story_id
            base_story = story.original
        else:
            story_id = story.id
            base_story = story

        # Stage 1: Impact analysis
        impact = self.impact_analyzer.analyze(story)

        # Stage 2: Conflict detection
        conflicts = self._detect_conflicts(impact, base_story)

        # If conflicts, block and return
        if conflicts:
            return DesignEvolutionResult(
                story_id=story_id,
                status="blocked_on_conflicts",
                impact=impact,
                conflicts=conflicts,
                requires_approval=True,
                approval_reason="Conflicts detected that require resolution",
            )

        # Stage 3: Decision generation
        decisions_made = self._generate_decisions(impact)

        # Stage 4: Determine if approval needed
        requires_approval = self._requires_approval(impact)

        return DesignEvolutionResult(
            story_id=story_id,
            status="ready" if not requires_approval else "blocked_on_approval",
            impact=impact,
            decisions_made=decisions_made,
            requires_approval=requires_approval,
            approval_reason="New capability requires confirmation" if requires_approval else "",
        )

    def evolve_and_apply(
        self, story: Story | InterpretedStory, auto_approve: bool = False
    ) -> DesignEvolutionResult:
        """Evolve design and apply changes to state.

        Args:
            story: Story to process
            auto_approve: If True, auto-approve changes that normally need approval

        Returns:
            DesignEvolutionResult with applied changes
        """
        result = self.evolve(story)

        # If blocked on conflicts, don't apply
        if result.status == "blocked_on_conflicts":
            return result

        # If needs approval and not auto-approved, don't apply
        if result.requires_approval and not auto_approve:
            return result

        # Apply changes
        self._apply_changes(result)

        # Update status
        result.status = "ready"
        result.requires_approval = False

        return result

    def _detect_conflicts(self, impact: ImpactAnalysisResult, story: Story) -> list[ConflictInfo]:
        """Detect conflicts with existing state."""
        conflicts = []

        # Check for decision contradictions
        existing_decisions = self.queries.get_decisions()
        for proposed in impact.new_decisions:
            for existing in existing_decisions:
                if self._decisions_conflict(proposed, existing):
                    conflicts.append(
                        ConflictInfo(
                            conflict_type="decision_contradiction",
                            description=f"Proposed decision on '{proposed.topic}' may conflict with existing {existing.id}",
                            existing_id=existing.id,
                            proposed_change=proposed.question,
                            resolution_suggestions=[
                                "Override existing",
                                "Adapt to work within existing",
                            ],
                        )
                    )

        # Check for capability overlap (simplified - just check for duplicate names)
        # In a full implementation, this would be more sophisticated
        # For POC, we skip this check

        return conflicts

    def _decisions_conflict(self, proposed: ProposedDecision, existing: Decision) -> bool:
        """Check if proposed decision conflicts with existing one.

        For POC, this is a simple check - only flag as conflict if
        the topics are identical but recommendations differ.
        """
        # Simple check: same topic might indicate conflict
        # In practice, this would be more sophisticated
        if proposed.topic.lower() == existing.title.lower().replace(" ", "_"):
            return True
        return False

    def _generate_decisions(self, impact: ImpactAnalysisResult) -> list[Decision]:
        """Generate Decision objects from proposed decisions."""
        decisions = []

        for proposed in impact.new_decisions:
            if proposed.auto_resolvable and proposed.recommendation:
                # Auto-resolve with recommendation
                decision = Decision(
                    title=f"Use {proposed.recommendation} for {proposed.topic}",
                    rationale=proposed.rationale,
                    affects=[impact.story_id],
                )
                decisions.append(decision)

        return decisions

    def _requires_approval(self, impact: ImpactAnalysisResult) -> bool:
        """Determine if changes require human approval."""
        # Require approval for:
        # 1. Non-auto-resolvable decisions
        # 2. New entities
        # 3. Entity modifications

        if any(not d.auto_resolvable for d in impact.new_decisions):
            return True

        if impact.new_entities:
            return True

        if impact.entity_modifications:
            return True

        return False

    def _apply_changes(self, result: DesignEvolutionResult) -> None:
        """Apply design evolution changes to state."""
        story_id = result.story_id

        # Register decisions
        for decision in result.decisions_made:
            added = self.updater.add_decision(decision)
            result.decisions_made = [
                added if d.title == added.title else d for d in result.decisions_made
            ]

        # Register any new entities as "planned"
        for proposed_entity in result.impact.new_entities:
            entity = Entity(
                name=proposed_entity.name,
                status="planned",
            )
            added = self.updater.add_entity(entity)
            result.entities_registered.append(added.id)

        # Update story status to "designed"
        self.updater.update_story_status(story_id, "designed")

        # Set current context
        self.updater.set_current(story_id, "design-evolution")

    def register_entity_as_planned(self, entity_id: str, from_story: str | None = None) -> bool:
        """Register an existing entity as planned for implementation.

        Called when a story requires an entity that already exists
        in the domain model but hasn't been implemented yet.

        Args:
            entity_id: Entity ID (E-XXX)
            from_story: Optional story that triggered this

        Returns:
            True if entity was found and updated
        """
        entity = self.queries.get_entity(entity_id)
        if entity:
            if entity.status == "planned":
                return True  # Already planned
            return self.updater.update_entity_status(entity_id, "planned")
        return False

    def register_all_story_entities(self, story: Story) -> list[str]:
        """Register all entities that a story depends on as planned.

        Args:
            story: Story to process

        Returns:
            List of entity IDs that were registered as planned
        """
        registered = []
        for dep in story.depends_on:
            if dep.startswith("E-"):
                if self.register_entity_as_planned(dep, story.id):
                    registered.append(dep)
        return registered


def evolve_story_design(
    story: Story, state: PipelineState, save_callback=None
) -> DesignEvolutionResult:
    """Convenience function to run design evolution.

    Args:
        story: Story to process
        state: Pipeline state
        save_callback: Optional save callback

    Returns:
        DesignEvolutionResult
    """
    engine = DesignEvolutionEngine(state, save_callback)
    return engine.evolve(story)
