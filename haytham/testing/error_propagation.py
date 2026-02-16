"""Error propagation testing for phase-boundary verifiers (ADR-022 Part 7d).

Measures whether phase-boundary verifiers reduce error propagation across
the pipeline. Based on findings from Kim et al. (2025) showing that centralized
verification reduces error amplification from 17.2x to 4.4x.

Measurement approach:
1. Introduce a known error at Stage N (e.g., wrong market size, fabricated claim)
2. Track whether the error appears in Stages N+1, N+2, ... N+k
3. Compare propagation rates with and without verifiers enabled

Target: Phase-boundary verifiers should reduce error propagation by at least 50%.
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class ErrorType(Enum):
    """Types of errors that can be injected for chaos testing."""

    # Fabrication errors (S2)
    FABRICATED_STATISTIC = "fabricated_statistic"
    FABRICATED_CLAIM = "fabricated_claim"
    WRONG_COMPETITOR = "wrong_competitor"

    # Contradiction errors (S3)
    TRAIT_CONTRADICTION = "trait_contradiction"
    SCOPE_CONTRADICTION = "scope_contradiction"

    # Genericization errors (S1)
    GENERICIZED_FEATURE = "genericized_feature"
    EXPANDED_AUDIENCE = "expanded_audience"

    # Constraint violation (anchor invariants)
    INVARIANT_VIOLATION = "invariant_violation"


@dataclass
class InjectedError:
    """An error injected into the pipeline for testing."""

    error_type: ErrorType
    stage_injected: str  # Stage where error was introduced
    description: str  # Human-readable description
    original_value: str  # What the correct value should be
    injected_value: str  # What we replaced it with
    detection_keywords: list[str] = field(default_factory=list)  # Keywords to detect propagation


@dataclass
class PropagationResult:
    """Result of tracking error propagation through the pipeline."""

    error: InjectedError
    stages_checked: list[str]
    stages_with_error: list[str]  # Stages where error appeared
    stages_caught: list[str]  # Stages where verifier caught the error
    propagation_rate: float  # Percentage of downstream stages affected

    @property
    def was_caught(self) -> bool:
        """Check if the error was caught by any verifier."""
        return len(self.stages_caught) > 0

    @property
    def propagation_stopped(self) -> bool:
        """Check if error propagation was stopped after being caught."""
        if not self.was_caught:
            return False
        # Check if stages after the catch point are error-free
        catch_index = min(
            self.stages_checked.index(s) for s in self.stages_caught if s in self.stages_checked
        )
        later_stages = self.stages_checked[catch_index + 1 :]
        return not any(s in self.stages_with_error for s in later_stages)


@dataclass
class ChaosTestResult:
    """Results from a full chaos testing run."""

    test_idea: str
    verifiers_enabled: bool
    errors_injected: list[InjectedError]
    propagation_results: list[PropagationResult]

    @property
    def average_propagation_rate(self) -> float:
        """Calculate average propagation rate across all injected errors."""
        if not self.propagation_results:
            return 0.0
        return sum(r.propagation_rate for r in self.propagation_results) / len(
            self.propagation_results
        )

    @property
    def catch_rate(self) -> float:
        """Percentage of errors caught by verifiers."""
        if not self.propagation_results:
            return 0.0
        caught = sum(1 for r in self.propagation_results if r.was_caught)
        return caught / len(self.propagation_results)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "test_idea": self.test_idea,
            "verifiers_enabled": self.verifiers_enabled,
            "errors_injected": len(self.errors_injected),
            "average_propagation_rate": self.average_propagation_rate,
            "catch_rate": self.catch_rate,
            "details": [
                {
                    "error_type": r.error.error_type.value,
                    "stage_injected": r.error.stage_injected,
                    "propagation_rate": r.propagation_rate,
                    "was_caught": r.was_caught,
                    "stages_with_error": r.stages_with_error,
                }
                for r in self.propagation_results
            ],
        }


# =============================================================================
# Error Injection Templates
# =============================================================================

ERROR_TEMPLATES: dict[ErrorType, dict[str, Any]] = {
    ErrorType.FABRICATED_STATISTIC: {
        "stages": ["market-context", "risk-assessment"],
        "template": {
            "original_value": "[real market data]",
            "injected_value": "The market size is $500 billion with 45% CAGR [validated]",
            "detection_keywords": ["$500 billion", "45% CAGR"],
        },
    },
    ErrorType.WRONG_COMPETITOR: {
        "stages": ["market-context"],
        "template": {
            "original_value": "[relevant competitors]",
            "injected_value": "Key competitors include Giftster, Elfster, and Wishlistr",
            "detection_keywords": ["Giftster", "Elfster", "Wishlistr"],
        },
    },
    ErrorType.TRAIT_CONTRADICTION: {
        "stages": ["system-traits"],
        "template": {
            "original_value": "realtime: true",
            "injected_value": "realtime: false (MVP focuses on batch processing)",
            "detection_keywords": ["realtime: false", "batch processing"],
        },
    },
    ErrorType.GENERICIZED_FEATURE: {
        "stages": ["mvp-scope", "capability-model"],
        "template": {
            "original_value": "1:7 receiver/giver structure",
            "injected_value": "flexible group sizes to accommodate various needs",
            "detection_keywords": ["flexible group", "various needs", "any size"],
        },
    },
    ErrorType.EXPANDED_AUDIENCE: {
        "stages": ["validation-summary", "mvp-scope"],
        "template": {
            "original_value": "closed community for existing patients",
            "injected_value": "open platform for anyone interested in wellness",
            "detection_keywords": ["open platform", "anyone", "general public"],
        },
    },
}


def create_error_injection(
    error_type: ErrorType,
    stage: str,
    custom_values: dict[str, str] | None = None,
) -> InjectedError:
    """Create an error injection configuration.

    Args:
        error_type: Type of error to inject
        stage: Stage where error will be introduced
        custom_values: Optional custom original/injected values

    Returns:
        InjectedError ready for injection
    """
    template = ERROR_TEMPLATES.get(error_type, {}).get("template", {})

    original = (
        custom_values.get("original_value") if custom_values else template.get("original_value", "")
    )
    injected = (
        custom_values.get("injected_value") if custom_values else template.get("injected_value", "")
    )
    keywords = template.get("detection_keywords", [])

    return InjectedError(
        error_type=error_type,
        stage_injected=stage,
        description=f"Injected {error_type.value} at {stage}",
        original_value=original,
        injected_value=injected,
        detection_keywords=keywords,
    )


def detect_error_in_output(output: str, error: InjectedError) -> bool:
    """Check if an injected error appears in a stage output.

    Args:
        output: Stage output text to check
        error: The injected error to look for

    Returns:
        True if error appears to have propagated to this output
    """
    output_lower = output.lower()

    # Check for detection keywords
    for keyword in error.detection_keywords:
        if keyword.lower() in output_lower:
            return True

    # Check for injected value directly
    if error.injected_value.lower() in output_lower:
        return True

    return False


def calculate_propagation_rate(
    error: InjectedError,
    stage_outputs: dict[str, str],
    stage_order: list[str],
) -> PropagationResult:
    """Calculate how far an error propagated through the pipeline.

    Args:
        error: The injected error
        stage_outputs: Dict mapping stage slug to output content
        stage_order: Ordered list of stage slugs

    Returns:
        PropagationResult with propagation statistics
    """
    # Find stages after the injection point
    try:
        injection_index = stage_order.index(error.stage_injected)
    except ValueError:
        logger.warning(f"Injection stage {error.stage_injected} not in stage order")
        return PropagationResult(
            error=error,
            stages_checked=[],
            stages_with_error=[],
            stages_caught=[],
            propagation_rate=0.0,
        )

    downstream_stages = stage_order[injection_index + 1 :]
    stages_with_error = []
    stages_caught = []

    for stage in downstream_stages:
        output = stage_outputs.get(stage, "")
        if not output:
            continue

        if detect_error_in_output(output, error):
            stages_with_error.append(stage)

        # Check if verifier caught the error (look for warning/violation markers)
        if "BLOCKING" in output or "invariant violated" in output.lower():
            if any(kw.lower() in output.lower() for kw in error.detection_keywords):
                stages_caught.append(stage)

    propagation_rate = len(stages_with_error) / len(downstream_stages) if downstream_stages else 0.0

    return PropagationResult(
        error=error,
        stages_checked=downstream_stages,
        stages_with_error=stages_with_error,
        stages_caught=stages_caught,
        propagation_rate=propagation_rate,
    )


def compare_propagation_rates(
    with_verifiers: ChaosTestResult,
    without_verifiers: ChaosTestResult,
) -> dict[str, Any]:
    """Compare error propagation rates with and without verifiers.

    Args:
        with_verifiers: Results with phase-boundary verifiers enabled
        without_verifiers: Results without verifiers

    Returns:
        Comparison metrics including reduction percentage
    """
    rate_with = with_verifiers.average_propagation_rate
    rate_without = without_verifiers.average_propagation_rate

    reduction = (rate_without - rate_with) / rate_without * 100 if rate_without > 0 else 0.0

    return {
        "propagation_rate_with_verifiers": rate_with,
        "propagation_rate_without_verifiers": rate_without,
        "reduction_percentage": reduction,
        "catch_rate_with_verifiers": with_verifiers.catch_rate,
        "target_reduction": 50.0,  # ADR-022 target
        "meets_target": reduction >= 50.0,
        "research_baseline": {
            "independent_agents": 17.2,  # Error amplification factor
            "with_verification": 4.4,
            "expected_reduction": 74.4,  # (17.2 - 4.4) / 17.2 * 100
        },
    }


# =============================================================================
# Standard Pipeline Stage Order
# =============================================================================

PIPELINE_STAGE_ORDER = [
    "idea-analysis",
    "market-context",
    "risk-assessment",
    "pivot-strategy",
    "validation-summary",
    "mvp-scope",
    "capability-model",
    "system-traits",
    "build-buy-analysis",
    "architecture-decisions",
    "story-generation",
    "story-validation",
    "dependency-ordering",
]
