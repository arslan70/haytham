"""Task Executor for the Story-to-Implementation Pipeline.

Executes tasks sequentially, running verification after each task
and updating state with results.

Reference: ADR-001g: Implementation Execution
"""

from dataclasses import dataclass, field
from enum import Enum

from haytham.project.state_models import PipelineState, Story, Task
from haytham.project.state_queries import StateQueries
from haytham.project.state_updater import StateUpdater
from haytham.tasks.task_generator import format_task_prompt


class TaskStatus(Enum):
    """Task execution status."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class TaskExecutionResult:
    """Result of executing a single task."""

    task_id: str
    status: TaskStatus
    file_path: str | None = None
    error_message: str | None = None
    retry_count: int = 0

    @property
    def succeeded(self) -> bool:
        return self.status == TaskStatus.COMPLETED

    @property
    def failed(self) -> bool:
        return self.status == TaskStatus.FAILED


@dataclass
class StoryExecutionResult:
    """Result of executing all tasks for a story."""

    story_id: str
    task_results: list[TaskExecutionResult] = field(default_factory=list)
    all_completed: bool = False

    @property
    def completed_count(self) -> int:
        return sum(1 for t in self.task_results if t.succeeded)

    @property
    def failed_count(self) -> int:
        return sum(1 for t in self.task_results if t.failed)

    @property
    def total_count(self) -> int:
        return len(self.task_results)


class TaskExecutor:
    """Executes tasks and updates state.

    Processes tasks sequentially, marking each as in_progress during
    execution and completed/failed after. Updates entity status when
    entity-related tasks complete.

    Reference: ADR-001g: Implementation Execution
    """

    def __init__(self, state: PipelineState, save_callback=None, max_retries: int = 3):
        """Initialize task executor.

        Args:
            state: Current pipeline state
            save_callback: Optional callback to save state after updates
            max_retries: Maximum retry attempts for failed tasks
        """
        self.state = state
        self.queries = StateQueries(state)
        self.updater = StateUpdater(state, save_callback or (lambda s: None))
        self.max_retries = max_retries

    def start_task(self, task_id: str) -> bool:
        """Mark a task as in progress.

        Args:
            task_id: Task ID (T-XXX)

        Returns:
            True if task was found and updated
        """
        task = self.queries.get_task(task_id)
        if not task:
            return False

        self.updater.update_task_status(task_id, "in_progress")
        self.updater.set_current(task.story_id, "implementation")
        return True

    def complete_task(self, task_id: str, file_path: str | None = None) -> TaskExecutionResult:
        """Mark a task as completed.

        Args:
            task_id: Task ID (T-XXX)
            file_path: Optional path to created/modified file

        Returns:
            TaskExecutionResult
        """
        task = self.queries.get_task(task_id)
        if not task:
            return TaskExecutionResult(
                task_id=task_id,
                status=TaskStatus.FAILED,
                error_message="Task not found",
            )

        self.updater.update_task_status(task_id, "completed", file_path)

        # Check if this completes entity implementation
        self._check_entity_completion(task)

        # Check if this completes all story tasks
        self._check_story_completion(task.story_id)

        return TaskExecutionResult(
            task_id=task_id,
            status=TaskStatus.COMPLETED,
            file_path=file_path,
        )

    def fail_task(
        self, task_id: str, error_message: str, retry_count: int = 0
    ) -> TaskExecutionResult:
        """Mark a task as failed.

        Args:
            task_id: Task ID (T-XXX)
            error_message: Description of the failure
            retry_count: Number of retries attempted

        Returns:
            TaskExecutionResult
        """
        self.updater.update_task_status(task_id, "failed")

        return TaskExecutionResult(
            task_id=task_id,
            status=TaskStatus.FAILED,
            error_message=error_message,
            retry_count=retry_count,
        )

    def get_next_pending_task(self) -> Task | None:
        """Get the next pending task to execute.

        Returns tasks in order: first pending task overall.

        Returns:
            Next pending task or None if no tasks pending
        """
        return next(
            (t for t in self.state.tasks if t.status == "pending"),
            None,
        )

    def get_story_pending_tasks(self, story_id: str) -> list[Task]:
        """Get all pending tasks for a story.

        Args:
            story_id: Story ID (S-XXX)

        Returns:
            List of pending tasks for the story
        """
        return [t for t in self.queries.get_story_tasks(story_id) if t.status == "pending"]

    def execute_task_simulated(
        self, task_id: str, success: bool = True, file_path: str | None = None
    ) -> TaskExecutionResult:
        """Execute a task in simulated mode (for testing).

        This simulates the execution loop without actually invoking
        Claude Code - useful for testing state updates.

        Args:
            task_id: Task ID (T-XXX)
            success: Whether the task succeeds
            file_path: File path for successful tasks

        Returns:
            TaskExecutionResult
        """
        task = self.queries.get_task(task_id)
        if not task:
            return TaskExecutionResult(
                task_id=task_id,
                status=TaskStatus.FAILED,
                error_message="Task not found",
            )

        # Mark as in progress
        self.start_task(task_id)

        # Simulate execution result
        if success:
            return self.complete_task(task_id, file_path)
        else:
            return self.fail_task(task_id, "Simulated failure", retry_count=self.max_retries)

    def execute_story_tasks(
        self, story_id: str, simulate_success: bool = True
    ) -> StoryExecutionResult:
        """Execute all pending tasks for a story (simulated for testing).

        Args:
            story_id: Story ID (S-XXX)
            simulate_success: Whether to simulate success for all tasks

        Returns:
            StoryExecutionResult with all task results
        """
        result = StoryExecutionResult(story_id=story_id)
        pending_tasks = self.get_story_pending_tasks(story_id)

        for task in pending_tasks:
            task_result = self.execute_task_simulated(
                task.id,
                success=simulate_success,
                file_path=f"src/{task.title.lower().replace(' ', '_')}.py",
            )
            result.task_results.append(task_result)

        # Check if all completed
        story = self.queries.get_story(story_id)
        if story:
            result.all_completed = story.status == "completed"

        return result

    def get_task_prompt(self, task_id: str) -> str | None:
        """Generate the prompt for a task.

        Args:
            task_id: Task ID (T-XXX)

        Returns:
            Formatted prompt string or None if task not found
        """
        task = self.queries.get_task(task_id)
        if not task:
            return None

        story = self.queries.get_story(task.story_id)
        if not story:
            return None

        return format_task_prompt(task, story, self.state.stack)

    def _check_entity_completion(self, task: Task) -> None:
        """Check if a task completes entity implementation.

        If task title mentions "model" or "Define", mark related
        entities as implemented.

        Args:
            task: Completed task
        """
        title_lower = task.title.lower()
        if "model" in title_lower or "define" in title_lower:
            # Find related entity from story dependencies
            story = self.queries.get_story(task.story_id)
            if story:
                for dep in story.depends_on:
                    if dep.startswith("E-"):
                        entity = self.queries.get_entity(dep)
                        if entity and entity.status == "planned":
                            self.updater.update_entity_status(dep, "implemented", task.file_path)

    def _check_story_completion(self, story_id: str) -> None:
        """Check if all tasks for a story are completed.

        If all tasks are completed, mark story as completed.

        Args:
            story_id: Story ID (S-XXX)
        """
        tasks = self.queries.get_story_tasks(story_id)
        if not tasks:
            return

        all_completed = all(t.status == "completed" for t in tasks)
        if all_completed:
            self.updater.update_story_status(story_id, "completed")
            self.updater.clear_current()


def create_execution_prompt(task: Task, story: Story, state: PipelineState) -> str:
    """Create a full execution prompt for Claude Code.

    Args:
        task: Task to execute
        story: Parent story
        state: Pipeline state for context

    Returns:
        Complete prompt string for Claude Code
    """
    base_prompt = format_task_prompt(task, story, state.stack)

    # Add execution instructions
    lines = [
        base_prompt,
        "",
        "---",
        "",
        "## Instructions",
        "",
        "1. Implement the task as described above",
        "2. Create necessary files with proper structure",
        "3. Add unit tests for the implementation",
        "4. Run the tests to verify correctness",
        "5. Report any issues or blockers encountered",
        "",
        "Please implement this task now.",
    ]

    return "\n".join(lines)
