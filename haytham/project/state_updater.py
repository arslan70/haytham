"""Update helpers for modifying pipeline state.

This module provides mutation operations on PipelineState.
All updates trigger a save callback to persist changes immediately.

Reference: ADR-001c: Update Helpers
"""

from collections.abc import Callable
from datetime import UTC, datetime

from .id_generator import (
    next_decision_id,
    next_entity_id,
    next_story_id,
    next_task_id,
)
from .state_models import Ambiguity, Decision, Entity, PipelineState, Stack, Story, Task
from .state_queries import StateQueries


class StateUpdater:
    """Update helpers for modifying pipeline state.

    All mutations trigger the save callback to persist changes.
    This ensures state is never out of sync with disk.

    Usage:
        state = manager.load_pipeline_state()
        updater = StateUpdater(state, manager.save_pipeline_state)
        updater.add_entity(Entity(name="User"))
        # State is automatically saved after add_entity
    """

    def __init__(self, state: PipelineState, save_callback: Callable[[PipelineState], None]):
        """Initialize with state and save callback.

        Args:
            state: PipelineState to modify
            save_callback: Function to call after each update
                           (typically manager.save_pipeline_state)
        """
        self.state = state
        self.save_callback = save_callback

    def _save(self) -> None:
        """Trigger save callback."""
        self.save_callback(self.state)

    # ========== Entity Operations ==========

    def add_entity(self, entity: Entity) -> Entity:
        """Add new entity.

        Called during Design Evolution when new entities are discovered.
        Assigns ID if not present.

        Args:
            entity: Entity to add (id will be assigned if empty)

        Returns:
            Entity with assigned ID
        """
        if not entity.id:
            entity.id = next_entity_id(self.state)
        self.state.entities.append(entity)
        self._save()
        return entity

    def update_entity_status(
        self, entity_id: str, status: str, file_path: str | None = None
    ) -> bool:
        """Update entity status (planned → implemented).

        Called after Implementation Execution completes entity task.

        Args:
            entity_id: Entity ID in E-XXX format
            status: New status (planned, implemented)
            file_path: Optional path where entity was implemented

        Returns:
            True if entity was found and updated, False otherwise
        """
        queries = StateQueries(self.state)
        entity = queries.get_entity(entity_id)
        if entity:
            entity.status = status
            if file_path:
                entity.file_path = file_path
            self._save()
            return True
        return False

    def update_entity(self, entity_id: str, **kwargs) -> bool:
        """Update entity fields.

        Args:
            entity_id: Entity ID in E-XXX format
            **kwargs: Fields to update

        Returns:
            True if entity was found and updated, False otherwise
        """
        queries = StateQueries(self.state)
        entity = queries.get_entity(entity_id)
        if entity:
            for key, value in kwargs.items():
                if hasattr(entity, key):
                    setattr(entity, key, value)
            self._save()
            return True
        return False

    # ========== Story Operations ==========

    def add_story(self, story: Story) -> Story:
        """Add story (from MVP spec or as prerequisite).

        Assigns ID if not present.

        Args:
            story: Story to add (id will be assigned if empty)

        Returns:
            Story with assigned ID
        """
        if not story.id:
            story.id = next_story_id(self.state)
        self.state.stories.append(story)
        self._save()
        return story

    def update_story_status(self, story_id: str, status: str) -> bool:
        """Update story lifecycle status.

        Story lifecycle: pending → interpreting → designing → implementing → completed

        Args:
            story_id: Story ID in S-XXX format
            status: New status

        Returns:
            True if story was found and updated, False otherwise
        """
        queries = StateQueries(self.state)
        story = queries.get_story(story_id)
        if story:
            story.status = status
            self._save()
            return True
        return False

    def add_story_ambiguity(self, story_id: str, ambiguity: Ambiguity) -> bool:
        """Add ambiguity to a story.

        Called during Story Interpretation when ambiguities are detected.

        Args:
            story_id: Story ID in S-XXX format
            ambiguity: Ambiguity to add

        Returns:
            True if story was found and ambiguity added, False otherwise
        """
        queries = StateQueries(self.state)
        story = queries.get_story(story_id)
        if story:
            story.ambiguities.append(ambiguity)
            self._save()
            return True
        return False

    def resolve_ambiguity(self, story_id: str, question: str, resolution: str) -> bool:
        """Resolve an ambiguity on a story.

        Args:
            story_id: Story ID in S-XXX format
            question: The ambiguity question to resolve
            resolution: The chosen resolution

        Returns:
            True if ambiguity was found and resolved, False otherwise
        """
        queries = StateQueries(self.state)
        story = queries.get_story(story_id)
        if story:
            for amb in story.ambiguities:
                if amb.question == question:
                    amb.resolved = True
                    amb.resolution = resolution
                    self._save()
                    return True
        return False

    # ========== Task Operations ==========

    def add_task(self, task: Task) -> Task:
        """Add task and link to story.

        Assigns ID if not present. Also updates the parent story's task list.

        Args:
            task: Task to add (id will be assigned if empty)

        Returns:
            Task with assigned ID
        """
        if not task.id:
            task.id = next_task_id(self.state)
        self.state.tasks.append(task)

        # Also update story's task list
        queries = StateQueries(self.state)
        story = queries.get_story(task.story_id)
        if story and task.id not in story.tasks:
            story.tasks.append(task.id)

        self._save()
        return task

    def update_task_status(self, task_id: str, status: str, file_path: str | None = None) -> bool:
        """Update task status and optionally file path.

        Args:
            task_id: Task ID in T-XXX format
            status: New status (pending, in_progress, completed, failed)
            file_path: Optional path where task was implemented

        Returns:
            True if task was found and updated, False otherwise
        """
        queries = StateQueries(self.state)
        task = queries.get_task(task_id)
        if task:
            task.status = status
            if file_path:
                task.file_path = file_path
            self._save()
            return True
        return False

    # ========== Decision Operations ==========

    def add_decision(self, decision: Decision) -> Decision:
        """Record architectural decision.

        Assigns ID if not present. Sets made_at timestamp if not set.

        Args:
            decision: Decision to add

        Returns:
            Decision with assigned ID and timestamp
        """
        if not decision.id:
            decision.id = next_decision_id(self.state)
        if not decision.made_at:
            decision.made_at = datetime.now(UTC)
        self.state.decisions.append(decision)
        self._save()
        return decision

    # ========== Current Context Operations ==========

    def set_current(self, story_id: str | None, chunk: str) -> None:
        """Set what's currently being processed.

        Used by Orchestration to track pipeline progress.

        Args:
            story_id: S-XXX being processed, or None if not processing a story
            chunk: Current pipeline stage (e.g., "story-interpretation", "task-generation")
        """
        self.state.current.story = story_id
        self.state.current.chunk = chunk
        self._save()

    def clear_current(self) -> None:
        """Clear current processing context.

        Called when pipeline is idle or between stages.
        """
        self.state.current.story = None
        self.state.current.chunk = "ready"
        self._save()

    # ========== Stack Operations ==========

    def set_stack(self, stack_template_id: str) -> bool:
        """Set the stack in pipeline state from template.

        Called after user selects a stack during Stack Selection phase.
        Updates pipeline.stack with the selected template.

        Args:
            stack_template_id: Template ID (e.g., "web-python-react")

        Returns:
            True if stack was set, False if template not found

        Reference: ADR-001b: Platform & Stack Proposal
        """
        from .stack_templates import get_stack_template

        stack = get_stack_template(stack_template_id)
        if stack is None:
            return False

        self.state.stack = stack
        self._save()
        return True

    def set_stack_from_object(self, stack: Stack) -> None:
        """Set the stack directly from a Stack object.

        Use when you already have a Stack object (e.g., from tests).

        Args:
            stack: Stack object to set
        """
        self.state.stack = stack
        self._save()
