"""
NASA API client.

Fetches data from:
- Astronomy Picture of the Day (APOD)
- DONKI space-weather events (optional)

Handles HTTP errors, timeouts, rate limits, and missing fields gracefully.
"""

from __future__ import annotations

import logging
from datetime import date
from typing import Any, Optional

import httpx

from config import NASAConfig
from models import NASAAPODData, NASADONKIEvent

logger = logging.getLogger(__name__)


class NASAClientError(Exception):
    """Raised when a NASA API call fails in a way the caller must handle."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class NASAClient:
    """Thin async wrapper around the NASA public APIs."""

    def __init__(self, config: NASAConfig) -> None:
        self._config = config
        self._client = httpx.AsyncClient(timeout=config.request_timeout)

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------

    async def get_apod(self, apod_date: Optional[str] = None) -> NASAAPODData:
        """
        Fetch the Astronomy Picture of the Day.

        Parameters
        ----------
        apod_date:
            ISO-8601 date string (``YYYY-MM-DD``).  Defaults to today when
            *None*.

        Returns
        -------
        NASAAPODData
            Normalised payload.

        Raises
        ------
        NASAClientError
            On any retrieval or validation failure.
        """
        params: dict[str, str] = {"api_key": self._config.api_key}
        if apod_date:
            params["date"] = apod_date

        raw = await self._get(self._config.apod_url, params, source="APOD")
        return self._normalise_apod(raw)

    async def get_donki_cme(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> list[NASADONKIEvent]:
        """
        Fetch Coronal Mass Ejection events from DONKI.

        Returns an empty list if the endpoint fails, so the rest of the
        pipeline can continue without CME data.
        """
        url = f"{self._config.donki_url}/CME"
        params: dict[str, str] = {"api_key": self._config.api_key}
        if start_date:
            params["startDate"] = start_date
        if end_date:
            params["endDate"] = end_date

        try:
            raw_list = await self._get(url, params, source="DONKI/CME")
        except NASAClientError as exc:
            logger.warning("DONKI CME fetch failed (non-fatal): %s", exc.message)
            return []

        if not isinstance(raw_list, list):
            logger.warning("DONKI CME returned unexpected type: %s", type(raw_list))
            return []

        events: list[NASADONKIEvent] = []
        for item in raw_list:
            try:
                events.append(self._normalise_donki_cme(item))
            except Exception as exc:  # noqa: BLE001
                logger.debug("Skipping malformed DONKI item: %s", exc)
        return events

    async def close(self) -> None:
        """Release the underlying HTTP client."""
        await self._client.aclose()

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _get(
        self,
        url: str,
        params: dict[str, str],
        source: str,
    ) -> Any:
        """
        Perform an async GET request and return the parsed JSON body.

        Raises NASAClientError on any failure so the caller can handle it
        uniformly without worrying about HTTP details.
        """
        logger.debug("NASA %s request → %s", source, url)
        try:
            response = await self._client.get(url, params=params)
        except httpx.TimeoutException:
            raise NASAClientError(
                "NASA_TIMEOUT",
                f"Request to NASA {source} timed out after {self._config.request_timeout}s",
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
            # NASA returns a JSON body with an error message for bad requests
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

        # Mandatory fields
        title = raw.get("title") or ""
        explanation = raw.get("explanation") or ""
        date_str = raw.get("date") or str(date.today())
        media_type = raw.get("media_type", "image")

        if not title or not explanation:
            raise NASAClientError(
                "NASA_MISSING_FIELDS",
                "APOD response is missing required fields (title / explanation).",
            )

        # Optional fields
        url = raw.get("url")
        hdurl = raw.get("hdurl")
        copyright_ = raw.get("copyright")

        # Capture everything else as additional_data for completeness
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
