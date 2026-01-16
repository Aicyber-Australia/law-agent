"""
Reranker Service for RAG

Uses Cohere's rerank API to improve retrieval precision.
Falls back gracefully if Cohere is not configured.
"""

import asyncio
from typing import List, Dict, Optional
from app.config import logger

# Try to import cohere, but make it optional
try:
    import cohere
    COHERE_AVAILABLE = True
except ImportError:
    COHERE_AVAILABLE = False
    logger.warning("Cohere not installed. Reranking will be disabled.")

import os

COHERE_API_KEY = os.environ.get("COHERE_API_KEY")


class CohereReranker:
    """
    Reranker using Cohere's rerank API.

    Falls back to returning original results if Cohere is not available
    or not configured.
    """

    MODEL = "rerank-english-v3.0"

    def __init__(self):
        if COHERE_AVAILABLE and COHERE_API_KEY:
            self.client = cohere.Client(COHERE_API_KEY)
            self.enabled = True
            logger.info("Cohere reranker initialized")
        else:
            self.client = None
            self.enabled = False
            if not COHERE_API_KEY:
                logger.warning("COHERE_API_KEY not set. Reranking disabled.")

    async def rerank(
        self,
        query: str,
        documents: List[Dict],
        top_n: int = 5
    ) -> List[Dict]:
        """
        Rerank documents using Cohere.

        Args:
            query: The search query
            documents: List of document dicts (must have 'content' key)
            top_n: Number of top results to return

        Returns:
            Reranked documents with rerank_score added
        """
        if not documents:
            return []

        if not self.enabled:
            # Fallback: return top_n documents as-is
            logger.debug("Reranking disabled, returning top results by RRF score")
            return documents[:top_n]

        try:
            # Extract document texts
            doc_texts = [doc.get("content", "") for doc in documents]

            # Call Cohere rerank API (sync call wrapped in thread)
            response = await asyncio.to_thread(
                self.client.rerank,
                model=self.MODEL,
                query=query,
                documents=doc_texts,
                top_n=min(top_n, len(documents)),
                return_documents=False
            )

            # Build reranked results
            reranked = []
            for result in response.results:
                doc = documents[result.index].copy()
                doc["rerank_score"] = result.relevance_score
                reranked.append(doc)

            return reranked

        except Exception as e:
            logger.error(f"Cohere rerank error: {e}. Falling back to RRF results.")
            return documents[:top_n]

    def rerank_sync(
        self,
        query: str,
        documents: List[Dict],
        top_n: int = 5
    ) -> List[Dict]:
        """
        Synchronous wrapper for rerank.

        Args:
            query: The search query
            documents: List of document dicts
            top_n: Number of top results to return

        Returns:
            Reranked documents
        """
        return asyncio.run(self.rerank(query, documents, top_n))

    def is_enabled(self) -> bool:
        """Check if reranking is enabled."""
        return self.enabled


# Singleton instance
_reranker = None


def get_reranker() -> CohereReranker:
    """Get or create the singleton CohereReranker instance."""
    global _reranker
    if _reranker is None:
        _reranker = CohereReranker()
    return _reranker
