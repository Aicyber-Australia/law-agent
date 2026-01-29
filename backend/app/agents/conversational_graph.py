"""Conversational mode graph for natural legal chat.

This is a simpler, faster alternative to the adaptive graph.
Focuses on natural conversation with tools, not multi-stage pipelines.

Flow:
    initialize -> safety_check -> chat_response -> END
                      |
                      v (if crisis)
              escalation_response -> END
"""

import re
import uuid
from typing import Literal

from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from app.agents.conversational_state import ConversationalState, ConversationalOutput
from app.agents.stages.safety_check_lite import (
    safety_check_lite_node,
    route_after_safety_lite,
    format_escalation_response_lite,
)
from app.agents.stages.chat_response import chat_response_node
from app.config import logger


# ============================================
# CopilotKit Context Extraction
# ============================================

def extract_context_item(state: ConversationalState, keyword: str) -> str | None:
    """Extract a context item from CopilotKit context by keyword in description."""
    copilotkit_data = state.get("copilotkit", {})
    if not copilotkit_data:
        return None

    context_items = copilotkit_data.get("context", [])

    for item in context_items:
        try:
            description = item.get("description", "") if isinstance(item, dict) else getattr(item, "description", "")
            value = item.get("value", "") if isinstance(item, dict) else getattr(item, "value", "")

            if keyword.lower() in description.lower():
                return value
        except Exception:
            continue

    return None


def clean_context_value(value: str | None) -> str | None:
    """Remove extra quotes from context values if present."""
    if value and isinstance(value, str):
        if value.startswith('"') and value.endswith('"'):
            value = value[1:-1]
        value = value.replace('\\"', '"')
    return value


def extract_user_state_from_context(state: ConversationalState) -> str | None:
    """Extract user's Australian state from CopilotKit context."""
    raw_value = extract_context_item(state, "state/territory")
    cleaned = clean_context_value(raw_value)

    if not cleaned:
        return None

    # Extract state code (e.g., "NSW" from "User is in NSW")
    state_codes = ["NSW", "VIC", "QLD", "SA", "WA", "TAS", "NT", "ACT"]
    for code in state_codes:
        if code in cleaned.upper():
            return code

    return cleaned


def extract_document_url_from_context(state: ConversationalState) -> str | None:
    """Extract uploaded document URL from CopilotKit context."""
    raw_value = extract_context_item(state, "document")
    cleaned = clean_context_value(raw_value)

    if not cleaned:
        return None

    # Extract URL from context string
    url_match = re.search(r'https?://[^\s"]+', cleaned)
    if url_match:
        return url_match.group(0)

    return None


# ============================================
# Graph Nodes
# ============================================

async def initialize_node(state: ConversationalState) -> dict:
    """
    Initialize state with session ID, extract query and CopilotKit context.

    This is lightweight - just extracts what we need for conversation.
    """
    messages = state.get("messages", [])
    current_query = ""

    # Extract the latest human message as the current query
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            current_query = msg.content
            break

    session_id = state.get("session_id") or str(uuid.uuid4())

    # Extract CopilotKit context
    user_state = extract_user_state_from_context(state)
    uploaded_document_url = extract_document_url_from_context(state)

    # Check if this is the first message (new session)
    is_first_message = len(messages) <= 1

    logger.info(
        f"Conversational init: session={session_id[:8]}, "
        f"query_length={len(current_query)}, user_state={user_state}, "
        f"has_document={bool(uploaded_document_url)}, first_msg={is_first_message}"
    )

    return {
        "session_id": session_id,
        "current_query": current_query,
        "user_state": user_state,
        "uploaded_document_url": uploaded_document_url,
        "is_first_message": is_first_message,
        "mode": "chat",  # Default to chat mode
    }


def should_check_safety(state: ConversationalState) -> Literal["check", "skip"]:
    """
    Determine if we should run safety check.

    Run safety on first message or if query might be risky.
    Skip for simple follow-ups to speed up response.
    """
    # Always check on first message
    if state.get("is_first_message", True):
        return "check"

    # Quick heuristic: check if query is short follow-up
    query = state.get("current_query", "")
    if len(query) < 30 and not any(
        word in query.lower()
        for word in ["help", "emergency", "scared", "hurt", "kill", "die", "suicide"]
    ):
        return "skip"

    return "check"


# ============================================
# Graph Definition
# ============================================

def build_conversational_graph():
    """
    Build the conversational legal assistant graph.

    Simple flow:
    - Initialize (extract context)
    - Safety check (lightweight, skippable for follow-ups)
    - Chat response (natural conversation with tools)
    """
    # Output schema limits what gets streamed to UI
    workflow = StateGraph(ConversationalState, output=ConversationalOutput)

    # Add nodes
    workflow.add_node("initialize", initialize_node)
    workflow.add_node("safety_check", safety_check_lite_node)
    workflow.add_node("escalation_response", format_escalation_response_lite)
    workflow.add_node("chat_response", chat_response_node)

    # Entry point
    workflow.set_entry_point("initialize")

    # After initialize, optionally check safety
    workflow.add_conditional_edges(
        "initialize",
        should_check_safety,
        {
            "check": "safety_check",
            "skip": "chat_response",
        }
    )

    # After safety check, route based on result
    workflow.add_conditional_edges(
        "safety_check",
        route_after_safety_lite,
        {
            "escalate": "escalation_response",
            "continue": "chat_response",
        }
    )

    # Terminal nodes
    workflow.add_edge("escalation_response", END)
    workflow.add_edge("chat_response", END)

    return workflow


def create_conversational_agent():
    """Create the compiled conversational agent graph with memory."""
    workflow = build_conversational_graph()
    checkpointer = MemorySaver()
    return workflow.compile(checkpointer=checkpointer)


# Singleton compiled graph
_conversational_graph = None


def get_conversational_graph():
    """Get or create the singleton conversational graph."""
    global _conversational_graph
    if _conversational_graph is None:
        _conversational_graph = create_conversational_agent()
    return _conversational_graph
