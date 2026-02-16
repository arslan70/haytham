"""Project state management for Haytham.

This module provides the ProjectStateManager class that manages project.yaml
as the single source of truth for project state, replacing hardcoded constants.
"""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

import yaml

if TYPE_CHECKING:
    from .state_models import PipelineState


@dataclass
class EnrichedData:
    """Progressive enrichment data from workflow phases.

    Stores summaries from each phase to provide context for downstream phases.
    """

    concept: dict[str, Any] | None = None  # Phase 1 summary
    market: dict[str, Any] | None = None  # Phase 2 summary
    niche: dict[str, Any] | None = None  # Phase 3 summary
    validation: dict[str, Any] | None = None  # Phase 6 summary


@dataclass
class ProjectState:
    """Single source of truth for project state.

    Represents the complete state of a project including the system goal,
    workflow progress, and enriched data from each phase.
    """

    system_goal: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
    status: str = "awaiting_goal"  # awaiting_goal, in_progress, completed, archived
    current_phase: int = 0  # 0 = awaiting goal, 1-7 = workflow phases
    enriched_data: EnrichedData = field(default_factory=EnrichedData)


class ProjectStateManager:
    """Manages project.yaml read/write operations.

    This class provides the interface for reading and writing project state
    to the project.yaml file, which serves as the single source of truth
    for the system goal and workflow progress.

    Directory Structure:
        session/
        └── project.yaml    # Project state file

    Example project.yaml:
        system_goal: "A product that lets you create a startup by writing prompts"
        created_at: "2024-01-15T10:00:00Z"
        updated_at: "2024-01-15T12:00:00Z"
        status: "in_progress"
        current_phase: 3
        enriched_data:
          concept:
            problem_statement: "Founders lack systematic validation"
            target_audience: "Solo founders, bootstrappers"
          market:
            tam: "$50B"
            growth_rate: "15% CAGR"
          niche: null
          validation: null
    """

    PROJECT_FILE = "project.yaml"

    def __init__(self, session_dir: Path):
        """Initialize the ProjectStateManager.

        Args:
            session_dir: Path to the session directory where project.yaml is stored
        """
        self.session_dir = session_dir
        self.project_file = session_dir / self.PROJECT_FILE

    def exists(self) -> bool:
        """Check if project.yaml exists.

        Returns:
            True if project.yaml exists, False otherwise
        """
        return self.project_file.exists()

    def has_system_goal(self) -> bool:
        """Check if project.yaml exists and has a valid system_goal.

        Returns:
            True if project.yaml exists and has a non-empty system_goal,
            False otherwise
        """
        if not self.exists():
            return False
        state = self.load()
        return state.system_goal is not None and len(state.system_goal.strip()) > 0

    def load(self) -> ProjectState:
        """Load project state from project.yaml.

        Returns:
            ProjectState object with data from project.yaml,
            or default ProjectState if file doesn't exist
        """
        if not self.exists():
            return ProjectState()

        with open(self.project_file) as f:
            data = yaml.safe_load(f) or {}

        enriched_data_raw = data.get("enriched_data", {}) or {}
        enriched = EnrichedData(
            concept=enriched_data_raw.get("concept"),
            market=enriched_data_raw.get("market"),
            niche=enriched_data_raw.get("niche"),
            validation=enriched_data_raw.get("validation"),
        )

        return ProjectState(
            system_goal=data.get("system_goal"),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
            status=data.get("status", "awaiting_goal"),
            current_phase=data.get("current_phase", 0),
            enriched_data=enriched,
        )

    def save(self, state: ProjectState) -> None:
        """Save project state to project.yaml.

        Updates the updated_at timestamp automatically.

        Args:
            state: ProjectState object to save
        """
        state.updated_at = datetime.utcnow().isoformat() + "Z"

        data = {
            "system_goal": state.system_goal,
            "created_at": state.created_at,
            "updated_at": state.updated_at,
            "status": state.status,
            "current_phase": state.current_phase,
            "enriched_data": {
                "concept": state.enriched_data.concept,
                "market": state.enriched_data.market,
                "niche": state.enriched_data.niche,
                "validation": state.enriched_data.validation,
            },
        }

        self.session_dir.mkdir(parents=True, exist_ok=True)
        with open(self.project_file, "w") as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)

    def set_system_goal(self, goal: str) -> ProjectState:
        """Set the system goal and initialize project state.

        Creates or updates project.yaml with the provided system goal.
        Sets status to "in_progress" and current_phase to 1.

        Args:
            goal: The system goal string provided by the user

        Returns:
            Updated ProjectState object
        """
        state = self.load() if self.exists() else ProjectState()
        state.system_goal = goal
        state.status = "in_progress"
        state.current_phase = 1
        if not state.created_at:
            state.created_at = datetime.utcnow().isoformat() + "Z"
        self.save(state)
        return state

    def update_phase(self, phase_num: int, enriched_summary: dict[str, Any] | None = None) -> None:
        """Update current phase and optionally add enriched data.

        Updates the current_phase field and stores enriched data summaries
        for the appropriate phase. Phase 7 completion sets status to "completed".

        Args:
            phase_num: Phase number (1-7)
            enriched_summary: Optional dict containing phase summary data
        """
        state = self.load()
        state.current_phase = phase_num

        if enriched_summary:
            if phase_num == 1:
                state.enriched_data.concept = enriched_summary
            elif phase_num == 2:
                state.enriched_data.market = enriched_summary
            elif phase_num == 3:
                state.enriched_data.niche = enriched_summary
            elif phase_num == 6:
                state.enriched_data.validation = enriched_summary

        if phase_num == 7:
            state.status = "completed"

        self.save(state)

    def get_system_goal(self) -> str | None:
        """Get the system goal from project state.

        Returns:
            The system goal string, or None if not set
        """
        state = self.load()
        return state.system_goal


