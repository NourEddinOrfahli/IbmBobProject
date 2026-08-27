"""
Unit tests for OpenRouterProvider fallback model logic.

These tests verify that generate_structured_response():
  1. Returns a result from the primary model on success.
  2. Automatically retries with the fallback model when the primary returns
     AI_RATE_LIMIT or AI_SERVICE_UNAVAILABLE.
  3. Does NOT retry on permanent errors (AI_UNAUTHORIZED, AI_PAYMENT_REQUIRED,
     AI_NETWORK_ERROR, AI_TIMEOUT, MISSING_API_KEY).
  4. Propagates the fallback model's error when the fallback also fails.
  5. Does NOT fall back when no fallback_model is configured (None).

All tests are fully unit-level — no network calls are made.
"""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Any

import sys
import os

# conftest.py already inserts backend/ into sys.path; this guard keeps
# the file importable when run directly as well.
_backend = os.path.join(os.path.dirname(__file__), "..", "backend")
if os.path.abspath(_backend) not in sys.path:
    sys.path.insert(0, os.path.abspath(_backend))

from ai_provider import AIProviderError
from config import OpenRouterConfig
from openrouter_provider import OpenRouterProvider


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_GOOD_JSON = '{"title": "Test", "summary": "OK"}'
_GOOD_PARSED: dict[str, Any] = {"title": "Test", "summary": "OK"}


def _make_provider(
    primary: str = "primary-model",
    fallback: str | None = "fallback-model",
) -> OpenRouterProvider:
    """Build an OpenRouterProvider with a fake API key and controlled models.

    min_completion_tokens is set to 1 so the content guard never blocks
    the test's short JSON fixture — we're testing fallback routing, not
    the content-length guard (which has its own dedicated tests).
    """
    cfg = OpenRouterConfig(
        api_key="test-key",
        model=primary,
        fallback_model=fallback,  # type: ignore[call-arg]
        min_completion_tokens=1,
    )
    return OpenRouterProvider(cfg)


def _good_call_result() -> tuple[str, str]:
    """Return value from a successful _call_completions call."""
    return (_GOOD_JSON, "stop")


def _rate_limit_error() -> AIProviderError:
    return AIProviderError("AI_RATE_LIMIT", "Rate limited by primary model.")


def _unavailable_error() -> AIProviderError:
    return AIProviderError("AI_SERVICE_UNAVAILABLE", "Primary model unavailable.")


def _auth_error() -> AIProviderError:
    return AIProviderError("AI_UNAUTHORIZED", "Bad API key.")


def _payment_error() -> AIProviderError:
    return AIProviderError("AI_PAYMENT_REQUIRED", "No credits.")


def _network_error() -> AIProviderError:
    return AIProviderError("AI_NETWORK_ERROR", "Cannot reach OpenRouter.")


def _timeout_error() -> AIProviderError:
    return AIProviderError("AI_TIMEOUT", "Request timed out.")


# ---------------------------------------------------------------------------
# 1. Primary model succeeds
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_primary_success_no_fallback_called():
    """When the primary model works, the fallback is never called."""
    provider = _make_provider()
    with patch.object(
        provider,
        "_call_completions",
        new_callable=AsyncMock,
        return_value=_good_call_result(),
    ) as mock_call:
        result = await provider.generate_structured_response(
            system_prompt="sys",
            user_prompt="user",
        )

    assert result == _GOOD_PARSED
    # _call_completions was called exactly once with the primary model
    assert mock_call.call_count == 1
    _, kwargs = mock_call.call_args
    assert kwargs["model"] == "primary-model"


# ---------------------------------------------------------------------------
# 2. Fallback triggered on AI_RATE_LIMIT
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_fallback_triggered_on_rate_limit():
    """AI_RATE_LIMIT on primary causes a single retry with the fallback model."""
    provider = _make_provider()

    call_results = [
        _rate_limit_error(),   # primary raises
        _good_call_result(),   # fallback succeeds
    ]

    async def side_effect(*args, **kwargs):
        value = call_results.pop(0)
        if isinstance(value, AIProviderError):
            raise value
        return value

    with patch.object(provider, "_call_completions", side_effect=side_effect) as mock_call:
        result = await provider.generate_structured_response(
            system_prompt="sys",
            user_prompt="user",
        )

    assert result == _GOOD_PARSED
    assert mock_call.call_count == 2
    # First call: primary model
    assert mock_call.call_args_list[0][1]["model"] == "primary-model"
    # Second call: fallback model
    assert mock_call.call_args_list[1][1]["model"] == "fallback-model"


# ---------------------------------------------------------------------------
# 3. Fallback triggered on AI_SERVICE_UNAVAILABLE
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_fallback_triggered_on_service_unavailable():
    """AI_SERVICE_UNAVAILABLE on primary triggers fallback just like rate-limit."""
    provider = _make_provider()

    call_results = [
        _unavailable_error(),
        _good_call_result(),
    ]

    async def side_effect(*args, **kwargs):
        value = call_results.pop(0)
        if isinstance(value, AIProviderError):
            raise value
        return value

    with patch.object(provider, "_call_completions", side_effect=side_effect) as mock_call:
        result = await provider.generate_structured_response("sys", "user")

    assert result == _GOOD_PARSED
    assert mock_call.call_count == 2


# ---------------------------------------------------------------------------
# 4. Permanent errors propagate immediately — no fallback
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("error_fn", [
    _auth_error,
    _payment_error,
    _network_error,
    _timeout_error,
])
@pytest.mark.asyncio
async def test_permanent_errors_propagate_without_fallback(error_fn):
    """Errors other than rate-limit/unavailable are re-raised immediately."""
    provider = _make_provider()

    async def side_effect(*args, **kwargs):
        raise error_fn()

    with patch.object(provider, "_call_completions", side_effect=side_effect) as mock_call:
        with pytest.raises(AIProviderError) as exc_info:
            await provider.generate_structured_response("sys", "user")

    # Only the primary was attempted
    assert mock_call.call_count == 1
    assert exc_info.value.code == error_fn().code


# ---------------------------------------------------------------------------
# 5. Fallback model also fails — propagates fallback error
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_fallback_failure_propagates():
    """When both primary and fallback fail, the fallback's error is raised."""
    provider = _make_provider()

    call_results = [
        _rate_limit_error(),
        AIProviderError("AI_SERVICE_UNAVAILABLE", "Fallback also down."),
    ]

    async def side_effect(*args, **kwargs):
        value = call_results.pop(0)
        if isinstance(value, AIProviderError):
            raise value
        return value

    with patch.object(provider, "_call_completions", side_effect=side_effect) as mock_call:
        with pytest.raises(AIProviderError) as exc_info:
            await provider.generate_structured_response("sys", "user")

    assert mock_call.call_count == 2
    assert exc_info.value.code == "AI_SERVICE_UNAVAILABLE"


# ---------------------------------------------------------------------------
# 6. No fallback configured — rate-limit propagates immediately
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_no_fallback_configured_propagates_rate_limit():
    """When fallback_model is None, rate-limit from primary raises immediately."""
    provider = _make_provider(fallback=None)

    async def side_effect(*args, **kwargs):
        raise _rate_limit_error()

    with patch.object(provider, "_call_completions", side_effect=side_effect) as mock_call:
        with pytest.raises(AIProviderError) as exc_info:
            await provider.generate_structured_response("sys", "user")

    assert mock_call.call_count == 1
    assert exc_info.value.code == "AI_RATE_LIMIT"
