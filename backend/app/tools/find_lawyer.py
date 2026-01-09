from langchain_core.tools import tool
from app.db import supabase
from app.config import logger


@tool
def find_lawyer(location: str, specialty: str) -> str | list[dict]:
    """
    Find a lawyer based on location (e.g., Melbourne) and specialty (e.g., Tenancy).
    """
    try:
        response = supabase.table("lawyers").select("*")\
            .eq("location", location)\
            .ilike("specialty", f"%{specialty}%")\
            .execute()
        if not response.data:
            return "No matching lawyers found."
        return response.data
    except Exception as e:
        logger.error(f"Error in find_lawyer: {e}")
        return "Sorry, I couldn't search for lawyers at this time."
