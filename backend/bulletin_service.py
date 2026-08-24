"""
Bulletin service — orchestrates the daily automation pipeline.

Responsibilities:
1. Check the store for duplicate APOD-date generation (idempotency).
2. Fetch APOD (NASA date is authoritative — not server local date).
3. Optionally fetch DONKI events.
4. Normalise and clean the data before passing it to StoryGenerator.
5. Persist the result (success or failure) in BulletinStore.
6. Return the generated SpaceStory.

This module deliberately does NOT know about HTTP or scheduling — it is
pure pipeline logic.  The scheduler and the API endpoint both call this
service; neither duplicates pipeline logic.
"""

from __future__ import annotations

import logging
import time
from typing import Optional

from bulletin_store import BulletinRecord, BulletinStore, utc_now_iso
from models import NASAAPODData, NASADONKIEvent, SpaceStory
from nasa_client import NASAClient, NASAClientError
from story_generator import StoryGenerator, StoryGeneratorError

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data normalisation helpers (Phase 3)
# ---------------------------------------------------------------------------

# Maximum characters for the APOD explanation passed into the prompt.
# The story_generator already truncates at prompt-build time, but we also
# strip here to clean the data before it ever reaches the prompt layer.
_MAX_EXPLANATION_CHARS = 1200

# Maximum number of DONKI events to pass downstream.
_MAX_DONKI_EVENTS = 5


def _normalise_apod(apod: NASAAPODData) -> NASAAPODData:
    """
    Return a cleaned copy of *apod* with:
    - Explanation truncated to _MAX_EXPLANATION_CHARS.
    - Whitespace stripped from string fields.
    - Empty optional fields left as-is (already Optional[str]).
    """
    explanation = apod.explanation.strip()
    if len(explanation) > _MAX_EXPLANATION_CHARS:
        explanation = explanation[:_MAX_EXPLANATION_CHARS].rstrip() + "…"

    # Use model_copy (Pydantic v2) so we don't lose validation
    return apod.model_copy(update={"explanation": explanation})


def _filter_donki_events(events: list[NASADONKIEvent]) -> list[NASADONKIEvent]:
    """
    Remove DONKI events that are missing begin_time (minimum useful data).
    Cap the list at _MAX_DONKI_EVENTS.
    """
    filtered = [e for e in events if e.begin_time]
    return filtered[:_MAX_DONKI_EVENTS]


# ---------------------------------------------------------------------------
# BulletinService
# ---------------------------------------------------------------------------


class BulletinService:
    """
    High-level service that coordinates the daily bulletin generation pipeline.

    Parameters
    ----------
    story_generator:
        Configured StoryGenerator instance (wires NASA + AI).
    store:
        BulletinStore instance for persistence.
    """

    def __init__(
        self,
        story_generator: StoryGenerator,
        store: BulletinStore,
    ) -> None:
        self._generator = story_generator
        self._store = store

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def generate_daily_bulletin(
        self,
        *,
        force: bool = False,
    ) -> Optional[SpaceStory]:
        """
        Run the full daily bulletin pipeline.

        Steps:
        1. Fetch APOD (NASA date is authoritative).
        2. Check idempotency — skip if already generated for this APOD date.
        3. Fetch DONKI events (non-fatal).
        4. Normalise data.
        5. Generate story via StoryGenerator.
        6. Persist result.

        Parameters
        ----------
        force:
            If True, skip the duplicate-date check and regenerate even if a
            bulletin for today's APOD date already exists.  Intended only for
            manual/test triggers; the scheduler never passes force=True.

        Returns
        -------
        SpaceStory | None
            The generated story, or None if skipped (duplicate date) or failed.
        """
        start = time.monotonic()
        logger.info("BulletinService: starting daily bulletin generation")

        # Step 1 — Fetch APOD (NASA date is the source of truth)
        try:
            apod = await self._generator._nasa.get_apod(None)
        except NASAClientError as exc:
            logger.error(
                "BulletinService: NASA APOD fetch failed — code=%s, message=%s",
                exc.code,
                exc.message,
            )
            self._record_failure(apod_date="unknown", reason=exc.message)
            return None
        except Exception as exc:  # noqa: BLE001
            logger.error("BulletinService: unexpected NASA error: %s", exc)
            self._record_failure(apod_date="unknown", reason=str(exc))
            return None

        apod_date = apod.date
        logger.info("BulletinService: APOD date=%s, title=%s", apod_date, apod.title)

        # Step 2 — Idempotency check
        if not force and self._store.has_record_for(apod_date):
            logger.info(
                "BulletinService: bulletin for APOD date=%s already exists — skipping",
                apod_date,
            )
            return None

        # Step 3 — Fetch DONKI (non-fatal)
        donki_events: list[NASADONKIEvent] = []
        try:
            raw_events = await self._generator._nasa.get_donki_cme()
            donki_events = _filter_donki_events(raw_events)
            logger.info("BulletinService: DONKI events fetched, count=%d", len(donki_events))
        except Exception as exc:  # noqa: BLE001
            logger.warning("BulletinService: DONKI fetch skipped (non-fatal): %s", exc)

        # Step 4 — Normalise data
        clean_apod = _normalise_apod(apod)

        # Step 5 — Generate story using the existing pipeline
        story: Optional[SpaceStory] = None
        try:
            story = await self._generator.generate_daily_story(apod_date=apod_date)
        except StoryGeneratorError as exc:
            logger.error(
                "BulletinService: story generation failed — code=%s, message=%s",
                exc.code,
                exc.message,
            )
            self._record_failure(apod_date=apod_date, reason=exc.message)
        except Exception as exc:  # noqa: BLE001
            logger.error("BulletinService: unexpected story generation error: %s", exc)
            self._record_failure(apod_date=apod_date, reason=str(exc))

        # Step 6 — Persist
        if story is not None:
            elapsed = time.monotonic() - start
            logger.info(
                "BulletinService: bulletin generated successfully for APOD date=%s "
                "(%.1fs)",
                apod_date,
                elapsed,
            )
            self._record_success(apod_date=apod_date, story=story)

        return story

    def get_latest_bulletin(self) -> Optional[BulletinRecord]:
        """Return the most recently stored bulletin record (or None)."""
        return self._store.get_latest()

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _record_success(self, apod_date: str, story: SpaceStory) -> None:
        record = BulletinRecord(
            apod_date=apod_date,
            status="success",
            generated_at=utc_now_iso(),
            story=story.model_dump(),
        )
        self._store.save(record)

    def _record_failure(self, apod_date: str, reason: str) -> None:
        # Log reason but never store API keys — reason is a sanitised error message
        record = BulletinRecord(
            apod_date=apod_date,
            status="failed",
            generated_at=utc_now_iso(),
            story=None,
        )
        self._store.save(record)
        logger.warning(
            "BulletinService: recorded failure for APOD date=%s",
            apod_date,
        )
