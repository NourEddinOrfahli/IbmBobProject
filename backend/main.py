"""
Space Interpreter — FastAPI application entry point.

Endpoints:
  GET  /health                  — liveness probe
  GET  /api/daily-news          — fetch today's APOD and generate an Arabic space story
  GET  /api/daily-news/status   — scheduler and latest bulletin status
  POST /api/analyze             — analyse a specific APOD date or free-text context
  POST /api/analyze-image       — analyse a user-uploaded space image with vision AI
"""

from __future__ import annotations

import base64
import logging
import sys
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Optional

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from bulletin_service import BulletinService
from bulletin_store import BulletinStore
from config import get_config, validate_config
from models import (
    AnalyzeRequest,
    ChatRequest,
    ChatResponse,
    ErrorDetail,
    ErrorResponse,
    HealthResponse,
    ImageAnalysisResult,
    SuccessResponse,
)
from nasa_client import NASAClient
from scheduler import DailyBulletinScheduler
from story_generator import StoryGenerator, StoryGeneratorError
from ai_provider import AIProviderError
from chat_service import ChatService
from prompts import get_vision_system_prompt, build_vision_user_prompt

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration (loaded once at startup)
# ---------------------------------------------------------------------------

config = get_config()

# ---------------------------------------------------------------------------
# Application lifecycle — create / dispose shared resources
# ---------------------------------------------------------------------------

