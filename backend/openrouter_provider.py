"""
OpenRouter AI provider implementation.

Implements the AIProvider interface using OpenRouter's OpenAI-compatible API.
The application never needs to know this provider exists; it only uses AIProvider.

Future providers (IBM Granite, Hugging Face, Gemini, …) simply implement the
same AIProvider interface and can be swapped in via dependency injection.

Changes vs. initial version:
- Logs finish_reason on every response (truncation diagnostic)
- Raises AI_TRUNCATED error with clear message when finish_reason == "length"
- Performs ONE retry with a shorter prompt on JSON parse failure
- Raises immediately on permanent errors (auth, rate limit) without retry
- Guards against safety-classifier/status-only responses before JSON parsing
  (e.g. "User Safety: safe" from content-moderation models that OpenRouter
  may route to when using openrouter/auto or openrouter/free)
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

import httpx

from ai_provider import AIProvider, AIProviderError
from config import OpenRouterConfig
from prompts import build_retry_user_prompt, RETRY_SYSTEM_PROMPT

# Vision-capable model to use for image analysis.
# Uses a free, multimodal-capable model on OpenRouter.
# Can be overridden via OPENROUTER_VISION_MODEL env var.
_VISION_MODEL = "nvidia/nemotron-nano-12b-v2-vl:free"

logger = logging.getLogger(__name__)

# Error codes that must NOT trigger a retry (permanent failures)
_PERMANENT_ERROR_CODES = frozenset({
    "AI_UNAUTHORIZED",
    "AI_PAYMENT_REQUIRED",
    "AI_RATE_LIMIT",
    "AI_SERVICE_UNAVAILABLE",
    "AI_API_ERROR",
    "AI_NETWORK_ERROR",
    "AI_TIMEOUT",
    "MISSING_API_KEY",
    # AI_INVALID_RESPONSE on retry means even the second model returned a
    # classifier/status response — raise immediately, no third attempt.
    "AI_INVALID_RESPONSE",
})


class OpenRouterProvider(AIProvider):
    """
    Concrete AIProvider backed by OpenRouter.

    Uses OpenRouter's OpenAI-compatible chat completions endpoint so that
    migration to a different provider requires only implementing the
    AIProvider interface in a new class.
    """

    _COMPLETIONS_PATH = "/chat/completions"

    def __init__(self, config: OpenRouterConfig) -> None:
        if not config.api_key:
            raise AIProviderError(
                "MISSING_API_KEY",
                "OPENROUTER_API_KEY is not set. Cannot initialise OpenRouterProvider.",
            )
        self._config = config
        self._min_completion_tokens: int = getattr(config, "min_completion_tokens", 100)
        self._client = httpx.AsyncClient(
            base_url=config.base_url,
            timeout=config.request_timeout,
            headers={
                "Authorization": f"Bearer {config.api_key}",
                "Content-Type": "application/json",
                # OpenRouter recommends these headers for routing/monitoring
                "HTTP-Referer": "https://github.com/space-interpreter",
                "X-Title": "Space Interpreter",
            },
        )
        logger.info(
            "OpenRouterProvider initialised (model=%s, base_url=%s, max_tokens=%d)",
            config.model,
            config.base_url,
            config.max_tokens,
        )

    # ------------------------------------------------------------------
    # AIProvider interface
    # ------------------------------------------------------------------

    async def generate_structured_response(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        max_tokens: int = 1800,
        temperature: float = 0.4,
    ) -> dict[str, Any]:
        """
        Send a chat-completion request to OpenRouter and return parsed JSON.

        - Logs finish_reason for every response (helps diagnose truncation).
        - If finish_reason == "length", raises AI_TRUNCATED immediately.
        - On JSON parse failure, performs ONE retry with a shorter prompt.
        - Never retries on permanent HTTP errors (auth, rate limit, etc.).
        """
        # First attempt
        try:
            raw_content, finish_reason = await self._call_completions(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                max_tokens=max_tokens,
                temperature=temperature,
            )
        except AIProviderError:
            raise  # permanent errors propagate immediately

        # Log finish_reason — critical for truncation diagnosis
        self._log_finish_reason(finish_reason, attempt=1)

        if finish_reason == "length":
            logger.warning(
                "finish_reason=length on attempt 1 — response was truncated by token limit. "
                "Attempting retry with a shorter prompt."
            )
            return await self._retry_with_shorter_prompt(
                original_user_prompt=user_prompt,
                max_tokens=max_tokens,
                temperature=temperature,
            )

        # Guard: reject safety-classifier / status-only / very-short responses
        # before attempting JSON parsing.  These arise when OpenRouter routes
        # to a content-moderation model instead of a generative model.
        try:
            self._validate_response_content(raw_content)
        except AIProviderError as guard_exc:
            logger.warning(
                "Response failed content guard on attempt 1 (code=%s): %s — "
                "performing single retry.",
                guard_exc.code,
                guard_exc.message,
            )
            return await self._retry_with_shorter_prompt(
                original_user_prompt=user_prompt,
                max_tokens=max_tokens,
                temperature=temperature,
            )

        # Try to parse first-attempt content
        try:
            return self._parse_json_response(raw_content)
        except AIProviderError as parse_exc:
            if parse_exc.code not in ("AI_JSON_PARSE_ERROR", "AI_UNEXPECTED_TYPE"):
                raise
            logger.warning(
                "JSON parse failed on attempt 1 (code=%s). Performing single retry.",
                parse_exc.code,
            )
            return await self._retry_with_shorter_prompt(
                original_user_prompt=user_prompt,
                max_tokens=max_tokens,
                temperature=temperature,
            )

    async def analyze_image(
        self,
        image_b64: str,
        image_mime: str,
        system_prompt: str,
        user_prompt: str,
        *,
        max_tokens: int = 1500,
        temperature: float = 0.4,
    ) -> dict[str, Any]:
        """
        Send a multimodal request (image + text) to a vision-capable model.

        Uses a dedicated vision model configured via _VISION_MODEL.
        The image is embedded as a base64 data-URI in the OpenAI vision format.
        """
        import os
        vision_model = os.getenv("OPENROUTER_VISION_MODEL", _VISION_MODEL)

        # Build multimodal user message per OpenAI vision spec
        multimodal_content: list[dict[str, Any]] = [
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:{image_mime};base64,{image_b64}",
                },
            },
            {
                "type": "text",
                "text": user_prompt,
            },
        ]

        payload: dict[str, Any] = {
            "model": vision_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": multimodal_content},
            ],
            "max_tokens": max_tokens,
            "temperature": temperature,
            "response_format": {"type": "json_object"},
        }

        logger.debug(
            "POST %s vision request (model=%s, max_tokens=%d)",
            self._COMPLETIONS_PATH,
            vision_model,
            max_tokens,
        )

        try:
            response = await self._client.post(self._COMPLETIONS_PATH, json=payload)
        except httpx.TimeoutException:
            raise AIProviderError(
                "AI_TIMEOUT",
                f"Vision request timed out after {self._config.request_timeout}s.",
            )
        except httpx.RequestError as exc:
            raise AIProviderError(
                "AI_NETWORK_ERROR",
                f"Network error reaching OpenRouter (vision): {exc}",
            )

        self._check_response_status(response)
        self._log_response_usage(response)

        content, finish_reason = self._extract_content_and_finish_reason(response)
        self._log_finish_reason(finish_reason, attempt=1)

        if finish_reason == "length":
            raise AIProviderError(
                "AI_TRUNCATED",
                "Vision model response was truncated (finish_reason=length). "
                "The image analysis could not be completed.",
            )

        self._validate_response_content(content)
        return self._parse_json_response(content)

    async def chat_completion(
        self,
        messages: list[dict[str, str]],
        *,
        max_tokens: int = 600,
        temperature: float = 0.5,
    ) -> str:
        """
        Send a multi-turn conversation to OpenRouter and return the assistant's
        plain-text reply.

        Uses the same model as configured for story generation.
        No JSON parsing — returns raw text.
        """
        payload: dict[str, Any] = {
            "model": self._config.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        logger.debug(
            "POST %s chat (model=%s, turns=%d)",
            self._COMPLETIONS_PATH,
            self._config.model,
            len(messages),
        )

        try:
            response = await self._client.post(self._COMPLETIONS_PATH, json=payload)
        except httpx.TimeoutException:
            raise AIProviderError(
                "AI_TIMEOUT",
                f"Chat request timed out after {self._config.request_timeout}s.",
            )
        except httpx.RequestError as exc:
            raise AIProviderError(
                "AI_NETWORK_ERROR",
                f"Network error reaching OpenRouter (chat): {exc}",
            )

        self._check_response_status(response)
        self._log_response_usage(response)

        content, finish_reason = self._extract_content_and_finish_reason(response)
        self._log_finish_reason(finish_reason, attempt=1)

        return content

    async def close(self) -> None:
        """Release the underlying HTTP client."""
        await self._client.aclose()

    # ------------------------------------------------------------------
    # Private — retry
    # ------------------------------------------------------------------

    async def _retry_with_shorter_prompt(
        self,
        original_user_prompt: str,
        max_tokens: int,
        temperature: float,
    ) -> dict[str, Any]:
        """
        Single retry that re-embeds the original NASA user prompt so the model
        remains grounded in the same APOD data as the first attempt.

        The retry sends:
          system  — RETRY_SYSTEM_PROMPT (format rules only)
          user    — original NASA prompt + concise retry instructions

        No conversation history is used (stateless).
        On any failure here, raises without further retries.
        """
        retry_user = build_retry_user_prompt(original_user_prompt)

        try:
            raw_content, finish_reason = await self._call_completions(
                system_prompt=RETRY_SYSTEM_PROMPT,
                user_prompt=retry_user,
                max_tokens=max_tokens,
                temperature=temperature,
            )
        except AIProviderError:
            raise  # propagate as-is

        self._log_finish_reason(finish_reason, attempt=2)

        if finish_reason == "length":
            raise AIProviderError(
                "AI_TRUNCATED",
                "OpenRouter response was truncated (finish_reason=length) even on retry. "
                "Try increasing OPENROUTER_MAX_TOKENS or switching to a model with "
                "a larger context window.",
            )

        # Apply the same content guard on retry — no silent pass-through
        self._validate_response_content(raw_content)

        return self._parse_json_response(raw_content)

    # ------------------------------------------------------------------
    # Private — HTTP call
    # ------------------------------------------------------------------

    async def _call_completions(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int,
        temperature: float,
    ) -> tuple[str, str | None]:
        """
        POST to /chat/completions and return (content_string, finish_reason).

        finish_reason may be None if the response envelope omits it.
        Raises AIProviderError on all HTTP / parsing failures.
        """
        payload: dict[str, Any] = {
            "model": self._config.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "max_tokens": max_tokens,
            "temperature": temperature,
            "response_format": {"type": "json_object"},
        }

        logger.debug(
            "POST %s (model=%s, max_tokens=%d)",
            self._COMPLETIONS_PATH,
            self._config.model,
            max_tokens,
        )

        try:
            response = await self._client.post(self._COMPLETIONS_PATH, json=payload)
        except httpx.TimeoutException:
            raise AIProviderError(
                "AI_TIMEOUT",
                f"OpenRouter request timed out after {self._config.request_timeout}s.",
            )
        except httpx.RequestError as exc:
            raise AIProviderError(
                "AI_NETWORK_ERROR",
                f"Network error reaching OpenRouter: {exc}",
            )

        self._check_response_status(response)

        # Log safe diagnostic metadata — never logs keys or prompt content
        self._log_response_usage(response)

        content, finish_reason = self._extract_content_and_finish_reason(response)
        return content, finish_reason

    # ------------------------------------------------------------------
    # Private — response parsing
    # ------------------------------------------------------------------

    @staticmethod
    def _check_response_status(response: httpx.Response) -> None:
        """Raise AIProviderError for non-2xx status codes."""
        if response.status_code == 401:
            raise AIProviderError(
                "AI_UNAUTHORIZED",
                "OpenRouter rejected the API key. Check OPENROUTER_API_KEY.",
            )
        if response.status_code == 402:
            raise AIProviderError(
                "AI_PAYMENT_REQUIRED",
                "OpenRouter requires payment or credits for the requested model.",
            )
        if response.status_code == 429:
            raise AIProviderError(
                "AI_RATE_LIMIT",
                "OpenRouter rate limit exceeded. Try again later.",
            )
        if response.status_code == 503:
            raise AIProviderError(
                "AI_SERVICE_UNAVAILABLE",
                "OpenRouter is temporarily unavailable. Try again later.",
            )
        if not response.is_success:
            try:
                detail = response.json()
            except Exception:  # noqa: BLE001
                detail = response.text[:300]
            raise AIProviderError(
                "AI_API_ERROR",
                f"OpenRouter returned HTTP {response.status_code}: {detail}",
            )

    @staticmethod
    def _extract_content_and_finish_reason(
        response: httpx.Response,
    ) -> tuple[str, str | None]:
        """
        Parse the OpenAI-compatible response envelope.

        Returns (content_string, finish_reason).
        finish_reason is None if absent from the response.
        Never logs auth headers or secrets.
        """
        try:
            body = response.json()
        except Exception:  # noqa: BLE001
            raise AIProviderError(
                "AI_INVALID_JSON",
                "OpenRouter returned a non-JSON response body.",
            )

        try:
            choice = body["choices"][0]
            content = choice["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise AIProviderError(
                "AI_UNEXPECTED_SHAPE",
                f"Could not extract content from OpenRouter response: {exc}. "
                f"Body snippet: {str(body)[:300]}",
            )

        if not content or not content.strip():
            raise AIProviderError(
                "AI_EMPTY_RESPONSE",
                "OpenRouter returned an empty message content.",
            )

        # finish_reason is optional; log it safely
        finish_reason: str | None = choice.get("finish_reason")

        return content, finish_reason

    @staticmethod
    def _log_response_usage(response: httpx.Response) -> None:
        """
        Log safe diagnostic metadata from the OpenRouter response envelope.

        Extracts and logs:
          - model (which underlying model was actually used)
          - finish_reason
          - prompt_tokens / completion_tokens / total_tokens

        Never logs: API keys, Authorization headers, prompt content,
        full model output, or any personal data.
        If any field is absent, logs None rather than raising.
        """
        try:
            body = response.json()
        except Exception:  # noqa: BLE001
            logger.debug("Could not parse response body for usage logging")
            return

        model: str | None = body.get("model")

        finish_reason: str | None = None
        try:
            finish_reason = body["choices"][0].get("finish_reason")
        except (KeyError, IndexError, TypeError):
            pass

        usage: dict = body.get("usage") or {}
        prompt_tokens: int | None = usage.get("prompt_tokens")
        completion_tokens: int | None = usage.get("completion_tokens")
        total_tokens: int | None = usage.get("total_tokens")

        logger.info(
            "OpenRouter usage: model=%s, finish_reason=%s, "
            "prompt_tokens=%s, completion_tokens=%s, total_tokens=%s",
            model,
            finish_reason,
            prompt_tokens,
            completion_tokens,
            total_tokens,
        )

    def _validate_response_content(self, content: str) -> None:
        """
        Guard against non-story responses before JSON parsing is attempted.

        Raises AI_INVALID_RESPONSE when the content is clearly not a JSON story:

        1. Fewer than min_completion_tokens characters — safety classifiers,
           status models, and echo-only models produce tiny responses (e.g.
           "User Safety: safe" is 18 chars).  A minimum Arabic JSON story is
           always several hundred characters.

        2. Known safety-classifier patterns — exact-match on a small set of
           known non-story response prefixes from content-moderation models.
           This list must never grow into a denylist of legitimate content.

        This guard does NOT examine or log the full content of the response
        (to avoid leaking any sensitive user or model data into logs).
        It only checks length and a narrow set of known classifier prefixes.
        """
        stripped = content.strip()

        # Check 1 — minimum length (100 chars covers "User Safety: safe" and similar)
        if len(stripped) < self._min_completion_tokens:
            logger.warning(
                "Response rejected by content guard: too short (%d chars, minimum %d). "
                "This is likely a safety-classifier or status-only model response.",
                len(stripped),
                self._min_completion_tokens,
            )
            raise AIProviderError(
                "AI_INVALID_RESPONSE",
                f"Response is too short to be a valid story "
                f"({len(stripped)} chars, minimum {self._min_completion_tokens}). "
                "OpenRouter may have routed to a safety-classifier model. "
                "Set OPENROUTER_MODEL to a specific generative model.",
            )

        # Check 2 — known safety-classifier output patterns
        # These are narrow, exact prefix matches — not broad content filtering.
        _SAFETY_PREFIXES = (
            "User Safety:",
            "user safety:",
            "Content Safety:",
            "content safety:",
            "Input Safety:",
            "input safety:",
            "safe\n",
            "unsafe\n",
        )
        lower = stripped.lower()
        for prefix in _SAFETY_PREFIXES:
            if stripped.startswith(prefix) or lower.startswith(prefix.lower()):
                logger.warning(
                    "Response rejected by content guard: matches safety-classifier "
                    "pattern. OpenRouter routed to a non-generative model. "
                    "Set OPENROUTER_MODEL to a specific generative model slug."
                )
                raise AIProviderError(
                    "AI_INVALID_RESPONSE",
                    "OpenRouter returned a safety-classifier response instead of "
                    "a generated story. This happens when using 'openrouter/free' "
                    "or 'openrouter/auto' and the router picks a moderation model. "
                    "Set OPENROUTER_MODEL to a specific generative model.",
                )

    @staticmethod
    def _log_finish_reason(finish_reason: str | None, attempt: int) -> None:
        """Log finish_reason at the appropriate level."""
        if finish_reason is None:
            logger.debug("finish_reason not present in response (attempt %d)", attempt)
        elif finish_reason == "stop":
            logger.info("finish_reason=stop (attempt %d) — normal completion", attempt)
        elif finish_reason == "length":
            logger.warning(
                "finish_reason=length (attempt %d) — response truncated by token limit",
                attempt,
            )
        else:
            logger.info("finish_reason=%s (attempt %d)", finish_reason, attempt)

    @staticmethod
    def _parse_json_response(raw: str) -> dict[str, Any]:
        """
        Robustly parse a JSON string that may be wrapped in markdown fences.

        Handles:
        - Pure JSON
        - ```json ... ``` fences
        - ``` ... ``` fences (without language tag)
        - Leading/trailing whitespace

        Does NOT attempt to repair truncated or broken JSON.
        Raises AIProviderError with a clear code on failure.
        """
        cleaned = raw.strip()

        # Strip markdown code fences if present
        fence_pattern = re.compile(r"^```(?:json)?\s*(.*?)\s*```$", re.DOTALL)
        match = fence_pattern.match(cleaned)
        if match:
            cleaned = match.group(1).strip()

        try:
            result = json.loads(cleaned)
        except json.JSONDecodeError as exc:
            logger.error(
                "JSON parsing failed (first 500 chars of raw): %.500s",
                raw,
            )
            raise AIProviderError(
                "AI_JSON_PARSE_ERROR",
                f"Could not parse AI response as JSON: {exc}. "
                f"Preview: {raw[:200]}",
            )

        if not isinstance(result, dict):
            raise AIProviderError(
                "AI_UNEXPECTED_TYPE",
                f"Expected a JSON object from the AI, got {type(result).__name__}.",
            )

        return result
