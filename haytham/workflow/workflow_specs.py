"""Declarative workflow specifications (ADR-024).

Each WorkflowSpec defines a workflow as data: actions, transitions, state keys.
The shared ``build_workflow()`` in ``workflow_builder.py`` uses these specs
to construct Burr Applications without copy-paste boilerplate.
"""

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from burr.core import default, when

from haytham.workflow.stage_registry import WorkflowType

from .burr_actions import (
    architecture_decisions,
    build_buy_analysis,
    capability_model,
    dependency_ordering,
    idea_analysis,
    market_context,
    mvp_scope,
    pivot_strategy,
    risk_assessment,
    story_generation,
    story_validation,
    system_traits,
    validation_summary,
)


@dataclass
class WorkflowSpec:
    """Declarative workflow definition.

    Attributes:
        workflow_type: Which workflow this spec defines.
        actions: Mapping of action name to Burr action callable.
        transitions: List of Burr transition tuples.
        entrypoint: Name of the first action.
        tracking_project: Burr tracking project name.
        stages: Ordered list of action names (used for progress tracking).
        context_stages: Stage slugs to load from session as context
            (previous workflow outputs). Uses slug format (hyphenated).
        extra_state_keys: Additional state keys that default to "".
            Stage output keys and status keys are auto-generated from
            ``stages``: each stage gets ``{stage}: ""`` and
            ``{stage}_status: "pending"``.
        null_state_keys: State keys that default to None.
    """

    workflow_type: WorkflowType
    actions: dict[str, Callable]
    transitions: list[tuple]
    entrypoint: str
    tracking_project: str
    stages: list[str]
    context_stages: list[str] = field(default_factory=list)
    extra_state_keys: list[str] = field(default_factory=list)
    null_state_keys: list[str] = field(default_factory=list)

    def build_default_state(self) -> dict[str, Any]:
        """Build the default state dict for this workflow.

        Auto-generates ``{stage}: ""`` and ``{stage}_status: "pending"``
        for each stage, plus extra_state_keys (default "") and
        null_state_keys (default None).

        Returns:
            Dict of state key to default value.
        """
        state: dict[str, Any] = {}
        for stage in self.stages:
            state[stage] = ""
            state[f"{stage}_status"] = "pending"
        for key in self.extra_state_keys:
            state.setdefault(key, "")
        for key in self.null_state_keys:
            state[key] = None
        return state


# ---------------------------------------------------------------------------
# Workflow Spec Definitions
# ---------------------------------------------------------------------------

IDEA_VALIDATION_SPEC = WorkflowSpec(
    workflow_type=WorkflowType.IDEA_VALIDATION,
    actions={
        "idea_analysis": idea_analysis,
        "market_context": market_context,
        "risk_assessment": risk_assessment,
        "pivot_strategy": pivot_strategy,
        "validation_summary": validation_summary,
    },
    transitions=[
        ("idea_analysis", "market_context"),
        ("market_context", "risk_assessment"),
        ("risk_assessment", "pivot_strategy", when(risk_level="HIGH")),
        ("risk_assessment", "validation_summary", default),
        ("pivot_strategy", "validation_summary"),
    ],
    entrypoint="idea_analysis",
    tracking_project="haytham-validation",
    stages=[
        "idea_analysis",
        "market_context",
        "risk_assessment",
        "pivot_strategy",
        "validation_summary",
    ],
    context_stages=[],
    extra_state_keys=["risk_level"],
)

MVP_SPECIFICATION_SPEC = WorkflowSpec(
    workflow_type=WorkflowType.MVP_SPECIFICATION,
    actions={
        "mvp_scope": mvp_scope,
        "capability_model": capability_model,
        "system_traits": system_traits,
    },
    transitions=[
        ("mvp_scope", "capability_model"),
        ("capability_model", "system_traits"),
    ],
    entrypoint="mvp_scope",
    tracking_project="haytham-mvp-spec",
    stages=["mvp_scope", "capability_model", "system_traits"],
    context_stages=[
        "validation-summary",
        "idea-analysis",
        "market-context",
        "risk-assessment",
    ],
    null_state_keys=["system_traits_parsed", "system_traits_warnings"],
)

BUILD_BUY_ANALYSIS_SPEC = WorkflowSpec(
    workflow_type=WorkflowType.BUILD_BUY_ANALYSIS,
    actions={"build_buy_analysis": build_buy_analysis},
    transitions=[],
    entrypoint="build_buy_analysis",
    tracking_project="haytham-build-buy",
    stages=["build_buy_analysis"],
    context_stages=[
        "capability-model",
        "mvp-scope",
        "validation-summary",
        "idea-analysis",
    ],
)

ARCHITECTURE_DECISIONS_SPEC = WorkflowSpec(
    workflow_type=WorkflowType.ARCHITECTURE_DECISIONS,
    actions={"architecture_decisions": architecture_decisions},
    transitions=[],
    entrypoint="architecture_decisions",
    tracking_project="haytham-architecture",
    stages=["architecture_decisions"],
    context_stages=[
        "capability-model",
        "mvp-scope",
        "build-buy-analysis",
        "validation-summary",
        "idea-analysis",
    ],
)

STORY_GENERATION_SPEC = WorkflowSpec(
    workflow_type=WorkflowType.STORY_GENERATION,
    actions={
        "story_generation": story_generation,
        "story_validation": story_validation,
        "dependency_ordering": dependency_ordering,
    },
    transitions=[
        ("story_generation", "story_validation"),
        ("story_validation", "dependency_ordering"),
    ],
    entrypoint="story_generation",
    tracking_project="haytham-stories",
    stages=["story_generation", "story_validation", "dependency_ordering"],
    context_stages=[
        "capability-model",
        "mvp-scope",
        "build-buy-analysis",
        "architecture-decisions",
        "validation-summary",
        "idea-analysis",
    ],
)

WORKFLOW_SPECS: dict[WorkflowType, WorkflowSpec] = {
    WorkflowType.IDEA_VALIDATION: IDEA_VALIDATION_SPEC,
    WorkflowType.MVP_SPECIFICATION: MVP_SPECIFICATION_SPEC,
    WorkflowType.BUILD_BUY_ANALYSIS: BUILD_BUY_ANALYSIS_SPEC,
    WorkflowType.ARCHITECTURE_DECISIONS: ARCHITECTURE_DECISIONS_SPEC,
    WorkflowType.STORY_GENERATION: STORY_GENERATION_SPEC,
}
