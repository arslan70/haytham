"""Story Generator Agent.

Generates implementation-ready user stories for an AI coding agent.
Uses a two-pass architecture: skeleton planning + parallel detail agents.
"""

from .story_generation_models import (
    StoryGenerationHybridOutput,
    StoryHybrid,
    StorySkeleton,
    StorySkeletonOutput,
)
from .story_swarm import (
    parse_stories_from_markdown,
    run_story_swarm,
)

__all__ = [
    # Models
    "StoryHybrid",
    "StoryGenerationHybridOutput",
    "StorySkeleton",
    "StorySkeletonOutput",
    # Swarm functions
    "run_story_swarm",
    "parse_stories_from_markdown",
]
