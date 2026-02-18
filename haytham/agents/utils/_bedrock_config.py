"""
Bedrock model configuration utilities.

This module provides utilities for creating BedrockModel instances with
optimized timeout configurations for handling large context processing
and file reading operations.

AWS Credentials:
    This module uses boto3's standard credential chain. To specify which
    AWS profile to use, set the AWS_PROFILE environment variable:

    AWS_PROFILE=my-profile  # Uses [my-profile] from ~/.aws/credentials

    If AWS_PROFILE is not set, boto3 will use the [default] profile.
"""

import logging
import os

from botocore.config import Config
from strands.models.bedrock import BedrockModel
from strands.models.model import CacheConfig

logger = logging.getLogger(__name__)


def get_default_max_tokens() -> int:
    """Resolve max_tokens from DEFAULT_MAX_TOKENS env var (default: 5000).

    Nova models support up to 10,000 output tokens; the 5000 default
    provides headroom for complex responses.
    """
    return int(os.getenv("DEFAULT_MAX_TOKENS", "5000"))


def _log_aws_profile_info() -> None:
    """Log information about which AWS profile is being used."""
    profile = os.getenv("AWS_PROFILE")
    if profile:
        logger.info(f"Using AWS profile: {profile}")
    else:
        logger.info("Using default AWS profile (AWS_PROFILE not set)")


def get_model_id_for_tier(tier: str) -> str:
    """Get the Bedrock model ID for a given tier.

    Args:
        tier: Model tier ("heavy" or "light").

    Returns:
        Bedrock model ID string.

    Raises:
        ValueError: If no model ID can be resolved.
    """
    env_key = {
        "heavy": "BEDROCK_HEAVY_MODEL_ID",
        "light": "BEDROCK_LIGHT_MODEL_ID",
        "reasoning": "BEDROCK_REASONING_MODEL_ID",
    }.get(tier)
    if env_key:
        model_id = os.getenv(env_key)
        if model_id:
            return model_id

    # Fallback: REASONING → HEAVY
    if tier == "reasoning":
        fallback = os.getenv("BEDROCK_HEAVY_MODEL_ID")
        if fallback:
            logger.warning(
                "BEDROCK_REASONING_MODEL_ID not set, falling back to BEDROCK_HEAVY_MODEL_ID"
            )
            return fallback

    raise ValueError(
        f"No model ID found for tier '{tier}'. Set BEDROCK_HEAVY_MODEL_ID, "
        "BEDROCK_LIGHT_MODEL_ID, and/or BEDROCK_REASONING_MODEL_ID in your .env file."
    )


