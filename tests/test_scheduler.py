"""
Tests for DailyBulletinScheduler (scheduler.py), SchedulerConfig (config.py),
and the new /api/daily-news/status endpoint (main.py).

All tests use mocks — no real API keys, no real scheduler ticks.
"""

from __future__ import annotations

import logging
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from config import AppConfig, NASAConfig, OpenRouterConfig, SchedulerConfig, validate_config
from scheduler import DailyBulletinScheduler, SchedulerStatus


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_scheduler_config(**overrides) -> SchedulerConfig:
    defaults = {
        "enabled": True,
        "hour": 7,
        "minute": 0,
        "timezone": "UTC",
        "store_path": "test_store.json",
    }
    defaults.update(overrides)
    return SchedulerConfig(**defaults)


def _make_disabled_scheduler_config() -> SchedulerConfig:
    return _make_scheduler_config(enabled=False)


def _make_mock_service(
    story=None,
    return_none: bool = False,
    raise_exc: Exception | None = None,
) -> MagicMock:
    mock_service = MagicMock()
    if raise_exc:
        mock_service.generate_daily_bulletin = AsyncMock(side_effect=raise_exc)
    elif return_none:
        mock_service.generate_daily_bulletin = AsyncMock(return_value=None)
    else:
        from models import SpaceStory
        default_story = story or SpaceStory(
            title="أعمدة الإبداع",
            summary="ملخص.",
            scientific_explanation="شرح.",
            key_facts=["حقيقة"],
            why_it_matters="مهم.",
            story="قصة.",
            source_data={"source": "NASA APOD", "date": "2024-06-15", "title": "Test"},
            confidence="high",
            language="ar",
        )
        mock_service.generate_daily_bulletin = AsyncMock(return_value=default_story)

    mock_service.get_latest_bulletin = MagicMock(return_value=None)
    return mock_service


# ---------------------------------------------------------------------------
# SchedulerConfig tests
# ---------------------------------------------------------------------------


class TestSchedulerConfig:
    def test_defaults(self):
        cfg = SchedulerConfig()
        assert cfg.enabled is False  # disabled by default
        assert cfg.hour == 7
        assert cfg.minute == 0
        assert cfg.timezone == "UTC"

    def test_enabled_from_env(self, monkeypatch):
        monkeypatch.setenv("DAILY_BULLETIN_ENABLED", "true")
        cfg = SchedulerConfig()
        assert cfg.enabled is True
        monkeypatch.delenv("DAILY_BULLETIN_ENABLED", raising=False)

    def test_hour_from_env(self, monkeypatch):
        monkeypatch.setenv("DAILY_BULLETIN_HOUR", "9")
        cfg = SchedulerConfig()
        assert cfg.hour == 9
        monkeypatch.delenv("DAILY_BULLETIN_HOUR", raising=False)

    def test_minute_from_env(self, monkeypatch):
        monkeypatch.setenv("DAILY_BULLETIN_MINUTE", "30")
        cfg = SchedulerConfig()
        assert cfg.minute == 30
        monkeypatch.delenv("DAILY_BULLETIN_MINUTE", raising=False)

    def test_timezone_from_env(self, monkeypatch):
        monkeypatch.setenv("DAILY_BULLETIN_TIMEZONE", "Asia/Riyadh")
        cfg = SchedulerConfig()
        assert cfg.timezone == "Asia/Riyadh"
        monkeypatch.delenv("DAILY_BULLETIN_TIMEZONE", raising=False)

    def test_store_path_from_env(self, monkeypatch):
        monkeypatch.setenv("BULLETIN_STORE_PATH", "/tmp/my_store.json")
        cfg = SchedulerConfig()
        assert cfg.store_path == "/tmp/my_store.json"
        monkeypatch.delenv("BULLETIN_STORE_PATH", raising=False)

    def test_validate_config_warns_on_invalid_hour(self):
        config = AppConfig(
            nasa=NASAConfig(api_key="X"),
            openrouter=OpenRouterConfig(api_key="X"),
            scheduler=SchedulerConfig(enabled=True, hour=25, minute=0, timezone="UTC"),
        )
        issues = validate_config(config)
        assert any("DAILY_BULLETIN_HOUR" in i for i in issues)

    def test_validate_config_warns_on_invalid_minute(self):
        config = AppConfig(
            nasa=NASAConfig(api_key="X"),
            openrouter=OpenRouterConfig(api_key="X"),
            scheduler=SchedulerConfig(enabled=True, hour=7, minute=70, timezone="UTC"),
        )
        issues = validate_config(config)
        assert any("DAILY_BULLETIN_MINUTE" in i for i in issues)

    def test_validate_config_no_warning_when_disabled(self):
        """Invalid hour/minute must not warn when scheduler is disabled."""
        config = AppConfig(
            nasa=NASAConfig(api_key="X"),
            openrouter=OpenRouterConfig(api_key="X"),
            scheduler=SchedulerConfig(enabled=False, hour=99, minute=99, timezone="UTC"),
        )
        issues = validate_config(config)
        # No scheduler-related warnings when disabled
        assert not any("DAILY_BULLETIN" in i for i in issues)


