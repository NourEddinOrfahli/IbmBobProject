"""
Pydantic models for Space Interpreter.

Covers:
- NASA API response normalisation
- AI-generated SpaceStory output
- Space-weather summary (DONKI CME passthrough)
- API request / response envelopes
"""

from __future__ import annotations

import re
from typing import Any, Optional
from pydantic import BaseModel, Field, field_validator, model_validator

# ---------------------------------------------------------------------------
# Language detection helper
# ---------------------------------------------------------------------------

# Arabic Unicode block: U+0600–U+06FF (covers all Arabic letters and diacritics)
_ARABIC_RE = re.compile(r"[\u0600-\u06FF]")


def _arabic_ratio(text: str) -> float:
    """Return the fraction of characters in *text* that are Arabic script.

    Only letter-like characters (non-whitespace, non-punctuation) are counted
    so that short texts with lots of spaces are not unfairly penalised.
    Raises no exceptions; returns 0.0 for empty or whitespace-only strings.
    """
    stripped = text.strip()
    if not stripped:
        return 0.0
    # Count all non-whitespace characters as the denominator so that
    # Roman-script content such as "The Case of the Mysterious Maybe Meteor"
    # registers as 0 % Arabic even when there are spaces.
    non_ws = len(re.sub(r"\s", "", stripped))
    if non_ws == 0:
        return 0.0
    arabic_chars = len(_ARABIC_RE.findall(stripped))
    return arabic_chars / non_ws


def _story_is_arabic(story: "SpaceStory") -> bool:
    """Return True if the story's user-facing text fields are predominantly Arabic.

    Collects title + summary into a single sample and checks that at least
    30 % of its non-whitespace characters are Arabic-script.  A 30 % threshold
    is intentionally conservative: genuine Arabic prose easily exceeds 80 %,
    while English prose rarely exceeds 1–2 % (only loanwords or names).
    """
    sample = " ".join([
        story.title,
        story.summary,
    ])
    return _arabic_ratio(sample) >= 0.30


# ---------------------------------------------------------------------------
# NASA data models
# ---------------------------------------------------------------------------


class NASAAPODData(BaseModel):
    """Normalised Astronomy Picture Of the Day payload."""

    title: str
    explanation: str
    date: str
    media_type: str
    image_url: Optional[str] = None
    hd_image_url: Optional[str] = None
    copyright: Optional[str] = None
    source: str = "NASA APOD"
    additional_data: dict[str, Any] = Field(default_factory=dict)

    @field_validator("title", "explanation", "date", mode="before")
    @classmethod
    def must_not_be_empty(cls, value: Any) -> Any:
        if isinstance(value, str) and not value.strip():
            raise ValueError("Field must not be empty")
        return value


class NASADONKIEvent(BaseModel):
    """Single DONKI space-weather event."""

    event_type: str
    begin_time: Optional[str] = None
    peak_time: Optional[str] = None
    end_time: Optional[str] = None
    linked_events: list[str] = Field(default_factory=list)
    source: str = "NASA DONKI"
    raw: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Space-weather models (DONKI CME passthrough)
# ---------------------------------------------------------------------------


class CMEEventSummary(BaseModel):
    """
    A single CME (Coronal Mass Ejection) event extracted from NASA DONKI.

    All fields beyond event_type are Optional — real DONKI responses often
    omit cmeAnalyses or enlilList entries, especially for slower CMEs.
    """

    event_type: str
    begin_time: Optional[str] = None
    speed_kmps: Optional[float] = None
    is_earth_directed: Optional[bool] = None
    estimated_arrival: Optional[str] = None
    kp_index: Optional[float] = None
    source_location: Optional[str] = None
    note: Optional[str] = None


class SpaceWeatherSummary(BaseModel):
    """
    Structured summary of recent DONKI CME space-weather events.

    ``available`` is True when at least one CME event with a begin_time was
    returned by DONKI.  When no events are present the frontend renders a
    deliberate "no active events" state rather than hiding the section.
    """

    available: bool
    event_count: int
    events: list[CMEEventSummary] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# AI output model
# ---------------------------------------------------------------------------


