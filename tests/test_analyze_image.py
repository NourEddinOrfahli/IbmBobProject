"""
Tests for POST /api/analyze-image.

Covers:
- Valid JPEG/PNG/WEBP upload
- Invalid MIME type rejection
- Oversized image rejection
- Empty/missing image rejection
- Optional question parameter
- Structured AI response validation
- Malformed AI response (ValidationError)
- AI provider failure (AIProviderError)
- Safe error handling (no stack traces, no key leakage)

All AI provider calls are mocked — no real API keys required.
"""

from __future__ import annotations

import base64
import json
from io import BytesIO
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from pydantic import ValidationError

from models import ImageAnalysisResult
from ai_provider import AIProviderError


# ---------------------------------------------------------------------------
# Minimal 1×1 PNG (valid image bytes)
# ---------------------------------------------------------------------------

_TINY_PNG_B64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk"
    "YPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
)
_TINY_PNG_BYTES = base64.b64decode(_TINY_PNG_B64)

_TINY_JPEG_BYTES = (
    b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
    b"\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t"
    b"\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a"
    b"\x1f\x1e\x1d\x1a\x1c\x1c $.' \",#\x1c\x1c(7),\x01\x02\x03\x04"
    b"\xff\xd9"
)


def _valid_ai_response() -> dict:
    return {
        "title": "سديم رائع في الفضاء",
        "summary": "صورة رائعة لسديم بعيد تظهر ألوانه الزاهية.",
        "observations": ["يظهر سحاب غازي كثيف", "نجوم مضيئة في الخلفية"],
        "scientific_explanation": "يُرجَّح أن هذا سديم انبعاثي يتكوّن من غاز الهيدروجين.",
        "confidence": "medium",
        "story": "في أعماق الفضاء الشاسع تولد النجوم من رحم الغيوم الكونية.",
        "question_answer": "",
        "is_space_related": True,
    }


# ---------------------------------------------------------------------------
# Fixture: app with mocked AI
# ---------------------------------------------------------------------------


@pytest.fixture()
def mock_ai():
    """Return a mock AI object whose analyze_image returns a valid response."""
    ai = MagicMock()
    ai.analyze_image = AsyncMock(return_value=_valid_ai_response())
    return ai


@pytest.fixture()
def client(mock_ai):
    """
    TestClient with the lifespan bypassed for the AI provider.

    The TestClient runs the lifespan which initialises _story_generator with the
    real provider (if OPENROUTER_API_KEY is set).  We patch AFTER lifespan by
    directly replacing the module attribute so endpoint calls see our mock.
    """
    import main as main_module

    with TestClient(main_module.app, raise_server_exceptions=False) as c:
        # After lifespan has run, replace the module-level generator with our mock
        original = main_module._story_generator
        mock_generator = MagicMock()
        mock_generator._ai = mock_ai
        main_module._story_generator = mock_generator
        try:
            yield c
        finally:
            main_module._story_generator = original


@pytest.fixture()
def client_no_ai():
    """TestClient with _story_generator set to None (AI not configured)."""
    import main as main_module

    with TestClient(main_module.app, raise_server_exceptions=False) as c:
        original = main_module._story_generator
        main_module._story_generator = None
        try:
            yield c
        finally:
            main_module._story_generator = original


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _upload(client, file_bytes: bytes, mime: str, question: str | None = None):
    """POST to /api/analyze-image with given bytes and MIME type."""
    data = {}
    if question is not None:
        data["question"] = question
    return client.post(
        "/api/analyze-image",
        files={"image": ("test.img", BytesIO(file_bytes), mime)},
        data=data,
    )


# ---------------------------------------------------------------------------
# Valid uploads
# ---------------------------------------------------------------------------


