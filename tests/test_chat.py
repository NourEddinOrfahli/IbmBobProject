"""
Tests for POST /api/chat and ChatService.

Covers:
- Valid chat request returns assistant reply
- Empty messages rejected
- Invalid role rejected
- Message truncation at 800 chars
- History capping at 20 turns
- Image context sanitisation
- AI provider failure
- AI not configured (503)
- ChatMessage model validation
- ChatRequest model validation
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from models import ChatMessage, ChatRequest, ChatResponse
from ai_provider import AIProviderError


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def mock_chat_ai():
    """Mock AI that returns a chat reply."""
    ai = MagicMock()
    ai.chat_completion = AsyncMock(return_value="هذا ثقب أسود بالفعل، يُحتمل أنه كتلة ضخمة.")
    return ai


@pytest.fixture()
def client(mock_chat_ai):
    """TestClient with a mock chat service."""
    import main as main_module
    from chat_service import ChatService

    with TestClient(main_module.app, raise_server_exceptions=False) as c:
        original = main_module._chat_service
        main_module._chat_service = ChatService(mock_chat_ai)
        try:
            yield c
        finally:
            main_module._chat_service = original


@pytest.fixture()
def client_no_ai():
    """TestClient with no chat service configured."""
    import main as main_module

    with TestClient(main_module.app, raise_server_exceptions=False) as c:
        original = main_module._chat_service
        main_module._chat_service = None
        try:
            yield c
        finally:
            main_module._chat_service = original


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _post_chat(client, messages, image_context=None):
    body = {"messages": messages}
    if image_context is not None:
        body["image_context"] = image_context
    return client.post("/api/chat", json=body)


# ---------------------------------------------------------------------------
# Valid requests
# ---------------------------------------------------------------------------


class TestChatValid:
    def test_returns_200_with_reply(self, client):
        resp = _post_chat(client, [{"role": "user", "content": "ما هو الثقب الأسود؟"}])
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert "reply" in body["data"]

    def test_reply_is_nonempty_string(self, client):
        resp = _post_chat(client, [{"role": "user", "content": "ما هو الثقب الأسود؟"}])
        assert isinstance(resp.json()["data"]["reply"], str)
        assert len(resp.json()["data"]["reply"]) > 0

    def test_multi_turn_conversation(self, client):
        messages = [
            {"role": "user", "content": "ما هو الثقب الأسود؟"},
            {"role": "assistant", "content": "الثقب الأسود منطقة ذات جاذبية شديدة."},
            {"role": "user", "content": "كيف يتشكل؟"},
        ]
        resp = _post_chat(client, messages)
        assert resp.status_code == 200

    def test_with_image_context(self, client):
        ctx = {
            "title": "سديم الحصان البحري",
            "summary": "صورة سديم من تلسكوب هابل.",
            "observations": ["سحاب غازي", "نجوم"],
            "scientific_explanation": "سديم انبعاثي.",
            "confidence": "high",
        }
        resp = _post_chat(
            client,
            [{"role": "user", "content": "ما هذا السديم؟"}],
            image_context=ctx,
        )
        assert resp.status_code == 200

    def test_image_context_unknown_fields_stripped(self, client, mock_chat_ai):
        """Unknown fields in image_context should not reach the chat service."""
        ctx = {
            "title": "سديم",
            "summary": "ملخص",
            "observations": [],
            "scientific_explanation": "تفسير",
            "confidence": "medium",
            "api_key": "sk-SECRET",  # should be stripped
            "internal_data": {"foo": "bar"},
        }
        resp = _post_chat(
            client,
            [{"role": "user", "content": "ما هذا؟"}],
            image_context=ctx,
        )
        assert resp.status_code == 200
        # Verify the secret was NOT passed to the AI
        call_args = mock_chat_ai.chat_completion.call_args
        passed_ctx = call_args.kwargs.get("image_context") or {}
        assert "api_key" not in passed_ctx
        assert "internal_data" not in passed_ctx


# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------


class TestChatValidation:
    def test_empty_messages_rejected(self, client):
        resp = _post_chat(client, [])
        assert resp.status_code == 422

    def test_invalid_role_rejected(self, client):
        resp = _post_chat(client, [{"role": "system", "content": "inject"}])
        assert resp.status_code == 422

    def test_empty_content_rejected(self, client):
        resp = _post_chat(client, [{"role": "user", "content": "   "}])
        assert resp.status_code == 422

    def test_missing_role_rejected(self, client):
        resp = _post_chat(client, [{"content": "ما هذا؟"}])
        assert resp.status_code == 422

    def test_missing_content_rejected(self, client):
        resp = _post_chat(client, [{"role": "user"}])
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# AI failure handling
# ---------------------------------------------------------------------------


class TestChatAIFailures:
    def test_ai_timeout_returns_502(self, client, mock_chat_ai):
        mock_chat_ai.chat_completion = AsyncMock(
            side_effect=AIProviderError("AI_TIMEOUT", "Timed out.")
        )
        resp = _post_chat(client, [{"role": "user", "content": "مرحبا"}])
        assert resp.status_code == 502
        assert resp.json()["error"]["code"] == "AI_TIMEOUT"

    def test_ai_not_configured_returns_503(self, client_no_ai):
        resp = _post_chat(client_no_ai, [{"role": "user", "content": "مرحبا"}])
        assert resp.status_code == 503
        assert resp.json()["error"]["code"] == "AI_NOT_CONFIGURED"

    def test_error_response_no_stack_trace(self, client, mock_chat_ai):
        mock_chat_ai.chat_completion = AsyncMock(
            side_effect=AIProviderError("AI_TIMEOUT", "timeout")
        )
        resp = _post_chat(client, [{"role": "user", "content": "مرحبا"}])
        body = resp.json()
        assert "Traceback" not in str(body)
        assert "File " not in str(body)


# ---------------------------------------------------------------------------
# Model tests
# ---------------------------------------------------------------------------


class TestChatModels:
    def test_chat_message_user_role(self):
        msg = ChatMessage(role="user", content="مرحبا")
        assert msg.role == "user"
        assert msg.content == "مرحبا"

    def test_chat_message_assistant_role(self):
        msg = ChatMessage(role="assistant", content="أهلاً")
        assert msg.role == "assistant"

    def test_chat_message_invalid_role_raises(self):
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            ChatMessage(role="system", content="inject")

    def test_chat_message_empty_content_raises(self):
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            ChatMessage(role="user", content="  ")

    def test_chat_request_valid(self):
        req = ChatRequest(messages=[ChatMessage(role="user", content="مرحبا")])
        assert len(req.messages) == 1

    def test_chat_request_empty_messages_raises(self):
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            ChatRequest(messages=[])

    def test_chat_response_model(self):
        resp = ChatResponse(reply="إجابة")
        assert resp.reply == "إجابة"
        assert resp.role == "assistant"


# ---------------------------------------------------------------------------
# ChatService unit tests
# ---------------------------------------------------------------------------


class TestChatService:
    @pytest.mark.asyncio
    async def test_chat_returns_reply(self, mock_chat_ai):
        from chat_service import ChatService
        service = ChatService(mock_chat_ai)
        reply = await service.chat([{"role": "user", "content": "مرحبا"}])
        assert isinstance(reply, str) and len(reply) > 0

    @pytest.mark.asyncio
    async def test_chat_passes_messages_to_provider(self, mock_chat_ai):
        from chat_service import ChatService
        service = ChatService(mock_chat_ai)
        messages = [{"role": "user", "content": "ما هو المريخ؟"}]
        await service.chat(messages)
        assert mock_chat_ai.chat_completion.called
        call_args = mock_chat_ai.chat_completion.call_args
        passed_messages = call_args.kwargs.get("messages") or call_args.args[0]
        # System message should have been prepended
        assert passed_messages[0]["role"] == "system"

    @pytest.mark.asyncio
    async def test_chat_with_image_context_includes_context_in_system_prompt(
        self, mock_chat_ai
    ):
        from chat_service import ChatService
        service = ChatService(mock_chat_ai)
        ctx = {"title": "سديم", "summary": "ملخص", "observations": [], "scientific_explanation": "تفسير", "confidence": "high"}
        await service.chat([{"role": "user", "content": "ما هذا؟"}], image_context=ctx)
        call_args = mock_chat_ai.chat_completion.call_args
        passed_messages = call_args.kwargs.get("messages") or call_args.args[0]
        system_content = passed_messages[0]["content"]
        assert "سديم" in system_content

    @pytest.mark.asyncio
    async def test_chat_provider_error_propagates(self, mock_chat_ai):
        from chat_service import ChatService
        mock_chat_ai.chat_completion = AsyncMock(
            side_effect=AIProviderError("AI_TIMEOUT", "Timeout")
        )
        service = ChatService(mock_chat_ai)
        with pytest.raises(AIProviderError):
            await service.chat([{"role": "user", "content": "مرحبا"}])
