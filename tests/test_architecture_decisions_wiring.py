"""Tests for architecture decisions structured output wiring."""

import json
from unittest import mock

from haytham.agents.worker_architecture_decisions.architecture_decisions_models import (
    ArchitectureDecisionsOutput,
)

_SAMPLE_OUTPUT = ArchitectureDecisionsOutput(
    decisions=[
        {
            "id": "DEC-AUTH-001",
            "name": "Auth Strategy",
            "description": "Use Supabase Auth",
            "rationale": "Managed auth",
            "serves_capabilities": ["CAP-F-001"],
            "implements_recommendation": "Supabase",
            "alternatives_considered": [],
        }
    ],
    coverage_check={
        "functional_capabilities_covered": ["CAP-F-001"],
        "non_functional_capabilities_covered": [],
        "uncovered_capabilities": [],
    },
    summary="Supabase-first approach",
)


class TestArchitectureDecisionsConfig:
    def test_agent_config_has_structured_output(self):
        from haytham.config import AGENT_CONFIGS

        config = AGENT_CONFIGS["architecture_decisions"]
        assert config.structured_output_model_path is not None
        assert "ArchitectureDecisionsOutput" in config.structured_output_model_path

    def test_stage_config_has_output_model(self):
        from haytham.workflow.stages.configs import STAGE_CONFIGS

        config = STAGE_CONFIGS["architecture-decisions"]
        assert config.output_model is not None


class TestExtractJsonDeleted:
    def test_extract_json_from_response_removed(self):
        from haytham.workflow.stages import technical_design

        assert not hasattr(technical_design, "_extract_json_from_response")


class TestRunArchitectureDecisions:
    @mock.patch("haytham.workflow.stages.technical_design.create_agent_by_name")
    def test_returns_json_not_markdown(self, mock_create):
        from burr.core import State

        from haytham.workflow.stages.technical_design import run_architecture_decisions

        mock_agent = mock.MagicMock()
        mock_result = mock.MagicMock()
        mock_result.structured_output = _SAMPLE_OUTPUT
        # Make the result behave like an AgentResult with structured output
        mock_result.message = {"role": "assistant", "content": []}
        mock_agent.return_value = mock_result
        mock_create.return_value = mock_agent

        state = State(
            {
                "system_goal": "A gym leaderboard",
                "mvp_scope": "## IN SCOPE\n- Leaderboard",
                "capability_model": json.dumps({"capabilities": {"functional": []}}),
                "build_buy_analysis": json.dumps({"recommended_stack": []}),
            }
        )

        output, status = run_architecture_decisions(state)
        assert status == "completed"
        # Output should be JSON (structured output model_dump_json)
        parsed = json.loads(output)
        assert "decisions" in parsed