class TestValidUploads:
    def test_valid_png_returns_200(self, client):
        resp = _upload(client, _TINY_PNG_BYTES, "image/png")
        assert resp.status_code == 200

    def test_valid_jpeg_returns_200(self, client, mock_ai):
        mock_ai.analyze_image = AsyncMock(return_value=_valid_ai_response())
        resp = _upload(client, _TINY_JPEG_BYTES, "image/jpeg")
        assert resp.status_code == 200

    def test_response_is_success_true(self, client):
        resp = _upload(client, _TINY_PNG_BYTES, "image/png")
        body = resp.json()
        assert body["success"] is True

    def test_response_contains_expected_fields(self, client):
        resp = _upload(client, _TINY_PNG_BYTES, "image/png")
        data = resp.json()["data"]
        assert "title" in data
        assert "summary" in data
        assert "observations" in data
        assert "scientific_explanation" in data
        assert "confidence" in data
        assert "is_space_related" in data

    def test_optional_question_is_passed_through(self, client, mock_ai):
        mock_ai.analyze_image = AsyncMock(return_value={
            **_valid_ai_response(),
            "question_answer": "هذا كوكب المشتري.",
        })
        resp = _upload(client, _TINY_PNG_BYTES, "image/png", question="ما هذا الكوكب؟")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["question_answer"] == "هذا كوكب المشتري."

    def test_no_question_succeeds(self, client):
        resp = _upload(client, _TINY_PNG_BYTES, "image/png")
        assert resp.status_code == 200

    def test_analyze_image_called_with_base64(self, client, mock_ai):
        _upload(client, _TINY_PNG_BYTES, "image/png")
        assert mock_ai.analyze_image.called
        call_kwargs = mock_ai.analyze_image.call_args
        image_b64 = call_kwargs.kwargs.get("image_b64")
        assert isinstance(image_b64, str) and len(image_b64) > 0
        decoded = base64.b64decode(image_b64)
        assert decoded == _TINY_PNG_BYTES

    def test_correct_mime_passed_to_ai(self, client, mock_ai):
        _upload(client, _TINY_PNG_BYTES, "image/png")
        call_kwargs = mock_ai.analyze_image.call_args
        image_mime = call_kwargs.kwargs.get("image_mime")
        assert image_mime == "image/png"

    def test_webp_mime_accepted(self, client, mock_ai):
        mock_ai.analyze_image = AsyncMock(return_value=_valid_ai_response())
        resp = _upload(client, _TINY_PNG_BYTES, "image/webp")
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# MIME type validation
# ---------------------------------------------------------------------------


class TestMimeValidation:
    def test_gif_rejected(self, client):
        resp = _upload(client, _TINY_PNG_BYTES, "image/gif")
        assert resp.status_code == 422
        body = resp.json()
        assert body["success"] is False
        assert body["error"]["code"] == "UNSUPPORTED_IMAGE_TYPE"

    def test_svg_rejected(self, client):
        resp = _upload(client, b"<svg/>", "image/svg+xml")
        assert resp.status_code == 422
        assert resp.json()["error"]["code"] == "UNSUPPORTED_IMAGE_TYPE"

    def test_pdf_rejected(self, client):
        resp = _upload(client, b"%PDF-1.4", "application/pdf")
        assert resp.status_code == 422
        assert resp.json()["error"]["code"] == "UNSUPPORTED_IMAGE_TYPE"

    def test_text_rejected(self, client):
        resp = _upload(client, b"hello", "text/plain")
        assert resp.status_code == 422
        assert resp.json()["error"]["code"] == "UNSUPPORTED_IMAGE_TYPE"

    def test_error_message_is_arabic(self, client):
        resp = _upload(client, _TINY_PNG_BYTES, "image/gif")
        msg = resp.json()["error"]["message"]
        arabic_chars = [ch for ch in msg if "\u0600" <= ch <= "\u06FF"]
        assert len(arabic_chars) > 5

    def test_no_api_key_in_error_message(self, client):
        resp = _upload(client, _TINY_PNG_BYTES, "image/gif")
        msg = resp.json()["error"]["message"]
        assert "sk-" not in msg
        assert "Bearer" not in msg
        assert "OPENROUTER" not in msg


