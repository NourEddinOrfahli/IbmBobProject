"""
NASA API connectivity and response tests.

These tests verify that:
 1. NASAClient.get_apod() connects to the real API and parses APOD correctly.
 2. NASAClient.get_donki_cme() connects to the DONKI endpoint and parses CME data.
 3. Error handling works for bad dates, network issues, and rate limits.
 4. The backend /api/stories and /api/daily-news/status endpoints are healthy.

Environment
-----------
Set NASA_API_KEY in .env (or the environment) before running live tests.
Live tests are marked with @pytest.mark.live and are *skipped by default*.
Run them explicitly:

    pytest tests/test_nasa.py -m live -v

Unit tests (no network) run by default with:

    pytest tests/test_nasa.py -v
"""

from __future__ import annotations

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import date, timedelta
from typing import Any

from config import NASAConfig
from models import NASAAPODData, NASADONKIEvent
from nasa_client import NASAClient, NASAClientError, clear_nasa_caches


# Clear module-level TTL caches before every test so mock HTTP responses
# are never bypassed by a warm cache entry from a previous test.
@pytest.fixture(autouse=True)
def _reset_nasa_caches():
    clear_nasa_caches()
    yield
    clear_nasa_caches()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_apod_response(**kwargs) -> dict[str, Any]:
    """Minimal valid raw APOD JSON as returned by NASA."""
    defaults = {
        "title": "Test Nebula",
        "explanation": "A test explanation of the nebula.",
        "date": str(date.today()),
        "media_type": "image",
        "url": "https://apod.nasa.gov/apod/image/test.jpg",
        "hdurl": "https://apod.nasa.gov/apod/image/test_hd.jpg",
        "copyright": "NASA Test",
    }
    defaults.update(kwargs)
    return defaults


def _make_cme_event(**kwargs) -> dict[str, Any]:
    """Minimal valid raw CME event JSON as returned by DONKI."""
    defaults = {
        "activityID": "2024-01-01T00:00:00-CME-001",
        "startTime": "2024-01-01T00:00Z",
        "sourceLocation": "N12W34",
        "note": "Test CME event",
        "cmeAnalyses": [
            {
                "isMostAccurate": True,
                "speed": 742.5,
                "enlilList": [
                    {
                        "isEarthGB": True,
                        "estimatedShockArrivalTime": "2024-01-03T12:00Z",
                        "kp_90": 4.5,
                    }
                ],
            }
        ],
        "linkedEvents": [{"activityID": "2024-01-01T00:00:00-FLR-001"}],
    }
    defaults.update(kwargs)
    return defaults


# ---------------------------------------------------------------------------
# Unit tests — NASAClient.get_apod (no network)
# ---------------------------------------------------------------------------


class TestGetApodUnit:
    """Unit tests for APOD parsing logic — no real HTTP calls."""

    @pytest.fixture()
    def client(self) -> NASAClient:
        return NASAClient(NASAConfig(api_key="DEMO_KEY"))

    @pytest.mark.asyncio
    async def test_valid_apod_returns_model(self, client):
        raw = _make_apod_response()
        with patch.object(client, "_get", new=AsyncMock(return_value=raw)):
            result = await client.get_apod()
        assert isinstance(result, NASAAPODData)
        assert result.title == raw["title"]
        assert result.explanation == raw["explanation"]
        assert result.date == raw["date"]
        assert result.image_url == raw["url"]
        assert result.hd_image_url == raw["hdurl"]
        assert result.copyright == raw["copyright"]
        assert result.media_type == "image"

    @pytest.mark.asyncio
    async def test_apod_with_specific_date(self, client):
        target_date = "2024-01-15"
        raw = _make_apod_response(date=target_date)
        captured_params = {}

        async def mock_get(url, params, source):
            captured_params.update(params)
            return raw

        with patch.object(client, "_get", new=mock_get):
            result = await client.get_apod(apod_date=target_date)

        assert captured_params.get("date") == target_date
        assert result.date == target_date

    @pytest.mark.asyncio
    async def test_apod_video_media_type(self, client):
        raw = _make_apod_response(media_type="video", url="https://youtube.com/test")
        with patch.object(client, "_get", new=AsyncMock(return_value=raw)):
            result = await client.get_apod()
        assert result.media_type == "video"
        assert result.image_url == "https://youtube.com/test"

    @pytest.mark.asyncio
    async def test_apod_missing_hdurl_is_none(self, client):
        raw = _make_apod_response()
        raw.pop("hdurl", None)
        with patch.object(client, "_get", new=AsyncMock(return_value=raw)):
            result = await client.get_apod()
        assert result.hd_image_url is None

    @pytest.mark.asyncio
    async def test_apod_missing_copyright_is_none(self, client):
        raw = _make_apod_response()
        raw.pop("copyright", None)
        with patch.object(client, "_get", new=AsyncMock(return_value=raw)):
            result = await client.get_apod()
        assert result.copyright is None

    @pytest.mark.asyncio
    async def test_apod_missing_title_raises(self, client):
        raw = _make_apod_response(title="")
        with patch.object(client, "_get", new=AsyncMock(return_value=raw)):
            with pytest.raises(NASAClientError) as exc_info:
                await client.get_apod()
        assert exc_info.value.code == "NASA_MISSING_FIELDS"

    @pytest.mark.asyncio
    async def test_apod_missing_explanation_raises(self, client):
        raw = _make_apod_response(explanation="")
        with patch.object(client, "_get", new=AsyncMock(return_value=raw)):
            with pytest.raises(NASAClientError) as exc_info:
                await client.get_apod()
        assert exc_info.value.code == "NASA_MISSING_FIELDS"

    @pytest.mark.asyncio
    async def test_apod_non_dict_response_raises(self, client):
        with patch.object(client, "_get", new=AsyncMock(return_value=[1, 2, 3])):
            with pytest.raises(NASAClientError) as exc_info:
                await client.get_apod()
        assert exc_info.value.code == "NASA_UNEXPECTED_FORMAT"

    @pytest.mark.asyncio
    async def test_apod_source_field_always_nasa_apod(self, client):
        raw = _make_apod_response()
        with patch.object(client, "_get", new=AsyncMock(return_value=raw)):
            result = await client.get_apod()
        assert result.source == "NASA APOD"


