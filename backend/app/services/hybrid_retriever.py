"""
Hybrid Retriever for RAG

Combines vector similarity search and keyword search using
Reciprocal Rank Fusion (RRF) for optimal retrieval performance.
"""

import asyncio
from typing import List, Dict, Optional
from app.db import supabase
from app.services.embedding_service import get_embedding_service
from app.config import logger


class HybridRetriever:
    """
    Hybrid retriever combining vector and keyword search.

    Uses Reciprocal Rank Fusion (RRF) to merge results from:
    - Vector similarity search (semantic understanding)
    - PostgreSQL full-text search (keyword matching)
    """

    RRF_K = 60  # RRF constant (standard value)
    MIN_RRF_SCORE = 0.01  # Filter very weak matches before reranking

    def __init__(self):
        self.embedding_service = get_embedding_service()

    async def search(
        self,
        query: str,
        jurisdiction: Optional[str] = None,
        top_k: int = 20
    ) -> List[Dict]:
        """
        Execute hybrid search with RRF fusion.

        Args:
            query: The search query
            jurisdiction: Optional filter (FEDERAL, NSW, QLD)
            top_k: Number of results to return

        Returns:
            List of search results with RRF scores
        """
        try:
            # Generate query embedding
            query_embedding = await self.embedding_service.embed_text(query)

            # Call PostgreSQL hybrid_search function via Supabase RPC
            response = supabase.rpc(
                "hybrid_search",
                {
                    "query_embedding": query_embedding,
                    "query_text": query,
                    "filter_jurisdiction": jurisdiction,
                    "match_count": top_k
                }
            ).execute()

            if not response.data:
                logger.info(f"No results found for query: {query}")
                return []

            # Apply RRF scoring
            results = self._apply_rrf(response.data)

            # Sort by RRF score
            sorted_results = sorted(
                results,
                key=lambda x: x.get("rrf_score", 0),
                reverse=True
            )

            # Filter out very weak matches
            filtered_results = [
                r for r in sorted_results
                if r.get("rrf_score", 0) >= self.MIN_RRF_SCORE
            ]

            if len(filtered_results) < len(sorted_results):
                logger.debug(
                    f"Filtered {len(sorted_results) - len(filtered_results)} weak RRF matches "
                    f"(threshold: {self.MIN_RRF_SCORE})"
                )

            return filtered_results[:top_k]

        except Exception as e:
            logger.error(f"Hybrid search error: {e}")
            raise

    def _apply_rrf(self, results: List[Dict]) -> List[Dict]:
        """
        Apply Reciprocal Rank Fusion scoring.

        RRF formula: score(d) = sum(1 / (k + rank(d)))

        Args:
            results: Raw search results with vector_rank and keyword_rank

        Returns:
            Results with rrf_score added
        """
        for result in results:
            score = 0.0

            # Vector search contribution
            vector_rank = result.get("vector_rank")
            if vector_rank is not None:
                score += 1.0 / (self.RRF_K + vector_rank)

            # Keyword search contribution
            keyword_rank = result.get("keyword_rank")
            if keyword_rank is not None:
                score += 1.0 / (self.RRF_K + keyword_rank)

            result["rrf_score"] = score

        return results

    def search_sync(
        self,
        query: str,
        jurisdiction: Optional[str] = None,
        top_k: int = 20
    ) -> List[Dict]:
        """
        Synchronous wrapper for search.

        Args:
            query: The search query
            jurisdiction: Optional filter (FEDERAL, NSW, QLD)
            top_k: Number of results to return

        Returns:
            List of search results with RRF scores
        """
        return asyncio.run(self.search(query, jurisdiction, top_k))

    async def vector_search_only(
        self,
        query: str,
        jurisdiction: Optional[str] = None,
        top_k: int = 20
    ) -> List[Dict]:
        """
        Execute vector-only search (for comparison/debugging).

        Args:
            query: The search query
            jurisdiction: Optional filter
            top_k: Number of results

        Returns:
            Vector search results
        """
        try:
            query_embedding = await self.embedding_service.embed_text(query)

            # Direct vector search via Supabase
            query_builder = supabase.table("legislation_chunks") \
                .select("""
                    id,
                    document_id,
                    parent_chunk_id,
                    content,
                    chunk_type,
                    legislation_documents!inner(citation, jurisdiction, source_url)
                """) \
                .eq("chunk_type", "child") \
                .not_.is_("embedding", "null")

            # Note: Supabase Python client doesn't support vector similarity directly
            # We'd need to use RPC for this. For now, use hybrid_search with null query_text
            response = supabase.rpc(
                "hybrid_search",
                {
                    "query_embedding": query_embedding,
                    "query_text": "",  # Empty to avoid keyword matching
                    "filter_jurisdiction": jurisdiction,
                    "match_count": top_k
                }
            ).execute()

            return response.data or []

        except Exception as e:
            logger.error(f"Vector search error: {e}")
            raise


# Singleton instance
_hybrid_retriever = None


def get_hybrid_retriever() -> HybridRetriever:
    """Get or create the singleton HybridRetriever instance."""
    global _hybrid_retriever
    if _hybrid_retriever is None:
        _hybrid_retriever = HybridRetriever()
    return _hybrid_retriever
