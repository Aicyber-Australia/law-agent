"""Brief generation flow for conversational mode.

User-triggered brief generation that:
1. Analyzes conversation to extract facts and identify gaps
2. Asks targeted follow-up questions if info is missing
3. Generates a comprehensive lawyer brief when ready

This is Phase 3 of conversational mode - activated when user clicks "Generate Brief".
"""

from typing import Literal, Optional
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.runnables import RunnableConfig

from app.agents.conversational_state import ConversationalState
from app.agents.utils import get_internal_llm_config
from app.config import logger


# ============================================
# Schemas for LLM Structured Output
# ============================================

class ExtractedFacts(BaseModel):
    """Facts extracted from conversation history."""
    legal_area: str = Field(
        description="Primary legal area (tenancy, employment, family, consumer, criminal, general)"
    )
    situation_summary: str = Field(
        description="Brief summary of the user's legal situation"
    )
    key_facts: list[str] = Field(
        default_factory=list,
        description="Key facts established in the conversation"
    )
    parties_involved: list[str] = Field(
        default_factory=list,
        description="Parties mentioned (landlord, employer, spouse, etc.)"
    )
    timeline_events: list[str] = Field(
        default_factory=list,
        description="Timeline of events if mentioned"
    )
    documents_mentioned: list[str] = Field(
        default_factory=list,
        description="Any documents or evidence mentioned"
    )
    user_goals: list[str] = Field(
        default_factory=list,
        description="What the user wants to achieve"
    )
    missing_critical_info: list[str] = Field(
        default_factory=list,
        description="Critical information still missing to provide a useful brief"
    )
    confidence: float = Field(
        ge=0.0, le=1.0,
        description="Confidence in understanding the situation (0.0-1.0)"
    )


class FollowUpQuestions(BaseModel):
    """Targeted questions to fill information gaps."""
    questions: list[str] = Field(
        min_length=1,
        max_length=3,
        description="1-3 targeted questions to ask the user"
    )
    question_context: str = Field(
        description="Brief explanation of why these questions are needed"
    )


class ConversationalBrief(BaseModel):
    """Comprehensive lawyer brief generated from conversation."""
    executive_summary: str = Field(
        description="1-2 sentence summary of the matter"
    )
    legal_area: str = Field(
        description="Primary legal area this falls under"
    )
    jurisdiction: str = Field(
        description="Relevant Australian jurisdiction"
    )
    situation_narrative: str = Field(
        description="Clear narrative of the client's situation"
    )
    key_facts: list[str] = Field(
        description="Established facts"
    )
    fact_gaps: list[str] = Field(
        description="Information still unknown or unclear"
    )
    parties: list[str] = Field(
        description="Parties involved"
    )
    documents_evidence: list[str] = Field(
        description="Documents or evidence available or mentioned"
    )
    client_goals: list[str] = Field(
        description="What the client wants to achieve"
    )
    potential_issues: list[str] = Field(
        description="Legal issues the lawyer should consider"
    )
    questions_for_lawyer: list[str] = Field(
        description="Specific questions the client should discuss with lawyer"
    )
    urgency_level: Literal["urgent", "standard", "low_priority"] = Field(
        description="How urgently the client should see a lawyer"
    )
    urgency_reason: str = Field(
        description="Brief explanation of urgency level"
    )


# ============================================
# Prompts
# ============================================

FACT_EXTRACTION_PROMPT = """You are analyzing a conversation between a user and a legal assistant to extract facts for a lawyer brief.

## Your Task

Extract all relevant facts from the conversation that would help a lawyer understand:
1. What the legal situation is
2. Who is involved
3. What happened and when
4. What documents or evidence exist
5. What the user wants

## Critical Info That Must Be Known

For a useful lawyer brief, we need at minimum:
- The general nature of the legal problem
- The user's role in the situation
- What outcome the user wants
- Any urgent deadlines or time pressures

If these are unclear, list them in missing_critical_info.

## Conversation History

{conversation}

## User's State/Territory

{user_state}

Extract the facts carefully. If something is implied but not stated, note it as uncertain."""


