"""
Application configuration loaded from environment variables.
Never hardcodes secrets or API keys.
"""

import os
from dataclasses import dataclass, field
from dotenv import load_dotenv

# Resolve .env from the project root (one level above this file) so that the
# server can be launched from any working directory (e.g. `cd backend; uvicorn
# main:app`) and still pick up the root-level .env file.
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))


@dataclass(frozen=True)
class NASAConfig:
    api_key: str = field(default_factory=lambda: os.getenv("NASA_API_KEY", "DEMO_KEY"))
    apod_url: str = "https://api.nasa.gov/planetary/apod"
    donki_url: str = "https://api.nasa.gov/DONKI"
    # 3 s strict timeout for APOD — keeps the UI snappy; fallback serves instantly on miss.
    request_timeout: float = float(os.getenv("NASA_REQUEST_TIMEOUT", "3"))
    # Separate timeout for DONKI — the DONKI endpoint is significantly slower than APOD
    # (typically 4-6 s) so it needs its own timeout independent of the APOD timeout.
    # Default: 12 s.  Set NASA_DONKI_TIMEOUT in .env to override.
    donki_request_timeout: float = float(os.getenv("NASA_DONKI_TIMEOUT", "12"))


@dataclass(frozen=True)
class OpenRouterConfig:
    api_key: str = field(default_factory=lambda: os.getenv("OPENROUTER_API_KEY", ""))
    base_url: str = field(
        default_factory=lambda: os.getenv(
            "OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"
        )
    )
    model: str = field(
        default_factory=lambda: os.getenv(
            "OPENROUTER_MODEL",
            # Default: nvidia/nemotron-3-ultra-550b-a55b:free
            # Verified working on the OpenRouter free tier (live-tested 2025).
            # DO NOT use openrouter/auto or openrouter/free — these route to
            # safety-classifier models that return "User Safety: safe" instead
            # of valid structured JSON responses.
            "nvidia/nemotron-3-ultra-550b-a55b:free",
        )
    )
    request_timeout: float = 60.0
    max_tokens: int = field(
        default_factory=lambda: int(os.getenv("OPENROUTER_MAX_TOKENS", "2000"))
    )
    temperature: float = 0.4
    # Minimum completion tokens required to be considered a real AI response.
    # Responses shorter than this are almost certainly classifier outputs,
    # safety-only responses, or empty replies — never valid story JSON.
    min_completion_tokens: int = field(
        default_factory=lambda: int(os.getenv("OPENROUTER_MIN_COMPLETION_TOKENS", "100"))
    )
    # Fallback model used when the primary model is rate-limited or unavailable.
    # Set to None (or leave env var unset) to disable fallback behaviour.
    # Must ALWAYS be a :free model — never set to a paid model.
    fallback_model: str | None = field(
        default_factory=lambda: os.getenv(
            "OPENROUTER_FALLBACK_MODEL",
            # poolside/laguna-s-2.1:free verified working on the free tier (2025).
            "poolside/laguna-s-2.1:free",
        ) or None
    )
    # Vision model used for image analysis (multimodal).
    # Must support the OpenAI vision (image_url) format.
    # Must ALWAYS be a :free model — never set to a paid model.
    vision_model: str = field(
        default_factory=lambda: os.getenv(
            "OPENROUTER_VISION_MODEL",
            # nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free verified working
            # for image_url vision with full structured JSON Arabic output (2025).
            "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free",
        )
    )
    # Fallback vision model — used when the primary vision model is rate-limited
    # or returns a 502/503 transient error.  Must ALWAYS be a :free model.
    vision_fallback_model: str | None = field(
        default_factory=lambda: os.getenv(
            "OPENROUTER_VISION_FALLBACK_MODEL",
            # minimax/minimax-m3:free verified working as vision fallback (2025).
            "minimax/minimax-m3:free",
        ) or None
    )


@dataclass(frozen=True)
class SchedulerConfig:
    """Configuration for the daily bulletin scheduler."""

    enabled: bool = field(
        default_factory=lambda: os.getenv("DAILY_BULLETIN_ENABLED", "false").lower() == "true"
    )
    hour: int = field(
        default_factory=lambda: int(os.getenv("DAILY_BULLETIN_HOUR", "7"))
    )
    minute: int = field(
        default_factory=lambda: int(os.getenv("DAILY_BULLETIN_MINUTE", "0"))
    )
    timezone: str = field(
        default_factory=lambda: os.getenv("DAILY_BULLETIN_TIMEZONE", "UTC")
    )
    # Directory for the bulletin JSON store (relative to CWD of the process)
    store_path: str = field(
        default_factory=lambda: os.getenv("BULLETIN_STORE_PATH", "bulletin_store.json")
    )


@dataclass(frozen=True)
class AppConfig:
    nasa: NASAConfig = field(default_factory=NASAConfig)
    openrouter: OpenRouterConfig = field(default_factory=OpenRouterConfig)
    scheduler: SchedulerConfig = field(default_factory=SchedulerConfig)
    debug: bool = field(default_factory=lambda: os.getenv("DEBUG", "false").lower() == "true")
    log_level: str = field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO").upper())


def get_config() -> AppConfig:
    """Return a fully populated AppConfig from the current environment."""
    return AppConfig(
        nasa=NASAConfig(),
        openrouter=OpenRouterConfig(),
        scheduler=SchedulerConfig(),
    )


def validate_config(config: AppConfig) -> list[str]:
    """
    Validate that mandatory runtime keys are present.
    Returns a list of warning/error messages (empty means OK).
    """
    issues: list[str] = []
    if not config.openrouter.api_key:
        issues.append(
            "OPENROUTER_API_KEY is not set. "
            "AI endpoints will fail until a valid key is provided."
        )
    if config.nasa.api_key == "DEMO_KEY":
        issues.append(
            "NASA_API_KEY is using the public DEMO_KEY. "
            "Rate limits are stricter. Set NASA_API_KEY in .env for production use."
        )
    if config.scheduler.enabled:
        if not (0 <= config.scheduler.hour <= 23):
            issues.append(
                f"DAILY_BULLETIN_HOUR={config.scheduler.hour} is out of range (0-23)."
            )
        if not (0 <= config.scheduler.minute <= 59):
            issues.append(
                f"DAILY_BULLETIN_MINUTE={config.scheduler.minute} is out of range (0-59)."
            )
    return issues
