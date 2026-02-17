"""Multi-provider LLM model factory.

Dispatches to the correct Strands SDK model class based on the ``LLM_PROVIDER``
environment variable (default: ``bedrock``).  Bedrock behaviour is unchanged —
existing users see zero difference.  Other providers (Anthropic, OpenAI, Ollama)
are optional extras that import lazily so the core install stays lean.

Resolution order for model IDs:
  1. Explicit ``model_id`` argument
  2. ``{PROVIDER}_{TIER}_MODEL_ID`` env var  (e.g. ``ANTHROPIC_HEAVY_MODEL_ID``)
  3. For bedrock: existing ``BEDROCK_*`` env vars via ``bedrock_config``
  4. Reasoning → heavy fallback
  5. ``PROVIDER_DEFAULTS`` smart defaults
"""

import logging
import os
from collections.abc import Callable
from enum import Enum
from typing import Any

from haytham.agents.utils._bedrock_config import (
    create_bedrock_model,
    get_default_max_tokens,
)
from haytham.agents.utils._bedrock_config import (
    get_model_id_for_tier as bedrock_get_model_id,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Provider enum
# ---------------------------------------------------------------------------


class LLMProvider(Enum):
    """Supported LLM providers."""

    BEDROCK = "bedrock"
    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    OLLAMA = "ollama"


# ---------------------------------------------------------------------------
# Smart defaults per provider × tier
# ---------------------------------------------------------------------------

PROVIDER_DEFAULTS: dict[LLMProvider, dict[str, str]] = {
    LLMProvider.BEDROCK: {
        "reasoning": "anthropic.claude-3-5-sonnet-20241022-v2:0",
        "heavy": "anthropic.claude-3-5-sonnet-20241022-v2:0",
        "light": "anthropic.claude-3-5-sonnet-20241022-v2:0",
    },
    LLMProvider.ANTHROPIC: {
        "reasoning": "claude-sonnet-4-20250514",
        "heavy": "claude-sonnet-4-20250514",
        "light": "claude-3-5-haiku-20241022",
    },
    LLMProvider.OPENAI: {
        "reasoning": "o3-mini",
        "heavy": "gpt-4o",
        "light": "gpt-4o-mini",
    },
    LLMProvider.OLLAMA: {
        "reasoning": "llama3.1:70b",
        "heavy": "llama3.1:70b",
        "light": "llama3.1:8b",
    },
}


# ---------------------------------------------------------------------------
# Provider detection
# ---------------------------------------------------------------------------


def get_active_provider() -> LLMProvider:
    """Return the active LLM provider from the ``LLM_PROVIDER`` env var.

    Defaults to ``bedrock`` when the variable is unset.

    Raises:
        ValueError: If the env var value is not a recognised provider.
    """
    raw = os.getenv("LLM_PROVIDER", "bedrock").strip().lower()
    try:
        return LLMProvider(raw)
    except ValueError:
        valid = ", ".join(p.value for p in LLMProvider)
        raise ValueError(f"Unknown LLM_PROVIDER '{raw}'. Valid options: {valid}") from None


# ---------------------------------------------------------------------------
# Model-ID resolution
# ---------------------------------------------------------------------------

_VALID_TIERS = {"reasoning", "heavy", "light"}


def get_model_id_for_tier(tier: str) -> str:
    """Return the model ID for a tier, respecting the active provider.

    Resolution order:
      1. ``{PROVIDER}_{TIER}_MODEL_ID`` env var
      2. For bedrock only: delegate to ``bedrock_config.get_model_id_for_tier``
      3. Reasoning → heavy fallback
      4. ``PROVIDER_DEFAULTS``

    Args:
        tier: One of ``"reasoning"``, ``"heavy"``, ``"light"``.

    Returns:
        Model ID string.

    Raises:
        ValueError: If the tier is invalid or no model ID can be resolved.
    """
    if tier not in _VALID_TIERS:
        raise ValueError(
            f"Invalid tier '{tier}'. Must be one of: {', '.join(sorted(_VALID_TIERS))}"
        )

    provider = get_active_provider()

    # 1. Provider-specific env var  (e.g. ANTHROPIC_HEAVY_MODEL_ID)
    env_key = f"{provider.value.upper()}_{tier.upper()}_MODEL_ID"
    from_env = os.getenv(env_key)
    if from_env:
        return from_env

    # 2. Bedrock backward compat — delegate to existing bedrock_config
    if provider is LLMProvider.BEDROCK:
        try:
            return bedrock_get_model_id(tier)
        except ValueError:
            pass  # fall through to defaults

    # 3. Reasoning → heavy fallback
    if tier == "reasoning":
        heavy_env_key = f"{provider.value.upper()}_HEAVY_MODEL_ID"
        heavy_from_env = os.getenv(heavy_env_key)
        if heavy_from_env:
            logger.warning("%s not set, falling back to %s", env_key, heavy_env_key)
            return heavy_from_env

    # 4. Smart defaults
    defaults = PROVIDER_DEFAULTS.get(provider, {})
    default_id = defaults.get(tier)
    if default_id:
        logger.info("Using default model for %s/%s: %s", provider.value, tier, default_id)
        return default_id

    raise ValueError(
        f"No model ID found for provider '{provider.value}', tier '{tier}'. "
        f"Set {env_key} in your environment."
    )


# ---------------------------------------------------------------------------
# Provider factory registry
# ---------------------------------------------------------------------------

_PROVIDER_FACTORIES: dict[LLMProvider, Callable[..., Any]] = {}


def _register_provider(provider: LLMProvider):
    """Decorator to register a provider factory function."""

    def decorator(fn):
        _PROVIDER_FACTORIES[provider] = fn
        return fn

    return decorator


_BEDROCK_ONLY_KWARGS = ("read_timeout", "connect_timeout", "region_name")


def _strip_bedrock_kwargs(kwargs: dict) -> None:
    """Remove Bedrock-specific kwargs that other providers don't accept."""
    for key in _BEDROCK_ONLY_KWARGS:
        kwargs.pop(key, None)


@_register_provider(LLMProvider.BEDROCK)
def _create_bedrock(model_id, max_tokens, streaming, temperature, **kwargs):
    return create_bedrock_model(
        model_id=model_id,
        max_tokens=max_tokens,
        streaming=streaming,
        temperature=temperature,
        **kwargs,
    )


@_register_provider(LLMProvider.ANTHROPIC)
def _create_anthropic(model_id, max_tokens, streaming, temperature, **kwargs):
    _strip_bedrock_kwargs(kwargs)
    if streaming:
        logger.warning("streaming=True ignored for Anthropic provider")

    try:
        from strands.models.anthropic import AnthropicModel
    except ImportError as e:
        raise ImportError(
            "Anthropic provider requires the 'anthropic' package. "
            "Install it with: pip install 'haytham[anthropic]'"
        ) from e

    client_args = {}
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if api_key:
        client_args["api_key"] = api_key

    params = {}
    if temperature is not None:
        params["temperature"] = temperature

    return AnthropicModel(
        client_args=client_args or None,
        model_id=model_id,
        max_tokens=max_tokens,
        params=params or None,
    )


@_register_provider(LLMProvider.OPENAI)
def _create_openai(model_id, max_tokens, streaming, temperature, **kwargs):
    _strip_bedrock_kwargs(kwargs)
    if streaming:
        logger.warning("streaming=True ignored for OpenAI provider")

    try:
        from strands.models.openai import OpenAIModel
    except ImportError as e:
        raise ImportError(
            "OpenAI provider requires the 'openai' package. "
            "Install it with: pip install 'haytham[openai]'"
        ) from e

    client_args = {}
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        client_args["api_key"] = api_key

    params = {}
    if max_tokens is not None:
        params["max_tokens"] = max_tokens
    if temperature is not None:
        params["temperature"] = temperature

    return OpenAIModel(
        client_args=client_args or None,
        model_id=model_id,
        params=params or None,
    )


@_register_provider(LLMProvider.OLLAMA)
def _create_ollama(model_id, max_tokens, streaming, temperature, **kwargs):
    _strip_bedrock_kwargs(kwargs)
    if streaming:
        logger.warning("streaming=True ignored for Ollama provider")

    try:
        from strands.models.ollama import OllamaModel
    except ImportError as e:
        raise ImportError(
            "Ollama provider requires the 'ollama' package. "
            "Install it with: pip install 'haytham[ollama]'"
        ) from e

    host = os.getenv("OLLAMA_HOST", "http://localhost:11434")

    ollama_kwargs = {
        "host": host,
        "model_id": model_id,
    }
    if max_tokens is not None:
        ollama_kwargs["max_tokens"] = max_tokens
    if temperature is not None:
        ollama_kwargs["temperature"] = temperature

    return OllamaModel(**ollama_kwargs)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def create_model(
    model_id: str | None = None,
    tier: str = "light",
    max_tokens: int | None = None,
    streaming: bool = True,
    temperature: float = 0.7,
    **kwargs,
):
    """Create a model instance for the active provider.

    This is the universal replacement for ``create_bedrock_model()``.
    Provider-specific parameters (``read_timeout``, ``connect_timeout``,
    ``region_name``) are forwarded to Bedrock and silently ignored by
    other providers.

    Args:
        model_id: Model identifier. Resolved from tier + provider defaults
            when ``None``.
        tier: Model tier for ID resolution (``"reasoning"``/``"heavy"``/``"light"``).
        max_tokens: Maximum response tokens. Falls back to ``DEFAULT_MAX_TOKENS``
            env var, then ``5000``.
        streaming: Enable streaming (default ``True``).
        temperature: Sampling temperature (default ``0.7``).
        **kwargs: Provider-specific extras (e.g. ``read_timeout`` for Bedrock).

    Returns:
        A Strands ``Model`` instance.
    """
    provider = get_active_provider()

    if model_id is None:
        model_id = get_model_id_for_tier(tier)

    if max_tokens is None:
        max_tokens = get_default_max_tokens()

    factory = _PROVIDER_FACTORIES[provider]

    logger.info(
        "Creating %s model: model_id=%s, tier=%s, max_tokens=%s",
        provider.value,
        model_id,
        tier,
        max_tokens,
    )

    return factory(
        model_id=model_id,
        max_tokens=max_tokens,
        streaming=streaming,
        temperature=temperature,
        **kwargs,
    )


def create_model_for_file_operations(
    model_id: str | None = None,
    tier: str = "light",
    **kwargs,
):
    """Create a model optimized for file-reading operations.

    Uses a 10-minute read timeout (Bedrock only), disables streaming, and
    defaults to 4096 max tokens — mirroring the old
    ``create_bedrock_model_for_file_operations()`` behaviour.

    Args:
        model_id: Model identifier (resolved from tier when ``None``).
        tier: Model tier for ID resolution.
        **kwargs: Forwarded to ``create_model``.

    Returns:
        A Strands ``Model`` instance.
    """
    kwargs.setdefault("max_tokens", 4096)
    return create_model(
        model_id=model_id,
        tier=tier,
        read_timeout=600.0,
        connect_timeout=60.0,
        streaming=False,
        **kwargs,
    )
