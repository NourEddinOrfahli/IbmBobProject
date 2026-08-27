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
# NOTE: this module-level constant is superseded by config.openrouter.vision_model
# (loaded from OPENROUTER_VISION_MODEL env var).  Kept only for reference.
# nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free is verified working for
# structured JSON vision output.  minimax/minimax-m3:free only returns 13-char
# stub JSON for complex prompts.
_VISION_MODEL = "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free"

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

        - Tries the primary model (OPENROUTER_MODEL, default: meta-llama/llama-3.3-70b-instruct:free).
        - On permanent primary failure (rate-limit / unavailable), automatically
          retries with the fallback model (OPENROUTER_FALLBACK_MODEL, default: qwen/qwen-2.5-coder-32b-instruct:free).
        - Logs finish_reason for every response (helps diagnose truncation).
        - If finish_reason == "length", retries with a shorter prompt.
        - On JSON parse failure, performs ONE retry with a shorter prompt.
        - Never retries on auth / API-key errors.
        """
        # Determine which models to try
        primary_model = self._config.model
        fallback_model = getattr(self._config, "fallback_model", None)

        # ── First attempt with primary model ──────────────────────────────
        try:
            raw_content, finish_reason = await self._call_completions(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                model=primary_model,
            )
        except AIProviderError as exc:
            # On rate-limit, service-unavailable, or model-not-found, try the fallback once.
            # AI_MODEL_NOT_FOUND means the primary model slug returned 404 from OpenRouter —
            # switching to the fallback is the correct recovery action.
            if exc.code in ("AI_RATE_LIMIT", "AI_SERVICE_UNAVAILABLE", "AI_MODEL_NOT_FOUND") and fallback_model:
                logger.warning(
                    "Primary model %s failed (%s) — retrying with fallback model %s",
                    primary_model, exc.code, fallback_model,
                )
                try:
                    raw_content, finish_reason = await self._call_completions(
                        system_prompt=system_prompt,
                        user_prompt=user_prompt,
                        max_tokens=max_tokens,
                        temperature=temperature,
                        model=fallback_model,
                    )
                except AIProviderError:
                    raise  # fallback also failed — propagate
            else:
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

        Tries the primary vision model (OPENROUTER_VISION_MODEL).
        On transient failure (rate-limit, 502/503, model-not-found) automatically
        retries once with the fallback vision model (OPENROUTER_VISION_FALLBACK_MODEL)
        if one is configured.

        The image is embedded as a base64 data-URI in the OpenAI vision format.
        """
        primary_model  = self._config.vision_model
        fallback_model = getattr(self._config, "vision_fallback_model", None)
        return await self._vision_with_model(
            model=primary_model,
            image_b64=image_b64,
            image_mime=image_mime,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            fallback_model=fallback_model,
        )

    async def _vision_with_model(
        self,
        model: str,
        image_b64: str,
        image_mime: str,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int,
        temperature: float,
        *,
        fallback_model: str | None,
    ) -> dict[str, Any]:
        """Internal: POST a vision completion for the given model slug."""
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
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": multimodal_content},
            ],
            "max_tokens": max_tokens,
            "temperature": temperature,
            # response_format is intentionally omitted for the vision path:
            # multimodal models on OpenRouter often do not support json_object mode.
            # _parse_json_response() handles markdown-fenced JSON already.
        }

        logger.debug(
            "POST %s vision request (model=%s, max_tokens=%d)",
            self._COMPLETIONS_PATH,
            model,
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

        _VISION_FALLBACK_CODES = ("AI_RATE_LIMIT", "AI_SERVICE_UNAVAILABLE", "AI_MODEL_NOT_FOUND")

        try:
            self._check_response_status(response)
        except AIProviderError as exc:
            if fallback_model and exc.code in _VISION_FALLBACK_CODES:
                logger.warning(
                    "Vision model %s failed (%s) — retrying with fallback model %s",
                    model, exc.code, fallback_model,
                )
                return await self._vision_with_model(
                    model=fallback_model,
                    image_b64=image_b64,
                    image_mime=image_mime,
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    fallback_model=None,  # no further recursion
                )
            raise

        self._log_response_usage(response)

        # _extract_content_and_finish_reason may raise AI_SERVICE_UNAVAILABLE for
        # 200+error bodies (e.g. upstream provider overloaded).  Treat these the
        # same as HTTP-level transient errors — trigger fallback if available.
        try:
            content, finish_reason = self._extract_content_and_finish_reason(response)
        except AIProviderError as exc:
            if fallback_model and exc.code in _VISION_FALLBACK_CODES:
                logger.warning(
                    "Vision model %s returned error body (%s) — retrying with fallback %s",
                    model, exc.code, fallback_model,
                )
                return await self._vision_with_model(
                    model=fallback_model,
                    image_b64=image_b64,
                    image_mime=image_mime,
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    fallback_model=None,
                )
            raise

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
        Safety-classifier prefixes (e.g. "Response Safety: safe\n...") are
        stripped before the text is returned to the caller.

        If the primary model returns 404 (AI_MODEL_NOT_FOUND) or is rate-limited,
        the fallback model is tried once before propagating the error.
        """
        return await self._chat_with_model(
            model=self._config.model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
            allow_fallback=True,
        )

    async def _chat_with_model(
        self,
        model: str,
        messages: list[dict[str, str]],
        max_tokens: int,
        temperature: float,
        *,
        allow_fallback: bool,
    ) -> str:
        """Internal: POST a chat-completion for the given model slug."""
        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        logger.debug(
            "POST %s chat (model=%s, turns=%d)",
            self._COMPLETIONS_PATH,
            model,
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

        try:
            self._check_response_status(response)
        except AIProviderError as exc:
            _FALLBACK_CODES = ("AI_RATE_LIMIT", "AI_SERVICE_UNAVAILABLE", "AI_MODEL_NOT_FOUND")
            fallback_model = getattr(self._config, "fallback_model", None)
            if allow_fallback and exc.code in _FALLBACK_CODES and fallback_model:
                logger.warning(
                    "Chat model %s failed (%s) — retrying with fallback model %s",
                    model, exc.code, fallback_model,
                )
                return await self._chat_with_model(
                    model=fallback_model,
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    allow_fallback=False,  # no further recursion
                )
            raise

        self._log_response_usage(response)

        content, finish_reason = self._extract_content_and_finish_reason(response)
        self._log_finish_reason(finish_reason, attempt=1)

        return self._strip_safety_prefix(content)

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
        *,
        model: str | None = None,
    ) -> tuple[str, str | None]:
        """
        POST to /chat/completions and return (content_string, finish_reason).

        finish_reason may be None if the response envelope omits it.
        Raises AIProviderError on all HTTP / parsing failures.

        Parameters
        ----------
        model:
            Override the model for this specific call (used by fallback logic).
            If None, uses self._config.model.
        """
        active_model = model or self._config.model
        payload: dict[str, Any] = {
            "model": active_model,
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
            active_model,
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
        if response.status_code == 404:
            raise AIProviderError(
                "AI_MODEL_NOT_FOUND",
                "النموذج المطلوب غير متاح على OpenRouter. "
                "يرجى التحقق من إعداد OPENROUTER_MODEL أو OPENROUTER_VISION_MODEL في ملف .env.",
            )
        if response.status_code in (502, 503):
            # 502 = upstream provider overloaded (e.g. NVIDIA backend)
            # 503 = OpenRouter itself temporarily unavailable
            # Both are transient — the fallback model should be tried.
            raise AIProviderError(
                "AI_SERVICE_UNAVAILABLE",
                "خدمة الذكاء الاصطناعي غير متاحة مؤقتاً. جارٍ تجربة النموذج الاحتياطي.",
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

        # OpenRouter sometimes returns HTTP 200 but with an error body
        # (e.g. upstream provider 502 "Service temporarily overloaded").
        # Detect this early so the fallback logic can trigger on it.
        if isinstance(body, dict) and "error" in body and "choices" not in body:
            err = body["error"]
            err_code = err.get("code") if isinstance(err, dict) else None
            err_msg  = err.get("message", str(err)) if isinstance(err, dict) else str(err)
            if err_code in (429, 502, 503):
                # Transient — trigger fallback
                ar_msg = "خدمة الذكاء الاصطناعي غير متاحة مؤقتاً. جارٍ تجربة النموذج الاحتياطي."
                raise AIProviderError("AI_SERVICE_UNAVAILABLE", ar_msg)
            if err_code == 404:
                raise AIProviderError(
                    "AI_MODEL_NOT_FOUND",
                    "النموذج المطلوب غير متاح على OpenRouter. "
                    "يرجى التحقق من إعداد OPENROUTER_MODEL أو OPENROUTER_VISION_MODEL في ملف .env.",
                )
            raise AIProviderError(
                "AI_API_ERROR",
                f"OpenRouter returned an error response: {err_msg[:300]}",
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
    def _strip_safety_prefix(content: str) -> str:
        """
        Remove safety-classifier preamble that some OpenRouter-routed models
        prepend to their actual reply.

        Patterns seen in the wild (all case-insensitive):
          "Safety: safe\\n<actual reply>"
          "Response Safety: safe\\n<actual reply>"
          "User Safety: safe\\n<actual reply>"
          "safe\\n<actual reply>"

        The heuristic: if the content starts with one of the known classifier
        labels (optionally followed by a colon, a value, and a newline), strip
        everything up to and including the first blank line or the first
        non-classifier line, then return the remainder trimmed.

        If no known prefix is found the content is returned unchanged so that
        legitimate short replies are never silently discarded.
        """
        # Quick exit — no colon on the first line means it's not a classifier header
        first_line_end = content.find("\n")
        first_line = content[:first_line_end].strip() if first_line_end != -1 else content.strip()
        if ":" not in first_line and first_line.lower() not in ("safe", "unsafe"):
            return content

        _CLASSIFIER_PREFIXES = (
            "safety:",
            "response safety:",
            "user safety:",
            "content safety:",
            "input safety:",
        )
        lower_first = first_line.lower()
        is_classifier = (
            any(lower_first.startswith(p) for p in _CLASSIFIER_PREFIXES)
            or lower_first in ("safe", "unsafe")
        )
        if not is_classifier:
            return content

        # Strip the classifier header line(s) — consume all leading lines that
        # look like "Key: value" classifier output, then return what follows.
        lines = content.splitlines()
        start_idx = 0
        for i, line in enumerate(lines):
            stripped_line = line.strip().lower()
            if any(stripped_line.startswith(p) for p in _CLASSIFIER_PREFIXES) or stripped_line in ("safe", "unsafe", ""):
                start_idx = i + 1
            else:
                break  # first non-classifier, non-blank line — real content starts here

        remainder = "\n".join(lines[start_idx:]).strip()
        if remainder:
            logger.warning(
                "Stripped safety-classifier prefix from chat response "
                "(first line was: %r). Returning remainder (%d chars).",
                first_line,
                len(remainder),
            )
            return remainder

        # The entire response was classifier output — return original so the
        # caller's error handling can deal with it rather than returning empty.
        logger.warning(
            "Safety-classifier prefix detected but no remainder found — "
            "returning original content (%d chars).",
            len(content),
        )
        return content

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
