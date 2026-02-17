"""Tests for haytham.workflow.stage_executor.

Covers the StageExecutor Template Method pattern: single-agent execution,
parallel execution, programmatic execution, custom agent factory, post-processors,
post-validators, idempotency checks, context building, and output model rendering.
"""

from unittest import mock

import pytest
from burr.core import State

from haytham.workflow.stage_executor import (
    StageExecutionConfig,
    StageExecutor,
    execute_stage,
    get_stage_executor,
)
from haytham.workflow.stage_registry import get_stage_registry

# =============================================================================
# Helpers
# =============================================================================


def _make_state(**overrides) -> State:
    """Build a minimal Burr State for testing."""
    defaults = {
        "system_goal": "A scheduling SaaS for remote teams",
        "session_manager": mock.MagicMock(),
        "idea_analysis": "",
        "idea_analysis_status": "pending",
        "market_context": "",
        "market_context_status": "pending",
        "risk_assessment": "",
        "risk_assessment_status": "pending",
        "concept_anchor_str": "",
        "current_stage": "",
    }
    defaults.update(overrides)
    return State(defaults)


# =============================================================================
# StageExecutionConfig
# =============================================================================


class TestStageExecutionConfig:
    """Tests for StageExecutionConfig dataclass."""

    def test_minimal_config(self):
        config = StageExecutionConfig(stage_slug="idea-analysis")
        assert config.stage_slug == "idea-analysis"
        assert config.query_template == ""
        assert config.parallel_agents is None
        assert config.post_processor is None
        assert config.programmatic_executor is None
        assert config.custom_agent_factory is None
        assert config.output_model is None
        assert config.post_validators is None
        assert config.use_context_tools is False

    def test_config_with_all_fields(self):
        post_proc = mock.Mock()
        prog_exec = mock.Mock()
        config = StageExecutionConfig(
            stage_slug="market-context",
            query_template="Analyze {system_goal}",
            programmatic_executor=prog_exec,
            post_processor=post_proc,
            use_context_tools=True,
        )
        assert config.query_template == "Analyze {system_goal}"
        assert config.programmatic_executor is prog_exec
        assert config.post_processor is post_proc
        assert config.use_context_tools is True


# =============================================================================
# StageExecutor: Idempotency
# =============================================================================


class TestIdempotency:
    """Tests for _is_already_completed check."""

    @mock.patch("haytham.workflow.stage_executor.run_agent")
    @mock.patch("haytham.workflow.stage_executor.save_stage_output")
    def test_skips_completed_stage(self, mock_save, mock_run):
        """Already-completed stages are skipped without re-execution."""
        state = _make_state(
            idea_analysis="## Analysis\nDone.",
            idea_analysis_status="completed",
        )
        executor = get_stage_executor("idea-analysis")
        result = executor.execute(state)

        mock_run.assert_not_called()
        assert result["idea_analysis_status"] == "completed"

    @mock.patch("haytham.workflow.stage_executor.run_agent")
    @mock.patch("haytham.workflow.stage_executor.save_stage_output")
    def test_executes_pending_stage(self, mock_save, mock_run):
        """Pending stages are executed normally."""
        mock_run.return_value = {"output": "## Analysis\nResult.", "status": "completed"}
        state = _make_state(idea_analysis="", idea_analysis_status="pending")

        executor = get_stage_executor("idea-analysis")
        result = executor.execute(state)

        mock_run.assert_called_once()
        assert result["idea_analysis"] == "## Analysis\nResult."
        assert result["idea_analysis_status"] == "completed"

    @mock.patch("haytham.workflow.stage_executor.run_agent")
    @mock.patch("haytham.workflow.stage_executor.save_stage_output")
    def test_status_completed_but_empty_output_reruns(self, mock_save, mock_run):
        """Status=completed but empty output triggers re-execution."""
        mock_run.return_value = {"output": "Fresh output.", "status": "completed"}
        state = _make_state(idea_analysis="", idea_analysis_status="completed")

        executor = get_stage_executor("idea-analysis")
        result = executor.execute(state)

        mock_run.assert_called_once()
        assert result["idea_analysis"] == "Fresh output."


# =============================================================================
# StageExecutor: Single Agent Execution
# =============================================================================