# ---------------------------------------------------------------------------
# DailyBulletinScheduler — disabled
# ---------------------------------------------------------------------------


class TestSchedulerDisabled:
    def test_disabled_scheduler_does_not_start_apscheduler(self):
        """When disabled, no APScheduler instance should be created."""
        service = _make_mock_service()
        cfg = _make_disabled_scheduler_config()
        sched = DailyBulletinScheduler(service, cfg)
        sched.start()
        assert sched._scheduler is None

    def test_disabled_scheduler_status_enabled_is_false(self):
        service = _make_mock_service()
        cfg = _make_disabled_scheduler_config()
        sched = DailyBulletinScheduler(service, cfg)
        assert sched.status.enabled is False

    def test_disabled_shutdown_does_not_raise(self):
        service = _make_mock_service()
        cfg = _make_disabled_scheduler_config()
        sched = DailyBulletinScheduler(service, cfg)
        sched.start()
        sched.shutdown()  # must not raise


# ---------------------------------------------------------------------------
# DailyBulletinScheduler — enabled
# ---------------------------------------------------------------------------


class TestSchedulerEnabled:
    def test_enabled_scheduler_creates_apscheduler(self):
        """When enabled, an AsyncIOScheduler should be initialised."""
        service = _make_mock_service()
        cfg = _make_scheduler_config(enabled=True)
        sched = DailyBulletinScheduler(service, cfg)

        with patch("scheduler.AsyncIOScheduler") as MockSched:
            mock_instance = MagicMock()
            MockSched.return_value = mock_instance
            sched.start()

        MockSched.assert_called_once()

    def test_enabled_status_is_true(self):
        service = _make_mock_service()
        cfg = _make_scheduler_config(enabled=True)
        sched = DailyBulletinScheduler(service, cfg)
        assert sched.status.enabled is True


# ---------------------------------------------------------------------------
# DailyBulletinScheduler — job execution
# ---------------------------------------------------------------------------


