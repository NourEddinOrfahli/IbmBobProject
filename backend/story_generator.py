"""
Story generator — the orchestration layer.

Wires together:
  NASAClient  →  data normalisation  →  Prompt builder  →  AIProvider
  →  JSON parsing  →  Pydantic validation  →  SpaceStory

This module keeps all the pipeline logic in one place so that main.py stays
thin and focused only on HTTP concerns.

Fallback behaviour
------------------
When the NASA APOD endpoint times out or returns a network error, _fetch_apod()
returns a static placeholder NASAAPODData so the rest of the pipeline can still
run (the AI will generate a general space story rather than hanging the UI).
Set NASA_APOD_FALLBACK=false in the environment to disable this and raise
StoryGeneratorError instead (original behaviour).
"""

from __future__ import annotations

import logging
import os
from datetime import date
from typing import Optional

from pydantic import ValidationError

from ai_provider import AIProvider, AIProviderError
from config import AppConfig
from models import (
    CMEEventSummary,
    NASAAPODData,
    NASADONKIEvent,
    SpaceStory,
    SpaceWeatherSummary,
)
from nasa_client import NASAClient, NASAClientError
from prompts import build_prompt_for_apod, build_custom_context_prompt, get_system_prompt

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Fallback mock APOD — returned immediately when NASA times out or errors.
# Gives the AI enough context to produce a generic space story so the UI
# never hangs waiting for a NASA response that will never arrive.
# ---------------------------------------------------------------------------

_APOD_FALLBACK_ENABLED: bool = os.getenv("NASA_APOD_FALLBACK", "true").lower() != "false"
_AI_STORY_FALLBACK_ENABLED: bool = os.getenv("AI_STORY_FALLBACK", "true").lower() != "false"


def _make_fallback_apod(requested_date: Optional[str] = None) -> NASAAPODData:
    """Return a static placeholder APOD when NASA cannot be reached."""
    today = requested_date or str(date.today())
    return NASAAPODData(
        title="استكشاف الكون — بيانات ناسا غير متاحة حالياً",
        explanation=(
            "تعذّر الاتصال بواجهة برمجة ناسا في الوقت الحالي. "
            "فيما يلي قصة فضائية مبنية على المعرفة العلمية العامة. "
            "يُرجى المحاولة مرة أخرى لاحقاً للاطلاع على صورة اليوم الفعلية."
        ),
        date=today,
        media_type="image",
        image_url=None,
        hd_image_url=None,
        copyright=None,
        source="NASA APOD (fallback)",
    )


def _make_fallback_story(apod_date: Optional[str] = None) -> "SpaceStory":
    """
    Return a fully populated static SpaceStory when all AI models are unavailable.

    The content is real, scientifically accurate information about the Milky Way
    so the dashboard always renders something meaningful instead of an error screen.
    The title and source_data clearly indicate this is cached/offline content.
    """
    today = apod_date or str(date.today())
    return SpaceStory(
        title="درب التبانة — مجرتنا الرائعة",
        summary=(
            "درب التبانة مجرةٌ حلزونية الشكل يبلغ قطرها نحو 100,000 سنة ضوئية، "
            "وتحتوي على ما يتراوح بين 100 و400 مليار نجم. "
            "نحن نقطن في أحد أذرعها الحلزونية على بُعد نحو 26,000 سنة ضوئية من مركزها."
        ),
        scientific_explanation=(
            "في قلب درب التبانة يرقد ثقبٌ أسود هائل يُعرف بـ Sagittarius A* "
            "تبلغ كتلته نحو 4 ملايين مرة كتلة الشمس. "
            "تدور مجرتنا بأكملها حول هذا المركز الثقيل بسرعة تصل إلى 220 كيلومتراً في الثانية، "
            "وتستغرق دورةً كاملةً نحو 225 مليون سنة تُعرف بـ'السنة الكونية'."
        ),
        key_facts=[
            "قطر المجرة: ~100,000 سنة ضوئية",
            "عدد النجوم: 100–400 مليار نجم",
            "المسافة إلى المركز من الأرض: ~26,000 سنة ضوئية",
            "الثقب الأسود المركزي: Sagittarius A* بكتلة 4 مليون شمس",
            "سرعة دوران الشمس حول المركز: ~220 كم/ث",
        ],
        why_it_matters=(
            "فهم مجرتنا يمنحنا سياقاً لفهم الكون كله. "
            "دراسة درب التبانة تكشف لنا كيف تتشكل النجوم والأنظمة الشمسية، "
            "وتساعدنا في البحث عن حياة محتملة في مناطق أخرى من المجرة."
        ),
        story=(
            "في ليلة صافية بعيداً عن أضواء المدينة، تستطيع رؤية شريط من الضوء "
            "يمتد عبر السماء — هذا هو درب التبانة، مجرتنا التي نحن جزءٌ صغيرٌ منها. "
            "ما تراه هو ملايين النجوم تتراص في الأذرع الحلزونية لمجرة عمرها 13.6 مليار سنة. "
            "أنت لا تنظر فحسب إلى النجوم، بل إلى تاريخ الكون نفسه."
        ),
        source_data={
            "source": "NASA APOD (offline fallback)",
            "date": today,
            "title": "درب التبانة — مجرتنا الرائعة",
            "media_type": "image",
            "image_url": None,
            "hd_image_url": None,
            "copyright": None,
            "note": "هذا محتوى احتياطي — خدمة الذكاء الاصطناعي غير متاحة حالياً",
        },
        confidence="high",
        language="ar",
        space_weather=None,
    )


