"""Workflow 2: Technical Translation (Software Architect Role).

This package implements Workflow 2 as defined in ADR-004:
Multi-Phase Workflow Architecture — Workflow Boundaries and State Handoff.

Workflow 2 translates capabilities into implementable, dependency-ordered
stories for coding agents. It operates in a diff-based mode, computing
what needs attention rather than operating in predefined modes.

Key components:
- ArchitectureDiff: What needs attention (uncovered capabilities, affected decisions)
- compute_architecture_diff(): Pure function to compute the diff
- create_architect_workflow(): Factory to create the Burr workflow
- validate_entry_conditions(): Validate preconditions for starting Workflow 2
- run_ai_judge_evaluation(): Manual AI Judge (ADR-006 pattern)

Entry conditions:
- capability_model_status == "completed" in Workflow 1
- At least 1 functional capability exists in VectorDB
- MVP Scope document exists

Stages (in order):
1. architecture_decisions: Define key technical decisions (DEC-*)
2. component_boundaries: Define component structure and entities (ENT-*)
3. story_generation: Generate stories → Backlog.md with implements:CAP-* labels
4. story_validation: Basic label validation (non-blocking)
5. dependency_ordering: Order stories by dependencies

Manual evaluation (ADR-006):
- run_ai_judge_evaluation(): Triggered via button, writes to improvement_signals.md
"""

from .actions import (
    run_ai_judge_evaluation,
)
from .diff import (
    ArchitectureDiff,
    compute_architecture_diff,
    get_diff_context_for_prompt,
)
from .factory import (
    EntryConditionResult,
    Workflow2EntryValidator,
    Workflow2Result,
    WorkflowContext,
    create_architect_workflow,
    load_workflow_context,
    run_architect_workflow,
    validate_entry_conditions,
)

__all__ = [
    # Diff computation
    "ArchitectureDiff",
    "compute_architecture_diff",
    "get_diff_context_for_prompt",
    # Entry validation
    "EntryConditionResult",
    "Workflow2EntryValidator",
    "validate_entry_conditions",
    # Context loading
    "WorkflowContext",
    "load_workflow_context",
    # Workflow factory
    "create_architect_workflow",
    "run_architect_workflow",
    "Workflow2Result",
    # Manual evaluation (ADR-006)
    "run_ai_judge_evaluation",
]
