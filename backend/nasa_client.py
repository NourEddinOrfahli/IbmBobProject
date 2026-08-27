"""
NASA API client.

Fetches data from:
- Astronomy Picture of the Day (APOD)
- DONKI space-weather events (optional)

Handles HTTP errors, timeouts, rate limits, and missing fields gracefully.

Performance optimisations (Phase 4):
- In-memory TTL cache via _TTLCache so repeated calls within the TTL window
  return instantly without hitting NASA servers.
  * APOD:      TTL = 3 600 s  (1 hour)   — changes once per day
  * DONKI/CME: TTL =   900 s  (15 min)   — space-weather updates more often
- Explicit per-request timeout passed from NASAConfig (default 15 s).
- Rate-limit (429) and server-error paths return cached stale data when
  available instead of raising, so the pipeline degrades gracefully.
"""

from __future__ import annotations

import logging
import time
from datetime import date
from typing import Any, Optional

import httpx

from config import NASAConfig
from models import NASAAPODData, NASADONKIEvent

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Tiny in-memory TTL cache
# ---------------------------------------------------------------------------

class _TTLCache:
    """
    Thread-safe, in-process TTL key/value cache.

    Each entry is stored as ``(value, expires_at)``.  After ``expires_at``
    the entry is treated as absent; a background eviction loop is NOT needed
    because stale entries are simply overwritten on the next cache miss.

    This is intentionally minimal — no external dependencies, no async
    primitives required (dict access in CPython is GIL-protected).
    """

    def __init__(self) -> None:
        self._store: dict[str, tuple[Any, float]] = {}

    def get(self, key: str) -> Any:
        """Return the cached value or ``_MISS`` sentinel if absent/expired."""
        entry = self._store.get(key)
        if entry is None:
            return _MISS
        value, expires_at = entry
        if time.monotonic() > expires_at:
            # Expired — remove and signal miss
            del self._store[key]
            return _MISS
        return value

    def set(self, key: str, value: Any, ttl_seconds: float) -> None:
        """Store *value* under *key* for *ttl_seconds* seconds."""
        self._store[key] = (value, time.monotonic() + ttl_seconds)

    def invalidate(self, key: str) -> None:
        """Remove a single cache entry (no-op if absent)."""
        self._store.pop(key, None)

    def clear(self) -> None:
        """Remove all entries (useful in tests)."""
        self._store.clear()

    def __len__(self) -> int:
        # Evict expired entries before reporting size
        now = time.monotonic()
        expired = [k for k, (_, exp) in self._store.items() if now > exp]
        for k in expired:
            del self._store[k]
        return len(self._store)


_MISS = object()  # sentinel — distinct from None so None can be a valid cached value

# Module-level shared caches (one per data type)
_apod_cache:  _TTLCache = _TTLCache()
_donki_cache: _TTLCache = _TTLCache()

# TTL constants
_APOD_TTL_SECONDS:  float = 3_600.0   # 1 hour  — APOD changes once per day
_DONKI_TTL_SECONDS: float =   900.0   # 15 min  — space-weather updates more often


# ---------------------------------------------------------------------------
# Public helper: allow tests / admin endpoints to flush caches
# ---------------------------------------------------------------------------

def clear_nasa_caches() -> None:
    """Flush all NASA response caches.  Call from tests or admin endpoints."""
    _apod_cache.clear()
    _donki_cache.clear()


# ---------------------------------------------------------------------------
# Exception
# ---------------------------------------------------------------------------

