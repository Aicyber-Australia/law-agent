"""Tests for Phase 3: Brief Generation Mode."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from langchain_core.messages import HumanMessage, AIMessage

from app.agents.conversational_state import ConversationalState
from app.agents.conversational_graph import (
    build_conversational_graph,
    route_after_initialize,
    route_brief_info,
    BRIEF_TRIGGER,
)
from app.agents.stages.brief_flow import (
    brief_check_info_node,
    brief_ask_questions_node,
    brief_generate_node,
    _format_conversation,
    _format_facts_for_prompt,
    _format_brief_as_message,
    _detect_skip_response,
    _detect_generate_now,
    ExtractedFacts,
    ConversationalBrief,
)


def _create_test_state(**overrides) -> ConversationalState:
    """Helper to create a test state with sensible defaults."""
    base_state: ConversationalState = {
        "messages": [],
        "session_id": "test-session",
        "current_query": "",
        "user_state": "NSW",
        "uploaded_document_url": None,
        "mode": "chat",
        "is_first_message": False,
        "quick_replies": None,
        "suggest_brief": False,
        "suggest_lawyer": False,
        "safety_result": "unknown",
        "crisis_resources": None,
        "brief_facts_collected": None,
        "brief_missing_info": None,
        "brief_unknown_info": None,
        "brief_info_complete": False,
        "brief_questions_asked": 0,
        "brief_needs_full_intake": False,
        "copilotkit": None,
        "error": None,
    }
    base_state.update(overrides)
    return base_state


class TestBriefTriggerDetection:
    """Test that the brief trigger is properly detected."""

    def test_brief_trigger_constant(self):
        """Verify the trigger constant matches frontend."""
        assert BRIEF_TRIGGER == "[GENERATE_BRIEF]"

    def test_route_to_brief_mode(self):
        """Test routing when in brief mode."""
        state = _create_test_state(mode="brief")
        assert route_after_initialize(state) == "brief"

    def test_route_to_safety_check_first_message(self):
        """Test routing to safety check on first message."""
        state = _create_test_state(mode="chat", is_first_message=True)
        assert route_after_initialize(state) == "check"

    def test_route_skip_safety_short_followup(self):
        """Test routing skips safety for short follow-ups."""
        state = _create_test_state(
            mode="chat",
            is_first_message=False,
            current_query="Tell me more"
        )
        assert route_after_initialize(state) == "skip"


class TestBriefInfoRouting:
    """Test routing logic for brief info completeness."""

    def test_route_to_generate_when_complete(self):
        """Route to generate when info is complete."""
        state = _create_test_state(brief_info_complete=True)
        assert route_brief_info(state) == "generate"

    def test_route_to_generate_on_early_request(self):
        """Route to generate when user requests via GENERATE_NOW_TRIGGER."""
        state = _create_test_state(
            brief_info_complete=False,
            brief_missing_info=["some info"],
            current_query="[GENERATE_NOW] Just generate it",
        )
        assert route_brief_info(state) == "generate"

    def test_route_to_generate_when_no_missing_info(self):
        """Route to generate when missing_info is empty."""
        state = _create_test_state(
            brief_info_complete=False,
            brief_missing_info=[],  # All answered or marked unknown
        )
        assert route_brief_info(state) == "generate"

    def test_route_to_ask_when_incomplete(self):
        """Route to ask questions when info is incomplete."""
        state = _create_test_state(
            brief_info_complete=False,
            brief_missing_info=["something"],
            brief_questions_asked=0
        )
        assert route_brief_info(state) == "ask"

    def test_route_to_ask_after_many_rounds(self):
        """No question limit - keep asking if info still missing."""
        state = _create_test_state(
            brief_info_complete=False,
            brief_missing_info=["still need this"],
            brief_questions_asked=10  # Even after many rounds
        )
        assert route_brief_info(state) == "ask"


class TestSkipDetection:
    """Test skip response detection helpers."""

    def test_detect_skip_i_dont_know(self):
        """Detect 'I don't know' as skip."""
        assert _detect_skip_response("I don't know") is True

    def test_detect_skip_not_sure(self):
        """Detect 'not sure' as skip."""
        assert _detect_skip_response("I'm not sure about that") is True

    def test_detect_skip_skip(self):
        """Detect 'skip' as skip."""
        assert _detect_skip_response("skip") is True

    def test_detect_skip_unsure(self):
        """Detect 'unsure' as skip."""
        assert _detect_skip_response("unsure") is True

    def test_normal_response_not_skip(self):
        """Normal response should not be detected as skip."""
        assert _detect_skip_response("The lease was signed in January") is False

    def test_empty_not_skip(self):
        """Empty string should not be skip."""
        assert _detect_skip_response("") is False

    def test_detect_generate_now(self):
        """Detect generate now request."""
        assert _detect_generate_now("generate brief now") is True

    def test_detect_generate_now_variation(self):
        """Detect 'just generate' variation."""
        assert _detect_generate_now("just generate it please") is True

    def test_normal_not_generate_now(self):
        """Normal response should not be generate now."""
        assert _detect_generate_now("I want to continue") is False


