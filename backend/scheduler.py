"""
Daily bulletin scheduler.

Uses APScheduler's AsyncIOScheduler (pure Python, no Redis, no Celery)
to trigger BulletinService.generate_daily_bulletin() once per day at the
configured time.

Design decisions:
- The scheduler is disabled by default (DAILY_BULLETIN_ENABLED=false).
- Schedule time is configurable via env vars (DAILY_BULLETIN_HOUR/MINUTE/TIMEZONE).
- NASA APOD date is used as the idempotency key — not the server's local date.
- Any exception in the scheduled job is caught; the scheduler keeps running.
- API keys are never logged.

Usage (from main.py lifespan):
    from scheduler import DailyBulletinScheduler
    sched = DailyBulletinScheduler(bulletin_service, config.scheduler)
    sched.start()
    ...
    sched.shutdown()
"""

from __future__ import annotations

import asyncio
import logging
from typing import Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from bulletin_service import BulletinService
from config import SchedulerConfig

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Scheduler state (observable by the status endpoint)
# ---------------------------------------------------------------------------


class SchedulerStatus:
    """Mutable snapshot of scheduler runtime state (safe to expose via API)."""

    def __init__(self) -> None:
        self.enabled: bool = False
        self.last_run: Optional[str] = None          # ISO-8601 UTC
        self.last_success: Optional[str] = None      # ISO-8601 UTC
        self.last_apod_date: Optional[str] = None
        self.last_status: Optional[str] = None       # "success" | "failed" | "skipped"


# ---------------------------------------------------------------------------
# Scheduler
# ---------------------------------------------------------------------------


class DailyBulletinScheduler:
    """
    Wraps APScheduler's AsyncIOScheduler with a single daily cron job.

    Parameters
    ----------
    service:
        BulletinService instance that performs the actual pipeline work.
    config:
        SchedulerConfig (hour, minute, timezone, enabled flag).
    """

    def __init__(self, service: BulletinService, config: SchedulerConfig) -> None:
        self._service = service
        self._config = config
        self._scheduler: Optional[AsyncIOScheduler] = None
        self.status = SchedulerStatus()
        self.status.enabled = config.enabled

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Start the scheduler if enabled.  Safe to call multiple times."""
        if not self._config.enabled:
            logger.info(
                "Daily bulletin scheduler is DISABLED "
                "(set DAILY_BULLETIN_ENABLED=true to enable)."
            )
            return

        self._scheduler = AsyncIOScheduler()
        trigger = CronTrigger(
            hour=self._config.hour,
            minute=self._config.minute,
            timezone=self._config.timezone,
        )
        self._scheduler.add_job(
            self._run_job,
            trigger=trigger,
            id="daily_bulletin",
            name="Daily Space Bulletin",
            replace_existing=True,
            misfire_grace_time=3600,  # allow 1 h of misfire tolerance
        )
        self._scheduler.start()
        logger.info(
            "Daily bulletin scheduler STARTED — "
            "runs at %02d:%02d %s every day.",
            self._config.hour,
            self._config.minute,
            self._config.timezone,
        )

    def shutdown(self) -> None:
        """Stop the scheduler gracefully."""
        if self._scheduler and self._scheduler.running:
            self._scheduler.shutdown(wait=False)
            logger.info("Daily bulletin scheduler stopped.")

    # ------------------------------------------------------------------
    # Manual trigger (for testing / admin use only)
    # ------------------------------------------------------------------

    async def trigger_now(self) -> None:
        """
        Execute the job immediately — for testing or manual admin use.

        This bypasses the idempotency check (force=False is still the
        default; duplicate protection remains active).
        """
        logger.info("DailyBulletinScheduler: manual trigger requested")
        await self._run_job()

    # ------------------------------------------------------------------
    # Private — the actual job
    # ------------------------------------------------------------------

    async def _run_job(self) -> None:
        """
        Execute the bulletin pipeline.

        Any exception is caught here so the scheduler stays alive and
        the next scheduled run is unaffected.  API keys must never appear
        in logs — the underlying service already ensures that.
        """
        from bulletin_store import utc_now_iso

        run_time = utc_now_iso()
        self.status.last_run = run_time
        logger.info("Scheduled bulletin job started at %s", run_time)

        try:
            story = await self._service.generate_daily_bulletin()
        except Exception as exc:  # noqa: BLE001
            # Catch-all: keeps the scheduler alive regardless of error type.
            # Log a sanitised message — never the exception chain which might
            # contain configuration details.
            logger.error(
                "Scheduled bulletin job raised an unexpected exception: %s — "
                "scheduler will continue running.",
                type(exc).__name__,
            )
            self.status.last_status = "failed"
            return

        if story is None:
            # None means either skipped (duplicate) or a handled pipeline failure.
            # The service already logged the specific reason.
            self.status.last_status = "skipped"
            logger.info("Scheduled bulletin job: no new story produced (skipped or failed).")
        else:
            completed_at = utc_now_iso()
            self.status.last_success = completed_at
            self.status.last_apod_date = story.source_data.get("date")
            self.status.last_status = "success"
            logger.info(
                "Scheduled bulletin job completed successfully — "
                "APOD date=%s",
                self.status.last_apod_date,
            )
