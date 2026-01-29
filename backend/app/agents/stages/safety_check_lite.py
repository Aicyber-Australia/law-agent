"""Lightweight safety check for conversational mode.

Faster than the full safety router by using keyword detection first,
only falling back to LLM for uncertain cases.
"""

import re
from typing import Optional
from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableConfig

from app.agents.conversational_state import ConversationalState
from app.agents.schemas.emergency_resources import get_resources_for_risk
from app.agents.routers.safety_router import get_safety_router
from app.config import logger


# High-confidence crisis keywords that don't need LLM verification
CRISIS_KEYWORDS = {
    "suicide_self_harm": [
        r"\b(kill myself|end my life|want to die|suicide|self.?harm)\b",
        r"\b(can'?t go on|no reason to live|better off dead)\b",
    ],
    "family_violence": [
        r"\b(hit me|beat me|abused|domestic violence|scared of (my|him|her))\b",
        r"\b(threatened to (kill|hurt)|AVO|DVO|protection order)\b",
    ],
    "child_welfare": [
        r"\b(child (protection|services)|DOCS|took my (kids|children))\b",
        r"\b(child abuse|hurt (my|the) (child|kid|baby))\b",
    ],
    "criminal": [
        r"\b(arrested|charged with|police (station|custody)|criminal charge)\b",
        r"\b(going to (jail|prison|court for crime))\b",
    ],
}

# Keywords that might indicate risk - need LLM to verify
UNCERTAIN_KEYWORDS = [
    r"\b(court|hearing|deadline|tomorrow|next week)\b",
    r"\b(evicted?|kicked out|homeless)\b",
    r"\b(scared|afraid|worried|anxious)\b",
    r"\b(police|officer|crime)\b",
    r"\b(hurt|pain|danger)\b",
]


def _check_crisis_keywords(query: str) -> tuple[bool, str | None]:
    """
    Check for high-confidence crisis keywords.

    Returns:
        (is_crisis, risk_category) - True with category if crisis detected
    """
    query_lower = query.lower()

    for category, patterns in CRISIS_KEYWORDS.items():
        for pattern in patterns:
            if re.search(pattern, query_lower, re.IGNORECASE):
                return True, category

    return False, None


def _might_be_risky(query: str) -> bool:
    """Check if query contains uncertain keywords that need LLM verification."""
    query_lower = query.lower()

    for pattern in UNCERTAIN_KEYWORDS:
        if re.search(pattern, query_lower, re.IGNORECASE):
            return True

    return False


async def safety_check_lite_node(
    state: ConversationalState,
    config: RunnableConfig
) -> dict:
    """
    Lightweight safety check - fast keyword detection with LLM fallback.

    This is much faster than always running the full LLM safety router.
    Only calls LLM when keywords suggest potential risk.

    Args:
        state: Current conversation state
        config: LangGraph config

    Returns:
        dict with safety_result and crisis_resources (if needed)
    """
    query = state.get("current_query", "")
    user_state = state.get("user_state")

    # Skip safety check for empty queries
    if not query.strip():
        return {
            "safety_result": "safe",
            "crisis_resources": None,
        }

    # Step 1: Check for obvious crisis keywords (no LLM needed)
    is_crisis, risk_category = _check_crisis_keywords(query)

    if is_crisis and risk_category:
        logger.warning(f"Crisis keywords detected: category={risk_category}")
        resources = get_resources_for_risk(risk_category, user_state)
        return {
            "safety_result": "escalate",
            "crisis_resources": resources,
        }

    # Step 2: Check if query might be risky (needs LLM verification)
    if _might_be_risky(query):
        logger.info("Uncertain keywords detected, running LLM safety check")
        router = get_safety_router()
        assessment = await router.assess(
            query=query,
            user_state=user_state,
            config=config,
        )

        if assessment.get("requires_escalation"):
            return {
                "safety_result": "escalate",
                "crisis_resources": assessment.get("recommended_resources", []),
            }

    # Step 3: No risk detected
    return {
        "safety_result": "safe",
        "crisis_resources": None,
    }


def route_after_safety_lite(state: ConversationalState) -> str:
    """
    Route based on safety check result.

    Returns:
        "escalate" if crisis detected, "continue" otherwise
    """
    safety_result = state.get("safety_result", "safe")

    if safety_result == "escalate":
        return "escalate"

    return "continue"


def format_escalation_response_lite(state: ConversationalState) -> dict:
    """
    Format a compassionate response for crisis situations.

    Uses the crisis resources from the safety check.
    """
    resources = state.get("crisis_resources", [])

    # Format resources
    resource_lines = []
    for resource in resources:
        line = f"**{resource['name']}**"
        if resource.get("phone"):
            line += f" - {resource['phone']}"
        if resource.get("description"):
            line += f"\n  _{resource['description']}_"
        if resource.get("url"):
            line += f"\n  {resource['url']}"
        resource_lines.append(line)

    resources_text = "\n\n".join(resource_lines) if resource_lines else ""

    message = f"""I'm concerned about what you've shared. Your safety and wellbeing come first.

**Please contact these services for immediate support:**

{resources_text}

---

These services are free and confidential. They can provide the urgent, professional support that I, as an AI assistant, cannot offer.

If you have other legal questions that aren't urgent safety matters, I'm still here to help with general legal information."""

    return {
        "messages": [AIMessage(content=message)],
    }
