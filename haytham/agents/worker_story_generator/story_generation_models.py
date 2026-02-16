"""Pydantic models for Story Generation structured output.

Three model families:
- StorySkeleton/StorySkeletonOutput: Lightweight planning output for the skeleton pass
- StoryHybrid/StoryGenerationHybridOutput: Hybrid model with structured metadata
  + freeform markdown content. Used with Strands structured_output for reliable
  JSON generation — no parsing needed.
"""

from pydantic import BaseModel, Field, field_validator

# =============================================================================
# Skeleton Models: Lightweight planning output for two-pass generation
# =============================================================================


class StorySkeleton(BaseModel):
    """A lightweight story skeleton for the planning pass.

    Contains only structural metadata — no detailed content.
    The detail pass fills in the full markdown body later.
    """

    id: str = Field(description="Story ID e.g. STORY-001")
    title: str = Field(description="Short descriptive title")
    layer: int = Field(description="Layer 0-5")
    implements: list[str] = Field(
        default_factory=list, description="CAP-F-*, CAP-NF-*, or DEC-* IDs this implements"
    )
    depends_on: list[str] = Field(
        default_factory=list, description="Story IDs this depends on e.g. [STORY-001]"
    )
    summary: str = Field(description="One-line description for detail agent context")

    @field_validator("implements", "depends_on", mode="before")
    @classmethod
    def coerce_to_list(cls, v):
        """LLMs sometimes return empty string or None instead of []."""
        if v is None or v == "":
            return []
        if isinstance(v, str):
            return [x.strip() for x in v.split(",") if x.strip()]
        return v


class StorySkeletonOutput(BaseModel):
    """Complete output from the skeleton planning pass."""

    stories: list[StorySkeleton] = Field(description="All planned story skeletons")


# =============================================================================
# Hybrid Models: Structured Metadata + Freeform Content
# =============================================================================


class StoryHybrid(BaseModel):
    """A story with structured metadata and freeform markdown content.

    The metadata fields (id, title, layer, implements, depends_on) are structured
    for programmatic use. The content field holds the full markdown body — description,
    acceptance criteria, files to create, verification commands, data models,
    permission matrices, Gherkin scenarios, etc.
    """

    id: str = Field(description="Story ID e.g. STORY-001")
    title: str = Field(description="Short descriptive title")
    layer: int = Field(description="Layer 0-5")
    implements: list[str] = Field(
        default_factory=list, description="CAP-F-*, CAP-NF-*, or DEC-* IDs this implements"
    )
    depends_on: list[str] = Field(
        default_factory=list, description="Story IDs this depends on e.g. [STORY-001]"
    )
    content: str = Field(
        description="Full markdown body: description, acceptance criteria, files to create, "
        "verification commands, data models, permission matrices"
    )

    @field_validator("implements", "depends_on", mode="before")
    @classmethod
    def coerce_to_list(cls, v):
        """LLMs sometimes return empty string or None instead of []."""
        if v is None or v == "":
            return []
        if isinstance(v, str):
            return [x.strip() for x in v.split(",") if x.strip()]
        return v


class StoryGenerationHybridOutput(BaseModel):
    """Complete output from story generation using the hybrid model.

    Used with Strands structured_output_model for validated JSON generation.
    """

    stories: list[StoryHybrid] = Field(description="All generated stories")

    def to_markdown(self) -> str:
        """Render stories to YAML frontmatter + body markdown format.

        This produces the same format the old system generated directly,
        for backward compatibility with session storage and display.
        """
        parts = []
        for story in self.stories:
            implements_str = ", ".join(story.implements)
            depends_str = ", ".join(story.depends_on)

            part = f"""---
id: {story.id}
title: {story.title}
layer: {story.layer}
implements: [{implements_str}]
depends_on: [{depends_str}]
---

{story.content}

---"""
            parts.append(part)

        return "\n\n".join(parts) + "\n"

    def to_dicts(self) -> list[dict]:
        """Convert stories to plain dicts for JSON serialization."""
        return [story.model_dump() for story in self.stories]
