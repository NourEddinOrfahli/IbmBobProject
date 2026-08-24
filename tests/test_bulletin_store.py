"""
Tests for BulletinStore (bulletin_store.py).

No external APIs, no API keys required.
All tests use temporary files (tmp_path fixture).
"""

from __future__ import annotations

import json
import os

import pytest

from bulletin_store import BulletinRecord, BulletinStore, utc_now_iso


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_store(tmp_path) -> BulletinStore:
    return BulletinStore(str(tmp_path / "test_store.json"))


def _make_record(apod_date: str = "2024-06-15", status: str = "success") -> BulletinRecord:
    return BulletinRecord(
        apod_date=apod_date,
        status=status,
        generated_at=utc_now_iso(),
        story={"title": "نجوم", "language": "ar"} if status == "success" else None,
    )


# ---------------------------------------------------------------------------
# BulletinRecord
# ---------------------------------------------------------------------------


class TestBulletinRecord:
    def test_to_dict_round_trips(self):
        rec = _make_record()
        d = rec.to_dict()
        restored = BulletinRecord.from_dict(d)
        assert restored.apod_date == rec.apod_date
        assert restored.status == rec.status
        assert restored.story == rec.story

    def test_from_dict_missing_optional_fields(self):
        minimal = {"apod_date": "2024-01-01"}
        rec = BulletinRecord.from_dict(minimal)
        assert rec.apod_date == "2024-01-01"
        assert rec.status == "unknown"
        assert rec.story is None
        assert rec.generated_at == ""

    def test_story_is_none_for_failed_record(self):
        rec = _make_record(status="failed")
        assert rec.story is None


# ---------------------------------------------------------------------------
# BulletinStore — basic operations
# ---------------------------------------------------------------------------


class TestBulletinStoreBasic:
    def test_empty_store_has_no_latest(self, tmp_path):
        store = _make_store(tmp_path)
        assert store.get_latest() is None

    def test_empty_store_has_no_records(self, tmp_path):
        store = _make_store(tmp_path)
        assert store.get_record("2024-06-15") is None

    def test_save_and_retrieve_record(self, tmp_path):
        store = _make_store(tmp_path)
        rec = _make_record("2024-06-15", "success")
        store.save(rec)
        retrieved = store.get_record("2024-06-15")
        assert retrieved is not None
        assert retrieved.apod_date == "2024-06-15"
        assert retrieved.status == "success"

    def test_save_updates_latest(self, tmp_path):
        store = _make_store(tmp_path)
        rec = _make_record("2024-06-15", "success")
        store.save(rec)
        latest = store.get_latest()
        assert latest is not None
        assert latest.apod_date == "2024-06-15"

    def test_has_record_for_success(self, tmp_path):
        store = _make_store(tmp_path)
        store.save(_make_record("2024-06-15", "success"))
        assert store.has_record_for("2024-06-15") is True

    def test_has_record_for_missing_date(self, tmp_path):
        store = _make_store(tmp_path)
        assert store.has_record_for("2024-06-15") is False

    def test_has_record_for_failed_not_counted_as_success(self, tmp_path):
        """A failed record must NOT count as a successful bulletin."""
        store = _make_store(tmp_path)
        store.save(_make_record("2024-06-15", "failed"))
        assert store.has_record_for("2024-06-15") is False


# ---------------------------------------------------------------------------
# BulletinStore — persistence
# ---------------------------------------------------------------------------


class TestBulletinStorePersistence:
    def test_data_survives_reload(self, tmp_path):
        """Saved data must be readable after the store is recreated."""
        path = str(tmp_path / "store.json")
        store1 = BulletinStore(path)
        store1.save(_make_record("2024-06-15", "success"))

        # Reload from the same file
        store2 = BulletinStore(path)
        assert store2.has_record_for("2024-06-15") is True
        latest = store2.get_latest()
        assert latest is not None
        assert latest.apod_date == "2024-06-15"

    def test_multiple_records_persisted(self, tmp_path):
        path = str(tmp_path / "store.json")
        store = BulletinStore(path)
        store.save(_make_record("2024-06-14", "success"))
        store.save(_make_record("2024-06-15", "success"))

        store2 = BulletinStore(path)
        assert store2.has_record_for("2024-06-14") is True
        assert store2.has_record_for("2024-06-15") is True

    def test_does_not_crash_on_missing_file(self, tmp_path):
        """Store initialised with a non-existent path must start empty."""
        path = str(tmp_path / "nonexistent.json")
        store = BulletinStore(path)
        assert store.get_latest() is None

    def test_does_not_crash_on_corrupt_file(self, tmp_path):
        """A corrupt JSON file must be silently ignored."""
        path = str(tmp_path / "corrupt.json")
        with open(path, "w") as fh:
            fh.write("THIS IS NOT JSON {{{ broken")
        store = BulletinStore(path)  # must not raise
        assert store.get_latest() is None

    def test_latest_is_most_recent_generated_at(self, tmp_path):
        """Latest must point to the record with the highest generated_at."""
        path = str(tmp_path / "store.json")
        store = BulletinStore(path)

        rec_old = BulletinRecord("2024-06-14", "success", "2024-06-14T07:00:00Z", {"t": "old"})
        rec_new = BulletinRecord("2024-06-15", "success", "2024-06-15T07:00:00Z", {"t": "new"})

        store.save(rec_old)
        store.save(rec_new)

        latest = store.get_latest()
        assert latest is not None
        assert latest.apod_date == "2024-06-15"


# ---------------------------------------------------------------------------
# utc_now_iso
# ---------------------------------------------------------------------------


class TestUtcNowIso:
    def test_returns_string(self):
        ts = utc_now_iso()
        assert isinstance(ts, str)
        assert len(ts) >= 20

    def test_ends_with_z(self):
        ts = utc_now_iso()
        assert ts.endswith("Z")

    def test_contains_date_separator(self):
        ts = utc_now_iso()
        assert "T" in ts