class PipelineStateManager:
    """Manages pipeline state within project.yaml.

    Extends existing ProjectStateManager pattern for the story-to-implementation
    pipeline. All pipeline state is stored in project.yaml under the 'pipeline' key.

    This allows pipeline state to coexist with existing project state
    (system_goal, status, enriched_data, etc.) in a single file.

    Example project.yaml with pipeline state:
        system_goal: "A notes app..."
        status: in_progress
        current_phase: 5
        enriched_data: {...}
        pipeline:
          schema_version: "1.0"
          stack: {...}
          entities: [...]
          stories: [...]
          tasks: [...]
          decisions: [...]
          current: {...}

    Usage:
        manager = PipelineStateManager(Path("session"))
        state = manager.load_pipeline_state()
        # ... modify state ...
        manager.save_pipeline_state(state)
    """

    PROJECT_FILE = "project.yaml"

    def __init__(self, session_dir: Path):
        """Initialize the PipelineStateManager.

        Args:
            session_dir: Path to the session directory where project.yaml is stored
        """
        self.session_dir = session_dir
        self.project_file = session_dir / self.PROJECT_FILE

    def exists(self) -> bool:
        """Check if project.yaml exists.

        Returns:
            True if project.yaml exists, False otherwise
        """
        return self.project_file.exists()

    def has_pipeline_state(self) -> bool:
        """Check if project.yaml has pipeline state.

        Returns:
            True if project.yaml exists and has a 'pipeline' section,
            False otherwise
        """
        if not self.exists():
            return False
        with open(self.project_file) as f:
            data = yaml.safe_load(f) or {}
        return "pipeline" in data

    def load_pipeline_state(self) -> "PipelineState":
        """Load pipeline state from project.yaml.

        If project.yaml doesn't exist or has no pipeline section,
        returns an empty PipelineState.

        Returns:
            PipelineState object with data from project.yaml

        Raises:
            FileNotFoundError: If project.yaml doesn't exist
        """
        # Import here to avoid circular imports
        from .state_models import PipelineState

        if not self.exists():
            raise FileNotFoundError(f"project.yaml not found: {self.project_file}")

        with open(self.project_file) as f:
            data = yaml.safe_load(f) or {}

        pipeline_data = data.get("pipeline", {})

        # Handle datetime serialization for decisions
        if "decisions" in pipeline_data:
            for decision in pipeline_data["decisions"]:
                if "made_at" in decision and isinstance(decision["made_at"], str):
                    from datetime import datetime as dt

                    try:
                        decision["made_at"] = dt.fromisoformat(
                            decision["made_at"].replace("Z", "+00:00")
                        )
                    except (ValueError, AttributeError):
                        pass

        return PipelineState(**pipeline_data)

    def save_pipeline_state(self, state: "PipelineState") -> None:
        """Save pipeline state to project.yaml, preserving other fields.

        This updates only the 'pipeline' section of project.yaml,
        leaving system_goal, status, enriched_data, etc. unchanged.

        Args:
            state: PipelineState object to save
        """
        # Load existing data to preserve other fields
        if self.exists():
            with open(self.project_file) as f:
                data = yaml.safe_load(f) or {}
        else:
            data = {}

        # Convert state to dict, handling datetime serialization
        state_dict = state.model_dump()

        # Convert datetime objects to ISO strings for YAML
        if "decisions" in state_dict:
            for decision in state_dict["decisions"]:
                if "made_at" in decision and decision["made_at"] is not None:
                    if hasattr(decision["made_at"], "isoformat"):
                        decision["made_at"] = decision["made_at"].isoformat() + "Z"

        # Update pipeline section
        data["pipeline"] = state_dict

        # Ensure session directory exists
        self.session_dir.mkdir(parents=True, exist_ok=True)

        # Save back with preserved field order
        with open(self.project_file, "w") as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)

    def initialize_pipeline_state(self) -> "PipelineState":
        """Initialize empty pipeline state in project.yaml.

        Creates the pipeline section with default values.
        Does not overwrite if pipeline state already exists.

        Returns:
            PipelineState object (new or existing)
        """
        from .state_models import PipelineState

        if self.has_pipeline_state():
            return self.load_pipeline_state()

        state = PipelineState()
        self.save_pipeline_state(state)
        return state
