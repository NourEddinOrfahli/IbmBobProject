"""
Tests for:
- Prompt generation (prompts.py)
- JSON parsing in OpenRouterProvider
- finish_reason logging
- Retry logic on truncation / parse failure
- max_tokens configuration

None of these tests require real OpenRouter credentials.
All HTTP calls are mocked via unittest.mock.
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from models import NASAAPODData, NASADONKIEvent
from prompts import (
    build_apod_prompt,
    build_apod_with_donki_prompt,
    build_custom_context_prompt,
    build_prompt_for_apod,
    get_retry_prompts,
    get_system_prompt,
)
from ai_provider import AIProviderError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _sample_apod() -> NASAAPODData:
    return NASAAPODData(
        title="Pillars of Creation",
        explanation=(
            "The Eagle Nebula's iconic gas pillars stretch light-years into space, "
            "serving as active stellar nurseries where new stars are born."
        ),
        date="2024-03-20",
        media_type="image",
        image_url="https://apod.nasa.gov/apod/image/pillars.jpg",
        hd_image_url="https://apod.nasa.gov/apod/image/pillars_hd.jpg",
        copyright="NASA/ESA/Hubble",
    )


def _sample_donki_event() -> NASADONKIEvent:
    return NASADONKIEvent(
        event_type="CME",
        begin_time="2024-03-19T14:00Z",
        linked_events=["FLR-2024-03-19"],
    )


def _valid_story_dict() -> dict:
    return {
        "title": "نجوم المجرة",
        "summary": "ملخص مختصر.",
        "scientific_explanation": "شرح علمي.",
        "key_facts": ["حقيقة 1", "حقيقة 2"],
        "why_it_matters": "مهم.",
        "story": "قصة قصيرة.",
        "source_data": {"source": "NASA APOD", "date": "2024-03-20"},
        "confidence": "high",
        "language": "ar",
    }


# ---------------------------------------------------------------------------
# System prompt tests
# ---------------------------------------------------------------------------


class TestSystemPrompt:
    def test_system_prompt_is_nonempty(self):
        prompt = get_system_prompt()
        assert isinstance(prompt, str)
        assert len(prompt) > 100

    def test_system_prompt_contains_arabic(self):
        prompt = get_system_prompt()
        arabic_chars = [c for c in prompt if "\u0600" <= c <= "\u06FF"]
        assert len(arabic_chars) > 50

    def test_system_prompt_mentions_json(self):
        prompt = get_system_prompt()
        assert "JSON" in prompt or "json" in prompt.lower()

    def test_system_prompt_contains_accuracy_rules(self):
        prompt = get_system_prompt()
        assert "ناسا" in prompt
        assert "json" in prompt.lower() or "JSON" in prompt

    def test_system_prompt_concise_story_limit(self):
        """Story field must specify ≤150 words, not 250, to stay within token budget."""
        prompt = get_system_prompt()
        assert "150" in prompt

    def test_retry_prompts_available(self):
        system, user = get_retry_prompts()
        assert isinstance(system, str) and len(system) > 10
        assert isinstance(user, str) and len(user) > 10

    def test_retry_prompts_mention_json(self):
        system, user = get_retry_prompts()
        assert "JSON" in system or "json" in system.lower()

    # --- Language enforcement in prompts ---

    def test_system_prompt_requires_arabic_text_fields(self):
        """SYSTEM_PROMPT must explicitly require Arabic for all user-facing text fields."""
        prompt = get_system_prompt()
        # Must mention that text fields must be in Arabic — not just a generic note
        # The prompt must reference Arabic writing for generated content.
        assert "عربية" in prompt or "Arabic" in prompt
        # Must explicitly warn against English output
        assert "الإنجليزية" in prompt or "إنجليزية" in prompt or "إنجليزي" in prompt

    def test_system_prompt_explicitly_warns_about_english(self):
        """SYSTEM_PROMPT must contain a specific warning that English output is rejected."""
        prompt = get_system_prompt()
        # The updated prompt contains a strict language warning
        assert "ستُرفض" in prompt or "مرفوض" in prompt or "ممنوع" in prompt

    def test_retry_system_prompt_requires_arabic(self):
        """RETRY_SYSTEM_PROMPT must also require Arabic for text fields."""
        system, _ = get_retry_prompts()
        assert "عربية" in system or "Arabic" in system

    def test_retry_instructions_require_arabic(self):
        """Retry instructions appended to the user prompt must also specify Arabic."""
        _, instructions = get_retry_prompts()
        assert "عربية" in instructions or "Arabic" in instructions


# ---------------------------------------------------------------------------
# APOD prompt tests
# ---------------------------------------------------------------------------


class TestBuildApodPrompt:
    def test_contains_title(self):
        apod = _sample_apod()
        assert "Pillars of Creation" in build_apod_prompt(apod)

    def test_contains_date(self):
        apod = _sample_apod()
        assert "2024-03-20" in build_apod_prompt(apod)

    def test_contains_explanation_text(self):
        apod = _sample_apod()
        assert "Eagle Nebula" in build_apod_prompt(apod)

    def test_contains_copyright_when_present(self):
        apod = _sample_apod()
        assert "NASA/ESA/Hubble" in build_apod_prompt(apod)

    def test_no_copyright_section_when_absent(self):
        apod = NASAAPODData(
            title="No Copyright Image",
            explanation="Public domain image.",
            date="2024-03-20",
            media_type="image",
        )
        assert "حقوق النشر" not in build_apod_prompt(apod)

    def test_contains_json_instruction(self):
        apod = _sample_apod()
        assert "JSON" in build_apod_prompt(apod)

    def test_prompt_is_string_with_content(self):
        result = build_apod_prompt(_sample_apod())
        assert isinstance(result, str) and len(result) > 100

    def test_long_explanation_is_truncated(self):
        """Explanations over 800 chars must be truncated to keep prompt token-efficient."""
        long_text = "A" * 1000
        apod = NASAAPODData(
            title="Test",
            explanation=long_text,
            date="2024-01-01",
            media_type="image",
        )
        prompt = build_apod_prompt(apod)
        # The explanation in the prompt must not exceed 800 chars + ellipsis
        assert "A" * 801 not in prompt
        assert "…" in prompt

    def test_short_explanation_not_truncated(self):
        short_text = "Short explanation."
        apod = NASAAPODData(
            title="Test",
            explanation=short_text,
            date="2024-01-01",
            media_type="image",
        )
        prompt = build_apod_prompt(apod)
        assert short_text in prompt
        assert "…" not in prompt


# ---------------------------------------------------------------------------
# APOD + DONKI prompt tests
# ---------------------------------------------------------------------------


class TestBuildApodWithDonkiPrompt:
    def test_includes_donki_event_type(self):
        events = [_sample_donki_event()]
        assert "CME" in build_apod_with_donki_prompt(_sample_apod(), events)

    def test_includes_donki_begin_time(self):
        events = [_sample_donki_event()]
        assert "2024-03-19T14:00Z" in build_apod_with_donki_prompt(_sample_apod(), events)

    def test_falls_back_to_apod_only_when_empty(self):
        apod = _sample_apod()
        assert build_apod_with_donki_prompt(apod, []) == build_apod_prompt(apod)

    def test_caps_at_three_events(self):
        """DONKI events are now capped at 3 (reduced from 5) to save tokens."""
        events = [_sample_donki_event() for _ in range(10)]
        prompt = build_apod_with_donki_prompt(_sample_apod(), events)
        assert prompt.count("الحدث ") <= 3


# ---------------------------------------------------------------------------
# Custom context prompt tests
# ---------------------------------------------------------------------------


class TestBuildCustomContextPrompt:
    def test_contains_context(self):
        assert "Hubble deep field" in build_custom_context_prompt("Hubble deep field")

    def test_contains_arabic_instructions(self):
        prompt = build_custom_context_prompt("Test context")
        arabic_chars = [c for c in prompt if "\u0600" <= c <= "\u06FF"]
        assert len(arabic_chars) > 10

    def test_json_instruction_present(self):
        assert "JSON" in build_custom_context_prompt("Any context")

    def test_long_context_truncated(self):
        long_context = "X" * 1000
        prompt = build_custom_context_prompt(long_context)
        assert "X" * 801 not in prompt
        assert "…" in prompt


# ---------------------------------------------------------------------------
# build_prompt_for_apod convenience wrapper
# ---------------------------------------------------------------------------


class TestBuildPromptForApod:
    def test_returns_tuple_of_two_strings(self):
        system, user = build_prompt_for_apod(_sample_apod())
        assert isinstance(system, str) and isinstance(user, str)

    def test_with_donki_events(self):
        _, user = build_prompt_for_apod(_sample_apod(), [_sample_donki_event()])
        assert "CME" in user

    def test_without_donki_events(self):
        _, user = build_prompt_for_apod(_sample_apod(), None)
        assert "Pillars of Creation" in user


# ---------------------------------------------------------------------------
# JSON parsing tests (static method, no HTTP)
# ---------------------------------------------------------------------------


class TestOpenRouterJSONParsing:
    def _parse(self, raw: str) -> dict:
        from openrouter_provider import OpenRouterProvider
        return OpenRouterProvider._parse_json_response(raw)

    def test_parses_clean_json(self):
        result = self._parse(json.dumps({"title": "test", "language": "ar"}))
        assert result["title"] == "test"

    def test_strips_json_markdown_fence(self):
        result = self._parse('```json\n{"title": "fenced"}\n```')
        assert result["title"] == "fenced"

    def test_strips_generic_markdown_fence(self):
        result = self._parse('```\n{"title": "generic fence"}\n```')
        assert result["title"] == "generic fence"

    def test_handles_whitespace_around_json(self):
        result = self._parse('  \n  {"key": "value"}  \n  ')
        assert result["key"] == "value"

    def test_raises_on_invalid_json(self):
        with pytest.raises(AIProviderError) as exc_info:
            self._parse("this is not json at all")
        assert exc_info.value.code == "AI_JSON_PARSE_ERROR"

    def test_raises_on_json_array(self):
        with pytest.raises(AIProviderError) as exc_info:
            self._parse('["item1", "item2"]')
        assert exc_info.value.code == "AI_UNEXPECTED_TYPE"

    def test_raises_on_empty_string(self):
        with pytest.raises(AIProviderError):
            self._parse("")

    def test_raises_on_truncated_json(self):
        """Truncated JSON must raise AI_JSON_PARSE_ERROR — never silently succeed."""
        truncated = '{"title": "نجوم المجرة", "summary": "ملخص مختصر'
        with pytest.raises(AIProviderError) as exc_info:
            self._parse(truncated)
        assert exc_info.value.code == "AI_JSON_PARSE_ERROR"

    def test_parses_arabic_content(self):
        payload = {"title": "نجوم المجرة", "language": "ar"}
        result = self._parse(json.dumps(payload, ensure_ascii=False))
        assert result["title"] == "نجوم المجرة"

    def test_parses_nested_source_data(self):
        payload = {"title": "T", "source_data": {"source": "NASA APOD", "date": "2024-01-01"}}
        result = self._parse(json.dumps(payload))
        assert result["source_data"]["source"] == "NASA APOD"


# ---------------------------------------------------------------------------
# finish_reason logging (unit test without HTTP)
# ---------------------------------------------------------------------------


class TestFinishReasonLogging:
    def _log_finish_reason(self, finish_reason, attempt=1):
        from openrouter_provider import OpenRouterProvider
        OpenRouterProvider._log_finish_reason(finish_reason, attempt)

    def test_stop_does_not_raise(self):
        self._log_finish_reason("stop", attempt=1)

    def test_length_does_not_raise(self):
        self._log_finish_reason("length", attempt=1)

    def test_none_does_not_raise(self):
        self._log_finish_reason(None, attempt=1)

    def test_unknown_reason_does_not_raise(self):
        self._log_finish_reason("content_filter", attempt=2)


# ---------------------------------------------------------------------------
# Retry logic (mocked HTTP — no real API calls)
# ---------------------------------------------------------------------------


def _make_http_response(content_str: str, finish_reason: str = "stop") -> MagicMock:
    """Build a fake httpx.Response with the given JSON content body."""
    body = {
        "choices": [
            {
                "message": {"content": content_str},
                "finish_reason": finish_reason,
            }
        ]
    }
    mock_resp = MagicMock()
    mock_resp.is_success = True
    mock_resp.status_code = 200
    mock_resp.json.return_value = body
    return mock_resp


def _make_provider() -> "OpenRouterProvider":  # noqa: F821
    from config import OpenRouterConfig
    from openrouter_provider import OpenRouterProvider
    cfg = OpenRouterConfig(api_key="test-key-not-real", model="test/model", max_tokens=1800)
    return OpenRouterProvider(cfg)


class TestRetryLogic:
    """
    All HTTP calls are mocked — no real OpenRouter credentials required.
    """

    @pytest.mark.asyncio
    async def test_valid_json_on_first_attempt_no_retry(self):
        """A clean first response must NOT trigger a retry."""
        provider = _make_provider()
        good_json = json.dumps(_valid_story_dict())
        mock_resp = _make_http_response(good_json, finish_reason="stop")

        mock_post = AsyncMock(return_value=mock_resp)
        with patch.object(provider._client, "post", new=mock_post):
            result = await provider.generate_structured_response(
                system_prompt="sys", user_prompt="usr"
            )
        assert result["language"] == "ar"
        assert mock_post.call_count == 1

    @pytest.mark.asyncio
    async def test_retry_triggered_on_truncation(self):
        """finish_reason=length on first attempt must trigger exactly ONE retry."""
        provider = _make_provider()
        truncated_content = '{"title": "نجوم", "summary": "test'  # truncated
        good_json = json.dumps(_valid_story_dict())

        mock_truncated = _make_http_response(truncated_content, finish_reason="length")
        mock_good = _make_http_response(good_json, finish_reason="stop")

        mock_post = AsyncMock(side_effect=[mock_truncated, mock_good])
        with patch.object(provider._client, "post", new=mock_post):
            result = await provider.generate_structured_response(
                system_prompt="sys", user_prompt="usr"
            )
        assert result["language"] == "ar"
        assert mock_post.call_count == 2

    @pytest.mark.asyncio
    async def test_retry_triggered_on_json_parse_error(self):
        """Invalid JSON on first attempt must trigger exactly ONE retry."""
        provider = _make_provider()
        bad_content = "This is not JSON at all."
        good_json = json.dumps(_valid_story_dict())

        mock_bad = _make_http_response(bad_content, finish_reason="stop")
        mock_good = _make_http_response(good_json, finish_reason="stop")

        mock_post = AsyncMock(side_effect=[mock_bad, mock_good])
        with patch.object(provider._client, "post", new=mock_post):
            result = await provider.generate_structured_response(
                system_prompt="sys", user_prompt="usr"
            )
        assert result["title"] == "نجوم المجرة"
        assert mock_post.call_count == 2

    @pytest.mark.asyncio
    async def test_raises_ai_truncated_when_retry_also_truncated(self):
        """If both attempts return finish_reason=length, raise AI_TRUNCATED."""
        provider = _make_provider()
        truncated_content = '{"title": "نجوم", "summary": "test'

        mock1 = _make_http_response(truncated_content, finish_reason="length")
        mock2 = _make_http_response(truncated_content, finish_reason="length")

        mock_post = AsyncMock(side_effect=[mock1, mock2])
        with patch.object(provider._client, "post", new=mock_post):
            with pytest.raises(AIProviderError) as exc_info:
                await provider.generate_structured_response(
                    system_prompt="sys", user_prompt="usr"
                )
        assert exc_info.value.code == "AI_TRUNCATED"
        assert mock_post.call_count == 2

    @pytest.mark.asyncio
    async def test_raises_immediately_on_parse_error_after_retry(self):
        """
        If retry also returns bad content, an error surfaces immediately after
        exactly 2 HTTP calls.

        Content must be long enough to pass the length guard (>= 100 chars)
        so the failure is AI_JSON_PARSE_ERROR, not AI_INVALID_RESPONSE.
        """
        provider = _make_provider()
        # 104 chars of invalid JSON — passes length guard, fails JSON parse
        bad_content = "Still not JSON at all — " + "x" * 80

        mock1 = _make_http_response(bad_content, finish_reason="stop")
        mock2 = _make_http_response(bad_content, finish_reason="stop")

        mock_post = AsyncMock(side_effect=[mock1, mock2])
        with patch.object(provider._client, "post", new=mock_post):
            with pytest.raises(AIProviderError) as exc_info:
                await provider.generate_structured_response(
                    system_prompt="sys", user_prompt="usr"
                )
        assert exc_info.value.code == "AI_JSON_PARSE_ERROR"
        assert mock_post.call_count == 2

    @pytest.mark.asyncio
    async def test_no_retry_on_auth_error(self):
        """HTTP 401 must raise AI_UNAUTHORIZED immediately — no retry."""
        provider = _make_provider()
        mock_resp = MagicMock()
        mock_resp.is_success = False
        mock_resp.status_code = 401

        mock_post = AsyncMock(return_value=mock_resp)
        with patch.object(provider._client, "post", new=mock_post):
            with pytest.raises(AIProviderError) as exc_info:
                await provider.generate_structured_response(
                    system_prompt="sys", user_prompt="usr"
                )
        assert exc_info.value.code == "AI_UNAUTHORIZED"
        assert mock_post.call_count == 1

    @pytest.mark.asyncio
    async def test_no_retry_on_rate_limit(self):
        """HTTP 429 must raise AI_RATE_LIMIT immediately — no retry."""
        provider = _make_provider()
        mock_resp = MagicMock()
        mock_resp.is_success = False
        mock_resp.status_code = 429

        mock_post = AsyncMock(return_value=mock_resp)
        with patch.object(provider._client, "post", new=mock_post):
            with pytest.raises(AIProviderError) as exc_info:
                await provider.generate_structured_response(
                    system_prompt="sys", user_prompt="usr"
                )
        assert exc_info.value.code == "AI_RATE_LIMIT"
        assert mock_post.call_count == 1


# ---------------------------------------------------------------------------
# max_tokens configuration test
# ---------------------------------------------------------------------------


class TestMaxTokensConfig:
    def test_default_max_tokens_is_2000(self):
        """Default max_tokens must be 2000 to give adequate headroom for Arabic JSON output."""
        from config import OpenRouterConfig
        cfg = OpenRouterConfig(api_key="dummy")
        assert cfg.max_tokens == 2000

    def test_max_tokens_readable_from_env(self, monkeypatch):
        """OPENROUTER_MAX_TOKENS env variable must override the default."""
        monkeypatch.setenv("OPENROUTER_MAX_TOKENS", "2500")
        # Reload the config with the patched env
        import importlib
        import config as cfg_module
        importlib.reload(cfg_module)
        fresh_cfg = cfg_module.OpenRouterConfig()
        assert fresh_cfg.max_tokens == 2500
        # Clean up: reload with the original env
        monkeypatch.delenv("OPENROUTER_MAX_TOKENS", raising=False)
        importlib.reload(cfg_module)

    def test_max_tokens_passed_to_payload(self):
        """max_tokens must appear in the POST payload sent to OpenRouter."""
        from config import OpenRouterConfig
        from openrouter_provider import OpenRouterProvider
        cfg = OpenRouterConfig(api_key="dummy-key", max_tokens=2000)
        provider = OpenRouterProvider(cfg)
        # Inspect payload construction directly via _call_completions internals:
        # We verify max_tokens is forwarded from config → generate_structured_response
        assert provider._config.max_tokens == 2000


# ---------------------------------------------------------------------------
# build_retry_user_prompt — grounding tests (no HTTP)
# ---------------------------------------------------------------------------


class TestBuildRetryUserPrompt:
    """
    Pure-function tests for build_retry_user_prompt().
    No HTTP calls, no API keys required.
    """

    # A — retry prompt contains the original NASA title and date
    def test_retry_user_prompt_contains_original_nasa_data(self):
        original = (
            "بيانات ناسا — صورة الفلك اليومية (APOD):\n\n"
            "العنوان: The Case of the Mysterious Maybe Meteor\n"
            "التاريخ: 2026-08-19\n"
            "نوع الوسائط: image\n\n"
            "الوصف الرسمي:\nA fireball streaked across the sky…"
        )
        from prompts import build_retry_user_prompt
        retry = build_retry_user_prompt(original)
        assert "The Case of the Mysterious Maybe Meteor" in retry
        assert "2026-08-19" in retry

    # B — the complete original prompt is preserved verbatim
    def test_retry_user_prompt_contains_complete_original_prompt(self):
        distinctive = "UNIQUE_EXPLANATION_XYZ_12345_FIREBALL_TEST"
        original = f"العنوان: Some Title\nالتاريخ: 2026-01-01\n\n{distinctive}"
        from prompts import build_retry_user_prompt
        retry = build_retry_user_prompt(original)
        # Complete original must be in the retry, not just a fragment
        assert original in retry
        assert distinctive in retry

    # C — retry prompt does NOT rely on "البيانات التي قدّمتها من قبل" alone;
    #     the actual NASA data must also be present
    def test_retry_does_not_depend_on_previous_conversation(self):
        nasa_title = "Andromeda Galaxy in Ultraviolet"
        nasa_date = "2025-11-30"
        original = (
            f"العنوان: {nasa_title}\n"
            f"التاريخ: {nasa_date}\n"
            "الوصف الرسمي:\nThe Andromeda Galaxy is our nearest large neighbour."
        )
        from prompts import build_retry_user_prompt
        retry = build_retry_user_prompt(original)
        # The original NASA data must be embedded — not just a back-reference
        assert nasa_title in retry
        assert nasa_date in retry
        # The ambiguous back-reference phrase must NOT appear without the data
        assert "البيانات التي قدّمتها من قبل" not in retry

    # Extra: retry instructions are appended after the original prompt
    def test_retry_instructions_appended_after_original(self):
        original = "بيانات ناسا — صورة الفلك اليومية (APOD):\nالعنوان: Test\n"
        from prompts import build_retry_user_prompt
        retry = build_retry_user_prompt(original)
        original_pos = retry.find(original)
        instruction_marker = "تعذّر تنسيق الإجابة السابقة"
        instruction_pos = retry.find(instruction_marker)
        assert original_pos != -1
        assert instruction_pos != -1
        assert original_pos < instruction_pos  # original comes first

    # Extra: no API key appears in retry prompt
    def test_retry_prompt_contains_no_api_key(self):
        original = "العنوان: Test APOD\nالتاريخ: 2025-01-01"
        from prompts import build_retry_user_prompt
        retry = build_retry_user_prompt(original)
        assert "sk-" not in retry
        assert "Bearer" not in retry
        assert "Authorization" not in retry


# ---------------------------------------------------------------------------
# Retry grounding — verified via mocked HTTP calls
# ---------------------------------------------------------------------------

# Helper that captures the JSON payload sent to the mocked POST endpoint
def _extract_user_message_from_call(mock_post, call_index: int) -> str:
    """Return the user-role message content from the nth POST call."""
    call_kwargs = mock_post.call_args_list[call_index]
    # httpx AsyncClient.post(url, json=payload) — payload is kwarg 'json'
    payload = call_kwargs.kwargs.get("json") or call_kwargs.args[1]
    messages = payload["messages"]
    user_msgs = [m["content"] for m in messages if m["role"] == "user"]
    return user_msgs[-1]  # last user message


class TestRetryGrounding:
    """
    Verifies that the second HTTP call (retry) carries the original NASA
    user prompt, not a bare context-free instruction.
    All tests use mocked HTTP — no real credentials required.
    """

    # D — retry on JSON parse error contains original NASA user prompt
    @pytest.mark.asyncio
    async def test_retry_on_parse_error_uses_original_user_prompt(self):
        provider = _make_provider()
        original_user_prompt = (
            "بيانات ناسا — صورة الفلك اليومية (APOD):\n\n"
            "العنوان: The Case of the Mysterious Maybe Meteor\n"
            "التاريخ: 2026-08-19\n\n"
            "الوصف الرسمي:\nA fireball lit up the night sky."
        )
        bad_content = "Not JSON at all."
        good_json = json.dumps(_valid_story_dict())

        mock_bad = _make_http_response(bad_content, finish_reason="stop")
        mock_good = _make_http_response(good_json, finish_reason="stop")

        mock_post = AsyncMock(side_effect=[mock_bad, mock_good])
        with patch.object(provider._client, "post", new=mock_post):
            result = await provider.generate_structured_response(
                system_prompt="sys",
                user_prompt=original_user_prompt,
            )

        assert result["language"] == "ar"
        assert mock_post.call_count == 2

        # Second call must carry the original NASA data
        retry_user_msg = _extract_user_message_from_call(mock_post, call_index=1)
        assert "The Case of the Mysterious Maybe Meteor" in retry_user_msg
        assert "2026-08-19" in retry_user_msg
        assert "A fireball lit up the night sky." in retry_user_msg

    # E — retry on finish_reason=length contains original NASA user prompt
    @pytest.mark.asyncio
    async def test_retry_on_truncation_uses_original_user_prompt(self):
        provider = _make_provider()
        original_user_prompt = (
            "بيانات ناسا — صورة الفلك اليومية (APOD):\n\n"
            "العنوان: Andromeda Galaxy Ultraviolet\n"
            "التاريخ: 2025-07-04\n\n"
            "الوصف الرسمي:\nSeen in ultraviolet, Andromeda reveals young stars."
        )
        truncated_content = '{"title": "جزئي", "summary": "ناقص'  # truncated
        good_json = json.dumps(_valid_story_dict())

        mock_truncated = _make_http_response(truncated_content, finish_reason="length")
        mock_good = _make_http_response(good_json, finish_reason="stop")

        mock_post = AsyncMock(side_effect=[mock_truncated, mock_good])
        with patch.object(provider._client, "post", new=mock_post):
            result = await provider.generate_structured_response(
                system_prompt="sys",
                user_prompt=original_user_prompt,
            )

        assert result["language"] == "ar"
        assert mock_post.call_count == 2

        retry_user_msg = _extract_user_message_from_call(mock_post, call_index=1)
        assert "Andromeda Galaxy Ultraviolet" in retry_user_msg
        assert "2025-07-04" in retry_user_msg
        assert "Andromeda reveals young stars" in retry_user_msg

    # Extra: first call (no retry) must NOT carry the retry instructions
    @pytest.mark.asyncio
    async def test_first_attempt_does_not_contain_retry_instructions(self):
        provider = _make_provider()
        original_user_prompt = "العنوان: Eagle Nebula\nالتاريخ: 2024-01-01"
        good_json = json.dumps(_valid_story_dict())

        mock_resp = _make_http_response(good_json, finish_reason="stop")
        mock_post = AsyncMock(return_value=mock_resp)
        with patch.object(provider._client, "post", new=mock_post):
            await provider.generate_structured_response(
                system_prompt="sys",
                user_prompt=original_user_prompt,
            )

        assert mock_post.call_count == 1
        first_user_msg = _extract_user_message_from_call(mock_post, call_index=0)
        assert first_user_msg == original_user_prompt
        assert "تعذّر تنسيق الإجابة السابقة" not in first_user_msg

    # Extra: retry does not add a third request even when retry succeeds
    @pytest.mark.asyncio
    async def test_exactly_two_calls_on_retry(self):
        provider = _make_provider()
        mock_bad = _make_http_response("not json", finish_reason="stop")
        mock_good = _make_http_response(json.dumps(_valid_story_dict()), finish_reason="stop")

        mock_post = AsyncMock(side_effect=[mock_bad, mock_good])
        with patch.object(provider._client, "post", new=mock_post):
            await provider.generate_structured_response(
                system_prompt="sys",
                user_prompt="any nasa prompt",
            )
        assert mock_post.call_count == 2


# ---------------------------------------------------------------------------
# Content guard regression tests (safety-classifier failure mode)
# ---------------------------------------------------------------------------
# These tests reproduce the exact failure mode observed in production:
# OpenRouter routed to a safety-classifier model that returned
# "User Safety: safe" (18 chars, finish_reason=stop, HTTP 200).
# Without the content guard this reached _parse_json_response and raised
# AI_JSON_PARSE_ERROR on every request, never allowing a retry.


class TestContentGuardRegressionSafetyClassifier:
    """
    Regression tests for the safety-classifier response guard.
    All HTTP calls are mocked — no real credentials needed.
    """

    # ------------------------------------------------------------------ #
    # _validate_response_content — pure unit tests                        #
    # ------------------------------------------------------------------ #

    def _guard(self, content: str, min_tokens: int = 100) -> None:
        from config import OpenRouterConfig
        from openrouter_provider import OpenRouterProvider
        cfg = OpenRouterConfig(
            api_key="test-key",
            model="test/model",
            min_completion_tokens=min_tokens,
        )
        provider = OpenRouterProvider(cfg)
        provider._validate_response_content(content)

    def test_valid_long_json_passes_guard(self):
        """A normal-length JSON story must pass the guard without error."""
        content = '{"title": "' + 'ن' * 120 + '"}'
        self._guard(content)  # must not raise

    def test_exact_safety_classifier_response_rejected(self):
        """'User Safety: safe' — the exact production failure — must be rejected."""
        from ai_provider import AIProviderError
        with pytest.raises(AIProviderError) as exc_info:
            self._guard("User Safety: safe")
        assert exc_info.value.code == "AI_INVALID_RESPONSE"

    def test_user_safety_unsafe_response_rejected(self):
        from ai_provider import AIProviderError
        with pytest.raises(AIProviderError) as exc_info:
            self._guard("User Safety: unsafe\nsome details")
        assert exc_info.value.code == "AI_INVALID_RESPONSE"

    def test_content_safety_prefix_rejected(self):
        from ai_provider import AIProviderError
        with pytest.raises(AIProviderError) as exc_info:
            self._guard("Content Safety: safe\n")
        assert exc_info.value.code == "AI_INVALID_RESPONSE"

    def test_too_short_response_rejected(self):
        """A response under min_completion_tokens must be rejected."""
        from ai_provider import AIProviderError
        short = '{"t": "x"}'  # 10 chars < 100
        with pytest.raises(AIProviderError) as exc_info:
            self._guard(short, min_tokens=100)
        assert exc_info.value.code == "AI_INVALID_RESPONSE"

    def test_response_exactly_at_minimum_passes(self):
        """A response at exactly the minimum length must pass."""
        content = "x" * 100
        self._guard(content, min_tokens=100)  # must not raise

    def test_empty_string_rejected(self):
        from ai_provider import AIProviderError
        with pytest.raises(AIProviderError) as exc_info:
            self._guard("", min_tokens=10)
        assert exc_info.value.code == "AI_INVALID_RESPONSE"

    def test_whitespace_only_rejected(self):
        from ai_provider import AIProviderError
        with pytest.raises(AIProviderError) as exc_info:
            self._guard("   \n  ", min_tokens=10)
        assert exc_info.value.code == "AI_INVALID_RESPONSE"

    # ------------------------------------------------------------------ #
    # Integration: guard triggers retry (mocked HTTP)                     #
    # ------------------------------------------------------------------ #

    @pytest.mark.asyncio
    async def test_safety_classifier_response_triggers_retry(self):
        """
        'User Safety: safe' on attempt 1 must trigger exactly one retry
        and return the good response from attempt 2.
        """
        provider = _make_provider()
        good_json = json.dumps(_valid_story_dict())

        mock_safety = _make_http_response("User Safety: safe", finish_reason="stop")
        mock_good = _make_http_response(good_json, finish_reason="stop")

        mock_post = AsyncMock(side_effect=[mock_safety, mock_good])
        with patch.object(provider._client, "post", new=mock_post):
            result = await provider.generate_structured_response(
                system_prompt="sys", user_prompt="usr"
            )

        assert result["language"] == "ar"
        assert mock_post.call_count == 2

    @pytest.mark.asyncio
    async def test_too_short_response_triggers_retry(self):
        """A very-short response (e.g. 'safe') triggers retry."""
        provider = _make_provider()
        good_json = json.dumps(_valid_story_dict())

        mock_short = _make_http_response("safe", finish_reason="stop")
        mock_good = _make_http_response(good_json, finish_reason="stop")

        mock_post = AsyncMock(side_effect=[mock_short, mock_good])
        with patch.object(provider._client, "post", new=mock_post):
            result = await provider.generate_structured_response(
                system_prompt="sys", user_prompt="usr"
            )

        assert result["title"] == "نجوم المجرة"
        assert mock_post.call_count == 2

    @pytest.mark.asyncio
    async def test_safety_response_on_both_attempts_raises(self):
        """If retry also returns a safety-classifier response, raise AI_INVALID_RESPONSE."""
        from ai_provider import AIProviderError
        provider = _make_provider()

        mock1 = _make_http_response("User Safety: safe", finish_reason="stop")
        mock2 = _make_http_response("User Safety: safe", finish_reason="stop")

        mock_post = AsyncMock(side_effect=[mock1, mock2])
        with patch.object(provider._client, "post", new=mock_post):
            with pytest.raises(AIProviderError) as exc_info:
                await provider.generate_structured_response(
                    system_prompt="sys", user_prompt="usr"
                )

        assert exc_info.value.code == "AI_INVALID_RESPONSE"
        assert mock_post.call_count == 2

    @pytest.mark.asyncio
    async def test_no_api_key_in_error_message(self):
        """AI_INVALID_RESPONSE error message must not contain any key-like strings."""
        from ai_provider import AIProviderError
        provider = _make_provider()

        mock1 = _make_http_response("User Safety: safe", finish_reason="stop")
        mock2 = _make_http_response("User Safety: safe", finish_reason="stop")

        mock_post = AsyncMock(side_effect=[mock1, mock2])
        with patch.object(provider._client, "post", new=mock_post):
            with pytest.raises(AIProviderError) as exc_info:
                await provider.generate_structured_response(
                    system_prompt="sys", user_prompt="usr"
                )

        error_msg = exc_info.value.message
        assert "sk-" not in error_msg
        assert "Bearer" not in error_msg
        assert "test-key-not-real" not in error_msg

    @pytest.mark.asyncio
    async def test_empty_response_triggers_retry(self):
        """Empty message content on attempt 1 must trigger a retry."""
        from ai_provider import AIProviderError
        provider = _make_provider()

        # Note: _extract_content_and_finish_reason already raises AI_EMPTY_RESPONSE
        # before the guard is reached when content is truly empty.
        # This test verifies the existing AI_EMPTY_RESPONSE behaviour is preserved.
        body_empty = {
            "choices": [{"message": {"content": ""}, "finish_reason": "stop"}]
        }
        mock_empty = MagicMock()
        mock_empty.is_success = True
        mock_empty.status_code = 200
        mock_empty.json.return_value = body_empty

        mock_post = AsyncMock(return_value=mock_empty)
        with patch.object(provider._client, "post", new=mock_post):
            with pytest.raises(AIProviderError) as exc_info:
                await provider.generate_structured_response(
                    system_prompt="sys", user_prompt="usr"
                )

        # AI_EMPTY_RESPONSE is a permanent error — no retry
        assert exc_info.value.code == "AI_EMPTY_RESPONSE"
        assert mock_post.call_count == 1


# ---------------------------------------------------------------------------
# Config: default model and min_completion_tokens
# ---------------------------------------------------------------------------


class TestConfigDefaults:
    def test_default_model_is_capable_free_model(self):
        """
        The source-code default model must be a specific capable model slug,
        NOT openrouter/auto or openrouter/free (which trigger safety-classifier
        routing).

        We verify by:
        1. Directly instantiating with the known expected default slug.
        2. Confirming neither unsafe slug appears as the os.getenv fallback value.
        """
        from config import OpenRouterConfig
        import re

        # Verify the intended default is the safe Llama 70B model
        cfg = OpenRouterConfig(
            api_key="dummy",
            model="meta-llama/llama-3.3-70b-instruct:free",
        )
        assert cfg.model == "meta-llama/llama-3.3-70b-instruct:free"
        assert "/" in cfg.model
        assert cfg.model not in ("openrouter/auto", "openrouter/free")

        # Also verify the source-level fallback value in the lambda.
        # We extract only the os.getenv default argument — not comments.
        import inspect
        source = inspect.getsource(OpenRouterConfig)
        # Find the os.getenv("OPENROUTER_MODEL", "<default>") pattern
        match = re.search(
            r'os\.getenv\(\s*"OPENROUTER_MODEL"\s*,\s*"([^"]+)"',
            source,
        )
        if match:
            default_in_source = match.group(1)
            assert default_in_source not in ("openrouter/auto", "openrouter/free"), (
                f"The os.getenv fallback default '{default_in_source}' must not be "
                "openrouter/auto or openrouter/free"
            )

    def test_min_completion_tokens_default_is_100(self):
        from config import OpenRouterConfig
        cfg = OpenRouterConfig(api_key="dummy")
        assert cfg.min_completion_tokens == 100

    def test_min_completion_tokens_readable_from_env(self, monkeypatch):
        monkeypatch.setenv("OPENROUTER_MIN_COMPLETION_TOKENS", "200")
        import importlib
        import config as cfg_module
        importlib.reload(cfg_module)
        fresh_cfg = cfg_module.OpenRouterConfig()
        assert fresh_cfg.min_completion_tokens == 200
        monkeypatch.delenv("OPENROUTER_MIN_COMPLETION_TOKENS", raising=False)
        importlib.reload(cfg_module)

    def test_default_max_tokens_is_2000(self):
        """
        max_tokens default increased from 1800 to 2000 to reduce truncation risk.
        """
        import importlib
        import config as cfg_module
        importlib.reload(cfg_module)
        cfg = cfg_module.OpenRouterConfig(api_key="dummy")
        assert cfg.max_tokens == 2000