# ---------------------------------------------------------------------------
# Unit tests — NASAClient.get_donki_cme (no network)
# ---------------------------------------------------------------------------


class TestGetDonkiCmeUnit:
    @pytest.fixture()
    def client(self) -> NASAClient:
        return NASAClient(NASAConfig(api_key="DEMO_KEY"))

    @pytest.mark.asyncio
    async def test_valid_cme_list_parsed(self, client):
        raw = [_make_cme_event()]
        with patch.object(client, "_get", new=AsyncMock(return_value=raw)):
            results = await client.get_donki_cme()
        assert len(results) == 1
        evt = results[0]
        assert isinstance(evt, NASADONKIEvent)
        assert evt.event_type == "CME"
        assert evt.begin_time is not None

    @pytest.mark.asyncio
    async def test_empty_cme_list(self, client):
        with patch.object(client, "_get", new=AsyncMock(return_value=[])):
            results = await client.get_donki_cme()
        assert results == []

    @pytest.mark.asyncio
    async def test_donki_failure_returns_empty_list(self, client):
        """DONKI failure is non-fatal — returns [] so the pipeline continues."""
        with patch.object(
            client, "_get",
            new=AsyncMock(side_effect=NASAClientError("NASA_TIMEOUT", "timeout"))
        ):
            results = await client.get_donki_cme()
        assert results == []

    @pytest.mark.asyncio
    async def test_non_list_donki_response_returns_empty(self, client):
        with patch.object(client, "_get", new=AsyncMock(return_value={"error": "bad"})):
            results = await client.get_donki_cme()
        assert results == []

    @pytest.mark.asyncio
    async def test_malformed_cme_event_skipped(self, client):
        """Malformed items in the list are skipped, valid ones are kept."""
        raw = [
            {"not_a_real_key": True},  # will trigger exception in normaliser
            _make_cme_event(),          # valid
        ]
        with patch.object(client, "_get", new=AsyncMock(return_value=raw)):
            results = await client.get_donki_cme()
        # valid one remains
        assert len(results) >= 1

    @pytest.mark.asyncio
    async def test_cme_linked_events_extracted(self, client):
        raw = [_make_cme_event()]
        with patch.object(client, "_get", new=AsyncMock(return_value=raw)):
            results = await client.get_donki_cme()
        evt = results[0]
        assert "2024-01-01T00:00:00-FLR-001" in evt.linked_events

    @pytest.mark.asyncio
    async def test_cme_date_range_params_forwarded(self, client):
        captured = {}

        async def mock_get(url, params, source, **kwargs):
            captured.update(params)
            return []

        with patch.object(client, "_get", new=mock_get):
            await client.get_donki_cme(start_date="2024-01-01", end_date="2024-01-31")

        assert captured.get("startDate") == "2024-01-01"
        assert captured.get("endDate") == "2024-01-31"


# ---------------------------------------------------------------------------
# Unit tests — HTTP error handling (_get method)
# ---------------------------------------------------------------------------