class TestFormatConversation:
    """Test conversation formatting helper."""

    def test_format_empty_conversation(self):
        """Handle empty conversation."""
        result = _format_conversation([])
        assert result == ""

    def test_format_single_message(self):
        """Format single human message."""
        messages = [HumanMessage(content="Hello")]
        result = _format_conversation(messages)
        assert "User: Hello" in result

    def test_format_conversation_with_both(self):
        """Format conversation with both human and AI messages."""
        messages = [
            HumanMessage(content="What are my rights?"),
            AIMessage(content="As a tenant, you have certain rights..."),
        ]
        result = _format_conversation(messages)
        assert "User: What are my rights?" in result
        assert "Assistant: As a tenant" in result

    def test_format_truncates_long_history(self):
        """Only include last N messages."""
        messages = [HumanMessage(content=f"Message {i}") for i in range(30)]
        result = _format_conversation(messages, max_messages=5)
        assert "Message 25" in result
        assert "Message 29" in result
        assert "Message 10" not in result


class TestFormatFactsForPrompt:
    """Test facts formatting helper."""

    def test_format_empty_facts(self):
        """Handle empty facts."""
        result = _format_facts_for_prompt({})
        assert result == ""

    def test_format_basic_facts(self):
        """Format basic fact structure."""
        facts = {
            "legal_area": "tenancy",
            "situation_summary": "Dispute with landlord",
            "key_facts": ["Lease signed 2024", "Rent increased 20%"],
        }
        result = _format_facts_for_prompt(facts)
        assert "tenancy" in result
        assert "Dispute with landlord" in result
        assert "Lease signed 2024" in result
        assert "Rent increased 20%" in result


class TestFormatBriefAsMessage:
    """Test brief formatting for display."""

    def test_format_brief_includes_summary(self):
        """Brief includes executive summary."""
        brief = ConversationalBrief(
            executive_summary="Tenant dispute requiring urgent attention",
            legal_area="tenancy",
            jurisdiction="NSW",
            situation_narrative="The tenant is facing an unlawful rent increase.",
            key_facts=["Lease signed Jan 2024"],
            fact_gaps=["Amount of increase unknown"],
            parties=["Tenant", "Landlord"],
            documents_evidence=["Lease agreement"],
            client_goals=["Reverse the rent increase"],
            potential_issues=["Breach of Residential Tenancies Act"],
            questions_for_lawyer=["Can I dispute this at NCAT?"],
            urgency_level="urgent",
            urgency_reason="Notice period expiring soon",
        )
        result = _format_brief_as_message(brief, "NSW")
        assert "# Lawyer Brief" in result
        assert "Tenant dispute requiring urgent attention" in result
        assert "Urgent" in result
        assert "NSW" in result

    def test_format_brief_includes_all_sections(self):
        """Brief includes all main sections."""
        brief = ConversationalBrief(
            executive_summary="Test case",
            legal_area="employment",
            jurisdiction="VIC",
            situation_narrative="Unfair dismissal claim.",
            key_facts=["Employed for 5 years", "No written warning"],
            fact_gaps=["Contract terms"],
            parties=["Employee", "Employer"],
            documents_evidence=["Employment contract"],
            client_goals=["Reinstatement or compensation"],
            potential_issues=["Unfair dismissal under Fair Work Act"],
            questions_for_lawyer=["Am I eligible to claim?"],
            urgency_level="standard",
            urgency_reason="21-day filing deadline",
        )
        result = _format_brief_as_message(brief, "VIC")
        assert "Your Situation" in result
        assert "Key Facts" in result
        assert "Questions for Your Lawyer" in result

    def test_format_brief_includes_unknown_info(self):
        """Brief includes unknown info section when provided."""
        brief = ConversationalBrief(
            executive_summary="Test case",
            legal_area="tenancy",
            jurisdiction="NSW",
            situation_narrative="Tenant dispute.",
            key_facts=["Rent was increased"],
            fact_gaps=[],
            parties=["Tenant", "Landlord"],
            documents_evidence=[],
            client_goals=["Dispute the increase"],
            potential_issues=["Excessive rent increase"],
            questions_for_lawyer=["Is this legal?"],
            urgency_level="standard",
            urgency_reason="No immediate deadline",
        )
        unknown_info = ["Type of lease", "Exact date of rent increase"]
        result = _format_brief_as_message(brief, "NSW", unknown_info)
        assert "Information Not Provided" in result
        assert "Type of lease" in result
        assert "Exact date of rent increase" in result

    def test_format_brief_no_unknown_section_when_empty(self):
        """Brief omits unknown section when no unknown info."""
        brief = ConversationalBrief(
            executive_summary="Complete case",
            legal_area="tenancy",
            jurisdiction="NSW",
            situation_narrative="All info provided.",
            key_facts=["Fact 1"],
            fact_gaps=[],
            parties=["Tenant"],
            documents_evidence=[],
            client_goals=["Goal"],
            potential_issues=["Issue"],
            questions_for_lawyer=["Question"],
            urgency_level="low_priority",
            urgency_reason="No urgency",
        )
        result = _format_brief_as_message(brief, "NSW", unknown_info=[])
        assert "Information Not Provided" not in result


