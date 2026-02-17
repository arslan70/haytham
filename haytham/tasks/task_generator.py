"""Task Generator for the Story-to-Implementation Pipeline.

Generates actionable technical tasks from designed stories, breaking them down
into backend, frontend, and test tasks that can be executed by coding agents.

Reference: ADR-001f: Task Generation & Refinement
"""

from dataclasses import dataclass, field

from haytham.interpretation.story_interpreter import ParsedStory
from haytham.project.state_models import PipelineState, Stack, Story, Task
from haytham.project.state_queries import StateQueries
from haytham.project.state_updater import StateUpdater


@dataclass
class TaskTemplate:
    """Template for generating a task."""

    title_template: str
    description_template: str
    task_type: str  # backend, frontend, test


@dataclass
class GeneratedTask:
    """A task generated for a story."""

    title: str
    description: str
    task_type: str  # backend, frontend, test
    story_id: str

    def to_task(self) -> Task:
        """Convert to Task model."""
        return Task(
            story_id=self.story_id,
            title=self.title,
            description=self.description,
            status="pending",
        )


@dataclass
class TaskGenerationResult:
    """Result of task generation for a story."""

    story_id: str
    tasks: list[GeneratedTask] = field(default_factory=list)
    presentation_text: str = ""

    @property
    def task_count(self) -> int:
        return len(self.tasks)

    @property
    def backend_tasks(self) -> list[GeneratedTask]:
        return [t for t in self.tasks if t.task_type == "backend"]

    @property
    def frontend_tasks(self) -> list[GeneratedTask]:
        return [t for t in self.tasks if t.task_type == "frontend"]

    @property
    def test_tasks(self) -> list[GeneratedTask]:
        return [t for t in self.tasks if t.task_type == "test"]


# ========== Task Templates by Verb Type ==========

TASK_TEMPLATES = {
    "create": [
        TaskTemplate(
            title_template="Define {entity} model",
            description_template="Create database model for {entity} entity with required fields",
            task_type="backend",
        ),
        TaskTemplate(
            title_template="Add {entity} API endpoints",
            description_template="Create POST /api/{entity_lower} endpoint for creating new {entity}",
            task_type="backend",
        ),
        TaskTemplate(
            title_template="Add {entity} form component",
            description_template="Create form component for creating new {entity}",
            task_type="frontend",
        ),
        TaskTemplate(
            title_template="Write {entity} creation tests",
            description_template="Unit tests for {entity} model, API endpoint, and form",
            task_type="test",
        ),
    ],
    "read": [
        TaskTemplate(
            title_template="Add {entity} list endpoint",
            description_template="Create GET /api/{entity_lower} endpoint for listing {entity}",
            task_type="backend",
        ),
        TaskTemplate(
            title_template="Add {entity} list component",
            description_template="Create list component to display {entity} items",
            task_type="frontend",
        ),
        TaskTemplate(
            title_template="Write {entity} retrieval tests",
            description_template="Unit tests for {entity} list endpoint and component",
            task_type="test",
        ),
    ],
    "update": [
        TaskTemplate(
            title_template="Add {entity} update endpoint",
            description_template="Create PUT /api/{entity_lower}/{{id}} endpoint for updating {entity}",
            task_type="backend",
        ),
        TaskTemplate(
            title_template="Add {entity} edit component",
            description_template="Create edit form component for modifying {entity}",
            task_type="frontend",
        ),
        TaskTemplate(
            title_template="Write {entity} update tests",
            description_template="Unit tests for {entity} update endpoint and component",
            task_type="test",
        ),
    ],
    "delete": [
        TaskTemplate(
            title_template="Add {entity} delete endpoint",
            description_template="Create DELETE /api/{entity_lower}/{{id}} endpoint for removing {entity}",
            task_type="backend",
        ),
        TaskTemplate(
            title_template="Add delete confirmation dialog",
            description_template="Create confirmation dialog for {entity} deletion",
            task_type="frontend",
        ),
        TaskTemplate(
            title_template="Write {entity} deletion tests",
            description_template="Unit tests for {entity} delete endpoint and confirmation",
            task_type="test",
        ),
    ],
    "search": [
        TaskTemplate(
            title_template="Add {entity} search endpoint",
            description_template="Create GET /api/{entity_lower}/search?q=keyword endpoint",
            task_type="backend",
        ),
        TaskTemplate(
            title_template="Add search input component",
            description_template="Create search bar component with instant search",
            task_type="frontend",
        ),
        TaskTemplate(
            title_template="Write search tests",
            description_template="Unit tests for search endpoint and component",
            task_type="test",
        ),
    ],
}


