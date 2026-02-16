"""Pydantic models for pipeline state schema.

This module defines the data models for the Story-to-Implementation Pipeline state.
All pipeline state is stored in session/project.yaml under the 'pipeline' key.

Reference: ADR-001c: System State Model
"""

from datetime import datetime

from pydantic import BaseModel, Field


class EntityAttribute(BaseModel):
    """Attribute definition for an entity.

    Represents a single field/column in a domain entity.
    """

    name: str
    type: str  # String, Integer, DateTime, Boolean, Text, UUID
    primary_key: bool = False
    unique: bool = False
    foreign_key: str | None = None  # Reference to entity ID (E-XXX)


class EntityRelationship(BaseModel):
    """Relationship between entities.

    Represents how entities are connected (one-to-many, etc).
    """

    type: str  # has_many, belongs_to, has_one
    target: str  # Entity ID (E-XXX)
    foreign_key: str | None = None


class Entity(BaseModel):
    """Domain entity definition.

    Represents a data structure in the system (e.g., User, Note).
    Status tracks whether the entity has been implemented in code.
    """

    id: str = ""  # E-XXX format, assigned by StateUpdater if empty
    name: str
    status: str = "planned"  # planned, implemented
    attributes: list[EntityAttribute] = Field(default_factory=list)
    relationships: list[EntityRelationship] = Field(default_factory=list)
    source_story: str | None = None  # S-XXX that introduced this entity
    file_path: str | None = None  # Path where entity is implemented


class Ambiguity(BaseModel):
    """Ambiguity detected during story interpretation.

    When a story is ambiguous, the interpretation engine creates
    an Ambiguity record. Decision-required ambiguities block processing
    until the user resolves them.
    """

    question: str
    classification: str  # decision_required, auto_resolvable
    options: list[str] = Field(default_factory=list)
    default: str | None = None
    resolved: bool = False
    resolution: str | None = None


class Story(BaseModel):
    """User story with interpretation metadata.

    Represents a feature to be implemented. Stories go through
    a lifecycle: pending → interpreting → designing → implementing → completed
    """

    id: str = ""  # S-XXX format, assigned by StateUpdater if empty
    title: str
    priority: str = "P0"  # P0, P1, P2
    status: str = "pending"  # pending, interpreting, designing, implementing, completed
    user_story: str  # "As a... I want... so that..."
    acceptance_criteria: list[str] = Field(default_factory=list)
    depends_on: list[str] = Field(default_factory=list)  # Entity or Story IDs
    ambiguities: list[Ambiguity] = Field(default_factory=list)
    tasks: list[str] = Field(default_factory=list)  # Task IDs (T-XXX)


class Task(BaseModel):
    """Implementation task for a story.

    Tasks are the atomic units of work generated from stories.
    Each task typically results in one or more file changes.
    """

    id: str = ""  # T-XXX format, assigned by StateUpdater if empty
    story_id: str  # S-XXX
    title: str
    status: str = "pending"  # pending, in_progress, completed, failed
    description: str = ""
    file_path: str | None = None  # Path where task was implemented


class Decision(BaseModel):
    """Architectural decision record.

    Records important decisions made during the pipeline,
    including the rationale and what components are affected.
    """

    id: str = ""  # D-XXX format, assigned by StateUpdater if empty
    title: str
    rationale: str
    made_at: datetime | None = None
    affects: list[str] = Field(default_factory=list)  # Entity, Story, or Task IDs


class BackendStack(BaseModel):
    """Backend technology stack configuration."""

    language: str = "python"
    language_version: str = "3.11+"
    framework: str = "fastapi"
    orm: str = "sqlalchemy"
    database: str = "sqlite"


class FrontendStack(BaseModel):
    """Frontend technology stack configuration."""

    language: str = "typescript"
    framework: str = "react"
    framework_version: str = "18+"
    bundler: str = "vite"
    styling: str = "tailwindcss"


class TestingStack(BaseModel):
    """Testing framework configuration."""

    backend: str = "pytest"
    frontend: str = "vitest"


class Stack(BaseModel):
    """Technology stack configuration.

    Populated during Session 3 (Stack Selection) when
    the user chooses the platform and technology stack.
    """

    platform: str = "web_application"  # web_application, cli, api
    backend: BackendStack | None = None
    frontend: FrontendStack | None = None
    testing: TestingStack | None = None
    project_structure: dict = Field(default_factory=dict)  # e.g., backend_dir, frontend_dir


class PipelineCurrent(BaseModel):
    """Current processing context.

    Tracks what the pipeline is currently working on,
    useful for resuming after interruptions.
    """

    story: str | None = None  # S-XXX being processed
    chunk: str = "ready"  # Current pipeline stage


class PipelineState(BaseModel):
    """Complete pipeline state schema.

    This extends the existing project.yaml with pipeline-specific fields.
    Stored in session/project.yaml alongside existing fields under 'pipeline' key.

    Example project.yaml structure:
        system_goal: "..."
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
    """

    schema_version: str = "1.0"

    # Stack (populated in Session 3)
    stack: Stack | None = None

    # Domain model
    entities: list[Entity] = Field(default_factory=list)

    # User stories from MVP spec
    stories: list[Story] = Field(default_factory=list)

    # Implementation tasks
    tasks: list[Task] = Field(default_factory=list)

    # Architectural decisions
    decisions: list[Decision] = Field(default_factory=list)

    # Current processing context
    current: PipelineCurrent = Field(default_factory=PipelineCurrent)
