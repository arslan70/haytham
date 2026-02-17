"""Tests for multi-provider LLM model factory."""

from unittest.mock import MagicMock

import pytest

from haytham.agents.utils.model_provider import (
    _PROVIDER_FACTORIES,
    LLMProvider,
    create_model,
    create_model_for_file_operations,
    get_active_provider,
    get_model_id_for_tier,
)

# ---------------------------------------------------------------------------
# get_active_provider
# ---------------------------------------------------------------------------


class TestGetActiveProvider:
    def test_default_is_bedrock(self, monkeypatch):
        monkeypatch.delenv("LLM_PROVIDER", raising=False)
        assert get_active_provider() is LLMProvider.BEDROCK

    @pytest.mark.parametrize(
        "value,expected",
        [
            ("bedrock", LLMProvider.BEDROCK),
            ("anthropic", LLMProvider.ANTHROPIC),
            ("openai", LLMProvider.OPENAI),
            ("ollama", LLMProvider.OLLAMA),
        ],
    )
    def test_each_provider(self, monkeypatch, value, expected):
        monkeypatch.setenv("LLM_PROVIDER", value)
        assert get_active_provider() is expected

    def test_case_insensitive(self, monkeypatch):
        monkeypatch.setenv("LLM_PROVIDER", "ANTHROPIC")
        assert get_active_provider() is LLMProvider.ANTHROPIC

    def test_invalid_raises(self, monkeypatch):
        monkeypatch.setenv("LLM_PROVIDER", "banana")
        with pytest.raises(ValueError, match="Unknown LLM_PROVIDER 'banana'"):
            get_active_provider()


# ---------------------------------------------------------------------------
# get_model_id_for_tier
# ---------------------------------------------------------------------------


class TestGetModelIdForTier:
    def test_provider_specific_env_var(self, monkeypatch):
        monkeypatch.setenv("LLM_PROVIDER", "anthropic")
        monkeypatch.setenv("ANTHROPIC_HEAVY_MODEL_ID", "my-custom-model")
        assert get_model_id_for_tier("heavy") == "my-custom-model"

    def test_defaults(self, monkeypatch):
        monkeypatch.setenv("LLM_PROVIDER", "openai")
        monkeypatch.delenv("OPENAI_LIGHT_MODEL_ID", raising=False)
        assert get_model_id_for_tier("light") == "gpt-4o-mini"

    def test_reasoning_falls_back_to_heavy(self, monkeypatch):
        monkeypatch.setenv("LLM_PROVIDER", "anthropic")
        monkeypatch.delenv("ANTHROPIC_REASONING_MODEL_ID", raising=False)
        monkeypatch.setenv("ANTHROPIC_HEAVY_MODEL_ID", "heavy-model")
        assert get_model_id_for_tier("reasoning") == "heavy-model"

    def test_bedrock_backward_compat(self, monkeypatch):
        monkeypatch.setenv("LLM_PROVIDER", "bedrock")
        monkeypatch.setenv("BEDROCK_HEAVY_MODEL_ID", "anthropic.claude-v2")
        assert get_model_id_for_tier("heavy") == "anthropic.claude-v2"

    def test_invalid_tier_raises(self, monkeypatch):
        monkeypatch.setenv("LLM_PROVIDER", "anthropic")
        with pytest.raises(ValueError, match="Invalid tier 'mega'"):
            get_model_id_for_tier("mega")

    def test_ollama_defaults(self, monkeypatch):
        monkeypatch.setenv("LLM_PROVIDER", "ollama")
        monkeypatch.delenv("OLLAMA_HEAVY_MODEL_ID", raising=False)
        assert get_model_id_for_tier("heavy") == "llama3.1:70b"


# ---------------------------------------------------------------------------
# create_model
# ---------------------------------------------------------------------------


