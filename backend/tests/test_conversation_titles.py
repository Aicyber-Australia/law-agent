"""Tests for conversation title suggestion heuristics."""

from app.db.production_store import (
    suggest_conversation_title,
    is_generic_conversation_title,
    suggest_conversation_title_with_llm,
)


class TestConversationTitleHeuristics:
    """Validate title generation and generic-title detection."""

    def test_greeting_message_falls_back_to_topic_default(self):
        title = suggest_conversation_title(content="Hi", legal_topic="general")
        assert title == "General Legal Help"

    def test_specific_message_generates_meaningful_title(self):
        title = suggest_conversation_title(
            content="I got a parking fine and need help writing an appeal letter.",
            legal_topic="parking_ticket",
        )
        assert title.startswith("I got a parking fine")
        assert "help" in title.lower()

    def test_greeting_title_is_treated_as_generic(self):
        assert is_generic_conversation_title(title="Hi", legal_topic="general") is True
        assert is_generic_conversation_title(title="General Legal Help", legal_topic="general") is True

    def test_specific_title_is_not_generic(self):
        assert (
            is_generic_conversation_title(
                title="Appeal options for parking infringement notice",
                legal_topic="parking_ticket",
            )
            is False
        )

    def test_llm_title_generation_uses_mocked_response(self, monkeypatch):
        captured = {}

        class FakeResponse:
            content = "Appeal parking fine options"

        class FakeLLM:
            def __init__(self, *args, **kwargs):
                pass

            def invoke(self, _prompt, **kwargs):
                captured.update(kwargs)
                return FakeResponse()

        monkeypatch.setattr("app.db.production_store.ChatOpenAI", FakeLLM)

        title = suggest_conversation_title_with_llm(
            user_messages=["Hi", "I got a parking fine and want to appeal it."],
            legal_topic="parking_ticket",
        )
        assert title == "Appeal parking fine options"
        cfg = captured.get("config", {})
        metadata = cfg.get("metadata", {})
        assert metadata.get("emit-messages") is False
        assert metadata.get("emit-tool-calls") is False

    def test_llm_title_generation_supports_single_meaningful_message(self, monkeypatch):
        class FakeResponse:
            content = "Bond return dispute in Victoria"

        class FakeLLM:
            def __init__(self, *args, **kwargs):
                pass

            def invoke(self, _prompt, **kwargs):
                return FakeResponse()

        monkeypatch.setattr("app.db.production_store.ChatOpenAI", FakeLLM)

        title = suggest_conversation_title_with_llm(
            user_messages=["My landlord has not returned my bond after I moved out."],
            legal_topic="general",
        )
        assert title == "Bond return dispute in Victoria"

    def test_llm_title_generation_falls_back_when_output_is_low_signal(self, monkeypatch):
        class FakeResponse:
            content = "Hi"

        class FakeLLM:
            def __init__(self, *args, **kwargs):
                pass

            def invoke(self, _prompt, **kwargs):
                return FakeResponse()

        monkeypatch.setattr("app.db.production_store.ChatOpenAI", FakeLLM)

        title = suggest_conversation_title_with_llm(
            user_messages=["Hi", "Hello"],
            legal_topic="insurance_claim",
        )
        assert title == "Insurance Claim Help"
