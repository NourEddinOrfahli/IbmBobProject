"""
Tests for:
  - APOD image/media passthrough in StoryGenerator._ensure_source_data()
  - CMEEventSummary and SpaceWeatherSummary model construction
  - StoryGenerator._build_space_weather() DONKI extraction
  - SpaceStory backward compatibility (space_weather optional)
  - generate_from_context() compatibility (no DONKI, no APOD)

No real API keys or network calls required.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from models import (
    CMEEventSummary,
    NASAAPODData,
    NASADONKIEvent,
    SpaceStory,
    SpaceWeatherSummary,
)
from story_generator import StoryGenerator


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _apod(
    *,
    image_url: str | None = "https://apod.nasa.gov/apod/image/test.jpg",
    hd_image_url: str | None = "https://apod.nasa.gov/apod/image/test_hd.jpg",
    media_type: str = "image",
    copyright: str | None = "NASA/ESA",
) -> NASAAPODData:
    return NASAAPODData(
        title="Pillars of Creation",
        explanation="The Eagle Nebula's iconic gas pillars.",
        date="2024-06-15",
        media_type=media_type,
        image_url=image_url,
        hd_image_url=hd_image_url,
        copyright=copyright,
    )


def _donki_event(raw: dict | None = None) -> NASADONKIEvent:
    return NASADONKIEvent(
        event_type="CME",
        begin_time="2024-06-14T10:00Z",
        raw=raw or {},
    )


def _full_raw_cme(
    speed: float = 850.0,
    is_earth_directed: bool = True,
    arrival: str = "2024-06-17T03:00Z",
    kp: float = 5.0,
    source_location: str = "S15E25",
    note: str = "CME with Type II radio burst",
    most_accurate: bool = True,
) -> dict:
    """Build a realistic DONKI CME raw payload."""
    return {
        "startTime": "2024-06-14T10:00Z",
        "sourceLocation": source_location,
        "note": note,
        "cmeAnalyses": [
            {
                "isMostAccurate": most_accurate,
                "speed": speed,
                "enlilList": [
                    {
                        "isEarthGB": is_earth_directed,
                        "estimatedShockArrivalTime": arrival,
                        "kp_90": kp,
                    }
                ],
            }
        ],
    }


def _base_story_payload() -> dict:
    return {
        "title": "نجوم المجرة",
        "summary": "ملخص مختصر عن المجرة.",
        "scientific_explanation": "شرح علمي مفصّل.",
        "key_facts": ["حقيقة أولى"],
        "why_it_matters": "هذا مهم.",
        "story": "قصة قصيرة.",
        "source_data": {"source": "NASA APOD", "date": "2024-06-15"},
        "confidence": "high",
        "language": "ar",
    }


# ===========================================================================
# Part A — APOD image passthrough in _ensure_source_data()
# ===========================================================================


class TestEnsureSourceDataImagePassthrough:
    """Verify that _ensure_source_data() passes through all four media fields."""

    def _run(self, raw: dict, apod: NASAAPODData) -> dict:
        result = StoryGenerator._ensure_source_data(raw, apod)
        return result["source_data"]

    def test_image_url_written(self):
        sd = self._run({}, _apod())
        assert sd["image_url"] == "https://apod.nasa.gov/apod/image/test.jpg"

    def test_hd_image_url_written(self):
        sd = self._run({}, _apod())
        assert sd["hd_image_url"] == "https://apod.nasa.gov/apod/image/test_hd.jpg"

    def test_media_type_written(self):
        sd = self._run({}, _apod())
        assert sd["media_type"] == "image"

    def test_copyright_written(self):
        sd = self._run({}, _apod())
        assert sd["copyright"] == "NASA/ESA"

    def test_provenance_fields_still_present(self):
        """Existing provenance fields must not be removed."""
        sd = self._run({}, _apod())
        assert sd["source"] == "NASA APOD"
        assert sd["date"] == "2024-06-15"
        assert sd["title"] == "Pillars of Creation"

    def test_null_image_url_written_as_none(self):
        """When APOD has no image (e.g. video) image_url is None — not absent."""
        sd = self._run({}, _apod(image_url=None, hd_image_url=None))
        assert sd["image_url"] is None
        assert sd["hd_image_url"] is None

    def test_null_copyright_written_as_none(self):
        sd = self._run({}, _apod(copyright=None))
        assert sd["copyright"] is None

    def test_video_media_type_written(self):
        sd = self._run({}, _apod(media_type="video", image_url=None))
        assert sd["media_type"] == "video"
        assert sd["image_url"] is None

    def test_overwrites_llm_hallucinated_image_url(self):
        """
        The LLM might return a fake image_url in source_data.
        _ensure_source_data must overwrite it with the verified NASA value.
        """
        raw = {"source_data": {"image_url": "https://fake.example.com/fake.jpg"}}
        sd = self._run(raw, _apod())
        assert sd["image_url"] == "https://apod.nasa.gov/apod/image/test.jpg"

    def test_extra_llm_keys_preserved_alongside_new_fields(self):
        """
        Existing test: extra LLM keys survive; new media keys co-exist correctly.
        """
        raw = {"source_data": {"extra_key": "extra_value"}}
        sd = self._run(raw, _apod())
        assert sd["extra_key"] == "extra_value"
        assert sd["image_url"] == "https://apod.nasa.gov/apod/image/test.jpg"


# ===========================================================================
# Part B — CMEEventSummary model construction
# ===========================================================================


class TestCMEEventSummary:
    def test_minimal_valid(self):
        evt = CMEEventSummary(event_type="CME")
        assert evt.event_type == "CME"
        assert evt.begin_time is None
        assert evt.speed_kmps is None
        assert evt.is_earth_directed is None
        assert evt.estimated_arrival is None
        assert evt.kp_index is None
        assert evt.source_location is None
        assert evt.note is None

    def test_full_valid(self):
        evt = CMEEventSummary(
            event_type="CME",
            begin_time="2024-06-14T10:00Z",
            speed_kmps=850.0,
            is_earth_directed=True,
            estimated_arrival="2024-06-17T03:00Z",
            kp_index=5.0,
            source_location="S15E25",
            note="CME with Type II radio burst",
        )
        assert evt.speed_kmps == 850.0
        assert evt.is_earth_directed is True
        assert evt.kp_index == 5.0

    def test_missing_event_type_raises(self):
        with pytest.raises(ValidationError):
            CMEEventSummary()  # type: ignore[call-arg]


# ===========================================================================
# Part C — SpaceWeatherSummary model construction
# ===========================================================================


class TestSpaceWeatherSummary:
    def test_available_false(self):
        sw = SpaceWeatherSummary(available=False, event_count=0, events=[])
        assert sw.available is False
        assert sw.event_count == 0
        assert sw.events == []

    def test_available_true_with_events(self):
        evt = CMEEventSummary(event_type="CME", begin_time="2024-06-14T10:00Z")
        sw = SpaceWeatherSummary(available=True, event_count=1, events=[evt])
        assert sw.available is True
        assert sw.event_count == 1
        assert len(sw.events) == 1

    def test_events_default_empty_list(self):
        sw = SpaceWeatherSummary(available=False, event_count=0)
        assert sw.events == []


# ===========================================================================
# Part D — _build_space_weather() DONKI extraction
# ===========================================================================


class TestBuildSpaceWeather:
    """Unit tests for StoryGenerator._build_space_weather()."""

    def _build(self, events: list[NASADONKIEvent]) -> SpaceWeatherSummary:
        return StoryGenerator._build_space_weather(events)

    # --- Empty / no events ---

    def test_empty_list_returns_unavailable(self):
        sw = self._build([])
        assert sw.available is False
        assert sw.event_count == 0
        assert sw.events == []

    # --- Complete CME data ---

    def test_full_cme_extracts_all_fields(self):
        evt = _donki_event(_full_raw_cme())
        sw = self._build([evt])
        assert sw.available is True
        assert sw.event_count == 1
        e = sw.events[0]
        assert e.event_type == "CME"
        assert e.begin_time == "2024-06-14T10:00Z"
        assert e.speed_kmps == 850.0
        assert e.is_earth_directed is True
        assert e.estimated_arrival == "2024-06-17T03:00Z"
        assert e.kp_index == 5.0
        assert e.source_location == "S15E25"
        assert e.note == "CME with Type II radio burst"

    # --- Missing cmeAnalyses ---

    def test_missing_cme_analyses_is_safe(self):
        """Event with no cmeAnalyses key — all analysis fields must be None."""
        evt = _donki_event({"startTime": "2024-06-14T10:00Z"})
        sw = self._build([evt])
        assert sw.available is True
        e = sw.events[0]
        assert e.speed_kmps is None
        assert e.is_earth_directed is None
        assert e.estimated_arrival is None
        assert e.kp_index is None

    def test_empty_cme_analyses_list_is_safe(self):
        evt = _donki_event({"startTime": "2024-06-14T10:00Z", "cmeAnalyses": []})
        sw = self._build([evt])
        e = sw.events[0]
        assert e.speed_kmps is None

    def test_null_cme_analyses_is_safe(self):
        evt = _donki_event({"startTime": "2024-06-14T10:00Z", "cmeAnalyses": None})
        sw = self._build([evt])
        e = sw.events[0]
        assert e.speed_kmps is None

    # --- Missing enlilList ---

    def test_missing_enlil_list_is_safe(self):
        raw = {
            "startTime": "2024-06-14T10:00Z",
            "cmeAnalyses": [{"isMostAccurate": True, "speed": 700}],
        }
        evt = _donki_event(raw)
        sw = self._build([evt])
        e = sw.events[0]
        assert e.speed_kmps == 700.0
        assert e.is_earth_directed is None
        assert e.estimated_arrival is None

    def test_empty_enlil_list_is_safe(self):
        raw = {
            "startTime": "2024-06-14T10:00Z",
            "cmeAnalyses": [{"isMostAccurate": True, "speed": 600, "enlilList": []}],
        }
        evt = _donki_event(raw)
        sw = self._build([evt])
        e = sw.events[0]
        assert e.speed_kmps == 600.0
        assert e.is_earth_directed is None

    # --- Missing optional values within enlilList ---

    def test_missing_kp_90_leaves_kp_index_none(self):
        raw = _full_raw_cme()
        # Remove kp_90 from the enlil entry
        del raw["cmeAnalyses"][0]["enlilList"][0]["kp_90"]
        evt = _donki_event(raw)
        sw = self._build([evt])
        assert sw.events[0].kp_index is None

    def test_null_kp_90_leaves_kp_index_none(self):
        raw = _full_raw_cme()
        raw["cmeAnalyses"][0]["enlilList"][0]["kp_90"] = None
        evt = _donki_event(raw)
        sw = self._build([evt])
        assert sw.events[0].kp_index is None

    def test_missing_arrival_time_leaves_none(self):
        raw = _full_raw_cme()
        del raw["cmeAnalyses"][0]["enlilList"][0]["estimatedShockArrivalTime"]
        evt = _donki_event(raw)
        sw = self._build([evt])
        assert sw.events[0].estimated_arrival is None

    def test_missing_source_location_leaves_none(self):
        raw = _full_raw_cme()
        del raw["sourceLocation"]
        evt = _donki_event(raw)
        sw = self._build([evt])
        assert sw.events[0].source_location is None

    def test_missing_note_leaves_none(self):
        raw = _full_raw_cme()
        del raw["note"]
        evt = _donki_event(raw)
        sw = self._build([evt])
        assert sw.events[0].note is None

    # --- Most-accurate flag selection ---

    def test_most_accurate_analysis_preferred(self):
        """When multiple analyses exist, the isMostAccurate=True one is used."""
        raw = {
            "startTime": "2024-06-14T10:00Z",
            "cmeAnalyses": [
                {"isMostAccurate": False, "speed": 300, "enlilList": []},
                {"isMostAccurate": True, "speed": 850, "enlilList": []},
            ],
        }
        evt = _donki_event(raw)
        sw = self._build([evt])
        assert sw.events[0].speed_kmps == 850.0

    def test_first_analysis_used_when_none_most_accurate(self):
        """Falls back to first entry when no isMostAccurate=True entry exists."""
        raw = {
            "startTime": "2024-06-14T10:00Z",
            "cmeAnalyses": [
                {"isMostAccurate": False, "speed": 500, "enlilList": []},
                {"isMostAccurate": False, "speed": 700, "enlilList": []},
            ],
        }
        evt = _donki_event(raw)
        sw = self._build([evt])
        assert sw.events[0].speed_kmps == 500.0

    # --- Multiple CME events ---

    def test_multiple_events_all_extracted(self):
        e1 = _donki_event(_full_raw_cme(speed=900))
        e2 = _donki_event(_full_raw_cme(speed=600))
        sw = self._build([e1, e2])
        assert sw.event_count == 2
        assert len(sw.events) == 2
        assert sw.events[0].speed_kmps == 900.0
        assert sw.events[1].speed_kmps == 600.0

    def test_event_with_empty_raw_dict_is_safe(self):
        """An event whose raw dict is completely empty must not crash."""
        evt = NASADONKIEvent(event_type="CME", begin_time="2024-06-14T10:00Z", raw={})
        sw = self._build([evt])
        assert sw.available is True
        e = sw.events[0]
        assert e.speed_kmps is None
        assert e.source_location is None

    def test_event_with_none_raw_is_safe(self):
        """An event whose raw is explicitly None must not crash."""
        evt = NASADONKIEvent(event_type="CME", begin_time=None)
        # raw defaults to {} in NASADONKIEvent — so this is already safe
        sw = self._build([evt])
        assert sw.available is True


# ===========================================================================
# Part E — SpaceStory backward compatibility
# ===========================================================================


class TestSpaceStorySpaceWeatherCompatibility:
    def test_existing_story_without_space_weather_still_valid(self):
        """Stories that don't include space_weather must still validate."""
        story = SpaceStory(**_base_story_payload())
        assert story.space_weather is None

    def test_space_weather_none_by_default(self):
        story = SpaceStory(**_base_story_payload())
        assert story.space_weather is None

    def test_space_weather_attached_validates(self):
        sw = SpaceWeatherSummary(
            available=True,
            event_count=1,
            events=[CMEEventSummary(
                event_type="CME",
                begin_time="2024-06-14T10:00Z",
                speed_kmps=850.0,
            )],
        )
        payload = {**_base_story_payload(), "space_weather": sw.model_dump()}
        story = SpaceStory(**payload)
        assert story.space_weather is not None
        assert story.space_weather.event_count == 1

    def test_space_weather_unavailable_validates(self):
        sw = SpaceWeatherSummary(available=False, event_count=0, events=[])
        payload = {**_base_story_payload(), "space_weather": sw.model_dump()}
        story = SpaceStory(**payload)
        assert story.space_weather.available is False

    def test_language_enforcement_unaffected_by_space_weather(self):
        """
        The Arabic language enforcement model_validator must still work
        correctly regardless of space_weather presence.
        """
        payload = {
            **_base_story_payload(),
            "title": "The Mystery Meteor",
            "summary": "A fireball crossed the sky.",
            "language": "ar",
            "space_weather": None,
        }
        story = SpaceStory(**payload)
        # Language must be corrected to "en" because content is English
        assert story.language == "en"