class StoryGeneratorError(Exception):
    """Raised when the story-generation pipeline fails in a non-recoverable way."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class StoryGenerator:
    """
    High-level orchestrator for the NASA → AI → SpaceStory pipeline.

    Parameters
    ----------
    nasa_client:
        Configured NASAClient instance.
    ai_provider:
        Any AIProvider implementation (OpenRouter, IBM Granite, …).
    config:
        Application configuration (used for AI provider defaults).
    """

    def __init__(
        self,
        nasa_client: NASAClient,
        ai_provider: AIProvider,
        config: AppConfig,
    ) -> None:
        self._nasa = nasa_client
        self._ai = ai_provider
        self._config = config

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def generate_daily_story(
        self, apod_date: Optional[str] = None
    ) -> SpaceStory:
        """
        Full pipeline: fetch today's (or a specific date's) APOD from NASA,
        optionally augment with DONKI data, call the AI, and return a
        validated SpaceStory.

        If every AI model is unavailable (404, timeout, rate-limit) AND
        AI_STORY_FALLBACK is enabled (default), a fully populated static
        SpaceStory is returned immediately so the dashboard always loads.

        Parameters
        ----------
        apod_date:
            Optional ISO-8601 date.  If None, NASA returns today's APOD.

        Raises
        ------
        StoryGeneratorError
            Only when _AI_STORY_FALLBACK_ENABLED is False and all AI calls fail.
        """
        # Step 1 — Fetch NASA APOD
        logger.info("Fetching NASA APOD (date=%s)", apod_date or "today")
        apod = await self._fetch_apod(apod_date)

        # Step 2 — Optionally fetch DONKI events (non-fatal if unavailable)
        donki_events = await self._fetch_donki_optional()

        # Step 3 — Build prompts
        system_prompt, user_prompt = build_prompt_for_apod(apod, donki_events or None)

        # Step 4 — Call AI provider (with fallback story on total AI failure)
        logger.info("Calling AI provider for story generation")
        try:
            raw_json = await self._call_ai(system_prompt, user_prompt)
        except StoryGeneratorError as exc:
            if _AI_STORY_FALLBACK_ENABLED:
                logger.warning(
                    "All AI models failed (%s) — serving static fallback story "
                    "so the dashboard loads instantly.",
                    exc.code,
                )
                fallback = _make_fallback_story(apod_date)
                # Overwrite source fields with the real NASA data that was already
                # fetched successfully, so the fallback story shows the correct
                # APOD image/title/date even when the AI fails.
                fallback.source_data.update({
                    "source": apod.source,
                    "date": apod.date,
                    "title": apod.title,
                    "media_type": apod.media_type,
                    "image_url": apod.image_url,
                    "hd_image_url": apod.hd_image_url,
                    "copyright": apod.copyright,
                    # Explicit flag so the frontend can distinguish fallback from AI-generated.
                    "fallback": True,
                })
                return fallback
            raise

        # Step 5 — Inject source_data (provenance + media passthrough)
        raw_json = self._ensure_source_data(raw_json, apod)

        # Step 6 — Attach structured space-weather summary (additive, non-fatal)
        raw_json["space_weather"] = self._build_space_weather(donki_events).model_dump()

        # Step 7 — Validate with Pydantic
        return self._validate_story(raw_json)

    async def generate_from_context(self, context: str) -> SpaceStory:
        """
        Generate a story from arbitrary free-text space context (used by
        POST /api/analyze when extra_context is provided without APOD data).

        Raises
        ------
        StoryGeneratorError
        """
        if not context.strip():
            raise StoryGeneratorError(
                "EMPTY_CONTEXT",
                "extra_context must not be empty.",
            )

        system_prompt = get_system_prompt()
        user_prompt = build_custom_context_prompt(context)

        raw_json = await self._call_ai(system_prompt, user_prompt)
        return self._validate_story(raw_json)

    async def generate_apod_story_with_context(
        self,
        apod_date: Optional[str],
        extra_context: Optional[str],
    ) -> SpaceStory:
        """
        Fetch APOD then optionally append extra_context to the user prompt.
        Used by POST /api/analyze when both apod_date and extra_context are set.
        """
        apod = await self._fetch_apod(apod_date)
        donki_events = await self._fetch_donki_optional()

        system_prompt, user_prompt = build_prompt_for_apod(apod, donki_events or None)

        if extra_context:
            user_prompt += (
                f"\n\nسياق إضافي مُقدَّم من المستخدم:\n{extra_context}\n"
                "يُرجى مراعاة هذا السياق عند الكتابة، مع الالتزام بالبيانات الرسمية من ناسا."
            )

        raw_json = await self._call_ai(system_prompt, user_prompt)
        raw_json = self._ensure_source_data(raw_json, apod)
        raw_json["space_weather"] = self._build_space_weather(donki_events).model_dump()
        return self._validate_story(raw_json)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _fetch_apod(self, apod_date: Optional[str]) -> NASAAPODData:
        try:
            return await self._nasa.get_apod(apod_date)
        except NASAClientError as exc:
            # On transient failures (timeout / network error) return fallback mock
            # data immediately so the UI doesn't hang.  On bad-request or
            # missing-fields errors (caller's fault) still raise so the endpoint
            # returns a clear 502.
            _TRANSIENT_CODES = frozenset({
                "NASA_TIMEOUT",
                "NASA_NETWORK_ERROR",
                "NASA_RATE_LIMIT",
                "NASA_SERVER_ERROR",
            })
            if exc.code in _TRANSIENT_CODES and _APOD_FALLBACK_ENABLED:
                logger.warning(
                    "NASA APOD unavailable (%s) — returning fallback mock data "
                    "so the pipeline can complete without hanging.",
                    exc.code,
                )
                return _make_fallback_apod(apod_date)
            logger.error("NASA APOD fetch failed: %s — %s", exc.code, exc.message)
            raise StoryGeneratorError(exc.code, exc.message) from exc

    async def _fetch_donki_optional(self) -> list[NASADONKIEvent]:
        """Fetch recent DONKI CME events; return empty list on any failure."""
        try:
            return await self._nasa.get_donki_cme()
        except Exception as exc:  # noqa: BLE001
            logger.warning("DONKI fetch skipped (non-fatal): %s", exc)
            return []

    async def _call_ai(
        self, system_prompt: str, user_prompt: str
    ) -> dict:
        try:
            return await self._ai.generate_structured_response(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                max_tokens=self._config.openrouter.max_tokens,
                temperature=self._config.openrouter.temperature,
            )
        except AIProviderError as exc:
            logger.error("AI provider error: %s — %s", exc.code, exc.message)
            raise StoryGeneratorError(exc.code, exc.message) from exc

    @staticmethod
    def _ensure_source_data(raw: dict, apod: NASAAPODData) -> dict:
        """
        Always enforce the NASA-verified provenance fields in source_data.

        The LLM is permitted to return extra keys but the authoritative
        fields — source, date, title — are ALWAYS overwritten with values
        from the verified NASAAPODData object to prevent hallucination.

        Additionally, the NASA-fetched media fields (image_url, hd_image_url,
        media_type, copyright) are passed through so the frontend can display
        the APOD image when available.  These are all Optional and may be None.
        """
        existing: dict = raw.get("source_data") or {}
        existing.update({
            # Authoritative provenance — always overwrite
            "source": apod.source,
            "date": apod.date,
            "title": apod.title,
            # Media passthrough — None when not present (e.g. video APODs)
            "media_type": apod.media_type,
            "image_url": apod.image_url,
            "hd_image_url": apod.hd_image_url,
            "copyright": apod.copyright,
        })
        raw["source_data"] = existing
        return raw

    @staticmethod
    def _build_space_weather(
        donki_events: list[NASADONKIEvent],
    ) -> SpaceWeatherSummary:
        """
        Build a structured SpaceWeatherSummary from already-fetched DONKI events.

        Extracts useful fields from the raw CME payload stored in each
        NASADONKIEvent.raw dict.  All nested access is guarded — real DONKI
        responses frequently omit cmeAnalyses, enlilList, or individual
        sub-fields.  Missing values become None; the pipeline never crashes.

        No new NASA API calls are made.
        """
        if not donki_events:
            return SpaceWeatherSummary(available=False, event_count=0, events=[])

        summaries: list[CMEEventSummary] = []
        for evt in donki_events:
            raw = evt.raw or {}

            # --- CME analysis block (speed + direction) ---
            speed: float | None = None
            is_earth_directed: bool | None = None
            estimated_arrival: str | None = None
            kp_index: float | None = None

            analyses = raw.get("cmeAnalyses") or []
            if analyses and isinstance(analyses, list):
                # Use the most-accurate analysis when flagged, otherwise first
                best = next(
                    (a for a in analyses if a.get("isMostAccurate")),
                    analyses[0] if analyses else None,
                )
                if best and isinstance(best, dict):
                    raw_speed = best.get("speed")
                    if raw_speed is not None:
                        try:
                            speed = float(raw_speed)
                        except (TypeError, ValueError):
                            pass

                    # enlilList carries Earth-impact predictions
                    enlil_list = best.get("enlilList") or []
                    if enlil_list and isinstance(enlil_list, list):
                        # Use first enlil entry that has isEarthGB set
                        earth_entry = next(
                            (
                                e for e in enlil_list
                                if isinstance(e, dict) and e.get("isEarthGB") is not None
                            ),
                            enlil_list[0] if enlil_list else None,
                        )
                        if earth_entry and isinstance(earth_entry, dict):
                            is_earth_directed = earth_entry.get("isEarthGB")

                            arrival_raw = earth_entry.get("estimatedShockArrivalTime")
                            if arrival_raw and isinstance(arrival_raw, str):
                                estimated_arrival = arrival_raw

                            kp_raw = earth_entry.get("kp_90")
                            if kp_raw is not None:
                                try:
                                    kp_index = float(kp_raw)
                                except (TypeError, ValueError):
                                    pass

            # --- Top-level CME fields ---
            source_location: str | None = raw.get("sourceLocation") or None
            note_raw = raw.get("note")
            note: str | None = str(note_raw).strip() if note_raw else None

            summaries.append(
                CMEEventSummary(
                    event_type=evt.event_type,
                    begin_time=evt.begin_time,
                    speed_kmps=speed,
                    is_earth_directed=is_earth_directed,
                    estimated_arrival=estimated_arrival,
                    kp_index=kp_index,
                    source_location=source_location,
                    note=note,
                )
            )

        return SpaceWeatherSummary(
            available=len(summaries) > 0,
            event_count=len(summaries),
            events=summaries,
        )

    @staticmethod
    def _validate_story(raw: dict) -> SpaceStory:
        try:
            return SpaceStory(**raw)
        except ValidationError as exc:
            logger.error("SpaceStory validation failed: %s", exc)
            raise StoryGeneratorError(
                "VALIDATION_ERROR",
                f"AI response did not match the expected schema: {exc}",
            ) from exc
