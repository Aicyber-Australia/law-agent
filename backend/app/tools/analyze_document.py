"""Fetch document tool - fetches and parses uploaded documents for agent analysis."""

from typing import Optional
from langchain_core.tools import tool

from app.config import logger
from app.utils.url_fetcher import fetch_and_parse_document


@tool
def analyze_document(
    document_url: Optional[str] = None,
    document_text: Optional[str] = None,
    analysis_type: str = "general",
    state: str = "VIC"
) -> str:
    """
    Fetch and parse a document for analysis. Returns the document text content for you to analyze.

    Args:
        document_url: URL to fetch the document from (e.g., Supabase Storage URL). Use this when user has uploaded a file.
        document_text: Direct text content of the document (fallback if URL not provided)
        analysis_type: Type of document - "lease", "contract", "visa", or "general" (for context)
        state: Australian state for jurisdiction-specific analysis (VIC, NSW, QLD, etc.)

    Returns:
        The parsed document text content. You should then analyze this content based on the analysis_type and state.
    """
    # If URL provided, fetch and parse the document
    if document_url:
        logger.info(f"analyze_document called with URL: {document_url}")
        try:
            document_text, content_type = fetch_and_parse_document(document_url)
            logger.info(f"Fetched document: type={content_type}, length={len(document_text)}")
        except ValueError as e:
            return f"Failed to fetch document from URL: {str(e)}"

    if not document_text or len(document_text.strip()) < 50:
        return "ERROR: The document appears to be empty or too short to analyze. Please upload a valid document."

    # Truncate very long documents to avoid token limits
    max_chars = 30000
    truncated = False
    if len(document_text) > max_chars:
        document_text = document_text[:max_chars]
        truncated = True
        logger.warning(f"Document truncated to {max_chars} characters")

    # Return document content with metadata for agent to analyze
    result = f"""=== DOCUMENT CONTENT ===
Type: {analysis_type}
Jurisdiction: {state}
Length: {len(document_text)} characters{" (truncated)" if truncated else ""}

{document_text}

=== END DOCUMENT ==="""

    logger.info(f"analyze_document returning {len(result)} chars for {analysis_type} document")
    return result
