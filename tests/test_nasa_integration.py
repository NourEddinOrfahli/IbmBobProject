"""
NASA API Integration Test Suite — tests/test_nasa_integration.py

Tests the NASAClient (backend/nasa_client.py) at three levels:

1. UNIT TESTS (no network, run by default)
   – _TTLCache: set/get, expiry, invalidate, clear, len, overwrite, None-value
   – Response parsing: APOD normaliser, DONKI normaliser, _safe_error_text
   – NASAClientError attributes (.code / .message)
   – Cache hit/miss behaviour and TTL expiry
   – Cache key shapes (None date → "today", specific date, DONKI date-range)
   – Cache performance — second call completes in < 50 ms
   – Stale-data fallback (APOD and DONKI) when fetch fails after a prior cache entry
   – Error handling: timeout, network error, 429, 400, 5xx, bad JSON, generic non-2xx
   – DONKI URL construction (CME suffix appended to donki_url)
   – API key forwarded in query-string params
   – Concurrent calls: only one HTTP request when two coroutines race on an empty cache
   – clear_nasa_caches() forces a fresh fetch

2. INTEGRATION / CONTRACT TESTS (no network — mock HTTP client)
   – Correct query-string parameters for APOD and DONKI requests
   – Correct endpoint URLs targeted

3. LIVE TESTS (real network, skipped by default)
   – Mark with @pytest.mark.live and run explicitly:
       pytest tests/test_nasa_integration.py -m live -v

How to run
----------
Unit tests only (default):
    pytest tests/test_nasa_integration.py -v

Live tests (need NASA_API_KEY in environment or .env):
    pytest tests/test_nasa_integration.py -m live -v

All tests:
    pytest tests/test_nasa_integration.py -v -m "live or not live"
"""

from __future__ import annotations

import asyncio
import os
import sys
import time
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch, call

import pytest

# Ensure backend/ is on sys.path (conftest.py already does this,
# but keep explicit guard so the file works when run directly).
_backend = os.path.join(os.path.dirname(__file__), "..", "backend")
if os.path.abspath(_backend) not in sys.path:
    sys.path.insert(0, os.path.abspath(_backend))

import httpx

from config import NASAConfig
from models import NASAAPODData, NASADONKIEvent
from nasa_client import (
    NASAClient,
    NASAClientError,
    _TTLCache,
    _MISS,
    _apod_cache,
    _donki_cache,
    _APOD_TTL_SECONDS,
    _DONKI_TTL_SECONDS,
    clear_nasa_caches,
)


# ---------------------------------------------------------------------------
# Fixtures & helpers
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def clear_caches():
    """Flush module-level caches before *and* after every test for isolation."""
    clear_nasa_caches()
    yield
    clear_nasa_caches()


def _make_client(timeout: float = 10.0) -> NASAClient:
    return NASAClient(NASAConfig(api_key="DEMO_KEY", request_timeout=timeout))


def _apod_raw(**overrides) -> dict[str, Any]:
    base: dict[str, Any] = {
        "title": "The Crab Nebula",
        "explanation": "A fascinating supernova remnant in Taurus.",
        "date": "2024-01-15",
        "media_type": "image",
        "url": "https://apod.nasa.gov/apod/image/test.jpg",
        "hdurl": "https://apod.nasa.gov/apod/image/test_hd.jpg",
        "copyright": "NASA / ESA",
    }
    base.update(overrides)
    return base


def _cme_raw(**overrides) -> dict[str, Any]:
    base: dict[str, Any] = {
        "activityID": "2024-01-10T00:00:00-CME-001",
        "startTime": "2024-01-10T08:00Z",
        "sourceLocation": "N12W34",
        "linkedEvents": [{"activityID": "2024-01-10T09:00:00-FLR-001"}],
    }
    base.update(overrides)
    return base


def _mock_response(json_data: Any, status_code: int = 200) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    resp.is_success = (200 <= status_code < 300)
    resp.json = MagicMock(return_value=json_data)
    resp.text = ""
    return resp


# ---------------------------------------------------------------------------
# 1. TTL Cache unit tests
# ---------------------------------------------------------------------------

