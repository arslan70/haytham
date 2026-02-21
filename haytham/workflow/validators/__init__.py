"""Validators for pipeline integrity (ADR-022).

Provides programmatic validators that operate on stage outputs:
- Story coherence: Appetite compliance, framework conflicts (Part 4)
- Trait propagation: Constraint extraction and enforcement (Part 2b)
"""

from .story_coherence import (
    FrameworkConflict,
    StoryCoherenceReport,
    count_stories,
    detect_framework_conflicts,
    validate_story_coherence,
)
from .trait_propagation import (
    Constraints,
    constraints_post_processor,
    create_constraints_validator,
    extract_anchor_constraints,
    extract_constraints,
    extract_traits_from_output,
    validate_against_constraints,
)

__all__ = [
    # Story coherence (Part 4) - framework conflict detection only
    "FrameworkConflict",
    "StoryCoherenceReport",
    "count_stories",
    "detect_framework_conflicts",
    "validate_story_coherence",
    # Trait propagation (Part 2b)
    "Constraints",
    "extract_constraints",
    "extract_traits_from_output",
    "extract_anchor_constraints",
    "constraints_post_processor",
    "validate_against_constraints",
    "create_constraints_validator",
]