class TestGraphIncludesBriefNodes:
    """Test that the graph includes brief mode nodes."""

    def test_graph_has_brief_nodes(self):
        """Graph should include all brief mode nodes."""
        workflow = build_conversational_graph()
        assert "brief_check_info" in workflow.nodes
        assert "brief_ask_questions" in workflow.nodes
        assert "brief_generate" in workflow.nodes

    def test_graph_still_has_chat_nodes(self):
        """Graph should still have chat mode nodes."""
        workflow = build_conversational_graph()
        assert "initialize" in workflow.nodes
        assert "safety_check" in workflow.nodes
        assert "chat_response" in workflow.nodes
        assert "escalation_response" in workflow.nodes


class TestBriefCheckInfoNode:
    """Test the brief info check node."""

    @pytest.mark.asyncio
    async def test_extracts_facts_from_conversation(self):
        """Node extracts facts from conversation history."""
        state = _create_test_state(
            messages=[
                HumanMessage(content="My landlord increased rent by 30%"),
                AIMessage(content="That sounds concerning. When did this happen?"),
                HumanMessage(content="Last week, I got a letter"),
            ],
            user_state="NSW",
        )

        # Mock the LLM response
        mock_facts = ExtractedFacts(
            legal_area="tenancy",
            situation_summary="Tenant facing large rent increase",
            key_facts=["30% rent increase", "Received letter last week"],
            parties_involved=["landlord", "tenant"],
            timeline_events=["Letter received last week"],
            documents_mentioned=["Letter"],
            user_goals=[],
            missing_critical_info=["Current rent amount", "Lease type"],
            confidence=0.7,
        )

        with patch("app.agents.stages.brief_flow.ChatOpenAI") as mock_llm_class:
            mock_llm = MagicMock()
            mock_structured = MagicMock()
            mock_structured.ainvoke = AsyncMock(return_value=mock_facts)
            mock_llm.with_structured_output.return_value = mock_structured
            mock_llm_class.return_value = mock_llm

            result = await brief_check_info_node(state, {})

        assert result["brief_facts_collected"]["legal_area"] == "tenancy"
        assert "30% rent increase" in result["brief_facts_collected"]["key_facts"]
        assert len(result["brief_missing_info"]) == 2

    @pytest.mark.asyncio
    async def test_marks_complete_when_confident(self):
        """Node marks info complete when confidence is high."""
        state = _create_test_state(
            messages=[
                HumanMessage(content="My landlord increased rent illegally"),
            ],
        )

        mock_facts = ExtractedFacts(
            legal_area="tenancy",
            situation_summary="Illegal rent increase",
            key_facts=["Rent increased", "Tenant wants to dispute"],
            parties_involved=["landlord", "tenant"],
            timeline_events=[],
            documents_mentioned=[],
            user_goals=["Dispute the increase"],
            missing_critical_info=[],
            confidence=0.8,
        )

        with patch("app.agents.stages.brief_flow.ChatOpenAI") as mock_llm_class:
            mock_llm = MagicMock()
            mock_structured = MagicMock()
            mock_structured.ainvoke = AsyncMock(return_value=mock_facts)
            mock_llm.with_structured_output.return_value = mock_structured
            mock_llm_class.return_value = mock_llm

            result = await brief_check_info_node(state, {})

        assert result["brief_info_complete"] is True


