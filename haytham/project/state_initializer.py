"""State Initializer for the Story-to-Implementation Pipeline.

Initializes pipeline state in project.yaml from a parsed MVP specification.
This bridges the gap between MVP spec generation and the implementation pipeline.

Reference: ADR-001c: Initialization from MVP Spec
"""

from pathlib import Path

from .mvp_spec_parser import MVPSpecParser, ParsedMVPSpec
from .mvp_spec_validator import validate_mvp_spec
from .project_state import PipelineStateManager
from .state_models import PipelineState


class StateInitializationError(Exception):
    """Raised when state initialization fails."""

    pass


def initialize_pipeline_state(
    manager: PipelineStateManager,
    parsed_spec: ParsedMVPSpec,
    validate: bool = True,
) -> PipelineState:
    """Create initial pipeline state from parsed MVP specification.

    This is called after MVP spec stage completes and before stack selection.
    Entities are added with status="planned", stories with status="pending".

    Args:
        manager: PipelineStateManager for saving state
        parsed_spec: Parsed MVP specification from MVPSpecParser
        validate: Whether to validate the spec before initialization

    Returns:
        Initialized PipelineState

    Raises:
        StateInitializationError: If validation fails or initialization errors occur
    """
    # Validate if requested
    if validate:
        errors = validate_mvp_spec(parsed_spec)
        if errors:
            raise StateInitializationError(
                "MVP spec validation failed:\n" + "\n".join(f"  - {e}" for e in errors)
            )

    # Create new pipeline state
    state = PipelineState()

    # Add entities from domain model
    for entity in parsed_spec.entities:
        # Ensure status is planned
        entity.status = "planned"
        state.entities.append(entity)

    # Add stories from MVP spec
    for story in parsed_spec.stories:
        # Ensure status is pending
        story.status = "pending"
        state.stories.append(story)

    # Set initial current context
    state.current.story = None
    state.current.chunk = "initialized"

    # Save to project.yaml
    manager.save_pipeline_state(state)

    return state


def initialize_from_mvp_spec_text(
    session_dir: Path,
    mvp_spec_text: str,
    validate: bool = True,
) -> PipelineState:
    """Initialize pipeline state directly from MVP spec markdown text.

    Convenience function that combines parsing and initialization.

    Args:
        session_dir: Path to session directory containing project.yaml
        mvp_spec_text: Raw markdown text of enhanced MVP specification
        validate: Whether to validate the spec before initialization

    Returns:
        Initialized PipelineState

    Raises:
        StateInitializationError: If parsing or validation fails
    """
    # Parse the MVP spec
    parser = MVPSpecParser()

    # Check for required sections
    missing = parser.validate_completeness(mvp_spec_text)
    if missing:
        raise StateInitializationError(
            "MVP spec is missing required sections:\n" + "\n".join(f"  - {m}" for m in missing)
        )

    # Parse the spec
    parsed_spec = parser.parse(mvp_spec_text)

    # Validate entity and story counts
    if not parsed_spec.entities:
        raise StateInitializationError("No entities found in MVP spec domain model")
    if not parsed_spec.stories:
        raise StateInitializationError("No stories found in MVP spec")

    # Initialize state
    manager = PipelineStateManager(session_dir)
    return initialize_pipeline_state(manager, parsed_spec, validate=validate)


def reinitialize_pipeline_state(
    manager: PipelineStateManager,
    parsed_spec: ParsedMVPSpec,
    preserve_progress: bool = False,
) -> PipelineState:
    """Reinitialize pipeline state, optionally preserving progress.

    This can be used to update the pipeline state when the MVP spec changes.

    Args:
        manager: PipelineStateManager for saving state
        parsed_spec: Newly parsed MVP specification
        preserve_progress: If True, preserve status of entities/stories that exist
                          in both old and new specs

    Returns:
        Reinitialized PipelineState
    """
    # Load existing state if preserving progress
    existing_state = None
    existing_entity_status: dict[str, str] = {}
    existing_story_status: dict[str, str] = {}

    if preserve_progress and manager.has_pipeline_state():
        existing_state = manager.load_pipeline_state()
        existing_entity_status = {e.id: e.status for e in existing_state.entities}
        existing_story_status = {s.id: s.status for s in existing_state.stories}

    # Create new state
    state = PipelineState()

    # Add entities, preserving status if applicable
    for entity in parsed_spec.entities:
        if preserve_progress and entity.id in existing_entity_status:
            entity.status = existing_entity_status[entity.id]
        else:
            entity.status = "planned"
        state.entities.append(entity)

    # Add stories, preserving status if applicable
    for story in parsed_spec.stories:
        if preserve_progress and story.id in existing_story_status:
            story.status = existing_story_status[story.id]
        else:
            story.status = "pending"
        state.stories.append(story)

    # Preserve decisions and tasks if they exist
    if preserve_progress and existing_state:
        state.decisions = existing_state.decisions
        state.tasks = existing_state.tasks
        state.stack = existing_state.stack

    # Set current context
    state.current.story = None
    state.current.chunk = "reinitialized"

    # Save to project.yaml
    manager.save_pipeline_state(state)

    return state