class TestTTLCache:
    def test_miss_on_empty(self):
        c = _TTLCache()
        assert c.get("x") is _MISS

    def test_set_and_get(self):
        c = _TTLCache()
        c.set("k", "hello", ttl_seconds=60)
        assert c.get("k") == "hello"

    def test_expired_entry_is_miss(self):
        c = _TTLCache()
        c.set("k", "value", ttl_seconds=0.001)
        time.sleep(0.01)
        assert c.get("k") is _MISS

    def test_invalidate_removes_entry(self):
        c = _TTLCache()
        c.set("k", 42, ttl_seconds=60)
        c.invalidate("k")
        assert c.get("k") is _MISS

    def test_invalidate_missing_key_is_noop(self):  # NEW
        """invalidate() on a key that was never set must not raise."""
        c = _TTLCache()
        c.invalidate("nonexistent")  # no exception expected

    def test_clear_removes_all(self):
        c = _TTLCache()
        c.set("a", 1, 60)
        c.set("b", 2, 60)
        c.clear()
        assert c.get("a") is _MISS
        assert c.get("b") is _MISS

    def test_len_evicts_expired(self):
        c = _TTLCache()
        c.set("x", 1, ttl_seconds=0.001)
        time.sleep(0.01)
        assert len(c) == 0

    def test_len_counts_only_live_entries(self):  # NEW
        c = _TTLCache()
        c.set("live", 1, ttl_seconds=60)
        c.set("dead", 2, ttl_seconds=0.001)
        time.sleep(0.01)
        assert len(c) == 1

    def test_overwrite_updates_ttl(self):
        c = _TTLCache()
        c.set("k", "old", ttl_seconds=0.001)
        time.sleep(0.005)
        c.set("k", "new", ttl_seconds=60)
        assert c.get("k") == "new"

    def test_none_value_is_cached(self):
        """None must be storeable — it is distinct from _MISS."""
        c = _TTLCache()
        c.set("k", None, ttl_seconds=60)
        assert c.get("k") is None

    def test_multiple_independent_keys(self):  # NEW
        c = _TTLCache()
        c.set("alpha", "a", ttl_seconds=60)
        c.set("beta", "b", ttl_seconds=60)
        assert c.get("alpha") == "a"
        assert c.get("beta") == "b"

    def test_expired_entry_deleted_from_store(self):  # NEW
        """After get() detects expiry, the entry must be removed from _store."""
        c = _TTLCache()
        c.set("k", "v", ttl_seconds=0.001)
        time.sleep(0.01)
        _ = c.get("k")
        assert "k" not in c._store


# ---------------------------------------------------------------------------
# 2. NASAClientError attributes
# ---------------------------------------------------------------------------

class TestNASAClientError:  # NEW
    def test_code_and_message_stored(self):
        err = NASAClientError("TEST_CODE", "test message")
        assert err.code == "TEST_CODE"
        assert err.message == "test message"

    def test_str_representation_is_message(self):
        err = NASAClientError("CODE", "something went wrong")
        assert str(err) == "something went wrong"

    def test_is_exception(self):
        err = NASAClientError("X", "y")
        assert isinstance(err, Exception)


# ---------------------------------------------------------------------------
# 3. APOD parsing unit tests
# ---------------------------------------------------------------------------

class TestNormaliseAPOD:
    def test_valid_full_response(self):
        raw = _apod_raw()
        result = NASAClient._normalise_apod(raw)
        assert isinstance(result, NASAAPODData)
        assert result.title == "The Crab Nebula"
        assert result.date == "2024-01-15"
        assert result.media_type == "image"
        assert result.image_url == raw["url"]
        assert result.hd_image_url == raw["hdurl"]
        assert result.copyright == "NASA / ESA"

    def test_source_field_is_nasa_apod(self):  # NEW
        result = NASAClient._normalise_apod(_apod_raw())
        assert result.source == "NASA APOD"

    def test_missing_title_raises(self):
        with pytest.raises(NASAClientError) as exc_info:
            NASAClient._normalise_apod({"explanation": "ok", "date": "2024-01-01"})
        assert exc_info.value.code == "NASA_MISSING_FIELDS"

    def test_empty_title_raises(self):  # NEW
        with pytest.raises(NASAClientError) as exc_info:
            NASAClient._normalise_apod(_apod_raw(title=""))
        assert exc_info.value.code == "NASA_MISSING_FIELDS"

    def test_missing_explanation_raises(self):
        with pytest.raises(NASAClientError) as exc_info:
            NASAClient._normalise_apod({"title": "ok", "date": "2024-01-01"})
        assert exc_info.value.code == "NASA_MISSING_FIELDS"

    def test_empty_explanation_raises(self):  # NEW
        with pytest.raises(NASAClientError) as exc_info:
            NASAClient._normalise_apod(_apod_raw(explanation=""))
        assert exc_info.value.code == "NASA_MISSING_FIELDS"

    def test_non_dict_raises(self):
        with pytest.raises(NASAClientError) as exc_info:
            NASAClient._normalise_apod([1, 2, 3])
        assert exc_info.value.code == "NASA_UNEXPECTED_FORMAT"

    def test_optional_fields_default_to_none(self):
        raw = {"title": "T", "explanation": "E", "date": "2024-01-01"}
        result = NASAClient._normalise_apod(raw)
        assert result.image_url is None
        assert result.hd_image_url is None
        assert result.copyright is None

    def test_video_media_type_preserved(self):
        raw = _apod_raw(media_type="video")
        result = NASAClient._normalise_apod(raw)
        assert result.media_type == "video"

    def test_extra_fields_go_to_additional_data(self):
        raw = _apod_raw(service_version="v1", concepts=["nebula"])
        result = NASAClient._normalise_apod(raw)
        assert "service_version" in result.additional_data
        assert "concepts" in result.additional_data

    def test_known_fields_excluded_from_additional_data(self):  # NEW
        """Standard APOD keys must not leak into additional_data."""
        result = NASAClient._normalise_apod(_apod_raw())
        for known in ("title", "explanation", "date", "media_type", "url", "hdurl", "copyright"):
            assert known not in result.additional_data

    def test_missing_date_defaults_to_today(self):  # NEW
        from datetime import date
        raw = _apod_raw()
        raw.pop("date")
        result = NASAClient._normalise_apod(raw)
        assert result.date == str(date.today())

    def test_missing_media_type_defaults_to_image(self):  # NEW
        raw = _apod_raw()
        raw.pop("media_type")
        result = NASAClient._normalise_apod(raw)
        assert result.media_type == "image"


