"""LLM-as-Judge agent testing framework for Haytham (ADR-018).

Extended with concept fidelity measurement (ADR-022 Part 7):
- Concept fidelity and anchor quality rubrics
- Error propagation testing for phase-boundary verifiers
- State divergence measurement using semantic similarity

Note: The criteria module requires strands_evals which may not be installed
in all environments. Error propagation and state divergence modules work
without strands_evals.
"""

# Error propagation and state divergence are always available (no strands_evals dependency)
from .error_propagation import (
    ChaosTestResult,
    ErrorType,
    InjectedError,
    PropagationResult,
    calculate_propagation_rate,
    compare_propagation_rates,
    create_error_injection,
    detect_error_in_output,
)
from .state_divergence import (
    DivergenceReport,
    SimilarityMeasurement,
    compare_divergence_reports,
    measure_pipeline_divergence,
)

__all__ = [
    # Error propagation (ADR-022 Part 7d) - always available
    "ErrorType",
    "InjectedError",
    "PropagationResult",
    "ChaosTestResult",
    "create_error_injection",
    "calculate_propagation_rate",
    "compare_propagation_rates",
    "detect_error_in_output",
    # State divergence (ADR-022 Part 7e) - always available
    "SimilarityMeasurement",
    "DivergenceReport",
    "measure_pipeline_divergence",
    "compare_divergence_reports",
]


# Lazy imports for criteria module (requires strands_evals)
def __getattr__(name):
    """Lazy import for strands_evals-dependent modules."""
    criteria_exports = {
        "AGENT_RUBRICS",
        "ANCHOR_QUALITY_RUBRIC",
        "CONCEPT_FIDELITY_RUBRIC",
        "IDEA_LABELS",
        "AgentTestConfig",
        "build_anchor_extractor_cases",
        "build_capability_model_cases",
        "build_concept_expansion_cases",
        "build_concept_fidelity_cases",
        "build_story_generator_cases",
        "build_system_traits_cases",
    }

    if name in criteria_exports:
        from . import criteria

        return getattr(criteria, name)

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
