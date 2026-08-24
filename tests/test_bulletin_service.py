"""
Tests for BulletinService (bulletin_service.py).

All NASA and AI calls are mocked — no real API keys required.
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from bulletin_service import BulletinService, _filter_donki_events, _normalise_apod
from bulletin_store import BulletinStore
from models import NASAAPODData, NASADONKIEvent, SpaceStory
from nasa_client import NASAClientError
from story_generator import StoryGeneratorError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _sample_apod(date: str = "2024-06-15") -> NASAAPODData:
    return NASAAPODData(
        title="Pillars of Creation",
        explanation="The Eagle Nebula's iconic gas pillars.",
        date=date,
        media_type="image",
    )


def _sample_story(apod_date: str = "2024-06-15") -> SpaceStory:
    return SpaceStory(
        title="أعمدة الإبداع",
        summary="ملخص مختصر عن السديم.",
        scientific_explanation="شرح علمي للأعمدة الغازية.",
        key_facts=["حقيقة 1"],
        why_it_matters="مهم للفلك.",
        story="قصة قصيرة.",
        source_data={"source": "NASA APOD", "date": apod_date, "title": "Pillars"},
        confidence="high",
        language="ar",
    )


def _sample_donki_events() -> list[NASADONKIEvent]:
    return [
        NASADONKIEvent(event_type="CME", begin_time="2024-06-14T10:00Z"),
        NASADONKIEvent(event_type="CME", begin_time="2024-06-13T08:00Z"),
    ]


def _make_store(tmp_path) -> BulletinStore:
    return BulletinStore(str(tmp_path / "test_service_store.json"))


def _make_mock_generator(
    apod: NASAAPODData | None = None,
    story: SpaceStory | None = None,
    nasa_error: Exception | None = None,
    ai_error: Exception | None = None,
    donki_events: list[NASADONKIEvent] | None = None,
) -> MagicMock:
    """Build a mock StoryGenerator with configurable behaviour."""
    mock_gen = MagicMock()

    # _nasa.get_apod
    if nasa_error:
        mock_gen._nasa.get_apod = AsyncMock(side_effect=nasa_error)
    else:
        mock_gen._nasa.get_apod = AsyncMock(return_value=apod or _sample_apod())

    # _nasa.get_donki_cme
    mock_gen._nasa.get_donki_cme = AsyncMock(return_value=donki_events or [])

    # generate_daily_story
    if ai_error:
        mock_gen.generate_daily_story = AsyncMock(side_effect=ai_error)
    else:
        mock_gen.generate_daily_story = AsyncMock(return_value=story or _sample_story())

    return mock_gen


# ---------------------------------------------------------------------------
# _normalise_apod
# ---------------------------------------------------------------------------


class TestNormaliseApod:
    def test_short_explanation_unchanged(self):
        apod = _sample_apod()
        result = _normalise_apod(apod)
        assert result.explanation == apod.explanation

    def test_long_explanation_truncated(self):
        long_text = "A" * 1500
        apod = NASAAPODData(
            title="Test", explanation=long_text, date="2024-01-01", media_type="image"
        )
        result = _normalise_apod(apod)
        assert len(result.explanation) <= 1205  # 1200 + "…"
        assert result.explanation.endswith("…")

    def test_title_and_date_unchanged(self):
        apod = _sample_apod()
        result = _normalise_apod(apod)
        assert result.title == apod.title
        assert result.date == apod.date

    def test_whitespace_stripped_from_explanation(self):
        apod = NASAAPODData(
            title="Test",
            explanation="  Some text with spaces  ",
            date="2024-01-01",
            media_type="image",
        )
        result = _normalise_apod(apod)
        assert not result.explanation.startswith(" ")
        assert not result.explanation.endswith(" ")


# ---------------------------------------------------------------------------
# _filter_donki_events
# ---------------------------------------------------------------------------


class TestFilterDonkiEvents:
    def test_removes_events_without_begin_time(self):
        events = [
            NASADONKIEvent(event_type="CME", begin_time="2024-06-14T10:00Z"),
            NASADONKIEvent(event_type="CME", begin_time=None),
        ]
        result = _filter_donki_events(events)
        assert len(result) == 1
        assert result[0].begin_time == "2024-06-14T10:00Z"

    def test_caps_at_five_events(self):
        events = [
            NASADONKIEvent(event_type="CME", begin_time=f"2024-06-{i:02d}T10:00Z")
            for i in range(1, 11)
        ]
        result = _filter_donki_events(events)
        assert len(result) == 5

    def test_empty_list_returns_empty(self):
        assert _filter_donki_events([]) == []

    def test_all_events_have_begin_time(self):
        events = _sample_donki_events()
        result = _filter_donki_events(events)
        assert len(result) == 2


# ---------------------------------------------------------------------------
# BulletinService.generate_daily_bulletin
# ---------------------------------------------------------------------------


class TestBulletinServiceGenerateDailyBulletin:

    @pytest.mark.asyncio
    async def test_successful_generation(self, tmp_path):
        """Happy path: generates story and saves it to the store."""
        store = _make_store(tmp_path)
        generator = _make_mock_generator()
        service = BulletinService(generator, store)

        result = await service.generate_daily_bulletin()

        assert result is not None
        assert result.language == "ar"
        assert store.has_record_for("2024-06-15") is True

    @pytest.mark.asyncio
    async def test_nasa_failure_returns_none_and_does_not_crash(self, tmp_path):
        """NASA fetch failure must return None — not raise."""
        store = _make_store(tmp_path)
        generator = _make_mock_generator(
            nasa_error=NASAClientError("NASA_TIMEOUT", "Timed out")
        )
        service = BulletinService(generator, store)

        result = await service.generate_daily_bulletin()

        assert result is None

    @pytest.mark.asyncio
    async def test_ai_failure_returns_none_and_does_not_crash(self, tmp_path):
        """AI failure must return None — not raise."""
        store = _make_store(tmp_path)
        generator = _make_mock_generator(
            ai_error=StoryGeneratorError("AI_TIMEOUT", "AI timed out")
        )
        service = BulletinService(generator, store)

        result = await service.generate_daily_bulletin()

        assert result is None

    @pytest.mark.asyncio
    async def test_duplicate_date_is_skipped(self, tmp_path):
        """If the APOD date already has a successful bulletin, skip and return None."""
        store = _make_store(tmp_path)

        # Pre-populate store with today's date
        from bulletin_store import BulletinRecord, utc_now_iso
        store.save(BulletinRecord(
            apod_date="2024-06-15",
            status="success",
            generated_at=utc_now_iso(),
            story={"title": "existing"},
        ))

        generator = _make_mock_generator()
        service = BulletinService(generator, store)

        result = await service.generate_daily_bulletin()

        assert result is None
        # generate_daily_story must NOT have been called
        generator.generate_daily_story.assert_not_called()

    @pytest.mark.asyncio
    async def test_force_flag_bypasses_duplicate_check(self, tmp_path):
        """force=True must regenerate even if the APOD date is already stored."""
        store = _make_store(tmp_path)

        from bulletin_store import BulletinRecord, utc_now_iso
        store.save(BulletinRecord(
            apod_date="2024-06-15",
            status="success",
            generated_at=utc_now_iso(),
            story={"title": "old"},
        ))

        generator = _make_mock_generator()
        service = BulletinService(generator, store)

        result = await service.generate_daily_bulletin(force=True)

        assert result is not None
        generator.generate_daily_story.assert_called_once()

    @pytest.mark.asyncio
    async def test_new_apod_date_generates_new_bulletin(self, tmp_path):
        """A new APOD date must always trigger generation."""
        store = _make_store(tmp_path)
        store.save(
            __import__("bulletin_store").BulletinRecord(
                apod_date="2024-06-14",  # yesterday
                status="success",
                generated_at=__import__("bulletin_store").utc_now_iso(),
                story={"title": "yesterday"},
            )
        )

        generator = _make_mock_generator(apod=_sample_apod("2024-06-15"))
        service = BulletinService(generator, store)

        result = await service.generate_daily_bulletin()

        assert result is not None
        assert store.has_record_for("2024-06-15") is True

    @pytest.mark.asyncio
    async def test_successful_generation_stores_story(self, tmp_path):
        """Generated story must be retrievable from the store after saving."""
        store = _make_store(tmp_path)
        generator = _make_mock_generator()
        service = BulletinService(generator, store)

        await service.generate_daily_bulletin()

        record = store.get_record("2024-06-15")
        assert record is not None
        assert record.status == "success"
        assert record.story is not None

    @pytest.mark.asyncio
    async def test_failed_generation_stores_failure_record(self, tmp_path):
        """AI failure must store a 'failed' record (not leave the store empty)."""
        store = _make_store(tmp_path)
        generator = _make_mock_generator(
            ai_error=StoryGeneratorError("AI_TIMEOUT", "timed out")
        )
        service = BulletinService(generator, store)

        await service.generate_daily_bulletin()

        record = store.get_record("2024-06-15")
        assert record is not None
        assert record.status == "failed"
        assert record.story is None

    @pytest.mark.asyncio
    async def test_failed_record_does_not_block_retry(self, tmp_path):
        """
        A 'failed' record for today must NOT block a subsequent attempt.
        The idempotency check only skips 'success' records.
        """
        store = _make_store(tmp_path)

        from bulletin_store import BulletinRecord, utc_now_iso
        store.save(BulletinRecord(
            apod_date="2024-06-15",
            status="failed",
            generated_at=utc_now_iso(),
            story=None,
        ))

        generator = _make_mock_generator()
        service = BulletinService(generator, store)

        result = await service.generate_daily_bulletin()

        assert result is not None
        generator.generate_daily_story.assert_called_once()

    @pytest.mark.asyncio
    async def test_unexpected_exception_does_not_propagate(self, tmp_path):
        """Completely unexpected exceptions must be caught and return None."""
        store = _make_store(tmp_path)
        generator = _make_mock_generator(nasa_error=RuntimeError("unexpected!"))
        service = BulletinService(generator, store)

        result = await service.generate_daily_bulletin()  # must not raise

        assert result is None


# ---------------------------------------------------------------------------
# BulletinService.get_latest_bulletin
# ---------------------------------------------------------------------------


class TestBulletinServiceGetLatest:
    def test_returns_none_when_store_empty(self, tmp_path):
        store = _make_store(tmp_path)
        generator = _make_mock_generator()
        service = BulletinService(generator, store)
        assert service.get_latest_bulletin() is None

    @pytest.mark.asyncio
    async def test_returns_latest_after_generation(self, tmp_path):
        store = _make_store(tmp_path)
        generator = _make_mock_generator()
        service = BulletinService(generator, store)

        await service.generate_daily_bulletin()
        latest = service.get_latest_bulletin()

        assert latest is not None
        assert latest.apod_date == "2024-06-15"
        assert latest.status == "success"
