"""
Tests for Pydantic models (models.py).

These tests do NOT require any real API keys or external network access.
"""

import pytest
from pydantic import ValidationError

from models import (
    NASAAPODData,
    NASADONKIEvent,
    SpaceStory,
    AnalyzeRequest,
    SuccessResponse,
    ErrorResponse,
    ErrorDetail,
    _arabic_ratio,
    _story_is_arabic,
)


# ---------------------------------------------------------------------------
# NASAAPODData
# ---------------------------------------------------------------------------


class TestNASAAPODData:
    def test_valid_minimal(self):
        data = NASAAPODData(
            title="Test Image",
            explanation="A beautiful nebula.",
            date="2024-01-15",
            media_type="image",
        )
        assert data.title == "Test Image"
        assert data.image_url is None
        assert data.source == "NASA APOD"

    def test_valid_full(self):
        data = NASAAPODData(
            title="Eagle Nebula",
            explanation="Pillars of Creation.",
            date="2024-01-15",
            media_type="image",
            image_url="https://apod.nasa.gov/apod/image/test.jpg",
            hd_image_url="https://apod.nasa.gov/apod/image/test_hd.jpg",
            copyright="NASA/ESA",
        )
        assert data.hd_image_url is not None
        assert data.copyright == "NASA/ESA"

    def test_rejects_empty_title(self):
        with pytest.raises(ValidationError) as exc_info:
            NASAAPODData(
                title="   ",
                explanation="Some text",
                date="2024-01-15",
                media_type="image",
            )
        errors = exc_info.value.errors()
        assert any("title" in str(e) for e in errors)

    def test_rejects_empty_explanation(self):
        with pytest.raises(ValidationError):
            NASAAPODData(
                title="Valid Title",
                explanation="",
                date="2024-01-15",
                media_type="image",
            )

    def test_additional_data_default_empty(self):
        data = NASAAPODData(
            title="Title",
            explanation="Explanation",
            date="2024-01-15",
            media_type="image",
        )
        assert data.additional_data == {}


# ---------------------------------------------------------------------------
# NASADONKIEvent
# ---------------------------------------------------------------------------


class TestNASADONKIEvent:
    def test_valid(self):
        event = NASADONKIEvent(event_type="CME", begin_time="2024-01-15T06:00Z")
        assert event.event_type == "CME"
        assert event.source == "NASA DONKI"
        assert event.linked_events == []

    def test_linked_events_default(self):
        event = NASADONKIEvent(event_type="FLR")
        assert isinstance(event.linked_events, list)


# ---------------------------------------------------------------------------
# SpaceStory
# ---------------------------------------------------------------------------


class TestSpaceStory:
    def _valid_payload(self) -> dict:
        return {
            "title": "نجوم المجرة",
            "summary": "ملخص مختصر عن المجرة.",
            "scientific_explanation": "شرح علمي مفصّل لظاهرة فلكية رائعة.",
            "key_facts": ["حقيقة أولى", "حقيقة ثانية"],
            "why_it_matters": "هذا مهم لأنه يكشف أسرار الكون.",
            "story": "كانت الأرض تدور في مدار هادئ...",
            "source_data": {"source": "NASA APOD", "date": "2024-01-15"},
            "confidence": "high",
            "language": "ar",
        }

    def test_valid_full(self):
        story = SpaceStory(**self._valid_payload())
        assert story.language == "ar"
        assert story.confidence == "high"
        assert len(story.key_facts) == 2

    def test_language_normalised_to_lowercase(self):
        payload = self._valid_payload()
        payload["language"] = "AR"
        story = SpaceStory(**payload)
        assert story.language == "ar"

    def test_language_normalised_with_whitespace(self):
        payload = self._valid_payload()
        payload["language"] = "  ar  "
        story = SpaceStory(**payload)
        assert story.language == "ar"

    def test_key_facts_coerces_string_to_list(self):
        payload = self._valid_payload()
        payload["key_facts"] = "حقيقة وحيدة"
        story = SpaceStory(**payload)
        assert story.key_facts == ["حقيقة وحيدة"]

    def test_key_facts_defaults_to_empty_list(self):
        payload = self._valid_payload()
        del payload["key_facts"]
        story = SpaceStory(**payload)
        assert story.key_facts == []

    def test_confidence_default(self):
        payload = self._valid_payload()
        del payload["confidence"]
        story = SpaceStory(**payload)
        assert story.confidence == "medium"

    def test_missing_required_field_raises(self):
        payload = self._valid_payload()
        del payload["title"]
        with pytest.raises(ValidationError):
            SpaceStory(**payload)

    def test_source_data_defaults_to_empty(self):
        payload = self._valid_payload()
        del payload["source_data"]
        story = SpaceStory(**payload)
        assert story.source_data == {}