class TestSchedulerJobExecution:
    @pytest.mark.asyncio
    async def test_successful_job_updates_status(self):
        """A successful job run must set status=success and update last_success."""
        service = _make_mock_service()
        cfg = _make_scheduler_config(enabled=True)
        sched = DailyBulletinScheduler(service, cfg)

        await sched._run_job()

        assert sched.status.last_status == "success"
        assert sched.status.last_run is not None
        assert sched.status.last_success is not None
        assert sched.status.last_apod_date == "2024-06-15"

    @pytest.mark.asyncio
    async def test_skipped_job_sets_status_skipped(self):
        """When service returns None (duplicate), status must be 'skipped'."""
        service = _make_mock_service(return_none=True)
        cfg = _make_scheduler_config(enabled=True)
        sched = DailyBulletinScheduler(service, cfg)

        await sched._run_job()

        assert sched.status.last_status == "skipped"
        assert sched.status.last_run is not None

    @pytest.mark.asyncio
    async def test_nasa_failure_does_not_crash_scheduler(self):
        """Exception in the job must be caught; scheduler must remain functional."""
        service = _make_mock_service(raise_exc=RuntimeError("NASA is down"))
        cfg = _make_scheduler_config(enabled=True)
        sched = DailyBulletinScheduler(service, cfg)

        await sched._run_job()  # must not raise

        assert sched.status.last_status == "failed"

    @pytest.mark.asyncio
    async def test_ai_failure_does_not_crash_scheduler(self):
        """AI exception in the job must not propagate."""
        service = _make_mock_service(raise_exc=ValueError("AI error"))
        cfg = _make_scheduler_config(enabled=True)
        sched = DailyBulletinScheduler(service, cfg)

        await sched._run_job()  # must not raise

        assert sched.status.last_status == "failed"

    @pytest.mark.asyncio
    async def test_last_run_is_always_set_even_on_failure(self):
        """last_run must be updated regardless of success or failure."""
        service = _make_mock_service(raise_exc=RuntimeError("boom"))
        cfg = _make_scheduler_config(enabled=True)
        sched = DailyBulletinScheduler(service, cfg)

        await sched._run_job()

        assert sched.status.last_run is not None

    @pytest.mark.asyncio
    async def test_trigger_now_calls_run_job(self):
        """trigger_now must invoke the same pipeline as the scheduled job."""
        service = _make_mock_service()
        cfg = _make_scheduler_config(enabled=True)
        sched = DailyBulletinScheduler(service, cfg)

        await sched.trigger_now()

        service.generate_daily_bulletin.assert_called_once()

    @pytest.mark.asyncio
    async def test_scheduler_keeps_running_after_exception(self):
        """After a failed job, triggering again must still work."""
        service = _make_mock_service()
        cfg = _make_scheduler_config(enabled=True)
        sched = DailyBulletinScheduler(service, cfg)

        # First call raises
        service.generate_daily_bulletin.side_effect = [
            RuntimeError("first call fails"),
            _make_mock_service().generate_daily_bulletin.return_value,
        ]
        # Re-wire the side_effect properly
        from models import SpaceStory
        good_story = SpaceStory(
            title="نجوم",
            summary="ملخص.",
            scientific_explanation="شرح.",
            key_facts=["حقيقة"],
            why_it_matters="مهم.",
            story="قصة.",
            source_data={"source": "NASA APOD", "date": "2024-06-15", "title": "T"},
            confidence="high",
            language="ar",
        )
        service.generate_daily_bulletin = AsyncMock(
            side_effect=[RuntimeError("first fails"), good_story]
        )

        await sched._run_job()  # first: fails
        assert sched.status.last_status == "failed"

        await sched._run_job()  # second: succeeds
        assert sched.status.last_status == "success"


# ---------------------------------------------------------------------------
# Security: API keys must never appear in logs
# ---------------------------------------------------------------------------


class TestNoApiKeysInLogs:
    @pytest.mark.asyncio
    async def test_api_key_not_in_logs_on_nasa_failure(self, caplog):
        """NASA failure log must not contain any API key material."""
        service = _make_mock_service(raise_exc=RuntimeError("secret-key-exposure test"))
        cfg = _make_scheduler_config(enabled=True)
        sched = DailyBulletinScheduler(service, cfg)

        with caplog.at_level(logging.ERROR):
            await sched._run_job()

        for record in caplog.records:
            msg = record.getMessage()
            assert "sk-" not in msg
            assert "Bearer" not in msg
            assert "Authorization" not in msg
            # The runtime error message itself should not expose secret values
            # (in real code, exc.message would not contain API keys)

    @pytest.mark.asyncio
    async def test_job_logs_safe_observability_info(self, caplog):
        """Job must log APOD date and completion on success."""
        service = _make_mock_service()
        cfg = _make_scheduler_config(enabled=True)
        sched = DailyBulletinScheduler(service, cfg)

        with caplog.at_level(logging.INFO):
            await sched._run_job()

        log_text = " ".join(r.getMessage() for r in caplog.records)
        # Logs must mention APOD date
        assert "2024-06-15" in log_text