class TestCreateModel:
    def _patch_factory(self, monkeypatch, provider):
        """Replace the factory in the dispatch dict and return the mock."""
        mock = MagicMock(return_value=MagicMock())
        monkeypatch.setitem(_PROVIDER_FACTORIES, provider, mock)
        return mock

    def test_bedrock_dispatch(self, monkeypatch):
        monkeypatch.setenv("LLM_PROVIDER", "bedrock")
        mock = self._patch_factory(monkeypatch, LLMProvider.BEDROCK)
        create_model(model_id="some-model", max_tokens=1000)
        mock.assert_called_once()
        assert mock.call_args[1]["model_id"] == "some-model"
        assert mock.call_args[1]["max_tokens"] == 1000

    def test_anthropic_dispatch(self, monkeypatch):
        monkeypatch.setenv("LLM_PROVIDER", "anthropic")
        mock = self._patch_factory(monkeypatch, LLMProvider.ANTHROPIC)
        create_model(model_id="claude-sonnet-4-20250514", max_tokens=2000)
        mock.assert_called_once()
        assert mock.call_args[1]["model_id"] == "claude-sonnet-4-20250514"

    def test_openai_dispatch(self, monkeypatch):
        monkeypatch.setenv("LLM_PROVIDER", "openai")
        mock = self._patch_factory(monkeypatch, LLMProvider.OPENAI)
        create_model(model_id="gpt-4o", max_tokens=3000)
        mock.assert_called_once()

    def test_ollama_dispatch(self, monkeypatch):
        monkeypatch.setenv("LLM_PROVIDER", "ollama")
        mock = self._patch_factory(monkeypatch, LLMProvider.OLLAMA)
        create_model(model_id="llama3.1:8b", max_tokens=4000)
        mock.assert_called_once()

    def test_default_tier_resolution(self, monkeypatch):
        """When model_id is None, it resolves from tier + provider."""
        monkeypatch.setenv("LLM_PROVIDER", "bedrock")
        monkeypatch.setenv("BEDROCK_LIGHT_MODEL_ID", "resolved-model")
        mock = self._patch_factory(monkeypatch, LLMProvider.BEDROCK)
        create_model()
        assert mock.call_args[1]["model_id"] == "resolved-model"

    def test_max_tokens_from_env(self, monkeypatch):
        monkeypatch.setenv("LLM_PROVIDER", "bedrock")
        monkeypatch.setenv("BEDROCK_LIGHT_MODEL_ID", "test-model")
        monkeypatch.setenv("DEFAULT_MAX_TOKENS", "8000")
        mock = self._patch_factory(monkeypatch, LLMProvider.BEDROCK)
        create_model(model_id="test-model")
        assert mock.call_args[1]["max_tokens"] == 8000


# ---------------------------------------------------------------------------
# create_model_for_file_operations
# ---------------------------------------------------------------------------


class TestCreateModelForFileOperations:
    def test_defaults(self, monkeypatch):
        monkeypatch.setenv("LLM_PROVIDER", "bedrock")
        monkeypatch.setenv("BEDROCK_LIGHT_MODEL_ID", "test-model")
        mock = MagicMock(return_value=MagicMock())
        monkeypatch.setitem(_PROVIDER_FACTORIES, LLMProvider.BEDROCK, mock)
        create_model_for_file_operations(model_id="test-model")
        kwargs = mock.call_args[1]
        assert kwargs["max_tokens"] == 4096
        assert not kwargs["streaming"]
        assert kwargs["read_timeout"] == 600.0
        assert kwargs["connect_timeout"] == 60.0

    def test_anthropic_ignores_timeouts(self, monkeypatch):
        """Non-bedrock providers silently consume read_timeout/connect_timeout."""
        monkeypatch.setenv("LLM_PROVIDER", "anthropic")
        mock = MagicMock(return_value=MagicMock())
        monkeypatch.setitem(_PROVIDER_FACTORIES, LLMProvider.ANTHROPIC, mock)
        create_model_for_file_operations(model_id="claude-sonnet-4-20250514")
        mock.assert_called_once()
