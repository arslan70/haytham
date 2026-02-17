"""Tests for Burr action metadata consistency.

Validates that @action reads/writes declarations in burr_actions.py are
consistent with StageMetadata from the registry, and that all agent names
referenced in the registry have corresponding factory entries.
"""

from haytham.workflow import burr_actions
from haytham.workflow.stage_registry import get_stage_registry

# =============================================================================
# Helpers
# =============================================================================


def _get_action_reads(action_fn) -> list[str]:
    """Extract reads from a Burr @action function.

    Burr's @action decorator stores metadata on fn.action_function (a
    FunctionBasedAction instance), not directly on the wrapper function.
    """
    af = getattr(action_fn, "action_function", None)
    if af is not None:
        return list(getattr(af, "reads", []))
    return list(getattr(action_fn, "reads", []))


def _get_action_writes(action_fn) -> list[str]:
    """Extract writes from a Burr @action function."""
    af = getattr(action_fn, "action_function", None)
    if af is not None:
        return list(getattr(af, "writes", []))
    return list(getattr(action_fn, "writes", []))


# =============================================================================
# Registry <-> Action Consistency
# =============================================================================


class TestRegistryActionConsistency:
    """Verify every stage in the registry has a corresponding Burr action."""

    def test_all_stages_have_burr_actions(self):
        """Every stage in the registry has a matching function in burr_actions."""
        registry = get_stage_registry()
        for stage in registry.all_stages(include_optional=True):
            assert hasattr(burr_actions, stage.action_name), (
                f"Stage '{stage.slug}' references action '{stage.action_name}' "
                f"but no such function exists in burr_actions"
            )

    def test_action_writes_include_state_key(self):
        """Every action's writes list includes the stage's state_key."""
        registry = get_stage_registry()
        for stage in registry.all_stages(include_optional=True):
            action_fn = getattr(burr_actions, stage.action_name)
            writes = _get_action_writes(action_fn)
            assert stage.state_key in writes, (
                f"Action '{stage.action_name}' writes={writes} "
                f"missing state_key '{stage.state_key}'"
            )

    def test_action_writes_include_status_key(self):
        """Every action's writes list includes the stage's status_key."""
        registry = get_stage_registry()
        for stage in registry.all_stages(include_optional=True):
            action_fn = getattr(burr_actions, stage.action_name)
            writes = _get_action_writes(action_fn)
            assert stage.status_key in writes, (
                f"Action '{stage.action_name}' writes={writes} "
                f"missing status_key '{stage.status_key}'"
            )

    def test_action_writes_include_current_stage(self):
        """Every stage action writes 'current_stage' for UI tracking."""
        registry = get_stage_registry()
        for stage in registry.all_stages(include_optional=True):
            action_fn = getattr(burr_actions, stage.action_name)
            writes = _get_action_writes(action_fn)
            assert "current_stage" in writes, (
                f"Action '{stage.action_name}' writes={writes} missing 'current_stage'"
            )

    def test_action_reads_include_system_goal(self):
        """Every stage action reads 'system_goal'."""
        registry = get_stage_registry()
        for stage in registry.all_stages(include_optional=True):
            action_fn = getattr(burr_actions, stage.action_name)
            reads = _get_action_reads(action_fn)
            assert "system_goal" in reads, (
                f"Action '{stage.action_name}' reads={reads} missing 'system_goal'"
            )

    def test_action_reads_include_session_manager(self):
        """Every stage action reads 'session_manager'."""
        registry = get_stage_registry()
        for stage in registry.all_stages(include_optional=True):
            action_fn = getattr(burr_actions, stage.action_name)
            reads = _get_action_reads(action_fn)
            assert "session_manager" in reads, (
                f"Action '{stage.action_name}' reads={reads} missing 'session_manager'"
            )

    def test_action_reads_include_own_status_key(self):
        """Every stage action reads its own status_key (for idempotency check)."""
        registry = get_stage_registry()
        for stage in registry.all_stages(include_optional=True):
            action_fn = getattr(burr_actions, stage.action_name)
            reads = _get_action_reads(action_fn)
            assert stage.status_key in reads, (
                f"Action '{stage.action_name}' reads={reads} "
                f"missing own status_key '{stage.status_key}'"
            )


