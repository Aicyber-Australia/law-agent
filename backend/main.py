import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver
from copilotkit import LangGraphAGUIAgent
from ag_ui_langgraph import add_langgraph_fastapi_endpoint

from app.tools import lookup_law, find_lawyer
from app.config import logger

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

# Setup Agent Logic
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

# Integrate with CopilotKit (using LangGraphAGUIAgent)
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
