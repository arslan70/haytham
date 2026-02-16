"""Story-to-Implementation Pipeline Orchestrator.

Coordinates the full pipeline flow from MVP specification through
implementation, managing state and presenting human gates.

Reference: ADR-001h: Orchestration & Feedback Loops
"""

# Import human_gates directly to avoid burr dependency in workflow/__init__
import importlib.util
import logging
import sys
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from haytham.design.design_evolution import DesignEvolutionEngine
from haytham.execution.task_executor import TaskExecutor
from haytham.interpretation.story_interpreter import StoryInterpreter
from haytham.project.project_state import PipelineStateManager
from haytham.project.stack_templates import (
    get_default_template_for_platform,
    recommend_platform,
)
from haytham.project.state_initializer import initialize_from_mvp_spec_text
from haytham.project.state_models import PipelineState, Story
from haytham.project.state_queries import StateQueries
from haytham.project.state_updater import StateUpdater
from haytham.tasks.task_generator import TaskGenerator

logger = logging.getLogger(__name__)

__all__ = [
    "PipelineOrchestrator",
    "PipelineStage",
    "PipelineProgress",
    "HumanGateRequest",
    "StoryProcessingResult",
    "run_notes_app_pipeline",
]

_human_gates_path = Path(__file__).parent.parent / "workflow" / "human_gates.py"
_spec = importlib.util.spec_from_file_location("human_gates", _human_gates_path)
_human_gates = importlib.util.module_from_spec(_spec)
sys.modules["human_gates"] = _human_gates
_spec.loader.exec_module(_human_gates)
present_stack_choices = _human_gates.present_stack_choices


class PipelineStage(Enum):
    """Stages of the story-to-implementation pipeline."""

    IDLE = "idle"
    MVP_SPEC = "mvp_specification"
    STACK_SELECTION = "stack_selection"
    STATE_INITIALIZATION = "state_initialization"
    STORY_INTERPRETATION = "story_interpretation"
    DESIGN_EVOLUTION = "design_evolution"
    TASK_GENERATION = "task_generation"
    IMPLEMENTATION = "implementation"
    COMPLETED = "completed"


@dataclass
class PipelineProgress:
    """Current progress through the pipeline."""

    stage: PipelineStage = PipelineStage.IDLE
    current_story_id: str | None = None
    stories_completed: int = 0
    stories_total: int = 0
    current_task_id: str | None = None
    tasks_completed: int = 0
    tasks_total: int = 0

    @property
    def progress_percentage(self) -> float:
        """Overall progress as percentage."""
        if self.stories_total == 0:
            return 0.0
        return (self.stories_completed / self.stories_total) * 100


@dataclass
class HumanGateRequest:
    """A request for human input."""

    gate_type: str  # stack_selection, ambiguity, design_approval, task_approval
    story_id: str | None = None
    presentation_text: str = ""
    options: list[str] = field(default_factory=list)
    default: str | None = None

    def needs_response(self) -> bool:
        return len(self.options) > 0


@dataclass
class StoryProcessingResult:
    """Result of processing a single story."""

    story_id: str
    success: bool = True
    error_message: str | None = None
    tasks_created: int = 0
    tasks_completed: int = 0
    entities_implemented: list[str] = field(default_factory=list)