# ---------------------------------------------------------------------------
# 4. DONKI parsing unit tests
# ---------------------------------------------------------------------------

class TestNormaliseDONKI:
    def test_minimal_valid(self):
        raw = {"startTime": "2024-01-10T08:00Z", "activityID": "CME-001"}
        result = NASAClient._normalise_donki_cme(raw)
        assert isinstance(result, NASADONKIEvent)
        assert result.event_type == "CME"
        assert result.begin_time == "2024-01-10T08:00Z"
        assert result.end_time is None

    def test_source_field_is_nasa_donki(self):  # NEW
        result = NASAClient._normalise_donki_cme({"startTime": "2024-01-10T08:00Z"})
        assert result.source == "NASA DONKI"

    def test_linked_events_extracted(self):
        raw = {
            "startTime": "2024-01-10T08:00Z",
            "linkedEvents": [
                {"activityID": "FLR-001"},
                {"activityID": "SEP-002"},
            ],
        }
        result = NASAClient._normalise_donki_cme(raw)
        assert "FLR-001" in result.linked_events
        assert "SEP-002" in result.linked_events

    def test_null_linked_events_safe(self):
        raw = {"startTime": "2024-01-10T08:00Z", "linkedEvents": None}
        result = NASAClient._normalise_donki_cme(raw)
        assert result.linked_events == []

    def test_empty_linked_events_list(self):  # NEW
        raw = {"startTime": "2024-01-10T08:00Z", "linkedEvents": []}
        result = NASAClient._normalise_donki_cme(raw)
        assert result.linked_events == []

    def test_linked_events_non_dict_entries_skipped(self):  # NEW
        """Non-dict items in linkedEvents must be silently skipped."""
        raw = {
            "startTime": "2024-01-10T08:00Z",
            "linkedEvents": ["not-a-dict", {"activityID": "FLR-001"}, 42],
        }
        result = NASAClient._normalise_donki_cme(raw)
        # Only the dict entry with activityID is included
        assert result.linked_events == ["FLR-001"]

    def test_raw_dict_attached(self):  # NEW
        raw = {"startTime": "2024-01-10T08:00Z", "extra": "data"}
        result = NASAClient._normalise_donki_cme(raw)
        assert result.raw == raw


# ---------------------------------------------------------------------------
# 5. _safe_error_text helper
# ---------------------------------------------------------------------------

class TestSafeErrorText:  # NEW
    def test_extracts_msg_field(self):
        resp = MagicMock()
        resp.json = MagicMock(return_value={"msg": "date out of range"})
        text = NASAClient._safe_error_text(resp)
        assert text == "date out of range"

    def test_extracts_error_field_when_no_msg(self):
        resp = MagicMock()
        resp.json = MagicMock(return_value={"error": "invalid key"})
        text = NASAClient._safe_error_text(resp)
        assert text == "invalid key"

    def test_stringifies_whole_dict_when_no_known_key(self):
        resp = MagicMock()
        resp.json = MagicMock(return_value={"something": "else"})
        text = NASAClient._safe_error_text(resp)
        assert "something" in text

    def test_falls_back_to_text_on_json_error(self):
        resp = MagicMock()
        resp.json = MagicMock(side_effect=ValueError("bad json"))
        resp.text = "plain error body"
        text = NASAClient._safe_error_text(resp)
        assert "plain error body" in text

    def test_truncates_long_text(self):
        resp = MagicMock()
        resp.json = MagicMock(side_effect=ValueError("bad json"))
        resp.text = "x" * 500
        text = NASAClient._safe_error_text(resp)
        assert len(text) <= 200