# ---------------------------------------------------------------------------
# AnalyzeRequest
# ---------------------------------------------------------------------------


class TestAnalyzeRequest:
    def test_all_optional_fields(self):
        req = AnalyzeRequest()
        assert req.apod_date is None
        assert req.extra_context is None

    def test_with_date(self):
        req = AnalyzeRequest(apod_date="2024-06-15")
        assert req.apod_date == "2024-06-15"

    def test_with_context(self):
        req = AnalyzeRequest(extra_context="Interesting nebula data")
        assert req.extra_context == "Interesting nebula data"


# ---------------------------------------------------------------------------
# Response envelopes
# ---------------------------------------------------------------------------


class TestResponseEnvelopes:
    def test_success_response(self):
        resp = SuccessResponse(data={"key": "value"})
        assert resp.success is True
        assert resp.data == {"key": "value"}

    def test_error_response(self):
        resp = ErrorResponse(error=ErrorDetail(code="TEST_ERROR", message="test"))
        assert resp.success is False
        assert resp.error.code == "TEST_ERROR"


# ---------------------------------------------------------------------------
# _ensure_source_data provenance enforcement
# ---------------------------------------------------------------------------


class TestEnsureSourceData:
    """
    Tests for StoryGenerator._ensure_source_data().

    Verifies that NASA-verified provenance fields (source, date, title) always
    win over whatever the LLM returned in source_data — including hallucinated
    values.
    """

    def _apod(self) -> NASAAPODData:
        return NASAAPODData(
            title="Pillars of Creation",
            explanation="Eagle Nebula gas pillars.",
            date="2024-05-10",
            media_type="image",
            image_url="https://apod.nasa.gov/apod/image/pillars.jpg",
            copyright="NASA/ESA",
        )

    def _run(self, raw: dict) -> dict:
        from story_generator import StoryGenerator
        apod = self._apod()
        result = StoryGenerator._ensure_source_data(raw, apod)
        return result["source_data"]

    # 1. LLM returns no source_data → NASA fields are created
    def test_missing_source_data_creates_nasa_fields(self):
        sd = self._run({"title": "some title"})
        assert sd["source"] == "NASA APOD"
        assert sd["date"] == "2024-05-10"
        assert sd["title"] == "Pillars of Creation"

    # 2. LLM returns empty source_data → NASA fields are inserted
    def test_empty_source_data_creates_nasa_fields(self):
        sd = self._run({"title": "t", "source_data": {}})
        assert sd["source"] == "NASA APOD"
        assert sd["date"] == "2024-05-10"
        assert sd["title"] == "Pillars of Creation"

    # 3. LLM returns a partially correct source_data → NASA fields overwrite
    def test_partial_source_data_is_overwritten(self):
        sd = self._run({"source_data": {"source": "Some Journal", "date": "1999-01-01"}})
        assert sd["source"] == "NASA APOD"
        assert sd["date"] == "2024-05-10"
        assert sd["title"] == "Pillars of Creation"

    # 4. LLM returns fully hallucinated source_data (the Nature Energy bug)
    def test_hallucinated_source_data_is_overwritten(self):
        hallucinated = {
            "source": "Nature Energy",
            "date": "2024-03-15",
            "title": "High-energy solid-state batteries",
        }
        sd = self._run({"source_data": hallucinated})
        assert sd["source"] == "NASA APOD"
        assert sd["date"] == "2024-05-10"
        assert sd["title"] == "Pillars of Creation"

    # 5. Non-authoritative extra keys returned by the model are preserved;
    #    authoritative fields (including copyright) are overwritten with
    #    NASA-verified values.
    def test_extra_model_keys_are_preserved(self):
        model_sd = {
            "source": "Made Up Source",
            "date": "2000-01-01",
            "title": "Made Up Title",
            "url": "https://model-added-url.example.com",
            "copyright": "Model Copyright",  # authoritative — will be overwritten
        }
        sd = self._run({"source_data": model_sd})
        # Authoritative provenance fields always overwritten
        assert sd["source"] == "NASA APOD"
        assert sd["date"] == "2024-05-10"
        assert sd["title"] == "Pillars of Creation"
        # copyright is now authoritative (NASA-verified) — overwritten with apod value
        assert sd["copyright"] == "NASA/ESA"
        # Non-authoritative extra field ("url") is preserved as-is
        assert sd["url"] == "https://model-added-url.example.com"

    # 6. Return value is the same dict (mutates in-place and returns it)
    def test_raw_dict_is_updated_in_place(self):
        raw = {"title": "t", "source_data": {"source": "Wrong"}}
        result = raw.copy()
        from story_generator import StoryGenerator
        apod = self._apod()
        returned = StoryGenerator._ensure_source_data(result, apod)
        assert returned is result
        assert returned["source_data"]["source"] == "NASA APOD"

    # 7. None source_data value (model returned null) is treated as missing
    def test_null_source_data_creates_nasa_fields(self):
        sd = self._run({"source_data": None})
        assert sd["source"] == "NASA APOD"
        assert sd["date"] == "2024-05-10"
        assert sd["title"] == "Pillars of Creation"