FOLLOW_UP_PROMPT = """Based on the conversation analysis, you need to ask the user some follow-up questions before generating their lawyer brief.

## What We Know

{situation_summary}

## Missing Information

{missing_info}

## Your Task

Generate 1-3 targeted questions that will:
1. Fill the most critical gaps
2. Be conversational and not feel like an interrogation
3. Help generate a useful lawyer brief

Keep questions focused and practical. Don't ask about irrelevant details.

Ask the questions naturally, as a helpful assistant would."""


BRIEF_GENERATION_PROMPT = """You are generating a comprehensive lawyer brief based on the conversation between a user and a legal assistant.

## User's State/Territory
{user_state}

## Conversation History
{conversation}

## Extracted Facts
{extracted_facts}

## Your Task

Generate a professional, structured brief that a lawyer can use to quickly understand:
1. What this case is about
2. Key facts and timeline
3. Who is involved
4. What documents exist
5. What the client wants
6. What questions the client should discuss with the lawyer

## Urgency Guidelines

**Urgent:**
- Court/tribunal deadlines within 14 days
- Limitation periods about to expire
- Risk of eviction, termination, or harm
- Criminal charges pending
- Family violence or safety concerns

**Standard:**
- Active disputes requiring resolution
- Deadlines within 1-3 months
- Complex matters needing analysis

**Low Priority:**
- Information gathering stage
- No immediate deadlines
- Preventative advice sought

Be thorough but concise. The brief should help a lawyer quickly understand the situation without reading the entire conversation."""


# ============================================
# Required Info by Legal Area
# ============================================

REQUIRED_INFO_BY_AREA = {
    "tenancy": [
        "type of tenancy (residential, commercial)",
        "lease status (signed, verbal, expired)",
        "issue (rent, repairs, eviction, bond, etc.)",
        "other party (landlord, agent, roommate)",
    ],
    "employment": [
        "employment type (full-time, part-time, casual, contractor)",
        "issue (dismissal, wages, discrimination, injury, etc.)",
        "employer relationship (current, former, potential)",
        "length of employment if relevant",
    ],
    "family": [
        "relationship type (marriage, de facto, etc.)",
        "issue (separation, children, property, violence)",
        "children involved (yes/no)",
        "current living situation",
    ],
    "consumer": [
        "product or service involved",
        "issue (refund, warranty, scam, etc.)",
        "value of transaction",
        "business or seller involved",
    ],
    "criminal": [
        "type of matter (charged, accused, victim, witness)",
        "nature of alleged offense",
        "court involvement (yes/no, stage)",
        "representation status",
    ],
    "general": [
        "nature of legal issue",
        "desired outcome",
        "any deadlines or urgency",
    ],
}


# ============================================
# Node Functions
# ============================================

async def brief_check_info_node(
    state: ConversationalState,
    config: RunnableConfig,
) -> dict:
    """
    Analyze conversation to extract facts and identify information gaps.

    This is the first step when user triggers brief generation.
    It reads the full conversation history and determines:
    - What facts we have
    - What's missing for a useful brief
    - Whether we need to ask more questions

    Args:
        state: Current conversation state
        config: LangGraph config

    Returns:
        dict with brief_facts_collected, brief_missing_info, brief_info_complete
    """
    messages = state.get("messages", [])
    user_state = state.get("user_state", "Not specified")

    logger.info(f"Brief check: analyzing {len(messages)} messages")

    # Format conversation for analysis
    conversation = _format_conversation(messages)

    try:
        # Use internal config to suppress streaming
        internal_config = get_internal_llm_config(config)

        llm = ChatOpenAI(model="gpt-4o", temperature=0)
        structured_llm = llm.with_structured_output(ExtractedFacts)

        facts = await structured_llm.ainvoke(
            FACT_EXTRACTION_PROMPT.format(
                conversation=conversation,
                user_state=user_state,
            ),
            config=internal_config,
        )

        # Determine if we have enough info
        missing_critical = facts.missing_critical_info
        has_enough_info = (
            facts.confidence >= 0.6
            and len(missing_critical) <= 1
            and facts.legal_area != "unknown"
            and len(facts.key_facts) >= 2
        )

        logger.info(
            f"Brief facts extracted: area={facts.legal_area}, "
            f"confidence={facts.confidence:.2f}, "
            f"missing={len(missing_critical)}, complete={has_enough_info}"
        )

        return {
            "brief_facts_collected": facts.model_dump(),
            "brief_missing_info": missing_critical,
            "brief_info_complete": has_enough_info,
        }

    except Exception as e:
        logger.error(f"Brief fact extraction error: {e}")
        return {
            "brief_facts_collected": {
                "legal_area": "general",
                "situation_summary": "Could not fully analyze conversation",
                "key_facts": [],
                "parties_involved": [],
                "timeline_events": [],
                "documents_mentioned": [],
                "user_goals": [],
                "missing_critical_info": ["Full conversation analysis failed"],
                "confidence": 0.3,
            },
            "brief_missing_info": ["Unable to complete analysis - proceeding with available info"],
            "brief_info_complete": True,  # Proceed anyway with what we have
        }


