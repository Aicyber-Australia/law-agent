"""
Embedding Service for RAG

Uses OpenAI's text-embedding-3-small model for generating embeddings.
"""

import asyncio
from typing import List
from openai import AsyncOpenAI
from app.config import logger


class EmbeddingService:
    """Service for generating text embeddings using OpenAI API."""

    MODEL = "text-embedding-3-small"
    DIMENSION = 1536

    def __init__(self):
        self.client = AsyncOpenAI()

    async def embed_text(self, text: str) -> List[float]:
        """
        Generate embedding for a single text.

        Args:
            text: The text to embed

        Returns:
            List of floats representing the embedding vector
        """
        try:
            response = await self.client.embeddings.create(
                model=self.MODEL,
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            raise

    async def embed_batch(
        self,
        texts: List[str],
        batch_size: int = 100
    ) -> List[List[float]]:
        """
        Generate embeddings for multiple texts with batching.

        Args:
            texts: List of texts to embed
            batch_size: Number of texts per API call (max 2048 for OpenAI)

        Returns:
            List of embedding vectors
        """
        all_embeddings = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]

            try:
                response = await self.client.embeddings.create(
                    model=self.MODEL,
                    input=batch
                )
                batch_embeddings = [d.embedding for d in response.data]
                all_embeddings.extend(batch_embeddings)

                # Rate limit protection
                if i + batch_size < len(texts):
                    await asyncio.sleep(0.1)

            except Exception as e:
                logger.error(f"Error generating batch embeddings at index {i}: {e}")
                raise

        return all_embeddings

    def embed_text_sync(self, text: str) -> List[float]:
        """
        Synchronous wrapper for embed_text.

        Args:
            text: The text to embed

        Returns:
            List of floats representing the embedding vector
        """
        return asyncio.run(self.embed_text(text))

    def embed_batch_sync(
        self,
        texts: List[str],
        batch_size: int = 100
    ) -> List[List[float]]:
        """
        Synchronous wrapper for embed_batch.

        Args:
            texts: List of texts to embed
            batch_size: Number of texts per API call

        Returns:
            List of embedding vectors
        """
        return asyncio.run(self.embed_batch(texts, batch_size))


# Singleton instance
_embedding_service = None


def get_embedding_service() -> EmbeddingService:
    """Get or create the singleton EmbeddingService instance."""
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service
