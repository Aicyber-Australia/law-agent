"""
Legal Document Lookup Tool using RAG

Provides hybrid search (vector + keyword) with reranking for
retrieving relevant Australian legislation.
"""

import asyncio
from langchain_core.tools import tool
from app.db import supabase
from app.services.hybrid_retriever import get_hybrid_retriever
from app.services.reranker import get_reranker
from app.config import logger


# State code to jurisdiction mapping
STATE_TO_JURISDICTION = {
    "NSW": "NSW",
    "QLD": "QLD",
    "FEDERAL": "FEDERAL",
    "ACT": "FEDERAL",  # ACT uses federal law primarily
}

# States not yet supported (no data in corpus)
UNSUPPORTED_STATES = ["VIC", "SA", "WA", "TAS", "NT"]


@tool
def lookup_law(query: str, state: str = "VIC") -> str | list[dict]:
    """
    Search for Australian laws/acts using advanced RAG retrieval.

    Uses hybrid search (vector similarity + keyword matching) combined
    with neural reranking for high-quality legal document retrieval.

    Args:
        query: Legal question or keywords (e.g., 'rent increase notice period',
               'tenant bond refund rights', 'criminal sentencing guidelines').
        state: Australian state/territory code (NSW, QLD, FEDERAL supported).
               For unsupported states (VIC, SA, WA, TAS, NT), falls back to
               showing relevant Federal law.

    Returns:
        List of matching legal passages with citations and source URLs,
        or error message if search fails.
    """
    try:
        # Map state to jurisdiction
        jurisdiction = STATE_TO_JURISDICTION.get(state)
        is_unsupported = state in UNSUPPORTED_STATES

        if is_unsupported:
            jurisdiction = "FEDERAL"  # Fallback

        logger.info(f"lookup_law: query='{query}', state='{state}', jurisdiction='{jurisdiction}'")

        # Run async search in sync context
        results = asyncio.run(_search_and_rerank(query, jurisdiction))

        if not results:
            msg = f"No legislation found for '{query}'"
            if jurisdiction:
                msg += f" in {state if not is_unsupported else 'Federal law'}"
            return msg + ". Try different keywords or check another jurisdiction."

        # Fetch parent content for better context
        formatted_results = []
        for chunk in results:
            parent_content = _get_parent_content(chunk)

            result = {
                "content": parent_content or chunk.get("content", ""),
                "citation": chunk.get("citation", "Unknown"),
                "jurisdiction": chunk.get("jurisdiction", state),
                "source_url": chunk.get("source_url", ""),
                "relevance_score": round(
                    chunk.get("rerank_score", chunk.get("rrf_score", 0)),
                    3
                ),
            }
            formatted_results.append(result)

        # Add note if showing federal law for unsupported state
        if is_unsupported and formatted_results:
            formatted_results.insert(0, {
                "note": f"Note: {state} legislation is not yet available in our database. "
                        f"Showing relevant Federal law instead. For state-specific advice, "
                        f"please consult a legal professional."
            })

        return formatted_results

    except Exception as e:
        logger.error(f"Error in lookup_law: {e}")
        return "Sorry, I couldn't search the legal database at this time. Please try again later."


async def _search_and_rerank(query: str, jurisdiction: str | None) -> list[dict]:
    """
    Execute hybrid search and reranking pipeline.

    Args:
        query: The search query
        jurisdiction: Jurisdiction filter (FEDERAL, NSW, QLD) or None

    Returns:
        List of reranked document chunks
    """
    retriever = get_hybrid_retriever()
    reranker = get_reranker()

    # Hybrid search (vector + keyword with RRF)
    results = await retriever.search(
        query=query,
        jurisdiction=jurisdiction,
        top_k=20
    )

    if not results:
        return []

    # Rerank for final precision (top 5)
    reranked = await reranker.rerank(
        query=query,
        documents=results,
        top_n=5
    )

    return reranked


def _get_parent_content(chunk: dict) -> str | None:
    """
    Fetch parent chunk content for fuller context.

    When we retrieve a child chunk (small, precise), we often want
    to return the parent chunk (larger, more context) to the user.

    Args:
        chunk: The retrieved chunk dict

    Returns:
        Parent chunk content if exists, None otherwise
    """
    parent_id = chunk.get("parent_chunk_id")

    if not parent_id:
        return None

    try:
        response = supabase.table("legislation_chunks") \
            .select("content") \
            .eq("id", parent_id) \
            .single() \
            .execute()

        if response.data:
            return response.data.get("content")
    except Exception as e:
        logger.warning(f"Failed to fetch parent chunk {parent_id}: {e}")

    return None


# Keep backward compatibility - also export as function
def search_law(query: str, state: str = "VIC") -> str | list[dict]:
    """Alias for lookup_law for backward compatibility."""
    return lookup_law.invoke({"query": query, "state": state})
