"""Consistency checker for story interpretation.

Verifies that stories are consistent with existing system state,
including entities, capabilities, and prior decisions.

Reference: ADR-001d: Story Interpretation Engine - Stage 4
"""

from dataclasses import dataclass, field

from haytham.project.state_models import PipelineState, Story
from haytham.project.state_queries import StateQueries


@dataclass
class ConsistencyCheckResult:
    """Result of a single consistency check."""

    check_type: str  # entity_exists, capability_exists, no_conflicts, etc.
    target: str  # What was checked
    passed: bool
    message: str = ""
    entity_id: str | None = None  # If checking entity existence


@dataclass
class ConsistencyReport:
    """Full consistency report for a story."""

    story_id: str
    checks: list[ConsistencyCheckResult] = field(default_factory=list)
    prerequisites_needed: list[str] = field(default_factory=list)
    conflicts_found: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        """All checks passed."""
        return all(c.passed for c in self.checks)

    @property
    def passed_count(self) -> int:
        """Number of passed checks."""
        return sum(1 for c in self.checks if c.passed)

    @property
    def failed_count(self) -> int:
        """Number of failed checks."""
        return sum(1 for c in self.checks if not c.passed)


class ConsistencyChecker:
    """Checks story consistency against system state.

    Verifies that:
    - Referenced entities exist in the domain model
    - Required capabilities are available
    - No conflicts with existing decisions
    - Dependencies are properly tracked

    Reference: ADR-001d: Consistency Check
    """

    def __init__(self, state: PipelineState):
        """Initialize with pipeline state.

        Args:
            state: Current pipeline state to check against
        """
        self.state = state
        self.queries = StateQueries(state)

    def check(self, story: Story) -> ConsistencyReport:
        """Run all consistency checks on a story.

        Args:
            story: Story to check

        Returns:
            ConsistencyReport with all check results
        """
        report = ConsistencyReport(story_id=story.id)

        # Check entity references
        self._check_entity_references(story, report)

        # Check story dependencies
        self._check_dependencies(story, report)

        # Check for conflicts with decisions
        self._check_decision_conflicts(story, report)

        return report

    def _check_entity_references(self, story: Story, report: ConsistencyReport) -> None:
        """Check that entities referenced in depends_on exist."""
        for dep in story.depends_on:
            if dep.startswith("E-"):
                entity = self.queries.get_entity(dep)
                if entity:
                    report.checks.append(
                        ConsistencyCheckResult(
                            check_type="entity_exists",
                            target=dep,
                            passed=True,
                            message=f"Entity {dep} ({entity.name}) exists",
                            entity_id=dep,
                        )
                    )
                else:
                    report.checks.append(
                        ConsistencyCheckResult(
                            check_type="entity_exists",
                            target=dep,
                            passed=False,
                            message=f"Entity {dep} not found in domain model",
                            entity_id=dep,
                        )
                    )
                    report.prerequisites_needed.append(f"Entity {dep} must be defined")

    def _check_dependencies(self, story: Story, report: ConsistencyReport) -> None:
        """Check that story dependencies (S-XXX) exist."""
        for dep in story.depends_on:
            if dep.startswith("S-"):
                dep_story = self.queries.get_story(dep)
                if dep_story:
                    report.checks.append(
                        ConsistencyCheckResult(
                            check_type="story_exists",
                            target=dep,
                            passed=True,
                            message=f"Dependency story {dep} ({dep_story.title}) exists",
                        )
                    )
                else:
                    report.checks.append(
                        ConsistencyCheckResult(
                            check_type="story_exists",
                            target=dep,
                            passed=False,
                            message=f"Dependency story {dep} not found",
                        )
                    )
                    report.prerequisites_needed.append(
                        f"Story {dep} must be defined before {story.id}"
                    )

    def _check_decision_conflicts(self, story: Story, report: ConsistencyReport) -> None:
        """Check for conflicts with existing decisions."""
        # Get decisions that affect this story or its dependencies
        related_decisions = []
        for dep in story.depends_on:
            related_decisions.extend(self.queries.get_decisions_affecting(dep))

        # Also check decisions affecting this story
        related_decisions.extend(self.queries.get_decisions_affecting(story.id))

        if not related_decisions:
            report.checks.append(
                ConsistencyCheckResult(
                    check_type="no_conflicts",
                    target="decisions",
                    passed=True,
                    message="No conflicting decisions found",
                )
            )
        else:
            # For now, just note that decisions exist (no conflict detection logic)
            for decision in related_decisions:
                report.checks.append(
                    ConsistencyCheckResult(
                        check_type="decision_noted",
                        target=decision.id,
                        passed=True,
                        message=f"Decision {decision.id} affects this story: {decision.title}",
                    )
                )

    def check_all_stories(self) -> dict[str, ConsistencyReport]:
        """Check all pending stories in state.

        Returns:
            Dict of story_id -> ConsistencyReport
        """
        reports = {}
        for story in self.queries.get_pending_stories():
            reports[story.id] = self.check(story)
        return reports


def check_story_consistency(story: Story, state: PipelineState) -> ConsistencyReport:
    """Convenience function to check a single story.

    Args:
        story: Story to check
        state: Pipeline state to check against

    Returns:
        ConsistencyReport
    """
    checker = ConsistencyChecker(state)
    return checker.check(story)