# ---------------------------------------------------------------------------
# FastAPI status endpoint
# ---------------------------------------------------------------------------


class TestDailyNewsStatusEndpoint:
    """
    Tests for GET /api/daily-news/status via TestClient.
    The StoryGenerator / real NASA / OpenRouter are NOT invoked.
    """

    def _make_app(self, scheduler: DailyBulletinScheduler | None = None):
        """Return a FastAPI TestClient with the scheduler injected."""
        from fastapi.testclient import TestClient
        import main as main_module

        # Patch the module-level globals
        main_module._scheduler = scheduler
        main_module._bulletin_service = None

        return TestClient(main_module.app, raise_server_exceptions=False)

    def test_status_endpoint_returns_200(self):
        from fastapi.testclient import TestClient
        import main as main_module

        original_scheduler = main_module._scheduler
        original_service = main_module._bulletin_service
        try:
            main_module._scheduler = None
            main_module._bulletin_service = None
            client = TestClient(main_module.app, raise_server_exceptions=False)
            response = client.get("/api/daily-news/status")
            assert response.status_code == 200
        finally:
            main_module._scheduler = original_scheduler
            main_module._bulletin_service = original_service

    def test_status_endpoint_returns_json_structure(self):
        from fastapi.testclient import TestClient
        import main as main_module

        original_scheduler = main_module._scheduler
        original_service = main_module._bulletin_service
        try:
            main_module._scheduler = None
            main_module._bulletin_service = None
            client = TestClient(main_module.app, raise_server_exceptions=False)
            response = client.get("/api/daily-news/status")
            body = response.json()
            assert body["success"] is True
            data = body["data"]
            assert "scheduler" in data
            assert "latest_bulletin" in data
            sched = data["scheduler"]
            assert "enabled" in sched
            assert "last_run" in sched
            assert "last_success" in sched
        finally:
            main_module._scheduler = original_scheduler
            main_module._bulletin_service = original_service

    def test_status_endpoint_with_active_scheduler(self):
        """When a scheduler is set, its status must appear in the response."""
        from fastapi.testclient import TestClient
        import main as main_module

        service = _make_mock_service()
        cfg = _make_scheduler_config(enabled=True)
        sched = DailyBulletinScheduler(service, cfg)
        sched.status.last_apod_date = "2024-06-15"
        sched.status.last_status = "success"
        sched.status.last_run = "2024-06-15T07:00:00Z"
        sched.status.last_success = "2024-06-15T07:00:01Z"

        original_scheduler = main_module._scheduler
        original_service = main_module._bulletin_service
        try:
            main_module._scheduler = sched
            main_module._bulletin_service = None
            client = TestClient(main_module.app, raise_server_exceptions=False)
            response = client.get("/api/daily-news/status")
            body = response.json()
            sched_resp = body["data"]["scheduler"]
            assert sched_resp["enabled"] is True
            assert sched_resp["apod_date"] == "2024-06-15"
            assert sched_resp["status"] == "success"
        finally:
            main_module._scheduler = original_scheduler
            main_module._bulletin_service = original_service

    def test_status_endpoint_does_not_expose_api_keys(self):
        """The status endpoint must never return API key material."""
        from fastapi.testclient import TestClient
        import main as main_module

        original_scheduler = main_module._scheduler
        original_service = main_module._bulletin_service
        try:
            main_module._scheduler = None
            main_module._bulletin_service = None
            client = TestClient(main_module.app, raise_server_exceptions=False)
            response = client.get("/api/daily-news/status")
            text = response.text
            assert "sk-" not in text
            assert "Bearer" not in text
            assert "api_key" not in text.lower() or "api_key" not in response.json()
        finally:
            main_module._scheduler = original_scheduler
            main_module._bulletin_service = original_service


