"""WHAT phase verification (ADR-022).

This module verifies WHAT phase outputs against the concept anchor using a
single comprehensive verification agent that checks:

- **Invariants**: Verifies anchor invariants are honored in MVP scope
- **Genericization**: Detects identity drift (specific → generic patterns)
- **Intent Alignment**: Verifies scope alignment with original intent

Usage:
    from haytham.workflow.verifiers.what_phase_swarm import (
        run_what_phase_swarm_verification,
    )

    result = run_what_phase_swarm_verification(anchor, anchor_str, phase_outputs)
"""

from .swarm import run_what_phase_swarm_verification

__all__ = ["run_what_phase_swarm_verification"]
