"""Validators for pipeline integrity (ADR-022).

Provides programmatic validators that operate on stage outputs:
- Story coherence: Appetite compliance, framework conflicts (Part 4)
- Trait propagation: Constraint extraction and enforcement (Part 2b)
- Revenue evidence: Score consistency with upstream pricing signals
- Claim origin: Score consistency with external claim support ratio
"""

from ._scorecard_utils import extract_dimension_score
from .claim_origin import validate_claim_origin
from .concept_health import validate_concept_health_bindings
from .dim8_inputs import validate_dim8_inputs
from .jtbd_match import validate_jtbd_match
from .revenue_evidence import validate_revenue_evidence
from .som_sanity import validate_som_sanity
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
    # Revenue evidence consistency
    "validate_revenue_evidence",
    # Claim origin consistency
    "validate_claim_origin",
    # JTBD match consistency
    "validate_jtbd_match",
    # Concept health binding constraints
    "validate_concept_health_bindings",
    # Dim 8 input consistency
    "validate_dim8_inputs",
    # SOM sanity check
    "validate_som_sanity",
    # Shared scorecard utilities
    "extract_dimension_score",
]