# ---------------------------------------------------------------------------
# Language detection helpers
# ---------------------------------------------------------------------------


class TestArabicRatio:
    """Unit tests for the _arabic_ratio() helper function."""

    def test_pure_arabic_returns_high_ratio(self):
        # Pure Arabic sentence
        ratio = _arabic_ratio("نجوم المجرة تضيء السماء")
        assert ratio >= 0.8

    def test_pure_english_returns_zero(self):
        ratio = _arabic_ratio("The Case of the Mysterious Maybe Meteor")
        assert ratio == 0.0

    def test_empty_string_returns_zero(self):
        assert _arabic_ratio("") == 0.0

    def test_whitespace_only_returns_zero(self):
        assert _arabic_ratio("   ") == 0.0

    def test_mixed_arabic_english_reflects_arabic_fraction(self):
        # ~50 % Arabic characters
        ratio = _arabic_ratio("نجوم stars")
        assert 0.0 < ratio < 1.0


class TestStoryIsArabic:
    """Unit tests for the _story_is_arabic() helper function."""

    def _arabic_story(self) -> SpaceStory:
        return SpaceStory(
            title="نجوم المجرة تضيء",
            summary="ملخص مختصر عن المجرة والنجوم والكون.",
            scientific_explanation="شرح علمي مفصّل.",
            key_facts=["حقيقة أولى", "حقيقة ثانية"],
            why_it_matters="هذا مهم.",
            story="قصة قصيرة عن الفضاء.",
            language="ar",
        )

    def _english_story_claiming_arabic(self) -> SpaceStory:
        # Build with language="en" so the validator does not correct it,
        # then we can inspect _story_is_arabic directly.
        return SpaceStory(
            title="The Case of the Mysterious Maybe Meteor",
            summary="A fireball lit up the night sky and scientists investigated.",
            scientific_explanation="Scientific details in English.",
            key_facts=["Fact one", "Fact two"],
            why_it_matters="It matters because of science.",
            story="A long English story about space.",
            language="en",
        )

    def test_arabic_story_detected_as_arabic(self):
        story = self._arabic_story()
        assert _story_is_arabic(story) is True

    def test_english_story_detected_as_not_arabic(self):
        story = self._english_story_claiming_arabic()
        assert _story_is_arabic(story) is False