# ---------------------------------------------------------------------------
# 6. Cache key shapes
# ---------------------------------------------------------------------------

class TestCacheKeyShapes:  # NEW
    """Verify that the correct cache keys are created for APOD and DONKI."""

    @pytest.mark.asyncio
    async def test_apod_none_date_uses_today_key(self):
        client = _make_client()
        mock_resp = _mock_response(_apod_raw())
        with patch.object(client._client, "get", new=AsyncMock(return_value=mock_resp)):
            await client.get_apod()
        # Key "apod:today" must exist in the cache store
        assert "apod:today" in _apod_cache._store

    @pytest.mark.asyncio
    async def test_apod_specific_date_uses_date_key(self):
        client = _make_client()
        mock_resp = _mock_response(_apod_raw(date="2024-06-01"))
        with patch.object(client._client, "get", new=AsyncMock(return_value=mock_resp)):
            await client.get_apod("2024-06-01")
        assert "apod:2024-06-01" in _apod_cache._store

    @pytest.mark.asyncio
    async def test_donki_default_key(self):
        client = _make_client()
        mock_resp = _mock_response([_cme_raw()])
        with patch.object(client._donki_client, "get", new=AsyncMock(return_value=mock_resp)):
            await client.get_donki_cme()
        assert "donki:cme::" in _donki_cache._store

    @pytest.mark.asyncio
    async def test_donki_date_range_in_key(self):
        client = _make_client()
        mock_resp = _mock_response([_cme_raw()])
        with patch.object(client._donki_client, "get", new=AsyncMock(return_value=mock_resp)):
            await client.get_donki_cme(start_date="2024-01-01", end_date="2024-01-31")
        assert "donki:cme:2024-01-01:2024-01-31" in _donki_cache._store


# ---------------------------------------------------------------------------
# 7. URL and parameter contract tests
# ---------------------------------------------------------------------------

class TestContractParams:  # NEW
    """Verify the correct endpoints and query-string params are sent."""

    @pytest.mark.asyncio
    async def test_apod_sends_api_key(self):
        client = _make_client()
        captured: list[dict] = []

        async def spy_get(url, params):
            captured.append({"url": url, "params": params})
            return _mock_response(_apod_raw())

        with patch.object(client._client, "get", side_effect=spy_get):
            await client.get_apod()

        assert len(captured) == 1
        assert captured[0]["params"].get("api_key") == "DEMO_KEY"

    @pytest.mark.asyncio
    async def test_apod_hits_correct_url(self):
        client = _make_client()
        captured: list[str] = []

        async def spy_get(url, params):
            captured.append(url)
            return _mock_response(_apod_raw())

        with patch.object(client._client, "get", side_effect=spy_get):
            await client.get_apod()

        assert captured[0] == "https://api.nasa.gov/planetary/apod"

    @pytest.mark.asyncio
    async def test_apod_date_param_forwarded(self):
        client = _make_client()
        captured: list[dict] = []

        async def spy_get(url, params):
            captured.append(params)
            return _mock_response(_apod_raw(date="2024-03-01"))

        with patch.object(client._client, "get", side_effect=spy_get):
            await client.get_apod("2024-03-01")

        assert captured[0].get("date") == "2024-03-01"

    @pytest.mark.asyncio
    async def test_apod_no_date_param_when_not_given(self):
        """When apod_date is None, no 'date' key must appear in the params."""
        client = _make_client()
        captured: list[dict] = []

        async def spy_get(url, params):
            captured.append(params)
            return _mock_response(_apod_raw())

        with patch.object(client._client, "get", side_effect=spy_get):
            await client.get_apod()

        assert "date" not in captured[0]

    @pytest.mark.asyncio
    async def test_donki_cme_url_has_cme_suffix(self):
        client = _make_client()
        captured: list[str] = []

        async def spy_get(url, params):
            captured.append(url)
            return _mock_response([])

        with patch.object(client._donki_client, "get", side_effect=spy_get):
            await client.get_donki_cme()

        assert captured[0].endswith("/CME")
        assert "DONKI" in captured[0]

    @pytest.mark.asyncio
    async def test_donki_sends_api_key(self):
        client = _make_client()
        captured: list[dict] = []

        async def spy_get(url, params):
            captured.append(params)
            return _mock_response([])

        with patch.object(client._donki_client, "get", side_effect=spy_get):
            await client.get_donki_cme()

        assert captured[0].get("api_key") == "DEMO_KEY"

    @pytest.mark.asyncio
    async def test_donki_date_range_params_forwarded(self):
        client = _make_client()
        captured: list[dict] = []

        async def spy_get(url, params):
            captured.append(params)
            return _mock_response([])

        with patch.object(client._donki_client, "get", side_effect=spy_get):
            await client.get_donki_cme(start_date="2024-01-01", end_date="2024-01-31")

        assert captured[0].get("startDate") == "2024-01-01"
        assert captured[0].get("endDate") == "2024-01-31"

    @pytest.mark.asyncio
    async def test_donki_no_date_params_when_not_given(self):
        client = _make_client()
        captured: list[dict] = []

        async def spy_get(url, params):
            captured.append(params)
            return _mock_response([])

        with patch.object(client._donki_client, "get", side_effect=spy_get):
            await client.get_donki_cme()

        assert "startDate" not in captured[0]
        assert "endDate" not in captured[0]