_nasa_client: NASAClient | None = None
_story_generator: StoryGenerator | None = None
_bulletin_service: BulletinService | None = None
_scheduler: DailyBulletinScheduler | None = None
_chat_service: ChatService | None = None


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Initialise shared resources on startup and release them on shutdown."""
    global _nasa_client, _story_generator, _bulletin_service, _scheduler, _chat_service

    logger.info("Space Interpreter starting up…")

    # Warn about configuration issues (missing API keys etc.)
    issues = validate_config(config)
    for issue in issues:
        logger.warning("Configuration warning: %s", issue)

    _nasa_client = NASAClient(config.nasa)

    # Build AI provider only if the key is available.  If not, AI endpoints
    # will return a clear error rather than crashing the whole application.
    if config.openrouter.api_key:
        from openrouter_provider import OpenRouterProvider

        ai_provider = OpenRouterProvider(config.openrouter)
        _story_generator = StoryGenerator(_nasa_client, ai_provider, config)
        _chat_service = ChatService(ai_provider)
        logger.info("AI provider (OpenRouter) initialised successfully.")

        # Set up bulletin store and service
        store = BulletinStore(config.scheduler.store_path)
        _bulletin_service = BulletinService(_story_generator, store)

        # Start scheduler (no-op if DAILY_BULLETIN_ENABLED=false)
        _scheduler = DailyBulletinScheduler(_bulletin_service, config.scheduler)
        _scheduler.start()
    else:
        logger.warning(
            "OPENROUTER_API_KEY is not set. "
            "AI endpoints (/api/daily-news, /api/analyze) will return errors."
        )

    logger.info("Space Interpreter ready.")

    yield  # Application runs here

    # Cleanup
    logger.info("Space Interpreter shutting down…")
    if _scheduler:
        _scheduler.shutdown()
    if _nasa_client:
        await _nasa_client.close()
    if _story_generator and hasattr(_story_generator, "_ai"):
        await _story_generator._ai.close()


# ---------------------------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Space Interpreter",
    description=(
        "AI-powered space data interpretation: "
        "real NASA data → Arabic scientific stories."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Error handling helpers
# ---------------------------------------------------------------------------


def _error_response(code: str, message: str, status_code: int) -> JSONResponse:
    body = ErrorResponse(error=ErrorDetail(code=code, message=message))
    return JSONResponse(content=body.model_dump(), status_code=status_code)


def _require_story_generator() -> StoryGenerator:
    if _story_generator is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "success": False,
                "error": {
                    "code": "AI_NOT_CONFIGURED",
                    "message": (
                        "The AI provider is not configured. "
                        "Set OPENROUTER_API_KEY in your environment and restart."
                    ),
                },
            },
        )
    return _story_generator


# ---------------------------------------------------------------------------
# Exception handlers
# ---------------------------------------------------------------------------


@app.exception_handler(StoryGeneratorError)
async def story_generator_error_handler(
    request: Request, exc: StoryGeneratorError
) -> JSONResponse:
    logger.error("StoryGeneratorError: %s — %s", exc.code, exc.message)
    return _error_response(exc.code, exc.message, status.HTTP_502_BAD_GATEWAY)


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
    return _error_response(
        "INTERNAL_ERROR",
        "An unexpected error occurred. Please try again later.",
        status.HTTP_500_INTERNAL_SERVER_ERROR,
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@app.get(
    "/health",
    response_model=HealthResponse,
    summary="Liveness probe",
    tags=["System"],
)
async def health() -> HealthResponse:
    """Returns ``{"status": "ok"}`` when the application is running."""
    return HealthResponse()


@app.get(
    "/api/daily-news",
    response_model=SuccessResponse,
    summary="Daily NASA APOD Arabic story",
    tags=["Space"],
)
async def daily_news() -> JSONResponse:
    """
    Fetches today's NASA Astronomy Picture of the Day, builds a scientific
    context, and returns an AI-generated Arabic space story.
    """
    generator = _require_story_generator()

    try:
        story = await generator.generate_daily_story()
    except StoryGeneratorError as exc:
        return _error_response(exc.code, exc.message, status.HTTP_502_BAD_GATEWAY)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Unexpected error in /api/daily-news")
        return _error_response(
            "INTERNAL_ERROR",
            "An unexpected error occurred.",
            status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    return JSONResponse(
        content=SuccessResponse(data=story.model_dump()).model_dump(),
        status_code=status.HTTP_200_OK,
    )


@app.get(
    "/api/daily-news/status",
    summary="Scheduler and latest bulletin status",
    tags=["Space"],
)
async def daily_news_status() -> JSONResponse:
    """
    Returns safe scheduler metadata and the latest generated bulletin summary.

    Never exposes API keys, full prompts, or model responses.
    """
    sched_info: dict[str, Any] = {
        "enabled": False,
        "last_run": None,
        "last_success": None,
        "apod_date": None,
        "status": None,
    }

    if _scheduler is not None:
        s = _scheduler.status
        sched_info = {
            "enabled": s.enabled,
            "last_run": s.last_run,
            "last_success": s.last_success,
            "apod_date": s.last_apod_date,
            "status": s.last_status,
        }

    latest_bulletin: dict[str, Any] | None = None
    if _bulletin_service is not None:
        record = _bulletin_service.get_latest_bulletin()
        if record is not None:
            latest_bulletin = {
                "apod_date": record.apod_date,
                "status": record.status,
                "generated_at": record.generated_at,
            }

    return JSONResponse(
        content={
            "success": True,
            "data": {
                "scheduler": sched_info,
                "latest_bulletin": latest_bulletin,
            },
        },
        status_code=status.HTTP_200_OK,
    )


@app.post(
    "/api/analyze",
    response_model=SuccessResponse,
    summary="Analyse a specific APOD date or custom space context",
    tags=["Space"],
)
async def analyze(body: AnalyzeRequest) -> JSONResponse:
    """
    Accepts an optional ``apod_date`` (ISO-8601) and/or ``extra_context``.

    Behaviour:
    - If only ``apod_date`` is provided → fetch that date's APOD and generate a story.
    - If only ``extra_context`` is provided → generate a story from the free-text.
    - If both are provided → fetch APOD and enrich the prompt with extra_context.
    - If neither is provided → default to today's APOD (same as /api/daily-news).
    """
    generator = _require_story_generator()

    try:
        has_date = bool(body.apod_date)
        has_context = bool(body.extra_context)

        if has_context and not has_date:
            story = await generator.generate_from_context(body.extra_context)  # type: ignore[arg-type]
        elif has_date or not has_context:
            # covers: date-only, date+context, or neither (→ today)
            story = await generator.generate_apod_story_with_context(
                body.apod_date, body.extra_context
            )
        else:
            story = await generator.generate_daily_story()

    except StoryGeneratorError as exc:
        return _error_response(exc.code, exc.message, status.HTTP_502_BAD_GATEWAY)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Unexpected error in /api/analyze")
        return _error_response(
            "INTERNAL_ERROR",
            "An unexpected error occurred.",
            status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    return JSONResponse(
        content=SuccessResponse(data=story.model_dump()).model_dump(),
        status_code=status.HTTP_200_OK,
    )


# ---------------------------------------------------------------------------
# Image analysis constants
# ---------------------------------------------------------------------------

# Supported MIME types for image upload
_ALLOWED_IMAGE_MIME_TYPES = frozenset({"image/jpeg", "image/png", "image/webp"})

# Maximum upload size: 5 MB (in bytes)
_MAX_IMAGE_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB


@app.post(
    "/api/analyze-image",
    response_model=SuccessResponse,
    summary="Analyse a user-uploaded space image with vision AI",
    tags=["Space"],
)
async def analyze_image(
    image: UploadFile = File(..., description="Space image to analyse (JPEG, PNG, WEBP)"),
    question: Optional[str] = Form(
        default=None,
        description="Optional Arabic question about the image (max 400 characters)",
    ),
) -> JSONResponse:
    """
    Accepts a multipart/form-data upload with an image file and optional question.

    - Validates MIME type and file size.
    - Encodes the image as base64 and sends it to the vision AI model.
    - Returns a structured Arabic space interpretation.

    Never stores the uploaded image permanently.
    Never exposes API keys, internal prompts, or stack traces.
    """
    if _story_generator is None:
        return _error_response(
            "AI_NOT_CONFIGURED",
            "خدمة الذكاء الاصطناعي غير مهيأة. يرجى الاتصال بمسؤول النظام.",
            status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    # --- Validate MIME type ---
    content_type = (image.content_type or "").lower().split(";")[0].strip()
    if content_type not in _ALLOWED_IMAGE_MIME_TYPES:
        return _error_response(
            "UNSUPPORTED_IMAGE_TYPE",
            "نوع الملف غير مدعوم. يُرجى رفع صورة بتنسيق JPEG أو PNG أو WEBP.",
            status.HTTP_422_UNPROCESSABLE_ENTITY,
        )

    # --- Read image and enforce size limit ---
    try:
        image_bytes = await image.read()
    except Exception:  # noqa: BLE001
        return _error_response(
            "IMAGE_READ_ERROR",
            "تعذّرت قراءة الصورة المرفوعة. يرجى المحاولة مجدداً.",
            status.HTTP_400_BAD_REQUEST,
        )

    if len(image_bytes) == 0:
        return _error_response(
            "EMPTY_IMAGE",
            "الصورة المرفوعة فارغة.",
            status.HTTP_422_UNPROCESSABLE_ENTITY,
        )

    if len(image_bytes) > _MAX_IMAGE_SIZE_BYTES:
        return _error_response(
            "IMAGE_TOO_LARGE",
            f"حجم الصورة يتجاوز الحد الأقصى المسموح ({_MAX_IMAGE_SIZE_BYTES // (1024 * 1024)} ميغابايت).",
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
        )

    # --- Base64-encode (no temp file written) ---
    image_b64 = base64.b64encode(image_bytes).decode("ascii")

    # --- Build prompts ---
    system_prompt = get_vision_system_prompt()
    user_prompt = build_vision_user_prompt(question)

    # --- Call vision AI ---
    try:
        raw_json = await _story_generator._ai.analyze_image(
            image_b64=image_b64,
            image_mime=content_type,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            max_tokens=config.openrouter.max_tokens,
            temperature=config.openrouter.temperature,
        )
    except AIProviderError as exc:
        logger.error("Vision AI error: %s — %s", exc.code, exc.message)
        return _error_response(exc.code, exc.message, status.HTTP_502_BAD_GATEWAY)
    except Exception:  # noqa: BLE001
        logger.exception("Unexpected error calling vision AI")
        return _error_response(
            "INTERNAL_ERROR",
            "حدث خطأ غير متوقع أثناء تحليل الصورة. يرجى المحاولة مجدداً.",
            status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    # --- Validate response with Pydantic ---
    try:
        result = ImageAnalysisResult(**raw_json)
    except ValidationError as exc:
        logger.error("ImageAnalysisResult validation failed: %s", exc)
        return _error_response(
            "VALIDATION_ERROR",
            "استجابة الذكاء الاصطناعي لم تطابق الهيكل المتوقع. يرجى المحاولة مجدداً.",
            status.HTTP_502_BAD_GATEWAY,
        )

    return JSONResponse(
        content=SuccessResponse(data=result.model_dump()).model_dump(),
        status_code=status.HTTP_200_OK,
    )


# ---------------------------------------------------------------------------
# Chat endpoint
# ---------------------------------------------------------------------------

# Maximum user message length
_MAX_CHAT_MESSAGE_LENGTH = 800

# Maximum number of history turns accepted from the client
_MAX_CHAT_HISTORY_TURNS = 20


@app.post(
    "/api/chat",
    response_model=SuccessResponse,
    summary="Multi-turn Arabic space AI chat",
    tags=["Space"],
)
async def chat(body: ChatRequest) -> JSONResponse:
    """
    Accepts a conversation history and returns the AI's next reply.

    - Supports optional image_context from a previous /api/analyze-image call.
    - Maximum {_MAX_CHAT_HISTORY_TURNS} history turns.
    - User messages capped at {_MAX_CHAT_MESSAGE_LENGTH} characters.
    - Never stores conversation server-side.
    - Never exposes API keys or stack traces.
    """
    if _chat_service is None:
        return _error_response(
            "AI_NOT_CONFIGURED",
            "خدمة الذكاء الاصطناعي غير مهيأة. يرجى الاتصال بمسؤول النظام.",
            status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    # Enforce max history length
    messages = body.messages[-_MAX_CHAT_HISTORY_TURNS:]

    # Truncate each user message
    safe_messages = []
    for msg in messages:
        content = msg.content
        if msg.role == "user" and len(content) > _MAX_CHAT_MESSAGE_LENGTH:
            content = content[:_MAX_CHAT_MESSAGE_LENGTH].rstrip() + "…"
        safe_messages.append({"role": msg.role, "content": content})

    # Sanitise image_context — only pass known safe fields
    image_context = None
    if body.image_context:
        raw_ctx = body.image_context
        image_context = {
            k: raw_ctx[k]
            for k in ("title", "summary", "observations", "scientific_explanation", "confidence")
            if k in raw_ctx
        }

    try:
        reply = await _chat_service.chat(
            messages=safe_messages,
            image_context=image_context,
            max_tokens=600,
            temperature=0.5,
        )
    except AIProviderError as exc:
        logger.error("Chat AI error: %s — %s", exc.code, exc.message)
        return _error_response(exc.code, exc.message, status.HTTP_502_BAD_GATEWAY)
    except Exception:
        logger.exception("Unexpected error in /api/chat")
        return _error_response(
            "INTERNAL_ERROR",
            "حدث خطأ غير متوقع في المحادثة. يرجى المحاولة مجدداً.",
            status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    chat_response = ChatResponse(reply=reply)
    return JSONResponse(
        content=SuccessResponse(data=chat_response.model_dump()).model_dump(),
        status_code=status.HTTP_200_OK,
    )


# ---------------------------------------------------------------------------
# Stories archive endpoint
# ---------------------------------------------------------------------------


@app.get(
    "/api/stories",
    response_model=SuccessResponse,
    summary="Fetch APOD stories for a date range",
    tags=["Space"],
)
async def stories(
    count: int = 5,
    end_date: Optional[str] = None,
) -> JSONResponse:
    """
    Returns a list of APOD entries for browsing/archive.

    Parameters
    ----------
    count
        Number of days to fetch (1–10, default 5).
    end_date
        End date in YYYY-MM-DD format. Defaults to today.
    """
    if _nasa_client is None:
        return _error_response(
            "NASA_NOT_CONFIGURED",
            "خدمة ناسا غير مهيأة.",
            status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    # Clamp count
    count = max(1, min(count, 10))

    import datetime

    # Resolve end_date
    try:
        if end_date:
            end = datetime.date.fromisoformat(end_date)
        else:
            end = datetime.date.today()
    except ValueError:
        return _error_response(
            "INVALID_DATE",
            "تنسيق التاريخ غير صالح. استخدم YYYY-MM-DD.",
            status.HTTP_400_BAD_REQUEST,
        )

    # Build list of dates (end inclusive, going backwards)
    dates = []
    for i in range(count):
        d = end - datetime.timedelta(days=i)
        dates.append(d.isoformat())

    # Fetch APOD for each date
    results = []
    for date_str in dates:
        try:
            apod = await _nasa_client.get_apod(apod_date=date_str)
            results.append({
                "id": date_str,
                "date": apod.date,
                "title": apod.title,
                "summary": apod.explanation[:300] + ("…" if len(apod.explanation) > 300 else ""),
                "image_url": apod.image_url,
                "hd_image_url": apod.hd_image_url,
                "media_type": apod.media_type,
                "copyright": apod.copyright,
                "source": "NASA APOD",
            })
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to fetch APOD for %s: %s", date_str, exc)
            # Skip missing dates gracefully
            continue

    return JSONResponse(
        content=SuccessResponse(data={"stories": results, "count": len(results)}).model_dump(),
        status_code=status.HTTP_200_OK,
    )
