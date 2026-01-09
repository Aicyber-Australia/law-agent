from langchain_core.tools import tool
from app.db import supabase
from app.config import logger


@tool
def lookup_law(query: str) -> str | list[dict]:
    """
    Search for Australian laws/acts in the database.
    Input should be a single keyword like 'rent' or 'landlord' or 'tenant'.
    """
    try:
        # Convert multi-word query to tsquery format using OR for better results
        # "rent increase frequency" -> "rent | increase | frequency"
        search_terms = query.strip().split()
        tsquery = " | ".join(search_terms)  # Use OR instead of AND for broader search

        logger.info(f"lookup_law called with query: '{query}' -> tsquery: '{tsquery}'")

        response = supabase.table("legal_docs").select("*").text_search("search_vector", tsquery).execute()

        logger.info(f"lookup_law results: {len(response.data) if response.data else 0} documents found")

        if not response.data:
            return "No specific legislation found in the database."
        return response.data
    except Exception as e:
        logger.error(f"Error in lookup_law: {e}")
        return "Sorry, I couldn't search the legal database at this time."