class TestSingleAgentExecution:
    """Tests for the default single-agent execution path."""

    @mock.patch("haytham.workflow.stage_executor.run_agent")
    @mock.patch("haytham.workflow.stage_executor.save_stage_output")
    def test_single_agent_happy_path(self, mock_save, mock_run):
        mock_run.return_value = {"output": "Risk assessment complete.", "status": "completed"}
        state = _make_state(
            idea_analysis="Idea content",
            market_context="Market content",
            risk_assessment="",
            risk_assessment_status="pending",
        )

        executor = get_stage_executor("risk-assessment")
        result = executor.execute(state)

        assert result["risk_assessment"] == "Risk assessment complete."
        assert result["risk_assessment_status"] == "completed"
        assert result["current_stage"] == "risk-assessment"

        # Verify run_agent was called with the correct agent name
        call_args = mock_run.call_args
        assert call_args[0][0] == "startup_validator"  # First positional arg is agent_name

    @mock.patch("haytham.workflow.stage_executor.run_agent")
    @mock.patch("haytham.workflow.stage_executor.save_stage_output")
    def test_single_agent_failure(self, mock_save, mock_run):
        mock_run.return_value = {"output": "Error: Token limit.", "status": "failed"}
        state = _make_state(
            idea_analysis="Idea",
            market_context="Market",
            risk_assessment="",
            risk_assessment_status="pending",
        )

        executor = get_stage_executor("risk-assessment")
        result = executor.execute(state)

        assert result["risk_assessment_status"] == "failed"
        # Failed stages should not save output
        mock_save.assert_not_called()

    @mock.patch("haytham.workflow.stage_executor.run_agent")
    @mock.patch("haytham.workflow.stage_executor.save_stage_output")
    def test_query_template_formats_system_goal(self, mock_save, mock_run):
        """Query template includes the system goal."""
        mock_run.return_value = {"output": "Done.", "status": "completed"}
        state = _make_state(
            idea_analysis="",
            idea_analysis_status="pending",
        )

        executor = get_stage_executor("idea-analysis")
        executor.execute(state)

        call_args = mock_run.call_args
        query = call_args[0][1]  # Second positional arg is query
        assert "A scheduling SaaS for remote teams" in query


# =============================================================================
# StageExecutor: Programmatic Execution
# =============================================================================


class TestProgrammaticExecution:
    """Tests for programmatic executor path (no LLM agent)."""

    @mock.patch("haytham.workflow.stage_executor.save_stage_output")
    def test_programmatic_executor_called(self, mock_save):
        """Programmatic executor is called instead of run_agent."""
        prog_exec = mock.Mock(return_value=("Programmatic output.", "completed"))
        config = StageExecutionConfig(
            stage_slug="market-context",
            programmatic_executor=prog_exec,
        )

        state = _make_state(
            market_context="",
            market_context_status="pending",
            idea_analysis="Prior context",
        )

        executor = StageExecutor(config)
        result = executor.execute(state)

        prog_exec.assert_called_once()
        assert result["market_context"] == "Programmatic output."
        assert result["market_context_status"] == "completed"

    @mock.patch("haytham.workflow.stage_executor.save_stage_output")
    def test_programmatic_executor_receives_state(self, mock_save):
        """Programmatic executor receives the full Burr state."""
        called_with = {}

        def capture_state(state):
            called_with["goal"] = state["system_goal"]
            return ("output", "completed")

        config = StageExecutionConfig(
            stage_slug="market-context",
            programmatic_executor=capture_state,
        )
        state = _make_state(market_context="", market_context_status="pending")

        executor = StageExecutor(config)
        executor.execute(state)

        assert called_with["goal"] == "A scheduling SaaS for remote teams"


# =============================================================================
# StageExecutor: Custom Agent Factory
# =============================================================================