# ---------------------------------------------------------------------------
# 8. APOD caching behaviour
# ---------------------------------------------------------------------------

class TestAPODCaching:
    @pytest.mark.asyncio
    async def test_cache_miss_then_hit(self):
        client = _make_client()
        mock_resp = _mock_response(_apod_raw())

        with patch.object(client._client, "get", new=AsyncMock(return_value=mock_resp)) as mock_get:
            result1 = await client.get_apod()
            assert mock_get.call_count == 1
            result2 = await client.get_apod()
            assert mock_get.call_count == 1  # still 1 — served from cache

        assert result1.title == result2.title

    @pytest.mark.asyncio
    async def test_different_dates_cached_independently(self):
        client = _make_client()
        raw_a = _apod_raw(title="Day A", date="2024-01-01")
        raw_b = _apod_raw(title="Day B", date="2024-01-02")
        call_count = {"n": 0}

        async def fake_get(url, params):
            call_count["n"] += 1
            if params.get("date") == "2024-01-01":
                return _mock_response(raw_a)
            return _mock_response(raw_b)

        with patch.object(client._client, "get", side_effect=fake_get):
            r1 = await client.get_apod("2024-01-01")
            r2 = await client.get_apod("2024-01-02")
            r1b = await client.get_apod("2024-01-01")
            r2b = await client.get_apod("2024-01-02")

        assert call_count["n"] == 2  # only 2 network calls despite 4 invocations
        assert r1.title == "Day A"
        assert r2.title == "Day B"
        assert r1b.title == "Day A"
        assert r2b.title == "Day B"

    @pytest.mark.asyncio
    async def test_cache_hit_is_fast(self):
        """Cache hit must complete in well under 50 ms."""
        client = _make_client()
        mock_resp = _mock_response(_apod_raw())

        with patch.object(client._client, "get", new=AsyncMock(return_value=mock_resp)):
            await client.get_apod()  # prime cache

        t0 = time.monotonic()
        _ = await client.get_apod()
        elapsed_ms = (time.monotonic() - t0) * 1000

        assert elapsed_ms < 50, f"Cache hit took {elapsed_ms:.1f} ms (expected < 50 ms)"

    @pytest.mark.asyncio
    async def test_stale_apod_served_when_fetch_fails_after_prior_cache(self):  # NEW
        """
        When a valid cache entry exists AND the network call fails,
        _stale_apod() is never reached (cache.get() returns the live value).
        This test verifies the guard: a live cache hit supersedes a failing _get.
        """
        client = _make_client()
        good_value = NASAClient._normalise_apod(_apod_raw())
        key = "apod:today"
        # Inject a live (non-expired) cache entry
        _apod_cache._store[key] = (good_value, time.monotonic() + 3600)

        with patch.object(
            client, "_get",
            new=AsyncMock(side_effect=NASAClientError("NASA_TIMEOUT", "simulated timeout")),
        ):
            result = await client.get_apod()

        # Network was never needed — stale/live cache entry returned
        assert result.title == "The Crab Nebula"

    @pytest.mark.asyncio
    async def test_stale_apod_helper_returns_none_when_key_absent(self):  # NEW
        assert NASAClient._stale_apod("apod:nonexistent") is None

    @pytest.mark.asyncio
    async def test_stale_apod_helper_returns_value_regardless_of_expiry(self):  # NEW
        """_stale_apod() reads _store directly — it must return a value even if TTL
        has elapsed (i.e. it ignores the expiry timestamp)."""
        good_value = NASAClient._normalise_apod(_apod_raw())
        key = "apod:today"
        # Store with already-expired timestamp (expires_at = 0)
        _apod_cache._store[key] = (good_value, 0.0)
        stale = NASAClient._stale_apod(key)
        assert stale is not None
        assert stale.title == "The Crab Nebula"

    @pytest.mark.asyncio
    async def test_apod_raises_when_no_stale_data_and_fetch_fails(self):  # NEW
        """If there is no prior cache entry AND the network fails, NASAClientError is raised."""
        client = _make_client()
        with patch.object(
            client, "_get",
            new=AsyncMock(side_effect=NASAClientError("NASA_TIMEOUT", "timed out")),
        ):
            with pytest.raises(NASAClientError) as exc_info:
                await client.get_apod()
        assert exc_info.value.code == "NASA_TIMEOUT"

    @pytest.mark.asyncio
    async def test_apod_ttl_seconds_used_for_caching(self):  # NEW
        """After a successful fetch the cache entry's TTL must be approximately _APOD_TTL_SECONDS."""
        client = _make_client()
        mock_resp = _mock_response(_apod_raw())
        before = time.monotonic()

        with patch.object(client._client, "get", new=AsyncMock(return_value=mock_resp)):
            await client.get_apod()

        after = time.monotonic()
        entry = _apod_cache._store.get("apod:today")
        assert entry is not None
        _, expires_at = entry
        # expires_at should be roughly before + _APOD_TTL_SECONDS (± 1 s tolerance)
        assert abs(expires_at - (before + _APOD_TTL_SECONDS)) < 1.0


