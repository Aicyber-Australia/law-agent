# backend/main.py
import os
import sys
import logging
from dotenv import load_dotenv

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_required_env(name: str) -> str:
    """Get required environment variable or exit with clear error."""
    value = os.environ.get(name)
    if not value:
        logger.error(f"Required environment variable '{name}' is not set.")
        sys.exit(1)
    return value


# Validate environment variables before importing heavy dependencies
SUPABASE_URL = get_required_env("SUPABASE_URL")
SUPABASE_KEY = get_required_env("SUPABASE_KEY")
get_required_env("OPENAI_API_KEY")  # langchain_openai reads this automatically

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from supabase import create_client, Client
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver
from copilotkit import LangGraphAGUIAgent
from ag_ui_langgraph import add_langgraph_fastapi_endpoint

# 1. Setup Supabase Client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

app = FastAPI(
    title="AusLaw AI API",
    description="Australian Legal Assistant Backend",
    version="1.0.0",
)

# Add CORS middleware for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)


# 2. Define Tools (The "Hands" of the AI)
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


# 3. Setup Agent Logic
model = ChatOpenAI(model="gpt-4o", temperature=0)

SYSTEM_PROMPT = """
You are 'AusLaw AI', a transparent legal assistant.

RULES:
1. You must use the `lookup_law` tool to find information.
2. DO NOT answer from your memory. If the tool returns nothing, say you don't know.
3. CITATIONS: When you find a law, you must cite it like this: "According to [Act Name] [Section]...".
4. If the user seems stressed or asks for professional help, use `find_lawyer` to suggest a contact.
"""

# Create the Graph with checkpointer for state management
checkpointer = MemorySaver()
graph = create_react_agent(
    model,
    tools=[lookup_law, find_lawyer],
    prompt=SYSTEM_PROMPT,
    checkpointer=checkpointer,
)

# 4. Integrate with CopilotKit (using LangGraphAGUIAgent)
add_langgraph_fastapi_endpoint(
    app=app,
    agent=LangGraphAGUIAgent(
        name="auslaw_agent",
        description="Australian Legal Assistant that searches laws and finds lawyers",
        graph=graph,
    ),
    path="/copilotkit",
)


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host=host, port=port)
