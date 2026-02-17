"""Phase-boundary verifiers for concept fidelity enforcement (ADR-022).

Verifiers run at decision gates to check cumulative phase output against the
concept anchor. This is categorically different from self-checking: a separate
agent with a narrow mandate reviews the producing agent's work.

Each verifier:
- Receives the concept anchor (~500 tokens, fixed)
- Receives the phase's stage outputs (1-3 stages, manageable context)
- Has a focused rubric for that phase
- Returns structured verification results
"""

# Import schemas first (no external dependencies)
from .schemas import (
    GenericizationFlag,
    InvariantViolation,
    PhaseVerification,
)

# Lazy imports for base module (requires burr)
__all__ = [
    "PhaseVerification",
    "InvariantViolation",
    "GenericizationFlag",
    # These are available via get_verifier() and run_phase_verification()
    "get_verifier",
    "run_phase_verification",
]


def get_verifier(phase: str):
    """Get the verifier for a phase (lazy import)."""
    from .base import get_verifier as _get_verifier

    return _get_verifier(phase)


def run_phase_verification(phase: str, state):
    """Run verification for a phase (lazy import)."""
    from .base import run_phase_verification as _run_phase_verification

    return _run_phase_verification(phase, state)