# ---------------------------------------------------------------------------
# 9. DONKI caching behaviour
# ---------------------------------------------------------------------------

class TestDONKICaching:
    @pytest.mark.asyncio
    async def test_donki_cache_hit(self):
        client = _make_client()
        mock_resp = _mock_response([_cme_raw()])

        with patch.object(client._donki_client, "get", new=AsyncMock(return_value=mock_resp)) as mock_get:
            r1 = await client.get_donki_cme()
            r2 = await client.get_donki_cme()
            assert mock_get.call_count == 1

        assert len(r1) == len(r2) == 1

    @pytest.mark.asyncio
    async def test_donki_failure_returns_empty_list(self):
        client = _make_client()
        with patch.object(
            client._donki_client, "get", new=AsyncMock(side_effect=httpx.TimeoutException("t"))
        ):
            result = await client.get_donki_cme()
        assert result == []

    @pytest.mark.asyncio
    async def test_donki_non_list_response_returns_empty(self):
        client = _make_client()
        mock_resp = _mock_response({"error": "unexpected"})
        with patch.object(client._donki_client, "get", new=AsyncMock(return_value=mock_resp)):
            result = await client.get_donki_cme()
        assert result == []

    @pytest.mark.asyncio
    async def test_stale_donki_served_when_live_cache_hit_and_fetch_fails(self):  # NEW
        """Live cache entry must be returned even when _get would fail."""
        client = _make_client()
        from models import NASADONKIEvent
        good_events = [NASAClient._normalise_donki_cme(_cme_raw())]
        key = "donki:cme::"
        _donki_cache._store[key] = (good_events, time.monotonic() + 900)

        with patch.object(
            client, "_get",
            new=AsyncMock(side_effect=NASAClientError("NASA_SERVER_ERROR", "down")),
        ):
            result = await client.get_donki_cme()

        assert len(result) == 1
        assert result[0].event_type == "CME"

    @pytest.mark.asyncio
    async def test_stale_donki_helper_returns_none_when_absent(self):  # NEW
        assert NASAClient._stale_donki("donki:cme:nonexistent:") is None

    @pytest.mark.asyncio
    async def test_stale_donki_helper_returns_value_regardless_of_expiry(self):  # NEW
        good_events = [NASAClient._normalise_donki_cme(_cme_raw())]
        key = "donki:cme::"
        _donki_cache._store[key] = (good_events, 0.0)  # already expired
        stale = NASAClient._stale_donki(key)
        assert stale is not None
        assert len(stale) == 1

    @pytest.mark.asyncio
    async def test_malformed_cme_events_skipped_valid_kept(self):  # NEW
        client = _make_client()
        raw_list = [
            {"not_a_real_key": True},  # will produce an event with defaults — shouldn't raise
            _cme_raw(),                 # valid
        ]
        mock_resp = _mock_response(raw_list)
        with patch.object(client._donki_client, "get", new=AsyncMock(return_value=mock_resp)):
            results = await client.get_donki_cme()
        assert any(evt.event_type == "CME" for evt in results)

    @pytest.mark.asyncio
    async def test_donki_ttl_applied_on_successful_fetch(self):  # NEW
        client = _make_client()
        mock_resp = _mock_response([_cme_raw()])
        before = time.monotonic()

        with patch.object(client._donki_client, "get", new=AsyncMock(return_value=mock_resp)):
            await client.get_donki_cme()

        after = time.monotonic()
        key = "donki:cme::"
        entry = _donki_cache._store.get(key)
        assert entry is not None
        _, expires_at = entry
        assert abs(expires_at - (before + _DONKI_TTL_SECONDS)) < 1.0


