"""Conversational mode graph for natural legal chat.

This is a simpler, faster alternative to the adaptive graph.
Focuses on natural conversation with tools, not multi-stage pipelines.

Flow (chat mode):
    initialize -> safety_check -> chat_response -> END
                      |
                      v (if crisis)
              escalation_response -> END

Flow (brief mode - triggered by user):
    initialize -> brief_check_info -> [brief_ask_questions | brief_generate] -> END
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
from app.agents.stages.brief_flow import (
    brief_check_info_node,
    brief_ask_questions_node,
    brief_generate_node,
)
from app.config import logger


# Brief generation trigger marker (sent from frontend)
BRIEF_TRIGGER = "[GENERATE_BRIEF]"


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
    Also detects brief generation trigger from frontend.
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

    # Check for brief generation trigger
    is_brief_mode = BRIEF_TRIGGER in current_query
    if is_brief_mode:
        # Clean the trigger from the query
        current_query = current_query.replace(BRIEF_TRIGGER, "").strip()

    logger.info(
        f"Conversational init: session={session_id[:8]}, "
        f"query_length={len(current_query)}, user_state={user_state}, "
        f"has_document={bool(uploaded_document_url)}, first_msg={is_first_message}, "
        f"brief_mode={is_brief_mode}"
    )

    return {
        "session_id": session_id,
        "current_query": current_query,
        "user_state": user_state,
        "uploaded_document_url": uploaded_document_url,
        "is_first_message": is_first_message,
        "mode": "brief" if is_brief_mode else "chat",
    }


def route_after_initialize(state: ConversationalState) -> Literal["brief", "check", "skip"]:
    """
    Route based on mode after initialization.

    - brief: User triggered brief generation
    - check: Run safety check (first message or risky content)
    - skip: Skip safety, go directly to chat
    """
    # Brief mode bypasses normal flow
    if state.get("mode") == "brief":
        return "brief"

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


def route_brief_info(state: ConversationalState) -> Literal["generate", "ask"]:
    """
    Route based on whether we have enough info for the brief.

    - generate: We have enough info, generate the brief
    - ask: Need more info, ask follow-up questions
    """
    # If info is complete, generate brief
    if state.get("brief_info_complete", False):
        return "generate"

    # If we've asked too many questions (max 3 rounds), generate anyway
    if state.get("brief_questions_asked", 0) >= 3:
        return "generate"

    # Otherwise, ask more questions
    return "ask"


# ============================================
# Graph Definition
# ============================================

def build_conversational_graph():
    """
    Build the conversational legal assistant graph.

    Chat flow:
    - Initialize (extract context)
    - Safety check (lightweight, skippable for follow-ups)
    - Chat response (natural conversation with tools)

    Brief flow (user-triggered):
    - Initialize (detect brief trigger)
    - Brief check info (extract facts, find gaps)
    - Brief ask questions (if info missing) or Brief generate (if ready)
    """
    # Output schema limits what gets streamed to UI
    workflow = StateGraph(ConversationalState, output=ConversationalOutput)

    # Add chat mode nodes
    workflow.add_node("initialize", initialize_node)
    workflow.add_node("safety_check", safety_check_lite_node)
    workflow.add_node("escalation_response", format_escalation_response_lite)
    workflow.add_node("chat_response", chat_response_node)

    # Add brief mode nodes
    workflow.add_node("brief_check_info", brief_check_info_node)
    workflow.add_node("brief_ask_questions", brief_ask_questions_node)
    workflow.add_node("brief_generate", brief_generate_node)

    # Entry point
    workflow.set_entry_point("initialize")

    # After initialize, route based on mode
    workflow.add_conditional_edges(
        "initialize",
        route_after_initialize,
        {
            "brief": "brief_check_info",
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

    # Brief mode routing
    workflow.add_conditional_edges(
        "brief_check_info",
        route_brief_info,
        {
            "generate": "brief_generate",
            "ask": "brief_ask_questions",
        }
    )

    # Terminal nodes
    workflow.add_edge("escalation_response", END)
    workflow.add_edge("chat_response", END)
    workflow.add_edge("brief_ask_questions", END)  # Wait for user response
    workflow.add_edge("brief_generate", END)

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
