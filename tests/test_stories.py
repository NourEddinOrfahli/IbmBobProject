"""
Tests for GET /api/stories endpoint.

Covers:
- Valid request returns stories list
- count parameter clamped to 1–10
- end_date parameter
- Invalid end_date rejected
- NASA client failure (graceful skip)
- NASA not configured (503)
- Response shape
"""

from __future__ import annotations

from datetime import date, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from models import NASAAPODData


# ---------------------------------------------------------------------------
# Minimal APOD fixture
# ---------------------------------------------------------------------------


def _make_apod(d: str) -> NASAAPODData:
    return NASAAPODData(
        title=f"Title {d}",
        explanation=f"Explanation for {d}. " * 20,
        date=d,
        media_type="image",
        image_url=f"https://apod.nasa.gov/apod/image/{d}.jpg",
        hd_image_url=f"https://apod.nasa.gov/apod/image/{d}_hd.jpg",
        copyright="NASA",
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def mock_nasa():
    nasa = MagicMock()
    nasa.get_apod = AsyncMock(side_effect=lambda apod_date=None: _make_apod(apod_date or str(date.today())))
    return nasa


@pytest.fixture()
def client(mock_nasa):
    import main as main_module

    with TestClient(main_module.app, raise_server_exceptions=False) as c:
        original = main_module._nasa_client
        main_module._nasa_client = mock_nasa
        try:
            yield c
        finally:
            main_module._nasa_client = original


@pytest.fixture()
def client_no_nasa():
    import main as main_module

    with TestClient(main_module.app, raise_server_exceptions=False) as c:
        original = main_module._nasa_client
        main_module._nasa_client = None
        try:
            yield c
        finally:
            main_module._nasa_client = original


# ---------------------------------------------------------------------------
# Valid requests
# ---------------------------------------------------------------------------


class TestStoriesValid:
    def test_returns_200(self, client):
        resp = client.get("/api/stories")
        assert resp.status_code == 200

    def test_response_is_success_true(self, client):
        resp = client.get("/api/stories")
        assert resp.json()["success"] is True

    def test_response_has_stories_list(self, client):
        resp = client.get("/api/stories")
        data = resp.json()["data"]
        assert "stories" in data
        assert isinstance(data["stories"], list)

    def test_default_count_is_5(self, client):
        resp = client.get("/api/stories")
        data = resp.json()["data"]
        assert data["count"] == 5

    def test_count_parameter(self, client):
        resp = client.get("/api/stories?count=3")
        data = resp.json()["data"]
        assert data["count"] == 3

    def test_story_has_required_fields(self, client):
        resp = client.get("/api/stories?count=1")
        stories = resp.json()["data"]["stories"]
        assert len(stories) >= 1
        story = stories[0]
        assert "id" in story
        assert "date" in story
        assert "title" in story
        assert "summary" in story
        assert "source" in story

    def test_story_source_is_nasa_apod(self, client):
        resp = client.get("/api/stories?count=1")
        story = resp.json()["data"]["stories"][0]
        assert story["source"] == "NASA APOD"

    def test_end_date_parameter(self, client, mock_nasa):
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        resp = client.get(f"/api/stories?count=2&end_date={yesterday}")
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Count clamping
# ---------------------------------------------------------------------------


class TestStoriesCountClamping:
    def test_count_0_clamped_to_1(self, client):
        resp = client.get("/api/stories?count=0")
        assert resp.status_code == 200
        assert resp.json()["data"]["count"] == 1

    def test_count_100_clamped_to_10(self, client):
        resp = client.get("/api/stories?count=100")
        assert resp.status_code == 200
        # At most 10
        assert resp.json()["data"]["count"] <= 10


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


class TestStoriesErrors:
    def test_invalid_end_date_returns_400(self, client):
        resp = client.get("/api/stories?end_date=not-a-date")
        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == "INVALID_DATE"

    def test_nasa_not_configured_returns_503(self, client_no_nasa):
        resp = client_no_nasa.get("/api/stories")
        assert resp.status_code == 503
        assert resp.json()["error"]["code"] == "NASA_NOT_CONFIGURED"

    def test_nasa_failure_for_one_date_skipped_gracefully(self, client, mock_nasa):
        """If NASA fails for one date, that date is skipped, others still returned."""
        call_count = 0

        async def flaky_apod(apod_date=None):
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                from nasa_client import NASAClientError
                raise NASAClientError("NASA_TIMEOUT", "Timeout")
            return _make_apod(apod_date or str(date.today()))

        mock_nasa.get_apod = AsyncMock(side_effect=flaky_apod)
        resp = client.get("/api/stories?count=3")
        assert resp.status_code == 200
        # 2 out of 3 should succeed
        data = resp.json()["data"]
        assert data["count"] == 2