# =============================================================================
# Required Context <-> Action Reads Consistency
# =============================================================================


class TestRequiredContextReads:
    """Verify that stages with required_context have those keys in reads."""

    def test_required_context_stages_appear_in_reads(self):
        """If a stage requires context from another stage, the state_key must be in reads."""
        registry = get_stage_registry()
        for stage in registry.all_stages(include_optional=True):
            action_fn = getattr(burr_actions, stage.action_name)
            reads = _get_action_reads(action_fn)

            for ctx_slug in stage.required_context:
                ctx_stage = registry.get_by_slug(ctx_slug)
                assert ctx_stage.state_key in reads, (
                    f"Action '{stage.action_name}' requires context from "
                    f"'{ctx_slug}' (state_key='{ctx_stage.state_key}') "
                    f"but reads={reads} doesn't include it"
                )


# =============================================================================
# Agent Factory Completeness
# =============================================================================


class TestAgentFactoryCompleteness:
    """Verify every agent name in the registry has a factory config."""

    def test_all_agent_names_have_configs(self):
        """Every agent_name used for actual LLM execution has an AGENT_CONFIGS entry.

        Stages with programmatic_executor skip agent factory lookup, so their
        agent_names are informational only and not required in AGENT_CONFIGS.
        """
        from haytham.config import AGENT_CONFIGS
        from haytham.workflow.stage_executor import get_stage_executor

        registry = get_stage_registry()
        missing = []
        for stage in registry.all_stages(include_optional=True):
            executor = get_stage_executor(stage.slug)
            # Programmatic stages don't use the agent factory
            if executor.config.programmatic_executor is not None:
                continue
            for agent_name in stage.agent_names:
                if agent_name not in AGENT_CONFIGS:
                    missing.append(f"{stage.slug}: {agent_name}")

        assert not missing, (
            "Agent names referenced in registry but missing from AGENT_CONFIGS:\n"
            + "\n".join(f"  - {m}" for m in missing)
        )


# =============================================================================
# Human-in-the-Loop Actions
# =============================================================================


class TestHumanActions:
    """Tests for human-in-the-loop actions."""

    def test_await_user_approval_exists(self):
        assert hasattr(burr_actions, "await_user_approval")

    def test_await_user_choice_exists(self):
        assert hasattr(burr_actions, "await_user_choice")

    def test_approval_writes_correct_keys(self):
        fn = burr_actions.await_user_approval
        writes = _get_action_writes(fn)
        assert "user_approved" in writes
        assert "user_feedback" in writes


# =============================================================================
# Workflow Spec <-> Action Cross-Check
# =============================================================================


class TestWorkflowSpecActions:
    """Verify workflow specs reference valid actions."""

    def test_all_spec_actions_are_real_functions(self):
        """Every action in a WorkflowSpec maps to a real function in burr_actions."""
        from haytham.workflow.workflow_specs import WORKFLOW_SPECS

        for wf_type, spec in WORKFLOW_SPECS.items():
            for action_name, action_fn in spec.actions.items():
                assert callable(action_fn), (
                    f"Spec {wf_type}: action '{action_name}' is not callable"
                )
                assert hasattr(burr_actions, action_name), (
                    f"Spec {wf_type}: action '{action_name}' not found in burr_actions"
                )

    def test_all_spec_stages_match_action_names(self):
        """Every stage in spec.stages corresponds to a key in spec.actions."""
        from haytham.workflow.workflow_specs import WORKFLOW_SPECS

        for wf_type, spec in WORKFLOW_SPECS.items():
            for stage_name in spec.stages:
                assert stage_name in spec.actions, (
                    f"Spec {wf_type}: stage '{stage_name}' not in actions dict"
                )

    def test_all_spec_entrypoints_are_valid(self):
        """Every spec's entrypoint is in its actions dict."""
        from haytham.workflow.workflow_specs import WORKFLOW_SPECS

        for wf_type, spec in WORKFLOW_SPECS.items():
            assert spec.entrypoint in spec.actions, (
                f"Spec {wf_type}: entrypoint '{spec.entrypoint}' not in actions"
            )
