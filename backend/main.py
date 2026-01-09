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
You are 'AusLaw AI', a transparent Australian legal assistant.

CAPABILITIES:
1. **Research**: Answer legal questions with citations using `lookup_law`
2. **Action**: Generate step-by-step checklists using `generate_checklist`
3. **Match**: Find lawyers using `find_lawyer`

IMPORTANT - STATE HANDLING:
- Australian law varies by state (VIC, NSW, QLD, SA, WA, TAS, NT, ACT)
- REMEMBER the user's state from conversation history. Once they tell you their state, use it for all subsequent queries.
- Only ask for state if they haven't mentioned it anywhere in the conversation.
- State mappings: "Victoria"/"Melbourne" = VIC, "Sydney"/"New South Wales" = NSW, "Brisbane"/"Queensland" = QLD
- Pass the state parameter to lookup_law and generate_checklist tools

RULES:
1. For legal questions: Use `lookup_law(query, state)` to find legislation. DO NOT answer from memory.
2. CITATIONS FORMAT: Always cite like this:
   "According to the **[Act Name] [Section]** ([State])..."
   Example: "According to the **Residential Tenancies Act 1997 s.44** (VIC)..."
3. For "how to" questions: Use `generate_checklist(procedure, state)` tool.
4. If user needs professional help: Use `find_lawyer` to suggest contacts.
5. End responses with: "_This is general information, not legal advice. Please consult a qualified lawyer for your specific situation._"
"""

# Import the new checklist tool
from app.tools.generate_checklist import generate_checklist

# Create the Graph with checkpointer for state management
checkpointer = MemorySaver()
graph = create_react_agent(
    model,
    tools=[lookup_law, find_lawyer, generate_checklist],
    prompt=SYSTEM_PROMPT,
    checkpointer=checkpointer,
)

# Integrate with CopilotKit (using LangGraphAGUIAgent)
add_langgraph_fastapi_endpoint(
    app=app,
    agent=LangGraphAGUIAgent(
        name="auslaw_agent",
        description="Australian Legal Assistant that searches laws, generates checklists, and finds lawyers",
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