async def brief_ask_questions_node(
    state: ConversationalState,
    config: RunnableConfig,
) -> dict:
    """
    Ask targeted questions to fill information gaps.

    Called when brief_info_complete is False and we haven't exceeded
    the maximum question rounds.

    Args:
        state: Current conversation state
        config: LangGraph config

    Returns:
        dict with messages (questions to ask) and incremented questions_asked
    """
    facts = state.get("brief_facts_collected", {})
    missing_info = state.get("brief_missing_info", [])
    questions_asked = state.get("brief_questions_asked", 0)

    logger.info(f"Brief questions: round {questions_asked + 1}, missing={len(missing_info)}")

    try:
        # Use internal config to suppress streaming
        internal_config = get_internal_llm_config(config)

        llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.3)
        structured_llm = llm.with_structured_output(FollowUpQuestions)

        result = await structured_llm.ainvoke(
            FOLLOW_UP_PROMPT.format(
                situation_summary=facts.get("situation_summary", "User needs legal help"),
                missing_info="\n".join(f"- {item}" for item in missing_info[:5]),
            ),
            config=internal_config,
        )

        # Format questions as natural message
        question_text = f"Before I prepare your lawyer brief, I need a bit more information:\n\n"
        for i, q in enumerate(result.questions, 1):
            question_text += f"{i}. {q}\n"

        return {
            "messages": [AIMessage(content=question_text)],
            "brief_questions_asked": questions_asked + 1,
            "quick_replies": ["I don't know", "Let me explain", "Skip this"],
        }

    except Exception as e:
        logger.error(f"Brief question generation error: {e}")
        # If question generation fails, proceed with brief generation
        return {
            "messages": [AIMessage(content="I'll prepare your brief with the information we have.")],
            "brief_questions_asked": questions_asked + 1,
            "brief_info_complete": True,  # Force completion
        }


async def brief_generate_node(
    state: ConversationalState,
    config: RunnableConfig,
) -> dict:
    """
    Generate the comprehensive lawyer brief.

    Called when we have enough information (brief_info_complete=True)
    or after maximum question rounds.

    Args:
        state: Current conversation state
        config: LangGraph config

    Returns:
        dict with messages (formatted brief) and mode reset to "chat"
    """
    messages = state.get("messages", [])
    user_state = state.get("user_state", "Not specified")
    facts = state.get("brief_facts_collected", {})

    logger.info(f"Brief generation: creating comprehensive brief")

    # Format conversation and facts
    conversation = _format_conversation(messages)
    facts_text = _format_facts_for_prompt(facts)

    try:
        # Use internal config to suppress streaming
        internal_config = get_internal_llm_config(config)

        llm = ChatOpenAI(model="gpt-4o", temperature=0)
        structured_llm = llm.with_structured_output(ConversationalBrief)

        brief = await structured_llm.ainvoke(
            BRIEF_GENERATION_PROMPT.format(
                user_state=user_state,
                conversation=conversation,
                extracted_facts=facts_text,
            ),
            config=internal_config,
        )

        # Format brief as readable message
        formatted_brief = _format_brief_as_message(brief, user_state)

        logger.info(
            f"Brief generated: area={brief.legal_area}, "
            f"urgency={brief.urgency_level}"
        )

        return {
            "messages": [AIMessage(content=formatted_brief)],
            "mode": "chat",  # Return to chat mode
            "quick_replies": [
                "Find me a lawyer",
                "What should I ask the lawyer?",
                "Explain the urgency",
            ],
            "suggest_lawyer": True,
        }

    except Exception as e:
        logger.error(f"Brief generation error: {e}")
        return {
            "messages": [AIMessage(
                content="I apologize, but I encountered an issue generating your brief. "
                "Please try again, or I can help you find a lawyer directly."
            )],
            "mode": "chat",
            "quick_replies": ["Find me a lawyer", "Try again", "What can you help with?"],
        }