class TestBriefAskQuestionsNode:
    """Test the brief questions node."""

    @pytest.mark.asyncio
    async def test_generates_follow_up_questions(self):
        """Node generates natural follow-up questions."""
        state = _create_test_state(
            brief_facts_collected={
                "situation_summary": "Tenant dispute",
                "legal_area": "tenancy",
            },
            brief_missing_info=["Lease type", "Current rent amount"],
            brief_questions_asked=0,
        )

        from app.agents.stages.brief_flow import FollowUpQuestions
        mock_questions = FollowUpQuestions(
            questions=[
                "Is your lease fixed-term or periodic?",
                "What is your current rent amount?",
            ],
            question_context="Need lease details for accurate brief",
        )

        with patch("app.agents.stages.brief_flow.ChatOpenAI") as mock_llm_class:
            mock_llm = MagicMock()
            mock_structured = MagicMock()
            mock_structured.ainvoke = AsyncMock(return_value=mock_questions)
            mock_llm.with_structured_output.return_value = mock_structured
            mock_llm_class.return_value = mock_llm

            result = await brief_ask_questions_node(state, {})

        assert "messages" in result
        assert len(result["messages"]) == 1
        assert "fixed-term or periodic" in result["messages"][0].content
        assert result["brief_questions_asked"] == 1

    @pytest.mark.asyncio
    async def test_includes_quick_replies(self):
        """Node includes quick reply options."""
        state = _create_test_state(
            brief_facts_collected={"situation_summary": "Test"},
            brief_missing_info=["Something"],
            brief_questions_asked=0,
        )

        from app.agents.stages.brief_flow import FollowUpQuestions
        mock_questions = FollowUpQuestions(
            questions=["What happened?"],
            question_context="Need details",
        )

        with patch("app.agents.stages.brief_flow.ChatOpenAI") as mock_llm_class:
            mock_llm = MagicMock()
            mock_structured = MagicMock()
            mock_structured.ainvoke = AsyncMock(return_value=mock_questions)
            mock_llm.with_structured_output.return_value = mock_structured
            mock_llm_class.return_value = mock_llm

            result = await brief_ask_questions_node(state, {})

        assert "quick_replies" in result
        assert "I don't know" in result["quick_replies"]


class TestBriefGenerateNode:
    """Test the brief generation node."""

    @pytest.mark.asyncio
    async def test_generates_comprehensive_brief(self):
        """Node generates a comprehensive brief."""
        state = _create_test_state(
            messages=[
                HumanMessage(content="My landlord raised rent 30%"),
                AIMessage(content="That's a significant increase."),
            ],
            user_state="NSW",
            brief_facts_collected={
                "legal_area": "tenancy",
                "situation_summary": "Large rent increase",
                "key_facts": ["30% increase"],
            },
        )

        mock_brief = ConversationalBrief(
            executive_summary="Tenant facing potentially unlawful rent increase",
            legal_area="tenancy",
            jurisdiction="NSW",
            situation_narrative="Tenant received 30% rent increase notice.",
            key_facts=["30% rent increase"],
            fact_gaps=["Lease terms"],
            parties=["Tenant", "Landlord"],
            documents_evidence=["Rent increase notice"],
            client_goals=["Dispute the increase"],
            potential_issues=["Excessive rent increase under NSW law"],
            questions_for_lawyer=["Is this increase legal?"],
            urgency_level="standard",
            urgency_reason="Should act before increase takes effect",
        )

        with patch("app.agents.stages.brief_flow.ChatOpenAI") as mock_llm_class:
            mock_llm = MagicMock()
            mock_structured = MagicMock()
            mock_structured.ainvoke = AsyncMock(return_value=mock_brief)
            mock_llm.with_structured_output.return_value = mock_structured
            mock_llm_class.return_value = mock_llm

            result = await brief_generate_node(state, {})

        assert "messages" in result
        assert len(result["messages"]) == 1
        assert "Lawyer Brief" in result["messages"][0].content
        assert result["mode"] == "chat"  # Returns to chat mode
        assert result["suggest_lawyer"] is True

    @pytest.mark.asyncio
    async def test_includes_quick_replies_after_brief(self):
        """Brief includes relevant quick replies."""
        state = _create_test_state(
            messages=[HumanMessage(content="Test")],
            brief_facts_collected={"legal_area": "general"},
        )

        mock_brief = ConversationalBrief(
            executive_summary="Test brief",
            legal_area="general",
            jurisdiction="NSW",
            situation_narrative="Test",
            key_facts=[],
            fact_gaps=[],
            parties=[],
            documents_evidence=[],
            client_goals=[],
            potential_issues=[],
            questions_for_lawyer=[],
            urgency_level="low_priority",
            urgency_reason="No urgency",
        )

        with patch("app.agents.stages.brief_flow.ChatOpenAI") as mock_llm_class:
            mock_llm = MagicMock()
            mock_structured = MagicMock()
            mock_structured.ainvoke = AsyncMock(return_value=mock_brief)
            mock_llm.with_structured_output.return_value = mock_structured
            mock_llm_class.return_value = mock_llm

            result = await brief_generate_node(state, {})

        assert "quick_replies" in result
        assert "Find me a lawyer" in result["quick_replies"]
