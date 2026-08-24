"""
Bulletin store — lightweight JSON-file persistence for daily bulletins.

Stores one record per APOD date so the scheduler can detect duplicates
and the API can return the latest bulletin without re-generating it.

The public interface (BulletinStore) is intentionally thin so it can be
replaced by a database backend later without touching any caller.

Record schema (stored in JSON):
{
    "apod_date": "2024-06-15",
    "status": "success" | "failed",
    "generated_at": "<ISO-8601 UTC datetime>",
    "story": { ...SpaceStory fields... } | null
}

The file contains a single top-level JSON object:
{
    "latest": <most-recent record or null>,
    "records": { "<apod_date>": <record>, ... }
}
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


class BulletinRecord:
    """In-memory representation of one daily bulletin record."""

    __slots__ = ("apod_date", "status", "generated_at", "story")

    def __init__(
        self,
        apod_date: str,
        status: str,
        generated_at: str,
        story: Optional[dict[str, Any]],
    ) -> None:
        self.apod_date = apod_date
        self.status = status          # "success" | "failed"
        self.generated_at = generated_at  # ISO-8601 UTC string
        self.story = story            # SpaceStory.model_dump() or None

    def to_dict(self) -> dict[str, Any]:
        return {
            "apod_date": self.apod_date,
            "status": self.status,
            "generated_at": self.generated_at,
            "story": self.story,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BulletinRecord":
        return cls(
            apod_date=data["apod_date"],
            status=data.get("status", "unknown"),
            generated_at=data.get("generated_at", ""),
            story=data.get("story"),
        )


# ---------------------------------------------------------------------------
# Store
# ---------------------------------------------------------------------------


class BulletinStore:
    """
    Repository abstraction around a local JSON file.

    All public methods are synchronous (file I/O is fast enough for one
    record per day).  The caller (BulletinService) runs in an asyncio
    context — blocking is acceptable here because the file is tiny.
    """

    def __init__(self, path: str) -> None:
        self._path = path
        self._data: dict[str, Any] = {"latest": None, "records": {}}
        self._load()

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def has_record_for(self, apod_date: str) -> bool:
        """Return True if a successful bulletin for *apod_date* already exists."""
        record = self._data["records"].get(apod_date)
        return record is not None and record.get("status") == "success"

    def get_latest(self) -> Optional[BulletinRecord]:
        """Return the most recently saved bulletin, or None."""
        raw = self._data.get("latest")
        if raw is None:
            return None
        try:
            return BulletinRecord.from_dict(raw)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Could not deserialise latest bulletin record: %s", exc)
            return None

    def get_record(self, apod_date: str) -> Optional[BulletinRecord]:
        """Return the bulletin for a specific APOD date, or None."""
        raw = self._data["records"].get(apod_date)
        if raw is None:
            return None
        try:
            return BulletinRecord.from_dict(raw)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Could not deserialise bulletin for %s: %s", apod_date, exc)
            return None

    def save(self, record: BulletinRecord) -> None:
        """Persist a bulletin record and update the latest pointer."""
        rec_dict = record.to_dict()
        self._data["records"][record.apod_date] = rec_dict
        # Latest is the record with the most recent generated_at timestamp
        current_latest = self._data.get("latest")
        if current_latest is None or record.generated_at >= current_latest.get("generated_at", ""):
            self._data["latest"] = rec_dict
        self._persist()

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _load(self) -> None:
        if not os.path.exists(self._path):
            return
        try:
            with open(self._path, "r", encoding="utf-8") as fh:
                loaded = json.load(fh)
            if isinstance(loaded, dict):
                self._data = loaded
        except Exception as exc:  # noqa: BLE001
            logger.warning("Could not load bulletin store from %s: %s", self._path, exc)

    def _persist(self) -> None:
        try:
            with open(self._path, "w", encoding="utf-8") as fh:
                json.dump(self._data, fh, ensure_ascii=False, indent=2)
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to persist bulletin store to %s: %s", self._path, exc)


# ---------------------------------------------------------------------------
# Timestamp helper (UTC)
# ---------------------------------------------------------------------------


def utc_now_iso() -> str:
    """Return the current UTC time as an ISO-8601 string (no microseconds)."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