class TaskGenerator:
    """Generates tasks from designed stories.

    Breaks down stories into backend, frontend, and test tasks
    based on the story's verb type and required capabilities.

    Reference: ADR-001f: Task Generation
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

    def generate(self, story: Story) -> TaskGenerationResult:
        """Generate tasks for a designed story.

        Args:
            story: Story to generate tasks for (should have status='designed')

        Returns:
            TaskGenerationResult with generated tasks
        """
        result = TaskGenerationResult(story_id=story.id)

        # Parse story to get verb type
        parsed = ParsedStory.from_story(story)

        # Determine entity name from story
        entity_name = self._extract_entity_name(parsed)

        # Get templates for verb type
        templates = self._get_templates_for_story(parsed)

        # Generate tasks from templates
        for template in templates:
            task = self._apply_template(template, entity_name, story.id)
            result.tasks.append(task)

        # Generate presentation text
        result.presentation_text = self._format_presentation(story, result)

        return result

    def generate_and_apply(self, story_id: str) -> TaskGenerationResult | None:
        """Generate tasks for a story and add them to state.

        Args:
            story_id: Story ID (S-XXX)

        Returns:
            TaskGenerationResult or None if story not found
        """
        story = self.queries.get_story(story_id)
        if not story:
            return None

        # Generate tasks
        result = self.generate(story)

        # Add tasks to state
        for gen_task in result.tasks:
            task = gen_task.to_task()
            self.updater.add_task(task)

        # Update story status
        self.updater.update_story_status(story_id, "implementing")

        return result

    def _extract_entity_name(self, parsed: ParsedStory) -> str:
        """Extract entity name from parsed story."""
        if parsed.object:
            # Clean up common words
            obj = parsed.object.lower()
            for word in ["a", "an", "the", "my", "new", "all"]:
                obj = obj.replace(f"{word} ", "")
            return obj.strip().title()
        return "Item"

    def _get_templates_for_story(self, parsed: ParsedStory) -> list[TaskTemplate]:
        """Get task templates for a story based on verb type."""
        verb_type = parsed.verb_type

        # Handle search specially
        if "search" in parsed.action.lower():
            verb_type = "search"

        if verb_type in TASK_TEMPLATES:
            return TASK_TEMPLATES[verb_type]

        # Default to read templates if unknown
        return TASK_TEMPLATES.get("read", [])

    def _apply_template(
        self, template: TaskTemplate, entity_name: str, story_id: str
    ) -> GeneratedTask:
        """Apply template to generate a task."""
        title = template.title_template.format(
            entity=entity_name,
            entity_lower=entity_name.lower(),
        )
        description = template.description_template.format(
            entity=entity_name,
            entity_lower=entity_name.lower(),
        )
        return GeneratedTask(
            title=title,
            description=description,
            task_type=template.task_type,
            story_id=story_id,
        )

    def _format_presentation(self, story: Story, result: TaskGenerationResult) -> str:
        """Format task breakdown for user presentation."""
        lines = [
            f"## Task Breakdown: {story.title} ({story.id})",
            "",
            "Here's how I plan to build this feature:",
            "",
            "---",
            "",
            "### Tasks",
            "",
        ]

        for i, task in enumerate(result.tasks, 1):
            lines.append(f"{i}. **{task.title}** ({task.task_type})")
            lines.append(f"   - {task.description}")
            lines.append("")

        lines.extend(
            [
                "---",
                "",
                "[Approve] [Request Changes]",
            ]
        )

        return "\n".join(lines)

    def generate_for_all_designed(self) -> list[TaskGenerationResult]:
        """Generate tasks for all designed stories.

        Returns:
            List of TaskGenerationResult for each designed story
        """
        results = []
        designed_stories = self.queries.get_stories_by_status("designed")
        for story in designed_stories:
            result = self.generate(story)
            results.append(result)
        return results


def generate_story_tasks(story: Story, state: PipelineState) -> TaskGenerationResult:
    """Convenience function to generate tasks for a story.

    Args:
        story: Story to generate tasks for
        state: Pipeline state

    Returns:
        TaskGenerationResult
    """
    generator = TaskGenerator(state)
    return generator.generate(story)


def format_task_prompt(task: Task, story: Story, stack: Stack | None = None) -> str:
    """Format a task as a prompt for Claude Code.

    Args:
        task: Task to format
        story: Parent story
        stack: Optional stack for context

    Returns:
        Formatted prompt string
    """
    lines = [
        f"## Task: {task.id} - {task.title}",
        "",
        f"**Story**: {story.id} ({story.title})",
    ]

    if stack:
        backend_info = ""
        if stack.backend:
            backend_info = f"{stack.backend.language.title()}/{stack.backend.framework.title()}"
        lines.append(f"**Stack**: {backend_info} backend")

    lines.extend(
        [
            "",
            "### Description",
            task.description or "No description provided",
            "",
            "### Requirements",
        ]
    )

    # Add requirements from story acceptance criteria
    for i, ac in enumerate(story.acceptance_criteria, 1):
        lines.append(f"{i}. {ac}")

    lines.extend(
        [
            "",
            "### Expected Output",
            "- Implementation file(s)",
            "- Unit tests",
        ]
    )

    return "\n".join(lines)
