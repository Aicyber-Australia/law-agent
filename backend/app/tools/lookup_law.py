from langchain_core.tools import tool
from app.db import supabase
from app.config import logger


@tool
def lookup_law(query: str, state: str = "VIC") -> str | list[dict]:
    """
    Search for Australian laws/acts in the database.

    Args:
        query: Search keywords like 'rent increase' or 'landlord entry' or 'bond refund'.
        state: Australian state to filter by (VIC, NSW, QLD, etc.). Defaults to VIC.

    Returns:
        List of matching legal documents with source citations, or error message.
    """
    try:
        # Convert multi-word query to tsquery format using OR for better results
        # "rent increase" -> "rent | increase"
        search_terms = query.strip().split()
        tsquery = " | ".join(search_terms)

        logger.info(f"lookup_law: query='{query}', state='{state}', tsquery='{tsquery}'")

        # Build query with optional state filter
        db_query = supabase.table("legal_docs").select("*").text_search("search_vector", tsquery)

        # Add state filter if the column exists
        try:
            db_query = db_query.eq("state", state)
        except Exception:
            pass  # state column might not exist in older schema

        response = db_query.execute()

        logger.info(f"lookup_law: {len(response.data) if response.data else 0} documents found")

        if not response.data:
            return f"No specific legislation found for '{query}' in {state}. Try different keywords or check another state."

        # Format results with clear citations
        results = []
        for doc in response.data:
            metadata = doc.get("metadata", {})
            results.append({
                "content": doc.get("content", ""),
                "source": metadata.get("source", "Unknown"),
                "section": metadata.get("section", ""),
                "state": doc.get("state", "VIC"),
                "url": metadata.get("url", "")
            })

        return results

    except Exception as e:
        logger.error(f"Error in lookup_law: {e}")
        return "Sorry, I couldn't search the legal database at this time."