class PipelineOrchestrator:
    """Main orchestrator for the story-to-implementation pipeline.

    Coordinates all pipeline stages:
    1. MVP Spec parsing
    2. Stack selection
    3. State initialization
    4. Story processing (interpret → design → tasks → execute)

    Reference: ADR-001h: Orchestration & Feedback Loops
    """

    def __init__(self, session_dir: Path | str):
        """Initialize orchestrator.

        Args:
            session_dir: Directory for session state
        """
        self.session_dir = Path(session_dir)
        self.manager = PipelineStateManager(self.session_dir)
        self._state: PipelineState | None = None
        self._progress = PipelineProgress()

    @property
    def state(self) -> PipelineState:
        """Current pipeline state (lazy-loaded)."""
        if self._state is None:
            self._state = self.manager.load_pipeline_state()
        return self._state

    @property
    def progress(self) -> PipelineProgress:
        """Current pipeline progress."""
        return self._progress

    def _save(self, state: PipelineState | None = None) -> None:
        """Save current state to disk.

        Args:
            state: Optional state to save (for callback compatibility)
        """
        if state is not None:
            self._state = state
        if self._state:
            self.manager.save_pipeline_state(self._state)

    def _queries(self) -> StateQueries:
        """Get state queries helper."""
        return StateQueries(self.state)

    def _updater(self) -> StateUpdater:
        """Get state updater helper."""
        return StateUpdater(self.state, self._save)

    # ========== Pipeline Initialization ==========

    def initialize_from_mvp_spec(self, mvp_spec_text: str) -> bool:
        """Initialize pipeline state from MVP specification.

        Args:
            mvp_spec_text: Full MVP specification markdown

        Returns:
            True if initialization succeeded
        """
        try:
            self._state = initialize_from_mvp_spec_text(self.session_dir, mvp_spec_text)
            self._save()
            self._update_progress()
            return True
        except Exception as e:
            logger.error("Failed to initialize from MVP spec: %s", e)
            return False

    def select_stack(self, mvp_spec_text: str) -> HumanGateRequest:
        """Generate stack selection gate.

        Args:
            mvp_spec_text: MVP spec for platform detection

        Returns:
            HumanGateRequest with stack options
        """
        platform, _ = recommend_platform(mvp_spec_text)
        default_stack = get_default_template_for_platform(platform)

        presentation = present_stack_choices(
            recommended_platform=platform,
            recommended_stack=default_stack,
            rationale="Based on your MVP specification analysis",
        )

        return HumanGateRequest(
            gate_type="stack_selection",
            presentation_text=presentation.formatted_text,
            options=[presentation.recommended.template_id]
            + [a.template_id for a in presentation.alternatives],
            default=default_stack,
        )

    def apply_stack_selection(self, stack_template_id: str) -> bool:
        """Apply the selected stack.

        Args:
            stack_template_id: Selected stack template ID

        Returns:
            True if stack was applied
        """
        updater = self._updater()
        result = updater.set_stack(stack_template_id)
        if result:
            self._progress.stage = PipelineStage.STATE_INITIALIZATION
        return result

    # ========== Story Processing ==========

    def get_next_story(self) -> Story | None:
        """Get the next story to process.

        Returns:
            Next pending story or None if all complete
        """
        queries = self._queries()
        pending = queries.get_pending_stories()
        return pending[0] if pending else None

    def process_story(self, story_id: str, auto_approve: bool = False) -> StoryProcessingResult:
        """Process a story through all pipeline stages.

        Args:
            story_id: Story ID (S-XXX) to process
            auto_approve: If True, auto-approve all gates

        Returns:
            StoryProcessingResult with processing outcome
        """
        result = StoryProcessingResult(story_id=story_id)
        updater = self._updater()

        # Update progress
        self._progress.current_story_id = story_id

        # Stage 1: Story Interpretation
        self._progress.stage = PipelineStage.STORY_INTERPRETATION
        updater.set_current(story_id, "interpretation")

        interpreter = StoryInterpreter(self.state, self._save)
        interpretation = interpreter.interpret_and_update(story_id)

        if interpretation is None:
            result.success = False
            result.error_message = f"Story {story_id} not found"
            return result

        # Handle pending ambiguities (auto-resolve for now)
        if interpretation.pending_ambiguities and auto_approve:
            for amb in interpretation.pending_ambiguities:
                if amb.default:
                    interpreter.apply_user_decisions(story_id, {amb.question: amb.default})

        # Stage 2: Design Evolution
        self._progress.stage = PipelineStage.DESIGN_EVOLUTION
        updater.set_current(story_id, "design-evolution")

        story = self._queries().get_story(story_id)
        if story:
            design_engine = DesignEvolutionEngine(self.state, self._save)
            design_result = design_engine.evolve_and_apply(story, auto_approve=auto_approve)

            if design_result.entities_registered:
                result.entities_implemented.extend(design_result.entities_registered)

        # Stage 3: Task Generation
        self._progress.stage = PipelineStage.TASK_GENERATION
        updater.set_current(story_id, "task-generation")

        task_generator = TaskGenerator(self.state, self._save)
        task_result = task_generator.generate_and_apply(story_id)

        if task_result:
            result.tasks_created = task_result.task_count
            self._progress.tasks_total = task_result.task_count

        # Stage 4: Implementation Execution
        self._progress.stage = PipelineStage.IMPLEMENTATION
        updater.set_current(story_id, "implementation")

        executor = TaskExecutor(self.state, self._save)
        execution_result = executor.execute_story_tasks(story_id, simulate_success=True)

        result.tasks_completed = execution_result.completed_count

        # Update progress
        self._progress.stories_completed += 1
        self._update_progress()

        return result

    def process_all_stories(self, auto_approve: bool = False) -> list[StoryProcessingResult]:
        """Process all pending stories.

        Args:
            auto_approve: If True, auto-approve all gates

        Returns:
            List of StoryProcessingResult for each story
        """
        results = []

        while True:
            story = self.get_next_story()
            if story is None:
                break

            result = self.process_story(story.id, auto_approve=auto_approve)
            results.append(result)

            if not result.success:
                break  # Stop on failure

        # Mark pipeline as completed
        if all(r.success for r in results):
            self._progress.stage = PipelineStage.COMPLETED

        return results

    # ========== Progress Tracking ==========

    def _update_progress(self) -> None:
        """Update progress counters from state."""
        queries = self._queries()

        completed = queries.get_completed_stories()
        all_stories = self.state.stories

        self._progress.stories_completed = len(completed)
        self._progress.stories_total = len(all_stories)

    def get_progress_summary(self) -> str:
        """Get human-readable progress summary.

        Returns:
            Formatted progress string
        """
        p = self._progress
        lines = [
            "## Pipeline Progress",
            "",
            f"**Stage**: {p.stage.value}",
            f"**Stories**: {p.stories_completed}/{p.stories_total}",
        ]

        if p.current_story_id:
            lines.append(f"**Current Story**: {p.current_story_id}")

        if p.stories_total > 0:
            lines.append(f"**Progress**: {p.progress_percentage:.0f}%")

        return "\n".join(lines)

    # ========== Full Pipeline Run ==========

    def run_full_pipeline(
        self,
        mvp_spec_text: str,
        stack_template_id: str | None = None,
        auto_approve: bool = False,
    ) -> list[StoryProcessingResult]:
        """Run the complete pipeline from MVP spec to implementation.

        Args:
            mvp_spec_text: Full MVP specification markdown
            stack_template_id: Optional stack to use (auto-select if None)
            auto_approve: If True, auto-approve all gates

        Returns:
            List of StoryProcessingResult for each story
        """
        # Step 1: Initialize state from MVP spec
        self._progress.stage = PipelineStage.MVP_SPEC
        if not self.initialize_from_mvp_spec(mvp_spec_text):
            return []

        # Step 2: Stack selection
        self._progress.stage = PipelineStage.STACK_SELECTION
        if stack_template_id is None:
            platform, _ = recommend_platform(mvp_spec_text)
            stack_template_id = get_default_template_for_platform(platform)

        self.apply_stack_selection(stack_template_id)

        # Step 3: Process all stories
        return self.process_all_stories(auto_approve=auto_approve)


def run_notes_app_pipeline(
    session_dir: Path | str, mvp_spec_text: str
) -> list[StoryProcessingResult]:
    """Convenience function to run the Notes App pipeline.

    Args:
        session_dir: Directory for session state
        mvp_spec_text: Notes App MVP specification

    Returns:
        List of StoryProcessingResult
    """
    orchestrator = PipelineOrchestrator(session_dir)
    return orchestrator.run_full_pipeline(
        mvp_spec_text,
        stack_template_id="web-python-react",
        auto_approve=True,
    )
