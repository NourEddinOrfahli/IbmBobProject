"""
Application configuration loaded from environment variables.
Never hardcodes secrets or API keys.
"""

import os
from dataclasses import dataclass, field
from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class NASAConfig:
    api_key: str = field(default_factory=lambda: os.getenv("NASA_API_KEY", "DEMO_KEY"))
    apod_url: str = "https://api.nasa.gov/planetary/apod"
    donki_url: str = "https://api.nasa.gov/DONKI"
    request_timeout: float = 15.0


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
            # Default: a capable free model that reliably produces Arabic JSON.
            # Override via OPENROUTER_MODEL env var — no source-code change needed.
            # "openrouter/auto" / "openrouter/free" must NOT be used as defaults
            # because OpenRouter may route them to safety-classifier or tiny models
            # that cannot generate valid structured Arabic content.
            "meta-llama/llama-3.3-70b-instruct:free",
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
    # Vision model used for image analysis (multimodal).
    # Defaults to a free vision-capable model on OpenRouter.
    vision_model: str = field(
        default_factory=lambda: os.getenv(
            "OPENROUTER_VISION_MODEL",
            "nvidia/nemotron-nano-12b-v2-vl:free",
        )
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