class TestCustomAgentExecution:
    """Tests for custom_agent_factory execution path."""

    @mock.patch("haytham.workflow.stage_executor.save_stage_output")
    @mock.patch("haytham.workflow.stage_executor.extract_text_from_result")
    def test_custom_agent_happy_path(self, mock_extract, mock_save):
        mock_extract.return_value = "Custom agent output."
        mock_agent = mock.Mock(return_value="raw result")

        config = StageExecutionConfig(
            stage_slug="capability-model",
            custom_agent_factory=mock.Mock(return_value=mock_agent),
            custom_context_builder=lambda state: {"_context_str": "Full context here"},
        )

        state = _make_state(
            capability_model="",
            capability_model_status="pending",
        )

        executor = StageExecutor(config)
        result = executor.execute(state)

        assert result["capability_model"] == "Custom agent output."
        assert result["capability_model_status"] == "completed"

    @mock.patch("haytham.workflow.stage_executor.save_stage_output")
    def test_custom_agent_error_shortcircuit(self, mock_save):
        """Context builder error flag short-circuits execution."""
        config = StageExecutionConfig(
            stage_slug="capability-model",
            custom_agent_factory=mock.Mock(),
            custom_context_builder=lambda state: {"_error": "Missing required data"},
        )

        state = _make_state(
            capability_model="",
            capability_model_status="pending",
        )

        executor = StageExecutor(config)
        result = executor.execute(state)

        assert result["capability_model_status"] == "failed"
        assert "Missing required data" in result["capability_model"]
        # Factory should NOT have been called
        config.custom_agent_factory.assert_not_called()

    @mock.patch("haytham.workflow.stage_executor.save_stage_output")
    def test_custom_agent_exception_handled(self, mock_save):
        """Exceptions in custom agents are caught and returned as errors."""

        def exploding_factory():
            raise RuntimeError("Agent crashed")

        config = StageExecutionConfig(
            stage_slug="capability-model",
            custom_agent_factory=exploding_factory,
            custom_context_builder=lambda state: {"_context_str": "context"},
        )

        state = _make_state(capability_model="", capability_model_status="pending")

        executor = StageExecutor(config)
        result = executor.execute(state)

        assert result["capability_model_status"] == "failed"
        assert "Error" in result["capability_model"]


# =============================================================================
# StageExecutor: Post-Processors
# =============================================================================


class TestPostProcessors:
    """Tests for post-processor invocation."""

    @mock.patch("haytham.workflow.stage_executor.run_agent")
    @mock.patch("haytham.workflow.stage_executor.save_stage_output")
    def test_post_processor_updates_state(self, mock_save, mock_run):
        """Post-processor return dict is merged into state."""
        mock_run.return_value = {"output": "Risk output.", "status": "completed"}

        def extract_risk(output, state):
            return {"risk_level": "HIGH"}

        config = StageExecutionConfig(
            stage_slug="risk-assessment",
            post_processor=extract_risk,
        )

        state = _make_state(
            idea_analysis="Idea",
            market_context="Market",
            risk_assessment="",
            risk_assessment_status="pending",
        )

        executor = StageExecutor(config)
        result = executor.execute(state)

        assert result["risk_level"] == "HIGH"
        assert result["risk_assessment_status"] == "completed"

    @mock.patch("haytham.workflow.stage_executor.run_agent")
    @mock.patch("haytham.workflow.stage_executor.save_stage_output")
    def test_post_processor_not_called_on_failure(self, mock_save, mock_run):
        """Post-processor is still called even on failure (it runs before save check)."""
        mock_run.return_value = {"output": "Error: failed.", "status": "failed"}
        post_proc = mock.Mock(return_value={})

        config = StageExecutionConfig(
            stage_slug="risk-assessment",
            post_processor=post_proc,
        )

        state = _make_state(
            idea_analysis="Idea",
            market_context="Market",
            risk_assessment="",
            risk_assessment_status="pending",
        )

        executor = StageExecutor(config)
        executor.execute(state)

        # Post-processor is called regardless of status
        post_proc.assert_called_once()


# =============================================================================
# StageExecutor: Post-Validators (ADR-022)
# =============================================================================


