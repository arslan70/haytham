"""
Tests for Bedrock timeout configuration utilities.

This module tests the bedrock_config utilities that provide extended
timeout configurations for handling large codebase analysis and file
reading operations.
"""

import os

import pytest

from haytham.agents.utils._bedrock_config import (
    create_bedrock_model,
    create_bedrock_model_for_file_operations,
    get_default_timeout_config,
    get_model_id_for_tier,
)


class TestBedrockTimeoutConfig:
    """Test suite for Bedrock timeout configuration."""

    def setup_method(self):
        """Set up test environment variables."""
        os.environ["BEDROCK_LIGHT_MODEL_ID"] = "global.anthropic.claude-sonnet-4-5-20250929-v1:0"
        os.environ["BEDROCK_HEAVY_MODEL_ID"] = "global.anthropic.claude-sonnet-4-5-20250929-v1:0"
        os.environ["AWS_REGION"] = "us-east-1"

    def test_create_bedrock_model_with_default_timeout(self):
        """Test creating BedrockModel with default timeout."""
        model = create_bedrock_model()

        assert model is not None
        # Model is created successfully - timeout is in boto_client_config

    def test_create_bedrock_model_with_custom_timeout(self):
        """Test creating BedrockModel with custom timeout."""
        model = create_bedrock_model(read_timeout=600.0, connect_timeout=120.0)

        assert model is not None
        # Timeout is configured in boto_client_config, not directly accessible
        # but we can verify the model was created successfully

    def test_create_bedrock_model_for_file_operations(self):
        """Test creating BedrockModel optimized for file operations."""
        model = create_bedrock_model_for_file_operations()

        assert model is not None
        # Model is created with 600s read timeout

    def test_create_bedrock_model_with_explicit_model_id(self):
        """Test creating BedrockModel with explicit model_id."""
        custom_model_id = "anthropic.claude-3-sonnet-20240229-v1:0"
        model = create_bedrock_model(model_id=custom_model_id)

        assert model is not None
        # Model is created with custom model_id

    def test_create_bedrock_model_with_explicit_region(self):
        """Test creating BedrockModel with explicit region."""
        model = create_bedrock_model(region_name="eu-west-1")

        assert model is not None
        # Region is configured in boto client, not directly accessible

    def test_create_bedrock_model_missing_env_vars(self):
        """Test that ValueError is raised when env vars are missing."""
        # Remove environment variables
        for key in (
            "BEDROCK_LIGHT_MODEL_ID",
            "BEDROCK_HEAVY_MODEL_ID",
            "BEDROCK_MODEL_ID",
            "AWS_REGION",
        ):
            os.environ.pop(key, None)

        with pytest.raises(ValueError, match="No model ID found for tier"):
            create_bedrock_model()

        # Restore for other tests
        self.setup_method()

    def test_get_default_timeout_config(self):
        """Test getting default timeout configuration."""
        config = get_default_timeout_config()

        assert "read_timeout" in config
        assert "connect_timeout" in config
        assert config["read_timeout"] == 300.0
        assert config["connect_timeout"] == 60.0

    def test_get_default_timeout_config_with_env_vars(self):
        """Test getting timeout configuration from environment variables."""
        os.environ["BEDROCK_READ_TIMEOUT"] = "900.0"
        os.environ["BEDROCK_CONNECT_TIMEOUT"] = "120.0"

        config = get_default_timeout_config()

        assert config["read_timeout"] == 900.0
        assert config["connect_timeout"] == 120.0

        # Clean up
        del os.environ["BEDROCK_READ_TIMEOUT"]
        del os.environ["BEDROCK_CONNECT_TIMEOUT"]

    def test_create_bedrock_model_with_streaming(self):
        """Test creating BedrockModel with streaming enabled."""
        model = create_bedrock_model(streaming=True)

        assert model is not None
        # Streaming is configured in model config

    def test_create_bedrock_model_with_temperature(self):
        """Test creating BedrockModel with custom temperature."""
        model = create_bedrock_model(temperature=0.5)

        assert model is not None
        # Temperature is configured in model config


class TestModelTierRouting:
    """Test suite for three-tier model routing via get_model_id_for_tier()."""

    def setup_method(self):
        """Clean tier-related env vars before each test."""
        for key in (
            "BEDROCK_HEAVY_MODEL_ID",
            "BEDROCK_LIGHT_MODEL_ID",
            "BEDROCK_REASONING_MODEL_ID",
        ):
            os.environ.pop(key, None)

    def test_heavy_tier_uses_dedicated_env_var(self):
        """HEAVY tier reads BEDROCK_HEAVY_MODEL_ID when set."""
        os.environ["BEDROCK_HEAVY_MODEL_ID"] = "heavy-model"

        assert get_model_id_for_tier("heavy") == "heavy-model"

    def test_light_tier_uses_dedicated_env_var(self):
        """LIGHT tier reads BEDROCK_LIGHT_MODEL_ID when set."""
        os.environ["BEDROCK_LIGHT_MODEL_ID"] = "light-model"

        assert get_model_id_for_tier("light") == "light-model"

    def test_reasoning_tier_uses_dedicated_env_var(self):
        """REASONING tier reads BEDROCK_REASONING_MODEL_ID when set."""
        os.environ["BEDROCK_REASONING_MODEL_ID"] = "reasoning-model"

        assert get_model_id_for_tier("reasoning") == "reasoning-model"

    def test_heavy_tier_missing_raises_error(self):
        """HEAVY tier raises ValueError when BEDROCK_HEAVY_MODEL_ID is not set."""
        with pytest.raises(ValueError, match="No model ID found for tier"):
            get_model_id_for_tier("heavy")

    def test_light_tier_missing_raises_error(self):
        """LIGHT tier raises ValueError when BEDROCK_LIGHT_MODEL_ID is not set."""
        with pytest.raises(ValueError, match="No model ID found for tier"):
            get_model_id_for_tier("light")

    def test_reasoning_tier_falls_back_to_heavy(self):
        """REASONING tier falls back to BEDROCK_HEAVY_MODEL_ID when REASONING is not set."""
        os.environ["BEDROCK_HEAVY_MODEL_ID"] = "heavy-model"

        assert get_model_id_for_tier("reasoning") == "heavy-model"

    def test_reasoning_tier_both_missing_raises_error(self):
        """REASONING tier raises ValueError when neither REASONING nor HEAVY is set."""
        with pytest.raises(ValueError, match="No model ID found for tier"):
            get_model_id_for_tier("reasoning")

    def test_reasoning_tier_prefers_dedicated_over_fallback(self):
        """REASONING tier uses dedicated var when both REASONING and HEAVY are set."""
        os.environ["BEDROCK_REASONING_MODEL_ID"] = "reasoning-model"
        os.environ["BEDROCK_HEAVY_MODEL_ID"] = "heavy-model"

        assert get_model_id_for_tier("reasoning") == "reasoning-model"

    def test_unknown_tier_raises_error(self):
        """Unknown tier string raises ValueError."""
        with pytest.raises(ValueError, match="No model ID found for tier"):
            get_model_id_for_tier("unknown")

    def test_no_env_vars_raises_value_error(self):
        """Raises ValueError when no env vars are set at all."""
        with pytest.raises(ValueError, match="No model ID found for tier"):
            get_model_id_for_tier("heavy")

    def test_tier_specific_set_but_empty_raises_error(self):
        """Empty tier-specific var raises ValueError."""
        os.environ["BEDROCK_HEAVY_MODEL_ID"] = ""

        with pytest.raises(ValueError, match="No model ID found for tier"):
            get_model_id_for_tier("heavy")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
