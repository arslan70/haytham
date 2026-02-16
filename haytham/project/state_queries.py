"""Query helpers for reading pipeline state.

This module provides read-only query operations on PipelineState.
All queries are non-mutating and do not trigger saves.

Reference: ADR-001c: Query Helpers
"""

from .state_models import Decision, Entity, PipelineState, Story, Task


class StateQueries:
    """Query helpers for reading pipeline state without modification.

    Usage:
        state = manager.load_pipeline_state()
        queries = StateQueries(state)
        entity = queries.get_entity("E-001")
        pending = queries.get_pending_stories()
    """

    def __init__(self, state: PipelineState):
        """Initialize with pipeline state.

        Args:
            state: PipelineState to query
        """
        self.state = state

    # ========== Entity Queries ==========

    def get_entity(self, entity_id: str) -> Entity | None:
        """Get entity by ID (E-XXX).

        Used by: Design Evolution to check if entity exists

        Args:
            entity_id: Entity ID in E-XXX format

        Returns:
            Entity if found, None otherwise
        """
        for e in self.state.entities:
            if e.id == entity_id:
                return e
        return None

    def get_entity_by_name(self, name: str) -> Entity | None:
        """Get entity by name.

        Args:
            name: Entity name (e.g., "User", "Note")

        Returns:
            Entity if found, None otherwise
        """
        for e in self.state.entities:
            if e.name == name:
                return e
        return None

    def entity_exists(self, name: str) -> bool:
        """Check if entity with given name exists.

        Used by: Story Interpretation to check dependencies

        Args:
            name: Entity name to check

        Returns:
            True if entity exists, False otherwise
        """
        return any(e.name == name for e in self.state.entities)

    def get_implemented_entities(self) -> list[Entity]:
        """Get entities with status='implemented'.

        Returns:
            List of implemented entities
        """
        return [e for e in self.state.entities if e.status == "implemented"]

    def get_planned_entities(self) -> list[Entity]:
        """Get entities with status='planned'.

        Returns:
            List of planned entities
        """
        return [e for e in self.state.entities if e.status == "planned"]

    # ========== Story Queries ==========

    def get_story(self, story_id: str) -> Story | None:
        """Get story by ID (S-XXX).

        Used by: Task Generation to get story details

        Args:
            story_id: Story ID in S-XXX format

        Returns:
            Story if found, None otherwise
        """
        for s in self.state.stories:
            if s.id == story_id:
                return s
        return None

    def get_pending_stories(self) -> list[Story]:
        """Get all stories with status='pending', ordered by priority then ID.

        Used by: Orchestration to determine next story to process

        Returns:
            List of pending stories, sorted by priority (P0 first) then ID
        """
        pending = [s for s in self.state.stories if s.status == "pending"]
        # Sort by priority (P0 < P1 < P2) then by ID
        return sorted(pending, key=lambda s: (s.priority, s.id))

    def get_stories_by_status(self, status: str) -> list[Story]:
        """Get all stories with given status.

        Args:
            status: Story status to filter by

        Returns:
            List of stories with matching status
        """
        return [s for s in self.state.stories if s.status == status]

    def get_completed_stories(self) -> list[Story]:
        """Get all stories with status='completed'.

        Returns:
            List of completed stories
        """
        return [s for s in self.state.stories if s.status == "completed"]

    # ========== Task Queries ==========

    def get_task(self, task_id: str) -> Task | None:
        """Get task by ID (T-XXX).

        Args:
            task_id: Task ID in T-XXX format

        Returns:
            Task if found, None otherwise
        """
        for t in self.state.tasks:
            if t.id == task_id:
                return t
        return None

    def get_story_tasks(self, story_id: str) -> list[Task]:
        """Get all tasks for a story.

        Used by: Execution to process tasks

        Args:
            story_id: Story ID in S-XXX format

        Returns:
            List of tasks belonging to the story
        """
        return [t for t in self.state.tasks if t.story_id == story_id]

    def get_pending_tasks(self) -> list[Task]:
        """Get all tasks with status='pending'.

        Returns:
            List of pending tasks
        """
        return [t for t in self.state.tasks if t.status == "pending"]

    def get_tasks_by_status(self, status: str) -> list[Task]:
        """Get all tasks with given status.

        Args:
            status: Task status to filter by

        Returns:
            List of tasks with matching status
        """
        return [t for t in self.state.tasks if t.status == status]

    # ========== Decision Queries ==========

    def get_decision(self, decision_id: str) -> Decision | None:
        """Get decision by ID (D-XXX).

        Args:
            decision_id: Decision ID in D-XXX format

        Returns:
            Decision if found, None otherwise
        """
        for d in self.state.decisions:
            if d.id == decision_id:
                return d
        return None

    def get_decisions_affecting(self, target_id: str) -> list[Decision]:
        """Get decisions that affect a specific entity/story/task.

        Used by: Story Interpretation to check for conflicting decisions

        Args:
            target_id: ID of entity, story, or task

        Returns:
            List of decisions affecting the target
        """
        return [d for d in self.state.decisions if target_id in d.affects]

    def get_decisions(self) -> list[Decision]:
        """Get all decisions.

        Used by: Design Evolution to check for conflicts

        Returns:
            List of all decisions
        """
        return list(self.state.decisions)

    # ========== Current Context Queries ==========

    def get_current_story(self) -> Story | None:
        """Get the story currently being processed.

        Returns:
            Current story if one is set, None otherwise
        """
        if self.state.current.story:
            return self.get_story(self.state.current.story)
        return None

    def get_current_chunk(self) -> str:
        """Get the current pipeline stage.

        Returns:
            Current chunk/stage name
        """
        return self.state.current.chunk
