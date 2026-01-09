from langchain_core.tools import tool
from app.db import supabase
from app.config import logger


# Map state codes to major cities
STATE_TO_CITY = {
    "VIC": "Melbourne",
    "NSW": "Sydney",
    "QLD": "Brisbane",
    "SA": "Adelaide",
    "WA": "Perth",
    "TAS": "Hobart",
    "NT": "Darwin",
    "ACT": "Canberra",
}


@tool
def find_lawyer(specialty: str, state: str = "VIC") -> str | list[dict]:
    """
    Find a lawyer based on specialty and state.

    Args:
        specialty: Area of law (e.g., "Tenancy", "Employment", "Family Law", "Commercial").
        state: Australian state code (VIC, NSW, QLD, etc.). Defaults to VIC.

    Returns:
        List of matching lawyers with name, specialty, location, and rate.
    """
    try:
        # Convert state to city
        location = STATE_TO_CITY.get(state, "Melbourne")

        logger.info(f"find_lawyer: specialty='{specialty}', state='{state}', location='{location}'")

        response = supabase.table("lawyers").select("*")\
            .eq("location", location)\
            .ilike("specialty", f"%{specialty}%")\
            .execute()

        if not response.data:
            # Try without location filter if no results
            response = supabase.table("lawyers").select("*")\
                .ilike("specialty", f"%{specialty}%")\
                .execute()

        if not response.data:
            return f"No {specialty} lawyers found in {location}. Try a different specialty or contact the Law Society of {state}."

        # Format results
        results = []
        for lawyer in response.data:
            results.append({
                "name": lawyer.get("name"),
                "specialty": lawyer.get("specialty"),
                "location": lawyer.get("location"),
                "rate": lawyer.get("rate")
            })

        return results

    except Exception as e:
        logger.error(f"Error in find_lawyer: {e}")
        return "Sorry, I couldn't search for lawyers at this time."
