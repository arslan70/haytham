"""Tests for startup config validation (WARN-05)."""

from unittest.mock import patch

import pytest

from haytham.config import validate_config


def test_validate_config_missing_heavy_model():
    """Missing BEDROCK_HEAVY_MODEL_ID should raise."""
    with patch.dict("os.environ", {}, clear=True):
        with pytest.raises(OSError, match="BEDROCK_HEAVY_MODEL_ID"):
            validate_config()


def test_validate_config_all_present():
    """All required vars present should not raise."""
    env = {
        "BEDROCK_HEAVY_MODEL_ID": "anthropic.claude-3-5-sonnet",
        "BEDROCK_LIGHT_MODEL_ID": "anthropic.claude-3-haiku",
        "BEDROCK_REASONING_MODEL_ID": "anthropic.claude-3-5-sonnet",
    }
    with patch.dict("os.environ", env, clear=True):
        validate_config()  # Should not raise


def test_validate_config_partial_missing():
    """Partially set env vars should report the missing ones."""
    env = {
        "BEDROCK_HEAVY_MODEL_ID": "some-model",
    }
    with patch.dict("os.environ", env, clear=True):
        with pytest.raises(OSError, match="BEDROCK_LIGHT_MODEL_ID"):
            validate_config()