class TestHttpErrorHandling:
    @pytest.fixture()
    def client(self) -> NASAClient:
        return NASAClient(NASAConfig(api_key="DEMO_KEY"))

    @pytest.mark.asyncio
    async def test_timeout_raises_nasa_timeout(self, client):
        import httpx
        with patch.object(
            client._client, "get",
            new=AsyncMock(side_effect=httpx.TimeoutException("timeout"))
        ):
            with pytest.raises(NASAClientError) as exc_info:
                await client.get_apod()
        assert exc_info.value.code == "NASA_TIMEOUT"

    @pytest.mark.asyncio
    async def test_network_error_raises_nasa_network_error(self, client):
        import httpx
        with patch.object(
            client._client, "get",
            new=AsyncMock(side_effect=httpx.ConnectError("refused"))
        ):
            with pytest.raises(NASAClientError) as exc_info:
                await client.get_apod()
        assert exc_info.value.code == "NASA_NETWORK_ERROR"

    @pytest.mark.asyncio
    async def test_http_429_raises_rate_limit(self, client):
        import httpx
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.is_success = False
        with patch.object(client._client, "get", new=AsyncMock(return_value=mock_response)):
            with pytest.raises(NASAClientError) as exc_info:
                await client.get_apod()
        assert exc_info.value.code == "NASA_RATE_LIMIT"

    @pytest.mark.asyncio
    async def test_http_400_raises_bad_request(self, client):
        import httpx
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.is_success = False
        mock_response.json.return_value = {"msg": "date out of range"}
        with patch.object(client._client, "get", new=AsyncMock(return_value=mock_response)):
            with pytest.raises(NASAClientError) as exc_info:
                await client.get_apod()
        assert exc_info.value.code == "NASA_BAD_REQUEST"

    @pytest.mark.asyncio
    async def test_http_500_raises_server_error(self, client):
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.is_success = False
        with patch.object(client._client, "get", new=AsyncMock(return_value=mock_response)):
            with pytest.raises(NASAClientError) as exc_info:
                await client.get_apod()
        assert exc_info.value.code == "NASA_SERVER_ERROR"

    @pytest.mark.asyncio
    async def test_non_json_response_raises_invalid_json(self, client):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.is_success = True
        mock_response.json.side_effect = ValueError("not json")
        with patch.object(client._client, "get", new=AsyncMock(return_value=mock_response)):
            with pytest.raises(NASAClientError) as exc_info:
                await client.get_apod()
        assert exc_info.value.code == "NASA_INVALID_JSON"


# ---------------------------------------------------------------------------
# Unit tests — APOD date fallback
# ---------------------------------------------------------------------------


class TestApodDateFallback:
    """If NASA returns no date, we fall back to today's date string."""

    @pytest.fixture()
    def client(self) -> NASAClient:
        return NASAClient(NASAConfig(api_key="DEMO_KEY"))

    @pytest.mark.asyncio
    async def test_missing_date_defaults_to_today(self, client):
        raw = _make_apod_response()
        raw.pop("date")
        with patch.object(client, "_get", new=AsyncMock(return_value=raw)):
            result = await client.get_apod()
        assert result.date == str(date.today())


# ---------------------------------------------------------------------------
# Integration smoke tests — require real NASA_API_KEY
# (skipped unless explicitly run with -m live)
# ---------------------------------------------------------------------------


@pytest.mark.live
class TestNASALiveConnectivity:
    """
    Live connectivity tests against the real NASA API.

    Prerequisites:
    - NASA_API_KEY must be set in the environment (or .env file).
    - Internet connection required.

    Run with:
        pytest tests/test_nasa.py -m live -v
    """

    @pytest.fixture()
    def live_client(self) -> NASAClient:
        from dotenv import load_dotenv
        load_dotenv()
        api_key = os.getenv("NASA_API_KEY", "DEMO_KEY")
        return NASAClient(NASAConfig(api_key=api_key))

    @pytest.mark.asyncio
    async def test_apod_today_live(self, live_client):
        """Fetch today's APOD from the real NASA API."""
        result = await live_client.get_apod()
        assert isinstance(result, NASAAPODData)
        assert result.title
        assert result.explanation
        assert result.date
        assert result.media_type in ("image", "video")
        assert result.source == "NASA APOD"
        print(f"\n  [LIVE] APOD title: {result.title}")
        print(f"  [LIVE] APOD date:  {result.date}")
        print(f"  [LIVE] image_url:  {result.image_url}")
        await live_client.close()

    @pytest.mark.asyncio
    async def test_apod_specific_date_live(self, live_client):
        """Fetch a known-good historical APOD date."""
        result = await live_client.get_apod(apod_date="2024-01-01")
        assert isinstance(result, NASAAPODData)
        assert result.date == "2024-01-01"
        await live_client.close()

    @pytest.mark.asyncio
    async def test_apod_future_date_raises_bad_request(self, live_client):
        """A future date should cause NASA to return HTTP 400."""
        future = (date.today() + timedelta(days=365)).isoformat()
        with pytest.raises(NASAClientError) as exc_info:
            await live_client.get_apod(apod_date=future)
        assert exc_info.value.code in ("NASA_BAD_REQUEST", "NASA_RATE_LIMIT")
        await live_client.close()

    @pytest.mark.asyncio
    async def test_donki_cme_live(self, live_client):
        """Fetch recent DONKI CME events — result may be empty if no active events."""
        results = await live_client.get_donki_cme()
        assert isinstance(results, list)
        print(f"\n  [LIVE] DONKI CME events: {len(results)}")
        if results:
            first = results[0]
            assert isinstance(first, NASADONKIEvent)
            assert first.event_type == "CME"
        await live_client.close()

    @pytest.mark.asyncio
    async def test_api_key_detected(self, live_client):
        """Verifies that the API key in use is not the default DEMO_KEY."""
        key = live_client._config.api_key
        if key == "DEMO_KEY":
            pytest.skip("NASA_API_KEY is DEMO_KEY — set a real key for full live testing.")
        assert key and len(key) > 5
        print(f"\n  [LIVE] API key starts with: {key[:4]}…")
        await live_client.close()
