import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.memory import MemorySaver
from copilotkit import CopilotKitState, LangGraphAGUIAgent
from ag_ui_langgraph import add_langgraph_fastapi_endpoint

from app.tools import lookup_law, find_lawyer
from app.tools.generate_checklist import generate_checklist
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
tools = [lookup_law, find_lawyer, generate_checklist]
model_with_tools = model.bind_tools(tools)

BASE_SYSTEM_PROMPT = """
You are 'AusLaw AI', a transparent Australian legal assistant.

CAPABILITIES:
1. **Research**: Answer legal questions with citations using `lookup_law`
2. **Action**: Generate step-by-step checklists using `generate_checklist`
3. **Match**: Find lawyers using `find_lawyer`

RULES:
1. For legal questions: Use `lookup_law(query, state)` to find legislation. DO NOT answer from memory.
2. CITATIONS FORMAT: Always cite like this:
   "According to the **[Act Name] [Section]** ([State])..."
   Example: "According to the **Residential Tenancies Act 1997 s.44** (VIC)..."
3. For "how to" questions: Use `generate_checklist(procedure, state)` tool.
4. For lawyer requests: Use `find_lawyer(specialty, state)`.
5. End responses with: "_This is general information, not legal advice. Please consult a qualified lawyer for your specific situation._"
"""


# Define state that inherits from CopilotKitState
class AgentState(CopilotKitState):
    pass


def extract_user_state(state: AgentState) -> str | None:
    """Extract user's Australian state from CopilotKit context."""
    copilotkit_data = state.get("copilotkit", {})
    context_items = copilotkit_data.get("context", [])

    for item in context_items:
        try:
            description = item.description if hasattr(item, "description") else item.get("description", "")
            value = item.value if hasattr(item, "value") else item.get("value", "")

            if "state" in description.lower() or "territory" in description.lower():
                return value
        except Exception:
            continue

    return None


def chat_node(state: AgentState, config: RunnableConfig):
    """Main chat node that reads CopilotKit context."""
    # Extract user state from CopilotKit context
    user_state_context = extract_user_state(state)

    # Build dynamic system message
    if user_state_context:
        state_instruction = f"""
USER LOCATION CONTEXT:
{user_state_context}

CRITICAL: The user's state is provided above. You MUST use this state for ALL tool calls.
- DO NOT ask for the user's state or location - you already have it!
- Use the state code (VIC, NSW, QLD, SA, WA, TAS, NT, ACT) from the context above for all tools.
"""
    else:
        state_instruction = """
USER LOCATION: Not yet selected.
Ask the user to select their Australian state/territory so you can provide accurate legal information.
"""

    system_message = SystemMessage(content=BASE_SYSTEM_PROMPT + state_instruction)

    # Invoke model with context-aware system message
    response = model_with_tools.invoke(
        [system_message, *state["messages"]],
        config
    )

    return {"messages": [response]}


def should_continue(state: AgentState):
    """Check if we should continue to tools or end."""
    messages = state["messages"]
    last_message = messages[-1]

    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tools"
    return END


# Build the graph
workflow = StateGraph(AgentState)

# Add nodes
workflow.add_node("chat", chat_node)
workflow.add_node("tools", ToolNode(tools))

# Add edges
workflow.set_entry_point("chat")
workflow.add_conditional_edges("chat", should_continue, {"tools": "tools", END: END})
workflow.add_edge("tools", "chat")

# Compile with checkpointer
checkpointer = MemorySaver()
graph = workflow.compile(checkpointer=checkpointer)

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
