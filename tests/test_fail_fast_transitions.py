"""Tests for fail-fast workflow transitions (CRIT-01).

Verifies that all multi-stage workflow specs use conditional 3-tuple
transitions with failure guards to ``workflow_failed``.
"""

import pytest
from burr.core import default

from haytham.workflow.workflow_specs import (
    ARCHITECTURE_DECISIONS_SPEC,
    BUILD_BUY_ANALYSIS_SPEC,
    IDEA_VALIDATION_SPEC,
    MVP_SPECIFICATION_SPEC,
    STORY_GENERATION_SPEC,
    WORKFLOW_SPECS,
)


def test_all_multi_stage_specs_have_conditional_transitions():
    """Every transition in multi-stage specs must be a 3-tuple with a condition."""
    for wt, spec in WORKFLOW_SPECS.items():
        if not spec.transitions:
            continue  # Single-stage workflows have no transitions
        for t in spec.transitions:
            assert len(t) == 3, (
                f"[{wt.value}] Transition {t[0]} -> {t[1]} is unconditional (2-tuple). "
                "Must include a Condition guard for fail-fast."
            )


def test_each_stage_has_failure_transition():
    """Each non-terminal stage must have a failure transition to workflow_failed."""
    for wt, spec in WORKFLOW_SPECS.items():
        if not spec.transitions:
            continue
        source_stages = {t[0] for t in spec.transitions}
        for stage in source_stages:
            failure_targets = [
                t[1] for t in spec.transitions if t[0] == stage and t[1] == "workflow_failed"
            ]
            assert failure_targets, (
                f"[{wt.value}] Stage '{stage}' has no failure transition to 'workflow_failed'"
            )


def test_each_stage_has_default_success_transition():
    """Each non-terminal stage must have a default (success) transition."""
    for wt, spec in WORKFLOW_SPECS.items():
        if not spec.transitions:
            continue
        source_stages = {t[0] for t in spec.transitions}
        for stage in source_stages:
            default_targets = [t[1] for t in spec.transitions if t[0] == stage and t[2] is default]
            assert default_targets, (
                f"[{wt.value}] Stage '{stage}' has no default (success) transition"
            )


def test_workflow_failed_in_all_spec_actions():
    """workflow_failed action must be in every spec's actions dict."""
    for wt, spec in WORKFLOW_SPECS.items():
        assert "workflow_failed" in spec.actions, (
            f"[{wt.value}] Missing 'workflow_failed' action in spec"
        )


def test_failure_transitions_checked_before_default():
    """Failure conditions must appear before default for each source stage."""
    for wt, spec in WORKFLOW_SPECS.items():
        if not spec.transitions:
            continue
        source_stages = {t[0] for t in spec.transitions}
        for stage in source_stages:
            stage_transitions = [t for t in spec.transitions if t[0] == stage]
            # Find indices of failure and default transitions
            failure_idx = None
            default_idx = None
            for i, t in enumerate(stage_transitions):
                if t[1] == "workflow_failed":
                    failure_idx = i
                if t[2] is default:
                    default_idx = i
            assert failure_idx is not None and default_idx is not None, (
                f"[{wt.value}] Stage '{stage}' missing failure or default transition"
            )
            assert failure_idx < default_idx, (
                f"[{wt.value}] Stage '{stage}': failure transition (idx {failure_idx}) "
                f"must come before default (idx {default_idx})"
            )


# ---------------------------------------------------------------------------
# Unused import guards (pytest collects but they verify import availability)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "spec",
    [
        IDEA_VALIDATION_SPEC,
        MVP_SPECIFICATION_SPEC,
        BUILD_BUY_ANALYSIS_SPEC,
        ARCHITECTURE_DECISIONS_SPEC,
        STORY_GENERATION_SPEC,
    ],
    ids=lambda s: s.workflow_type.value,
)
def test_spec_importable(spec):
    """Smoke test: each named spec constant is importable and has a workflow_type."""
    assert spec.workflow_type is not None