class TestPostValidators:
    """Tests for post-validator chain."""

    @mock.patch("haytham.workflow.stage_executor.run_agent")
    @mock.patch("haytham.workflow.stage_executor.save_stage_output")
    def test_validators_warnings_stored_in_state(self, mock_save, mock_run):
        """Post-validator warnings are stored in state for gate surfacing."""
        mock_run.return_value = {"output": "Summary output.", "status": "completed"}

        def validator_a(output, state):
            return ["Revenue evidence missing"]

        def validator_b(output, state):
            return []

        config = StageExecutionConfig(
            stage_slug="validation-summary",
            post_validators=[validator_a, validator_b],
        )

        state = _make_state(
            idea_analysis="Idea",
            market_context="Market",
            risk_assessment="Risk",
            validation_summary="",
            validation_summary_status="pending",
        )

        executor = StageExecutor(config)
        result = executor.execute(state)

        warnings = result.get("validation-summary_validation_warnings")
        assert warnings is not None
        assert "Revenue evidence missing" in warnings

    @mock.patch("haytham.workflow.stage_executor.run_agent")
    @mock.patch("haytham.workflow.stage_executor.save_stage_output")
    def test_validator_exceptions_are_caught(self, mock_save, mock_run):
        """Validator exceptions don't crash the stage."""
        mock_run.return_value = {"output": "Output.", "status": "completed"}

        def crashing_validator(output, state):
            raise ValueError("Validator bug")

        config = StageExecutionConfig(
            stage_slug="validation-summary",
            post_validators=[crashing_validator],
        )

        state = _make_state(
            idea_analysis="I",
            market_context="M",
            risk_assessment="R",
            validation_summary="",
            validation_summary_status="pending",
        )

        executor = StageExecutor(config)
        result = executor.execute(state)

        # Stage still completes despite validator crash
        assert result["validation_summary_status"] == "completed"

    @mock.patch("haytham.workflow.stage_executor.run_agent")
    @mock.patch("haytham.workflow.stage_executor.save_stage_output")
    def test_no_validators_no_warnings(self, mock_save, mock_run):
        """When there are no post-validators, no warning keys are added."""
        mock_run.return_value = {"output": "Output.", "status": "completed"}
        config = StageExecutionConfig(stage_slug="idea-analysis")

        state = _make_state(idea_analysis="", idea_analysis_status="pending")

        executor = StageExecutor(config)
        result = executor.execute(state)

        assert result.get("idea-analysis_validation_warnings") is None


# =============================================================================
# StageExecutor: Context Building
# =============================================================================


class TestContextBuilding:
    """Tests for _build_context logic."""

    def test_context_includes_system_goal(self):
        config = StageExecutionConfig(stage_slug="idea-analysis")
        executor = StageExecutor(config)
        state = _make_state()

        context = executor._build_context(state, "My SaaS idea")
        assert context["system_goal"] == "My SaaS idea"

    def test_context_includes_required_context_stages(self):
        """Context includes outputs from required_context stages."""
        config = StageExecutionConfig(stage_slug="risk-assessment")
        executor = StageExecutor(config)

        state = _make_state(
            idea_analysis="Idea output",
            market_context="Market output",
        )

        context = executor._build_context(state, "Goal")

        # risk-assessment requires idea-analysis and market-context
        assert context.get("idea_analysis") == "Idea output"
        assert context.get("market_context") == "Market output"

    def test_context_includes_concept_anchor_for_non_idea_analysis(self):
        """Concept anchor is included for all stages after idea-analysis."""
        config = StageExecutionConfig(stage_slug="risk-assessment")
        executor = StageExecutor(config)

        state = _make_state(
            concept_anchor_str="Core: scheduling. Invariant: must be real-time.",
            idea_analysis="Idea",
            market_context="Market",
        )

        context = executor._build_context(state, "Goal")
        assert "scheduling" in context.get("concept_anchor", "")

    def test_context_excludes_anchor_for_idea_analysis(self):
        """idea-analysis stage does not get concept_anchor (it creates it)."""
        config = StageExecutionConfig(stage_slug="idea-analysis")
        executor = StageExecutor(config)

        state = _make_state(concept_anchor_str="Some anchor")

        context = executor._build_context(state, "Goal")
        assert "concept_anchor" not in context

    def test_context_does_not_inject_pivot_strategy_as_special_case(self):
        """Pivot strategy is only available via required_context, not hardcoded injection.

        The validation-summary stage uses a programmatic_executor that reads
        pivot_strategy directly from State, so _build_context does not need to
        inject it as a special case.
        """
        config = StageExecutionConfig(stage_slug="validation-summary")
        executor = StageExecutor(config)

        state = _make_state(
            idea_analysis="I",
            market_context="M",
            risk_assessment="R",
            pivot_strategy="Pivot to B2B.",
        )

        context = executor._build_context(state, "Goal")
        # pivot_strategy is NOT in validation-summary's required_context,
        # so it should not appear in the context dict
        assert "pivot_strategy" not in context

    def test_custom_context_builder_used(self):
        """Custom context builder overrides default logic."""

        def custom_builder(state):
            return {"custom_key": "custom_value", "concept_anchor": "preserved"}

        config = StageExecutionConfig(
            stage_slug="capability-model",
            custom_context_builder=custom_builder,
        )
        executor = StageExecutor(config)
        state = _make_state()

        context = executor._build_context(state, "Goal")
        assert context["custom_key"] == "custom_value"
        assert "system_goal" not in context  # Custom builder replaces default

    def test_custom_context_builder_injects_anchor(self):
        """Custom context builder gets anchor injected if missing."""

        def custom_builder(state):
            return {"only_this": True}

        config = StageExecutionConfig(
            stage_slug="capability-model",
            custom_context_builder=custom_builder,
        )
        executor = StageExecutor(config)
        state = _make_state(concept_anchor_str="Anchor data")

        context = executor._build_context(state, "Goal")
        assert context.get("concept_anchor") == "Anchor data"