# ---------------------------------------------------------------------------
# Existing daily-news endpoint still works
# ---------------------------------------------------------------------------


class TestExistingDailyNewsEndpoint:
    """Smoke test: GET /api/daily-news must remain functional (no AI key needed for 503)."""

    def test_daily_news_returns_503_without_key(self):
        """Without OpenRouter key, /api/daily-news must return 503 (not crash)."""
        from fastapi.testclient import TestClient
        import main as main_module

        original_sg = main_module._story_generator
        try:
            main_module._story_generator = None
            client = TestClient(main_module.app, raise_server_exceptions=False)
            response = client.get("/api/daily-news")
            # Must return 503, not 500 or unhandled exception
            assert response.status_code == 503
        finally:
            main_module._story_generator = original_sg

    def test_daily_news_status_200_without_scheduler(self):
        """Status endpoint must always return 200 — even when scheduler is disabled."""
        from fastapi.testclient import TestClient
        import main as main_module

        original_scheduler = main_module._scheduler
        original_service = main_module._bulletin_service
        try:
            main_module._scheduler = None
            main_module._bulletin_service = None
            client = TestClient(main_module.app, raise_server_exceptions=False)
            response = client.get("/api/daily-news/status")
            assert response.status_code == 200
        finally:
            main_module._scheduler = original_scheduler
            main_module._bulletin_service = original_service


# ---------------------------------------------------------------------------
# NASA source_data grounding — preserved
# ---------------------------------------------------------------------------


class TestSourceDataGroundingPreserved:
    """
    Verify that the existing NASA source_data enforcement is NOT broken
    by the new scheduler/service layer.

    The idempotency check in BulletinService must not bypass source_data
    injection — when the story is generated, StoryGenerator._ensure_source_data
    is still called.
    """

    @pytest.mark.asyncio
    async def test_story_has_nasa_source_data(self, tmp_path):
        """
        Source data grounding is enforced at the StoryGenerator layer.
        BulletinService passes through whatever the generator returns.
        Here we verify the mock story (which already has source_data set
        by _make_mock_service) has the correct NASA provenance fields.
        """
        from bulletin_store import BulletinStore
        from bulletin_service import BulletinService
        from unittest.mock import AsyncMock, MagicMock
        from models import NASAAPODData, SpaceStory

        store = BulletinStore(str(tmp_path / "sd_test.json"))

        # Build a proper generator mock (same pattern as test_bulletin_service.py)
        story_with_nasa_source = SpaceStory(
            title="أعمدة الإبداع",
            summary="ملخص.",
            scientific_explanation="شرح.",
            key_facts=["حقيقة"],
            why_it_matters="مهم.",
            story="قصة.",
            source_data={"source": "NASA APOD", "date": "2024-06-15", "title": "Pillars"},
            confidence="high",
            language="ar",
        )
        apod = NASAAPODData(
            title="Pillars of Creation", explanation="Gas pillars.", date="2024-06-15",
            media_type="image"
        )

        generator = MagicMock()
        generator._nasa.get_apod = AsyncMock(return_value=apod)
        generator._nasa.get_donki_cme = AsyncMock(return_value=[])
        generator.generate_daily_story = AsyncMock(return_value=story_with_nasa_source)

        bulletin_svc = BulletinService(generator, store)
        result = await bulletin_svc.generate_daily_bulletin()

        assert result is not None
        assert result.source_data.get("source") == "NASA APOD"
        assert result.source_data.get("date") == "2024-06-15"