class SpaceStory(BaseModel):
    """Validated output from the AI provider."""

    title: str
    summary: str
    scientific_explanation: str
    key_facts: list[str] = Field(default_factory=list)
    why_it_matters: str
    story: str
    source_data: dict[str, Any] = Field(default_factory=dict)
    confidence: str = "medium"
    language: str = "ar"
    space_weather: Optional[SpaceWeatherSummary] = None

    @field_validator("language", mode="before")
    @classmethod
    def normalise_language(cls, value: Any) -> str:
        if isinstance(value, str):
            return value.lower().strip()
        return "ar"

    @field_validator("key_facts", mode="before")
    @classmethod
    def ensure_list(cls, value: Any) -> list:
        if isinstance(value, list):
            return value
        if isinstance(value, str):
            return [value]
        return []

    @model_validator(mode="after")
    def enforce_language_matches_content(self) -> "SpaceStory":
        """Deterministically correct the language field when content does not match.

        If the model claims ``language="ar"`` but the generated text fields are
        predominantly non-Arabic (e.g. English), the language tag is corrected
        to ``"en"`` so that the response is always internally consistent.

        This is a backend safety net — it does not replace prompt-level
        language enforcement; both layers work together.
        """
        if self.language == "ar" and not _story_is_arabic(self):
            object.__setattr__(self, "language", "en")
        return self


# ---------------------------------------------------------------------------
# API request / response envelopes
# ---------------------------------------------------------------------------


class AnalyzeRequest(BaseModel):
    """Optional body for POST /api/analyze."""

    apod_date: Optional[str] = Field(
        default=None,
        description="ISO-8601 date (YYYY-MM-DD) to fetch APOD for. Defaults to today.",
    )
    extra_context: Optional[str] = Field(
        default=None,
        description="Any additional free-text context to include in the AI prompt.",
    )


class SuccessResponse(BaseModel):
    success: bool = True
    data: Any


class ErrorDetail(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    success: bool = False
    error: ErrorDetail


class HealthResponse(BaseModel):
    status: str = "ok"


# ---------------------------------------------------------------------------
# Image analysis models
# ---------------------------------------------------------------------------


class ImageAnalysisResult(BaseModel):
    """
    Validated output from the vision AI provider for user-uploaded space images.

    Fields
    ------
    title               Short Arabic headline describing the image.
    summary             2–3 sentence Arabic overview of the image.
    observations        List of visual observations — only what is directly visible.
    scientific_explanation
                        Arabic scientific interpretation of what is observed.
    confidence          Analyst's confidence in the identification: high | medium | low.
    story               Optional short Arabic narrative inspired by the image.
    question_answer     Answer to the user's question, if one was provided.
    is_space_related    Whether the image appears to be space-related.
    """

    title: str
    summary: str
    observations: list[str] = Field(default_factory=list)
    scientific_explanation: str
    confidence: str = "medium"
    story: str = ""
    question_answer: str = ""
    is_space_related: bool = True

    @field_validator("confidence", mode="before")
    @classmethod
    def normalise_confidence(cls, value: Any) -> str:
        if isinstance(value, str) and value.lower() in ("high", "medium", "low"):
            return value.lower()
        return "medium"

    @field_validator("observations", mode="before")
    @classmethod
    def ensure_observations_list(cls, value: Any) -> list:
        if isinstance(value, list):
            return value
        if isinstance(value, str):
            return [value] if value.strip() else []
        return []


# ---------------------------------------------------------------------------
# Chat models
# ---------------------------------------------------------------------------


class ChatMessage(BaseModel):
    """A single message in a chat conversation."""

    role: str = Field(..., description="'user' or 'assistant'")
    content: str = Field(..., min_length=1)

    @field_validator("role", mode="before")
    @classmethod
    def validate_role(cls, value: Any) -> str:
        if isinstance(value, str) and value in ("user", "assistant"):
            return value
        raise ValueError("role must be 'user' or 'assistant'")

    @field_validator("content", mode="before")
    @classmethod
    def content_not_empty(cls, value: Any) -> Any:
        if isinstance(value, str) and not value.strip():
            raise ValueError("content must not be empty")
        return value


class ChatRequest(BaseModel):
    """Request body for POST /api/chat."""

    messages: list[ChatMessage] = Field(
        ...,
        min_length=1,
        description="Conversation history including the latest user message.",
    )
    image_context: Optional[dict[str, Any]] = Field(
        default=None,
        description="Optional ImageAnalysisResult from a previous vision analysis.",
    )

    @field_validator("messages", mode="before")
    @classmethod
    def at_least_one_message(cls, value: Any) -> Any:
        if isinstance(value, list) and len(value) == 0:
            raise ValueError("messages must contain at least one message")
        return value


class ChatResponse(BaseModel):
    """Response from POST /api/chat."""

    reply: str
    role: str = "assistant"
