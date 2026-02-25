from langchain_core.tools import tool
from app.db import supabase
from app.config import logger


@tool
def get_action_template(query: str, state: str, category: str = "") -> str | list[dict]:
    """
    Retrieve step-by-step action templates for common legal procedures.

    Use this tool when the user needs a structured checklist or action plan
    for a specific legal process (e.g., challenging a parking fine, getting
    bond back, breaking a lease).

    Args:
        query: Keywords describing the action (e.g., "parking fine challenge", "bond refund").
        state: Australian state code - REQUIRED. Use the user's selected state (VIC, NSW, QLD, etc.).
        category: Optional legal category filter (e.g., "parking_ticket", "tenancy").

    Returns:
        List of matching action templates with steps and estimated timing,
        or message if no templates found.
    """
    try:
        logger.info(f"get_action_template: query='{query}', state='{state}', category='{category}'")

        # Build query - filter by state first
        q = supabase.table("action_templates").select("*").eq("state", state)

        # Add category filter if provided
        if category:
            q = q.eq("category", category)

        response = q.execute()

        if not response.data:
            # Try without state filter as fallback
            q = supabase.table("action_templates").select("*")
            if category:
                q = q.eq("category", category)
            response = q.execute()

        if not response.data:
            return f"No action templates found for '{query}' in {state}. I'll use lookup_law to find the relevant legislation instead."

        # Filter results by keyword match against the query
        query_words = set(query.lower().split())
        scored_results = []
        for template in response.data:
            keywords = template.get("keywords", []) or []
            title = template.get("title", "").lower()
            description = template.get("description", "").lower()

            # Score by keyword overlap
            score = 0
            for word in query_words:
                if any(word in kw for kw in keywords):
                    score += 2
                if word in title:
                    score += 1
                if word in description:
                    score += 1

            if score > 0:
                scored_results.append((score, template))

        # Sort by score descending
        scored_results.sort(key=lambda x: x[0], reverse=True)

        if not scored_results:
            # Return best match from all templates if no keyword match
            scored_results = [(0, t) for t in response.data[:1]]

        # Format results — return best match only to keep token usage low
        results = []
        for _, template in scored_results[:1]:
            steps = template.get("steps", [])
            formatted_steps = []
            for step in sorted(steps, key=lambda s: s.get("order", 0)):
                formatted_steps.append({
                    "step": step.get("order"),
                    "title": step.get("title"),
                    "description": step.get("description"),
                })

            results.append({
                "title": template.get("title"),
                "description": template.get("description"),
                "state": template.get("state"),
                "category": template.get("category"),
                "estimated_time": template.get("estimated_time"),
                "steps": formatted_steps,
            })

        return results

    except Exception as e:
        logger.error(f"Error in get_action_template: {e}")
        return "Sorry, I couldn't retrieve action templates at this time."