# ---------------------------------------------------------------------------
# Size validation
# ---------------------------------------------------------------------------


class TestSizeValidation:
    def test_oversized_image_rejected(self, client):
        oversized = b"x" * (5 * 1024 * 1024 + 1)
        resp = _upload(client, oversized, "image/png")
        assert resp.status_code == 413
        assert resp.json()["error"]["code"] == "IMAGE_TOO_LARGE"

    def test_exact_max_size_accepted(self, client, mock_ai):
        mock_ai.analyze_image = AsyncMock(return_value=_valid_ai_response())
        exact_max = b"x" * (5 * 1024 * 1024)
        resp = _upload(client, exact_max, "image/png")
        assert resp.status_code != 413

    def test_empty_file_rejected(self, client):
        resp = _upload(client, b"", "image/png")
        assert resp.status_code == 422
        assert resp.json()["error"]["code"] == "EMPTY_IMAGE"


# ---------------------------------------------------------------------------
# AI provider failures
# ---------------------------------------------------------------------------


class TestAIProviderFailures:
    def test_ai_timeout_returns_502(self, client, mock_ai):
        mock_ai.analyze_image = AsyncMock(
            side_effect=AIProviderError("AI_TIMEOUT", "Request timed out.")
        )
        resp = _upload(client, _TINY_PNG_BYTES, "image/png")
        assert resp.status_code == 502
        assert resp.json()["error"]["code"] == "AI_TIMEOUT"

    def test_ai_network_error_returns_502(self, client, mock_ai):
        mock_ai.analyze_image = AsyncMock(
            side_effect=AIProviderError("AI_NETWORK_ERROR", "Network failure.")
        )
        resp = _upload(client, _TINY_PNG_BYTES, "image/png")
        assert resp.status_code == 502
        assert resp.json()["error"]["code"] == "AI_NETWORK_ERROR"

    def test_ai_auth_error_returns_502(self, client, mock_ai):
        mock_ai.analyze_image = AsyncMock(
            side_effect=AIProviderError("AI_UNAUTHORIZED", "Bad key.")
        )
        resp = _upload(client, _TINY_PNG_BYTES, "image/png")
        assert resp.status_code == 502
        body = resp.json()
        assert body["success"] is False
        assert body["error"]["code"] == "AI_UNAUTHORIZED"

    def test_ai_error_message_not_leaked_in_stack_trace(self, client, mock_ai):
        mock_ai.analyze_image = AsyncMock(
            side_effect=AIProviderError("AI_TIMEOUT", "timeout after 60s")
        )
        resp = _upload(client, _TINY_PNG_BYTES, "image/png")
        body = resp.json()
        assert "Traceback" not in str(body)
        assert "File " not in str(body)

    def test_malformed_ai_response_returns_502(self, client, mock_ai):
        mock_ai.analyze_image = AsyncMock(return_value={"unexpected_field": "value"})
        resp = _upload(client, _TINY_PNG_BYTES, "image/png")
        assert resp.status_code == 502
        assert resp.json()["error"]["code"] == "VALIDATION_ERROR"

    def test_ai_not_configured_returns_503(self, client_no_ai):
        resp = _upload(client_no_ai, _TINY_PNG_BYTES, "image/png")
        assert resp.status_code == 503
        assert resp.json()["error"]["code"] == "AI_NOT_CONFIGURED"


# ---------------------------------------------------------------------------
# ImageAnalysisResult Pydantic model
# ---------------------------------------------------------------------------


