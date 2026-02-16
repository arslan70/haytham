"""Embedding Service for System State.

Uses Amazon Titan Embeddings via AWS Bedrock to generate
vector embeddings for semantic search.
"""

import json
import logging
import os
from functools import lru_cache

import boto3
from botocore.config import Config

logger = logging.getLogger(__name__)


class TitanEmbedder:
    """Generate embeddings using Amazon Titan via AWS Bedrock.

    Uses amazon.titan-embed-text-v2:0 which produces 1024-dimension embeddings
    and supports up to 8,192 tokens per input.
    """

    MODEL_ID = "amazon.titan-embed-text-v2:0"
    EMBEDDING_DIMENSION = 1024
    MAX_TOKENS = 8192

    def __init__(
        self,
        region: str | None = None,
        profile: str | None = None,
    ):
        """Initialize the Titan embedder.

        Args:
            region: AWS region for Bedrock. Defaults to AWS_REGION env var.
            profile: AWS profile to use. Defaults to AWS_PROFILE env var.
        """
        self.region = region or os.environ.get("AWS_REGION", "us-east-1")
        self.profile = profile or os.environ.get("AWS_PROFILE")

        # Configure boto3 client with retries
        config = Config(
            retries={"max_attempts": 3, "mode": "adaptive"},
            read_timeout=30,
            connect_timeout=10,
        )

        session_kwargs = {}
        if self.profile:
            session_kwargs["profile_name"] = self.profile

        session = boto3.Session(**session_kwargs)
        self.client = session.client(
            "bedrock-runtime",
            region_name=self.region,
            config=config,
        )

        logger.info(f"TitanEmbedder initialized with region={self.region}")

    def embed(self, text: str) -> list[float]:
        """Generate embedding for a single text.

        Args:
            text: Text to embed (max 8,192 tokens)

        Returns:
            1024-dimension embedding vector
        """
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")

        # Truncate if needed (rough estimate: 4 chars per token)
        max_chars = self.MAX_TOKENS * 4
        if len(text) > max_chars:
            logger.warning(f"Text truncated from {len(text)} to {max_chars} chars for embedding")
            text = text[:max_chars]

        try:
            response = self.client.invoke_model(
                modelId=self.MODEL_ID,
                body=json.dumps({"inputText": text}),
                contentType="application/json",
                accept="application/json",
            )

            result = json.loads(response["body"].read())
            embedding = result["embedding"]

            logger.debug(f"Generated embedding with {len(embedding)} dimensions")
            return embedding

        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            raise

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts.

        Note: Titan doesn't support batch embedding API, so this
        calls embed() sequentially. For high-volume use cases,
        consider parallelization.

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors
        """
        embeddings = []
        for i, text in enumerate(texts):
            try:
                embedding = self.embed(text)
                embeddings.append(embedding)
            except Exception as e:
                logger.error(f"Failed to embed text {i}: {e}")
                raise

        return embeddings

    @property
    def dimension(self) -> int:
        """Return the embedding dimension."""
        return self.EMBEDDING_DIMENSION


@lru_cache(maxsize=1)
def get_embedder() -> TitanEmbedder:
    """Get a cached TitanEmbedder instance.

    Returns a singleton embedder to reuse the Bedrock client connection.
    """
    return TitanEmbedder()