# ---------------------------------------------------------------------------
# Language enforcement on SpaceStory
# ---------------------------------------------------------------------------


class TestSpaceStoryLanguageEnforcement:
    """
    Tests for the model_validator that corrects the language field when
    the claimed language does not match the actual content language.

    These are deterministic backend-enforcement tests — no LLM involved.
    """

    def _base(self) -> dict:
        return {
            "scientific_explanation": "شرح علمي مفصّل.",
            "key_facts": ["حقيقة 1"],
            "why_it_matters": "مهم.",
            "story": "قصة.",
            "source_data": {"source": "NASA APOD", "date": "2024-01-01"},
            "confidence": "high",
        }

    # 1. Arabic content + language="ar" → language stays "ar"
    def test_arabic_content_with_language_ar_passes(self):
        payload = {
            **self._base(),
            "title": "نجوم المجرة",
            "summary": "ملخص مختصر عن المجرة.",
            "language": "ar",
        }
        story = SpaceStory(**payload)
        assert story.language == "ar"

    # 2. English content with language="ar" → corrected to "en"
    def test_english_content_with_language_ar_is_corrected_to_en(self):
        payload = {
            **self._base(),
            "title": "The Case of the Mysterious Maybe Meteor",
            "summary": "A fireball lit up the night sky and scientists investigated.",
            "language": "ar",
        }
        story = SpaceStory(**payload)
        assert story.language == "en", (
            f"Expected language to be corrected to 'en', got '{story.language}'"
        )

    # 3. English content + language="en" → language stays "en" (no correction needed)
    def test_english_content_with_language_en_stays_en(self):
        payload = {
            **self._base(),
            "title": "The Mystery Meteor",
            "summary": "A fireball in the sky was studied by astronomers.",
            "language": "en",
        }
        story = SpaceStory(**payload)
        assert story.language == "en"

    # 4. Arabic content + language="en" → language stays "en" (we only correct ar→en, not en→ar)
    def test_arabic_content_with_language_en_stays_en(self):
        """We only enforce ar→en correction, not en→ar (language=en is caller's intent)."""
        payload = {
            **self._base(),
            "title": "نجوم المجرة",
            "summary": "ملخص عن الكون.",
            "language": "en",
        }
        story = SpaceStory(**payload)
        assert story.language == "en"

    # 5. The exact bug from the issue report: English title, language="ar"
    def test_exact_bug_scenario_corrected(self):
        """Reproduce the exact reported bug: English title with language='ar'."""
        payload = {
            "title": "The Case of the Mysterious Maybe Meteor",
            "summary": "Scientists puzzle over a fireball sighting near the coast.",
            "scientific_explanation": "The object exhibited characteristics of a bolide.",
            "key_facts": ["Bright flash", "Sonic boom", "No fragments recovered"],
            "why_it_matters": "It highlights gaps in meteor tracking coverage.",
            "story": "On a clear night, observers reported a dazzling streak of light.",
            "source_data": {"source": "NASA APOD", "date": "2024-08-19", "title": "..."},
            "confidence": "medium",
            "language": "ar",  # BUG: model claims ar but content is English
        }
        story = SpaceStory(**payload)
        # Backend must correct this deterministically
        assert story.language == "en", (
            f"Language should be corrected from 'ar' to 'en', got '{story.language}'"
        )

    # 6. source_data is preserved after language correction
    def test_source_data_preserved_after_language_correction(self):
        payload = {
            **self._base(),
            "title": "The Mystery Meteor",
            "summary": "A fireball crossed the night sky.",
            "language": "ar",
            "source_data": {
                "source": "NASA APOD",
                "date": "2024-08-19",
                "title": "Mystery Meteor",
            },
        }
        story = SpaceStory(**payload)
        assert story.language == "en"
        assert story.source_data["source"] == "NASA APOD"
        assert story.source_data["date"] == "2024-08-19"