class TestImageAnalysisResultModel:
    def test_valid_full(self):
        result = ImageAnalysisResult(**_valid_ai_response())
        assert result.title == "سديم رائع في الفضاء"
        assert result.confidence == "medium"
        assert result.is_space_related is True
        assert len(result.observations) == 2

    def test_confidence_normalised_to_lowercase(self):
        data = {**_valid_ai_response(), "confidence": "HIGH"}
        result = ImageAnalysisResult(**data)
        assert result.confidence == "high"

    def test_observations_default_empty_list(self):
        data = {**_valid_ai_response()}
        del data["observations"]
        result = ImageAnalysisResult(**data)
        assert result.observations == []

    def test_observations_coerces_string_to_list(self):
        data = {**_valid_ai_response(), "observations": "ملاحظة واحدة"}
        result = ImageAnalysisResult(**data)
        assert result.observations == ["ملاحظة واحدة"]

    def test_story_defaults_to_empty_string(self):
        data = {**_valid_ai_response()}
        del data["story"]
        result = ImageAnalysisResult(**data)
        assert result.story == ""

    def test_question_answer_defaults_to_empty_string(self):
        data = {**_valid_ai_response()}
        del data["question_answer"]
        result = ImageAnalysisResult(**data)
        assert result.question_answer == ""

    def test_is_space_related_defaults_to_true(self):
        data = {**_valid_ai_response()}
        del data["is_space_related"]
        result = ImageAnalysisResult(**data)
        assert result.is_space_related is True

    def test_missing_required_title_raises(self):
        data = {**_valid_ai_response()}
        del data["title"]
        with pytest.raises(ValidationError):
            ImageAnalysisResult(**data)

    def test_missing_required_summary_raises(self):
        data = {**_valid_ai_response()}
        del data["summary"]
        with pytest.raises(ValidationError):
            ImageAnalysisResult(**data)

    def test_missing_required_scientific_explanation_raises(self):
        data = {**_valid_ai_response()}
        del data["scientific_explanation"]
        with pytest.raises(ValidationError):
            ImageAnalysisResult(**data)

    def test_unknown_confidence_value_normalised_to_medium(self):
        data = {**_valid_ai_response(), "confidence": "very_high"}
        result = ImageAnalysisResult(**data)
        assert result.confidence == "medium"

    def test_invalid_confidence_type_normalised_to_medium(self):
        data = {**_valid_ai_response(), "confidence": 42}
        result = ImageAnalysisResult(**data)
        assert result.confidence == "medium"


# ---------------------------------------------------------------------------
# Vision prompts
# ---------------------------------------------------------------------------


class TestVisionPrompts:
    def test_vision_system_prompt_is_nonempty(self):
        from prompts import get_vision_system_prompt
        prompt = get_vision_system_prompt()
        assert isinstance(prompt, str) and len(prompt) > 100

    def test_vision_system_prompt_contains_arabic(self):
        from prompts import get_vision_system_prompt
        prompt = get_vision_system_prompt()
        arabic = [c for c in prompt if "\u0600" <= c <= "\u06FF"]
        assert len(arabic) > 50

    def test_vision_system_prompt_mentions_json(self):
        from prompts import get_vision_system_prompt
        prompt = get_vision_system_prompt()
        assert "JSON" in prompt or "json" in prompt.lower()

    def test_vision_system_prompt_no_hallucination_rule(self):
        from prompts import get_vision_system_prompt
        prompt = get_vision_system_prompt()
        assert "تخترع" in prompt or "تختلق" in prompt

    def test_vision_user_prompt_without_question(self):
        from prompts import build_vision_user_prompt
        prompt = build_vision_user_prompt(None)
        assert isinstance(prompt, str) and len(prompt) > 10
        assert "JSON" in prompt

    def test_vision_user_prompt_with_question_includes_question(self):
        from prompts import build_vision_user_prompt
        q = "هل هذا كوكب أم نجم؟"
        prompt = build_vision_user_prompt(q)
        assert q in prompt

    def test_vision_user_prompt_question_truncated_at_400_chars(self):
        from prompts import build_vision_user_prompt
        long_q = "س" * 500
        prompt = build_vision_user_prompt(long_q)
        assert long_q not in prompt
        assert "س" * 400 in prompt

    def test_vision_user_prompt_empty_question_treated_as_none(self):
        from prompts import build_vision_user_prompt
        prompt_no_q = build_vision_user_prompt(None)
        prompt_empty_q = build_vision_user_prompt("   ")
        assert prompt_no_q == prompt_empty_q