def create_bedrock_model(
    model_id: str | None = None,
    region_name: str | None = None,
    read_timeout: float = 300.0,
    connect_timeout: float = 60.0,
    streaming: bool = True,
    temperature: float = 0.7,
    max_tokens: int | None = None,
    **kwargs,
) -> BedrockModel:
    """
    Create a BedrockModel with extended timeout configuration.

    This function creates a BedrockModel with boto3 client configuration
    that includes extended timeouts to handle large context processing,
    file reading operations, and long-running agent executions.

    The default read_timeout is increased from boto3's default of 60 seconds
    to 300 seconds (5 minutes) to accommodate:
    - Large codebase analysis
    - Multiple file reads
    - Complex reasoning tasks
    - Long streaming responses

    Args:
        model_id: Bedrock model ID. Defaults to BEDROCK_LIGHT_MODEL_ID env var
                 (via get_model_id_for_tier("light")).
        region_name: AWS region. Defaults to AWS_REGION env var.
        read_timeout: Read timeout in seconds (default: 300s / 5 minutes).
                     This is the time to wait for data from the server.
        connect_timeout: Connection timeout in seconds (default: 60s).
                        This is the time to wait to establish a connection.
        streaming: Enable streaming responses (default: True).
        temperature: Model temperature for response generation (default: 0.7).
        max_tokens: Maximum tokens for response. Defaults to DEFAULT_MAX_TOKENS
                   env var, or 5000 if not set. Amazon Nova models support up to
                   10,000 output tokens; default of 5000 provides headroom for
                   complex agents while staying well under the limit.
        **kwargs: Additional arguments passed to BedrockModel.

    Returns:
        BedrockModel instance with extended timeout configuration

    Raises:
        ValueError: If model_id or region_name cannot be determined

    Example:
        >>> model = create_bedrock_model(read_timeout=600.0)  # 10 minute timeout
        >>> agent = Agent(model=model, system_prompt="...")
    """
    # Get model_id from environment if not provided
    if model_id is None:
        model_id = get_model_id_for_tier("light")

    # Get region from environment if not provided
    if region_name is None:
        region_name = os.getenv("AWS_REGION")
        if not region_name:
            raise ValueError(
                "region_name not provided and AWS_REGION environment "
                "variable is not set. Please configure it in your .env file."
            )

    if max_tokens is None:
        max_tokens = get_default_max_tokens()

    # Create boto3 client configuration with extended timeouts and retry logic
    # Using 'standard' mode with exponential backoff for transient errors
    # This will automatically retry on Bedrock internal server errors
    boto_config = Config(
        read_timeout=read_timeout,
        connect_timeout=connect_timeout,
        retries={
            "max_attempts": 3,  # Transport-level retry for network/HTTP errors only
            "mode": "standard",  # Standard mode with exponential backoff
        },
    )

    logger.info(
        f"Creating BedrockModel with extended timeouts: "
        f"read_timeout={read_timeout}s, connect_timeout={connect_timeout}s, "
        f"model={model_id}, region={region_name}, max_tokens={max_tokens}"
    )

    # Log AWS profile information
    _log_aws_profile_info()

    # Create BedrockModel with boto client configuration
    # cache_config with strategy="auto" injects cachePoint at optimal
    # positions (system prompt, last assistant turn), reducing latency and
    # cost for repeated invocations.
    model = BedrockModel(
        model_id=model_id,
        region_name=region_name,
        boto_client_config=boto_config,
        streaming=streaming,
        temperature=temperature,
        max_tokens=max_tokens,
        cache_config=CacheConfig(strategy="auto"),
        **kwargs,
    )

    return model


def get_default_timeout_config() -> dict:
    """
    Get default timeout configuration from environment variables.

    Allows customization of timeouts via environment variables:
    - BEDROCK_READ_TIMEOUT: Read timeout in seconds (default: 300)
    - BEDROCK_CONNECT_TIMEOUT: Connect timeout in seconds (default: 60)

    Returns:
        Dictionary with timeout configuration

    Example:
        >>> config = get_default_timeout_config()
        >>> model = create_bedrock_model(**config)
    """
    return {
        "read_timeout": float(os.getenv("BEDROCK_READ_TIMEOUT", "300.0")),
        "connect_timeout": float(os.getenv("BEDROCK_CONNECT_TIMEOUT", "60.0")),
    }


def create_bedrock_model_for_file_operations(
    model_id: str | None = None, region_name: str | None = None, **kwargs
) -> BedrockModel:
    """
    Create a BedrockModel optimized for file reading operations.

    This is a convenience function that creates a BedrockModel with
    extended timeouts specifically tuned for agents that read files
    from codebases (e.g., code_analyzer_agent, growth_planning_agent).

    Uses a 10-minute read timeout and DISABLES streaming to handle:
    - Reading multiple large files
    - Processing large codebases
    - Complex file analysis tasks
    - Transient Bedrock errors (boto3 retry works better without streaming)

    Args:
        model_id: Bedrock model ID. Defaults to BEDROCK_LIGHT_MODEL_ID env var.
        region_name: AWS region. Defaults to AWS_REGION env var.
        **kwargs: Additional arguments passed to create_bedrock_model.

    Returns:
        BedrockModel instance optimized for file operations

    Example:
        >>> model = create_bedrock_model_for_file_operations()
        >>> agent = Agent(
        ...     model=model,
        ...     system_prompt="...",
        ...     tools=[file_read, file_write]
        ... )
    """
    # Use 10-minute read timeout for file operations
    # Disable streaming to enable boto3 retry logic for transient errors
    # Default to 4096 tokens for file operation agents (medium complexity)
    if "max_tokens" not in kwargs:
        kwargs["max_tokens"] = 4096
    return create_bedrock_model(
        model_id=model_id,
        region_name=region_name,
        read_timeout=600.0,  # 10 minutes
        connect_timeout=60.0,
        streaming=False,  # Disable streaming to enable boto3 retries
        **kwargs,
    )