# =============================================================================
# StageExecutor: Output Model Rendering
# =============================================================================


class TestOutputModelRendering:
    """Tests for JSON -> markdown output model rendering."""

    @mock.patch("haytham.workflow.stage_executor.run_agent")
    @mock.patch("haytham.workflow.stage_executor.save_stage_output")
    def test_output_model_renders_markdown_for_disk(self, mock_save, mock_run):
        """When output_model is set, markdown is saved to disk but JSON stays in state."""
        json_output = '{"key": "value"}'
        mock_run.return_value = {"output": json_output, "status": "completed"}

        mock_model_instance = mock.Mock()
        mock_model_instance.to_markdown.return_value = "# Rendered Markdown"
        mock_model_class = mock.Mock()
        mock_model_class.model_validate_json.return_value = mock_model_instance

        config = StageExecutionConfig(
            stage_slug="validation-summary",
            output_model=mock_model_class,
        )

        state = _make_state(
            idea_analysis="I",
            market_context="M",
            risk_assessment="R",
            validation_summary="",
            validation_summary_status="pending",
        )

        executor = StageExecutor(config)
        result = executor.execute(state)

        # JSON stays in Burr state
        assert result["validation_summary"] == json_output
        # Markdown saved to disk
        mock_save.assert_called_once()
        saved_output = mock_save.call_args[1].get("output") or mock_save.call_args[0][3]
        assert "Rendered Markdown" in saved_output

    @mock.patch("haytham.workflow.stage_executor.run_agent")
    @mock.patch("haytham.workflow.stage_executor.save_stage_output")
    def test_output_model_validation_failure_saves_raw(self, mock_save, mock_run):
        """If output_model validation fails, raw output is saved instead."""
        mock_run.return_value = {"output": "not valid json", "status": "completed"}

        mock_model_class = mock.Mock()
        mock_model_class.model_validate_json.side_effect = ValueError("Invalid JSON")

        config = StageExecutionConfig(
            stage_slug="validation-summary",
            output_model=mock_model_class,
        )

        state = _make_state(
            idea_analysis="I",
            market_context="M",
            risk_assessment="R",
            validation_summary="",
            validation_summary_status="pending",
        )

        executor = StageExecutor(config)
        result = executor.execute(state)

        # Raw output saved to disk as fallback
        mock_save.assert_called_once()
        assert result["validation_summary"] == "not valid json"


# =============================================================================
# get_stage_executor and execute_stage
# =============================================================================


class TestGetStageExecutor:
    """Tests for factory function."""

    def test_get_executor_for_valid_slug(self):
        executor = get_stage_executor("idea-analysis")
        assert isinstance(executor, StageExecutor)
        assert executor.config.stage_slug == "idea-analysis"

    def test_get_executor_for_invalid_slug_raises(self):
        with pytest.raises(KeyError, match="No executor config for stage"):
            get_stage_executor("nonexistent-stage")

    def test_all_registry_stages_have_configs(self):
        """Every stage in the registry has a corresponding executor config."""
        registry = get_stage_registry()
        for stage in registry.all_stages(include_optional=True):
            executor = get_stage_executor(stage.slug)
            assert executor.config.stage_slug == stage.slug

    @mock.patch("haytham.workflow.stage_executor.run_agent")
    @mock.patch("haytham.workflow.stage_executor.save_stage_output")
    def test_execute_stage_convenience_function(self, mock_save, mock_run):
        """execute_stage() is a convenience wrapper around get_stage_executor().execute()."""
        mock_run.return_value = {"output": "Output.", "status": "completed"}
        state = _make_state(idea_analysis="", idea_analysis_status="pending")

        result = execute_stage("idea-analysis", state)

        assert result["idea_analysis"] == "Output."
        assert result["idea_analysis_status"] == "completed"