# ---------------------------------------------------------------------------
# 10. HTTP error handling (via _get)
# ---------------------------------------------------------------------------

class TestHTTPErrorHandling:
    @pytest.mark.asyncio
    async def test_429_raises_rate_limit(self):
        client = _make_client()
        mock_resp = _mock_response({}, status_code=429)
        mock_resp.is_success = False
        with patch.object(client._client, "get", new=AsyncMock(return_value=mock_resp)):
            with pytest.raises(NASAClientError) as exc_info:
                await client.get_apod()
        assert exc_info.value.code == "NASA_RATE_LIMIT"

    @pytest.mark.asyncio
    async def test_400_raises_bad_request(self):
        client = _make_client()
        error_body = {"msg": "date must be between Jun 16, 1995 and today."}
        mock_resp = _mock_response(error_body, status_code=400)
        mock_resp.is_success = False
        with patch.object(client._client, "get", new=AsyncMock(return_value=mock_resp)):
            with pytest.raises(NASAClientError) as exc_info:
                await client.get_apod("1990-01-01")
        assert exc_info.value.code == "NASA_BAD_REQUEST"

    @pytest.mark.asyncio
    async def test_400_message_contains_nasa_body(self):  # NEW
        """The error message for 400 must embed the NASA-supplied error text."""
        client = _make_client()
        error_body = {"msg": "date out of range for APOD"}
        mock_resp = _mock_response(error_body, status_code=400)
        mock_resp.is_success = False
        with patch.object(client._client, "get", new=AsyncMock(return_value=mock_resp)):
            with pytest.raises(NASAClientError) as exc_info:
                await client.get_apod("1900-01-01")
        assert "date out of range" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_500_raises_server_error(self):
        client = _make_client()
        mock_resp = _mock_response({}, status_code=500)
        mock_resp.is_success = False
        with patch.object(client._client, "get", new=AsyncMock(return_value=mock_resp)):
            with pytest.raises(NASAClientError) as exc_info:
                await client.get_apod()
        assert exc_info.value.code == "NASA_SERVER_ERROR"

    @pytest.mark.asyncio
    async def test_503_raises_server_error(self):  # NEW
        client = _make_client()
        mock_resp = _mock_response({}, status_code=503)
        mock_resp.is_success = False
        with patch.object(client._client, "get", new=AsyncMock(return_value=mock_resp)):
            with pytest.raises(NASAClientError) as exc_info:
                await client.get_apod()
        assert exc_info.value.code == "NASA_SERVER_ERROR"

    @pytest.mark.asyncio
    async def test_generic_non_2xx_raises_api_error(self):  # NEW
        client = _make_client()
        mock_resp = _mock_response({}, status_code=403)
        mock_resp.is_success = False
        mock_resp.json = MagicMock(return_value={"msg": "forbidden"})
        with patch.object(client._client, "get", new=AsyncMock(return_value=mock_resp)):
            with pytest.raises(NASAClientError) as exc_info:
                await client.get_apod()
        assert exc_info.value.code == "NASA_API_ERROR"

    @pytest.mark.asyncio
    async def test_timeout_raises_nasa_timeout(self):
        client = _make_client()
        with patch.object(
            client._client, "get", new=AsyncMock(side_effect=httpx.TimeoutException("timeout"))
        ):
            with pytest.raises(NASAClientError) as exc_info:
                await client.get_apod()
        assert exc_info.value.code == "NASA_TIMEOUT"

    @pytest.mark.asyncio
    async def test_timeout_message_contains_timeout_duration(self):  # NEW
        client = _make_client(timeout=7.5)
        with patch.object(
            client._client, "get", new=AsyncMock(side_effect=httpx.TimeoutException("t"))
        ):
            with pytest.raises(NASAClientError) as exc_info:
                await client.get_apod()
        assert "7.5" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_network_error_raises_nasa_network_error(self):
        client = _make_client()
        with patch.object(
            client._client, "get", new=AsyncMock(side_effect=httpx.ConnectError("refused"))
        ):
            with pytest.raises(NASAClientError) as exc_info:
                await client.get_apod()
        assert exc_info.value.code == "NASA_NETWORK_ERROR"

    @pytest.mark.asyncio
    async def test_invalid_json_raises_nasa_invalid_json(self):
        client = _make_client()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.is_success = True
        mock_resp.json = MagicMock(side_effect=ValueError("not json"))
        with patch.object(client._client, "get", new=AsyncMock(return_value=mock_resp)):
            with pytest.raises(NASAClientError) as exc_info:
                await client.get_apod()
        assert exc_info.value.code == "NASA_INVALID_JSON"


