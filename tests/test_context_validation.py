"""Tests for required context validation before stage execution (WARN-01)."""

from unittest.mock import MagicMock

import pytest

from haytham.workflow.stage_executor import StageExecutor


def test_build_context_raises_on_empty_required_context():
    """If a required_context stage has empty output, raise before LLM call."""
    executor = StageExecutor.__new__(StageExecutor)
    executor.config = MagicMock()
    executor.config.custom_context_builder = None
    executor.registry = MagicMock()

    executor.stage = MagicMock()
    executor.stage.slug = "report_synthesis"
    executor.stage.required_context = ["market_context"]

    mock_meta = MagicMock()
    mock_meta.state_key = "market_context_output"
    executor.registry.get_by_slug_safe.return_value = mock_meta

    state = MagicMock()
    state.get.side_effect = lambda key, default="": {
        "concept_anchor_str": "",
        "market_context_output": "",
    }.get(key, default)

    with pytest.raises(ValueError, match="required context.*empty"):
        executor._build_context(state, "test goal")


def test_build_context_succeeds_with_valid_context():
    """Non-empty required context should work fine."""
    executor = StageExecutor.__new__(StageExecutor)
    executor.config = MagicMock()
    executor.config.custom_context_builder = None
    executor.registry = MagicMock()

    executor.stage = MagicMock()
    executor.stage.slug = "report_synthesis"
    executor.stage.required_context = ["market_context"]

    mock_meta = MagicMock()
    mock_meta.state_key = "market_context_output"
    executor.registry.get_by_slug_safe.return_value = mock_meta

    state = MagicMock()
    state.get.side_effect = lambda key, default="": {
        "concept_anchor_str": "",
        "market_context_output": "Some valid market context data",
    }.get(key, default)

    result = executor._build_context(state, "test goal")
    assert result["market_context_output"] == "Some valid market context data"