# ============================================
# Helper Functions
# ============================================

def _format_conversation(messages: list, max_messages: int = 20) -> str:
    """Format conversation messages for LLM context."""
    formatted = []
    for msg in messages[-max_messages:]:
        if isinstance(msg, HumanMessage):
            formatted.append(f"User: {msg.content}")
        elif isinstance(msg, AIMessage):
            formatted.append(f"Assistant: {msg.content}")
    return "\n\n".join(formatted)


def _format_facts_for_prompt(facts: dict) -> str:
    """Format extracted facts for the brief generation prompt."""
    parts = []

    if facts.get("legal_area"):
        parts.append(f"**Legal Area:** {facts['legal_area']}")

    if facts.get("situation_summary"):
        parts.append(f"**Summary:** {facts['situation_summary']}")

    if facts.get("key_facts"):
        parts.append("**Key Facts:**")
        for fact in facts["key_facts"]:
            parts.append(f"- {fact}")

    if facts.get("parties_involved"):
        parts.append(f"**Parties:** {', '.join(facts['parties_involved'])}")

    if facts.get("timeline_events"):
        parts.append("**Timeline:**")
        for event in facts["timeline_events"]:
            parts.append(f"- {event}")

    if facts.get("documents_mentioned"):
        parts.append(f"**Documents:** {', '.join(facts['documents_mentioned'])}")

    if facts.get("user_goals"):
        parts.append("**User Goals:**")
        for goal in facts["user_goals"]:
            parts.append(f"- {goal}")

    return "\n".join(parts)


def _format_brief_as_message(brief: ConversationalBrief, user_state: str) -> str:
    """Format the brief as a readable chat message."""
    urgency_emoji = {
        "urgent": "🔴",
        "standard": "🟡",
        "low_priority": "🟢",
    }

    lines = [
        "# Lawyer Brief",
        "",
        f"## Summary",
        f"{brief.executive_summary}",
        "",
        f"**Urgency:** {urgency_emoji.get(brief.urgency_level, '⚪')} {brief.urgency_level.replace('_', ' ').title()}",
        f"*{brief.urgency_reason}*",
        "",
        f"**Legal Area:** {brief.legal_area.title()}",
        f"**Jurisdiction:** {brief.jurisdiction or user_state or 'Australia'}",
        "",
        "---",
        "",
        "## Your Situation",
        brief.situation_narrative,
        "",
    ]

    if brief.key_facts:
        lines.append("## Key Facts")
        for fact in brief.key_facts:
            lines.append(f"- {fact}")
        lines.append("")

    if brief.parties:
        lines.append(f"**Parties Involved:** {', '.join(brief.parties)}")
        lines.append("")

    if brief.documents_evidence:
        lines.append("## Documents & Evidence")
        for doc in brief.documents_evidence:
            lines.append(f"- {doc}")
        lines.append("")

    if brief.client_goals:
        lines.append("## Your Goals")
        for goal in brief.client_goals:
            lines.append(f"- {goal}")
        lines.append("")

    if brief.fact_gaps:
        lines.append("## Information to Gather")
        lines.append("*These are things the lawyer may ask about:*")
        for gap in brief.fact_gaps:
            lines.append(f"- {gap}")
        lines.append("")

    if brief.potential_issues:
        lines.append("## Potential Legal Issues")
        for issue in brief.potential_issues:
            lines.append(f"- {issue}")
        lines.append("")

    if brief.questions_for_lawyer:
        lines.append("## Questions for Your Lawyer")
        for q in brief.questions_for_lawyer:
            lines.append(f"- {q}")
        lines.append("")

    lines.extend([
        "---",
        "",
        "*This brief summarizes our conversation. Share it with a lawyer for professional advice.*",
    ])

    return "\n".join(lines)