class NASAClientError(Exception):
    """Raised when a NASA API call fails in a way the caller must handle."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


# ---------------------------------------------------------------------------
# NASAClient
# ---------------------------------------------------------------------------

class NASAClient:
    """Thin async wrapper around the NASA public APIs with TTL caching."""

    def __init__(self, config: NASAConfig) -> None:
        self._config = config
        # Primary client uses the APOD timeout (3 s by default — keeps dashboard snappy).
        self._client = httpx.AsyncClient(timeout=config.request_timeout)
        # Separate client for DONKI — uses the longer donki_request_timeout (12 s default)
        # because the DONKI endpoint is significantly slower than APOD.
        self._donki_client = httpx.AsyncClient(timeout=config.donki_request_timeout)

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------

    async def get_apod(self, apod_date: Optional[str] = None) -> NASAAPODData:
        """
        Fetch the Astronomy Picture of the Day.

        Cache key includes the requested date so different dates are stored
        independently.  ``None`` (today) is normalised to the literal string
        ``"today"`` for stable cache keys.

        Parameters
        ----------
        apod_date:
            ISO-8601 date string (``YYYY-MM-DD``).  Defaults to today when
            *None*.

        Returns
        -------
        NASAAPODData

        Raises
        ------
        NASAClientError
            On any retrieval or validation failure when no stale cache entry
            is available.
        """
        cache_key = f"apod:{apod_date or 'today'}"

        # ── Cache hit ─────────────────────────────────────────────────────
        cached = _apod_cache.get(cache_key)
        if cached is not _MISS:
            logger.debug("NASA APOD cache hit (key=%s)", cache_key)
            return cached  # type: ignore[return-value]

        # ── Fetch from NASA ───────────────────────────────────────────────
        params: dict[str, str] = {"api_key": self._config.api_key}
        if apod_date:
            params["date"] = apod_date

        try:
            raw = await self._get(self._config.apod_url, params, source="APOD")
        except NASAClientError:
            # On transient failure, serve stale cached data if we have it.
            # (Cache already expired at this point — check the raw store.)
            stale = self._stale_apod(cache_key)
            if stale is not None:
                logger.warning(
                    "NASA APOD fetch failed — serving stale cache for key=%s", cache_key
                )
                return stale
            raise  # no stale data available — propagate

        result = self._normalise_apod(raw)
        _apod_cache.set(cache_key, result, _APOD_TTL_SECONDS)
        logger.debug(
            "NASA APOD fetched and cached (key=%s, ttl=%.0fs)", cache_key, _APOD_TTL_SECONDS
        )
        return result

    async def get_donki_cme(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> list[NASADONKIEvent]:
        """
        Fetch Coronal Mass Ejection events from DONKI.

        Returns an empty list if the endpoint fails and no stale data exists,
        so the rest of the pipeline can continue without CME data.
        """
        cache_key = f"donki:cme:{start_date or ''}:{end_date or ''}"

        # ── Cache hit ─────────────────────────────────────────────────────
        cached = _donki_cache.get(cache_key)
        if cached is not _MISS:
            logger.debug("NASA DONKI cache hit (key=%s)", cache_key)
            return cached  # type: ignore[return-value]

        # ── Fetch from NASA ───────────────────────────────────────────────
        url = f"{self._config.donki_url}/CME"
        params: dict[str, str] = {"api_key": self._config.api_key}
        if start_date:
            params["startDate"] = start_date
        if end_date:
            params["endDate"] = end_date

        try:
            raw_list = await self._get(url, params, source="DONKI/CME", client=self._donki_client)
        except NASAClientError as exc:
            logger.warning("DONKI CME fetch failed (non-fatal): %s", exc.message)
            # Serve stale if available
            stale = self._stale_donki(cache_key)
            return stale if stale is not None else []

        if not isinstance(raw_list, list):
            logger.warning("DONKI CME returned unexpected type: %s", type(raw_list))
            return []

        events: list[NASADONKIEvent] = []
        for item in raw_list:
            try:
                events.append(self._normalise_donki_cme(item))
            except Exception as exc:  # noqa: BLE001
                logger.debug("Skipping malformed DONKI item: %s", exc)

        _donki_cache.set(cache_key, events, _DONKI_TTL_SECONDS)
        logger.debug(
            "NASA DONKI fetched and cached (key=%s, events=%d, ttl=%.0fs)",
            cache_key, len(events), _DONKI_TTL_SECONDS,
        )
        return events

    async def close(self) -> None:
        """Release the underlying HTTP clients."""
        await self._client.aclose()
        await self._donki_client.aclose()

    # ------------------------------------------------------------------
    # Stale-data helpers (access raw _store before eviction)
    # ------------------------------------------------------------------

    @staticmethod
    def _stale_apod(cache_key: str) -> Optional[NASAAPODData]:
        """Return any cached APOD entry regardless of expiry, or None."""
        entry = _apod_cache._store.get(cache_key)  # noqa: SLF001
        return entry[0] if entry is not None else None

    @staticmethod
    def _stale_donki(cache_key: str) -> Optional[list[NASADONKIEvent]]:
        """Return any cached DONKI entry regardless of expiry, or None."""
        entry = _donki_cache._store.get(cache_key)  # noqa: SLF001
        return entry[0] if entry is not None else None

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _get(
        self,
        url: str,
        params: dict[str, str],
        source: str,
        *,
        client: "httpx.AsyncClient | None" = None,
    ) -> Any:
        """
        Perform an async GET request and return the parsed JSON body.

        ``client`` defaults to ``self._client`` (APOD timeout).  Pass
        ``self._donki_client`` for DONKI requests to use the longer timeout.

        Raises NASAClientError on any failure so the caller can handle it
        uniformly without worrying about HTTP details.
        """
        http = client if client is not None else self._client
        timeout_s = http.timeout.read if hasattr(http, "timeout") else self._config.request_timeout
        logger.debug("NASA %s request -> %s", source, url)
        try:
            response = await http.get(url, params=params)
        except httpx.TimeoutException:
            raise NASAClientError(
                "NASA_TIMEOUT",
                f"Request to NASA {source} timed out after {timeout_s}s",
            )
        except httpx.RequestError as exc:
            raise NASAClientError(
                "NASA_NETWORK_ERROR",
                f"Network error reaching NASA {source}: {exc}",
            )

        if response.status_code == 429:
            raise NASAClientError(
                "NASA_RATE_LIMIT",
                f"NASA {source} rate limit exceeded. Try again later.",
            )
        if response.status_code == 400:
            detail = self._safe_error_text(response)
            raise NASAClientError(
                "NASA_BAD_REQUEST",
                f"NASA {source} rejected the request: {detail}",
            )
        if response.status_code >= 500:
            raise NASAClientError(
                "NASA_SERVER_ERROR",
                f"NASA {source} server error ({response.status_code}).",
            )
        if not response.is_success:
            raise NASAClientError(
                "NASA_API_ERROR",
                f"NASA {source} returned HTTP {response.status_code}.",
            )

        try:
            return response.json()
        except Exception:  # noqa: BLE001
            raise NASAClientError(
                "NASA_INVALID_JSON",
                f"NASA {source} returned non-JSON content.",
            )

    # ------------------------------------------------------------------
    # Normalisers
    # ------------------------------------------------------------------

    @staticmethod
    def _normalise_apod(raw: dict[str, Any]) -> NASAAPODData:
        """Convert raw APOD JSON to a validated NASAAPODData instance."""
        if not isinstance(raw, dict):
            raise NASAClientError(
                "NASA_UNEXPECTED_FORMAT",
                "APOD response was not a JSON object.",
            )

        title = raw.get("title") or ""
        explanation = raw.get("explanation") or ""
        date_str = raw.get("date") or str(date.today())
        media_type = raw.get("media_type", "image")

        if not title or not explanation:
            raise NASAClientError(
                "NASA_MISSING_FIELDS",
                "APOD response is missing required fields (title / explanation).",
            )

        url = raw.get("url")
        hdurl = raw.get("hdurl")
        copyright_ = raw.get("copyright")

        known_keys = {"title", "explanation", "date", "media_type", "url", "hdurl", "copyright"}
        additional = {k: v for k, v in raw.items() if k not in known_keys}

        try:
            return NASAAPODData(
                title=title,
                explanation=explanation,
                date=date_str,
                media_type=media_type,
                image_url=url,
                hd_image_url=hdurl,
                copyright=copyright_,
                additional_data=additional,
            )
        except Exception as exc:  # noqa: BLE001
            raise NASAClientError(
                "NASA_VALIDATION_ERROR",
                f"APOD data failed validation: {exc}",
            )

    @staticmethod
    def _normalise_donki_cme(raw: dict[str, Any]) -> NASADONKIEvent:
        linked = [
            e.get("activityID", "")
            for e in (raw.get("linkedEvents") or [])
            if isinstance(e, dict)
        ]
        return NASADONKIEvent(
            event_type="CME",
            begin_time=raw.get("startTime"),
            end_time=None,
            linked_events=linked,
            raw=raw,
        )

    @staticmethod
    def _safe_error_text(response: httpx.Response) -> str:
        try:
            body = response.json()
            if isinstance(body, dict):
                return body.get("msg") or body.get("error") or str(body)
            return str(body)
        except Exception:  # noqa: BLE001
            return response.text[:200]