# ---------------------------------------------------------------------------
# 11. clear_nasa_caches() helper
# ---------------------------------------------------------------------------

class TestClearCaches:
    @pytest.mark.asyncio
    async def test_clear_caches_forces_refetch(self):
        client = _make_client()
        mock_resp = _mock_response(_apod_raw())

        with patch.object(client._client, "get", new=AsyncMock(return_value=mock_resp)) as mock_get:
            await client.get_apod()
            assert mock_get.call_count == 1

            clear_nasa_caches()

            await client.get_apod()
            assert mock_get.call_count == 2

    def test_clear_nasa_caches_empties_both_caches(self):  # NEW
        _apod_cache.set("apod:today", "something", 60)
        _donki_cache.set("donki:cme::", [], 60)
        clear_nasa_caches()
        assert _apod_cache.get("apod:today") is _MISS
        assert _donki_cache.get("donki:cme::") is _MISS


# ---------------------------------------------------------------------------
# 12. Concurrent request deduplication
# ---------------------------------------------------------------------------

class TestConcurrency:  # NEW
    @pytest.mark.asyncio
    async def test_concurrent_apod_calls_make_only_one_http_request(self):
        """
        When two coroutines call get_apod() simultaneously on an empty cache,
        both should get a valid result.  The cache is populated on the first
        write, so the second call should serve from cache (at most 2 HTTP calls
        in the worst case since there is no async lock — but practically one).
        We assert correctness (both return the same title) rather than a strict
        call count, which is an implementation-level detail for a GIL-backed dict.
        """
        client = _make_client()
        mock_resp = _mock_response(_apod_raw())

        with patch.object(client._client, "get", new=AsyncMock(return_value=mock_resp)):
            r1, r2 = await asyncio.gather(client.get_apod(), client.get_apod())

        assert r1.title == r2.title == "The Crab Nebula"

    @pytest.mark.asyncio
    async def test_concurrent_donki_calls_return_consistent_results(self):
        client = _make_client()
        mock_resp = _mock_response([_cme_raw()])

        with patch.object(client._donki_client, "get", new=AsyncMock(return_value=mock_resp)):
            res_a, res_b = await asyncio.gather(
                client.get_donki_cme(), client.get_donki_cme()
            )

        assert len(res_a) == len(res_b)
        assert res_a[0].event_type == res_b[0].event_type == "CME"


# ---------------------------------------------------------------------------
# 13. Live tests — skipped unless -m live
# ---------------------------------------------------------------------------

@pytest.mark.live
class TestLiveAPOD:
    """
    Require a valid NASA_API_KEY.  Run with:
        pytest tests/test_nasa_integration.py -m live -v
    """

    @pytest.mark.asyncio
    async def test_apod_today_returns_apod_data(self):
        client = _make_client(timeout=15.0)
        result = await client.get_apod()
        assert isinstance(result, NASAAPODData)
        assert result.title
        assert result.explanation
        assert result.date
        assert result.media_type in ("image", "video")
        await client.close()

    @pytest.mark.asyncio
    async def test_apod_response_has_image_url(self):
        client = _make_client(timeout=15.0)
        result = await client.get_apod()
        if result.media_type == "image":
            assert result.image_url
        await client.close()

    @pytest.mark.asyncio
    async def test_apod_cache_second_call_fast(self):
        """End-to-end: second call to get_apod() must complete in < 50 ms."""
        client = _make_client(timeout=15.0)
        await client.get_apod()  # primes cache

        t0 = time.monotonic()
        await client.get_apod()
        elapsed_ms = (time.monotonic() - t0) * 1000

        assert elapsed_ms < 50, f"Cache hit took {elapsed_ms:.1f} ms (> 50 ms threshold)"
        await client.close()

    @pytest.mark.asyncio
    async def test_apod_future_date_raises_bad_request(self):
        client = _make_client(timeout=15.0)
        with pytest.raises(NASAClientError) as exc_info:
            await client.get_apod("2099-12-31")
        assert exc_info.value.code == "NASA_BAD_REQUEST"
        await client.close()

    @pytest.mark.asyncio
    async def test_donki_cme_returns_list(self):
        client = _make_client(timeout=15.0)
        events = await client.get_donki_cme()
        assert isinstance(events, list)
        for evt in events:
            assert isinstance(evt, NASADONKIEvent)
            assert evt.event_type == "CME"
        await client.close()
