from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

import requests


LOGGER = logging.getLogger(__name__)
LASTFM_API_URL = "https://ws.audioscrobbler.com/2.0/"


class LastFmError(RuntimeError):
    """Raised when Last.fm data cannot be loaded."""


class LastFmClient:
    def __init__(
        self,
        api_key: str,
        username: str,
        session: requests.Session | None = None,
        timeout: int = 20,
    ):
        self.api_key = api_key
        self.username = username
        self.session = session or requests.Session()
        self.timeout = timeout

    def get_recent_tracks(
        self,
        days: int = 7,
        now: datetime | None = None,
    ) -> list[dict[str, Any]]:
        end = now or datetime.now(timezone.utc)
        if end.tzinfo is None:
            end = end.replace(tzinfo=timezone.utc)
        end = end.astimezone(timezone.utc)
        start = end - timedelta(days=days)

        all_tracks: list[dict[str, Any]] = []
        seen: set[tuple[str, str, str]] = set()
        page = 1
        total_pages = 1

        while page <= total_pages:
            payload = self._request_page(start=start, end=end, page=page)
            recent_tracks = payload.get("recenttracks", {})
            total_pages = _parse_total_pages(recent_tracks)
            tracks = _as_list(recent_tracks.get("track", []))

            for raw_track in tracks:
                normalized = _normalize_track(raw_track)
                if normalized is None:
                    continue
                key = (
                    normalized["artist_name"].lower(),
                    normalized["track_name"].lower(),
                    normalized["played_at"].isoformat(),
                )
                if key in seen:
                    continue
                seen.add(key)
                all_tracks.append(normalized)

            LOGGER.info("Loaded Last.fm page %s/%s", page, total_pages)
            page += 1

        return all_tracks

    def _request_page(self, start: datetime, end: datetime, page: int) -> dict[str, Any]:
        params = {
            "method": "user.getRecentTracks",
            "user": self.username,
            "api_key": self.api_key,
            "format": "json",
            "from": int(start.timestamp()),
            "to": int(end.timestamp()),
            "limit": 200,
            "page": page,
        }

        try:
            response = self.session.get(LASTFM_API_URL, params=params, timeout=self.timeout)
            response.raise_for_status()
            payload = response.json()
        except requests.RequestException as exc:
            raise LastFmError("Could not connect to Last.fm API.") from exc
        except ValueError as exc:
            raise LastFmError("Last.fm returned invalid JSON.") from exc

        if "error" in payload:
            message = payload.get("message", "Unknown Last.fm API error")
            raise LastFmError(f"Last.fm API error: {message}")

        return payload


def _normalize_track(raw_track: dict[str, Any]) -> dict[str, Any] | None:
    date_info = raw_track.get("date")
    if not isinstance(date_info, dict) or not date_info.get("uts"):
        LOGGER.info("Skipping currently playing track without timestamp.")
        return None

    track_name = str(raw_track.get("name", "")).strip()
    artist_name = _field_text(raw_track.get("artist"))
    if not track_name or not artist_name:
        return None

    played_at = datetime.fromtimestamp(int(date_info["uts"]), tz=timezone.utc)

    return {
        "track_name": track_name,
        "artist_name": artist_name,
        "album_name": _field_text(raw_track.get("album")),
        "played_at": played_at,
        "lastfm_url": str(raw_track.get("url", "")).strip() or None,
    }


def _field_text(value: Any) -> str | None:
    if isinstance(value, dict):
        text = str(value.get("#text", "")).strip()
        return text or None
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _as_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if isinstance(value, dict):
        return [value]
    return []


def _parse_total_pages(recent_tracks: dict[str, Any]) -> int:
    attrs = recent_tracks.get("@attr", {}) if isinstance(recent_tracks, dict) else {}
    raw_total = attrs.get("totalPages", 1)
    try:
        return max(1, int(raw_total))
    except (TypeError, ValueError):
        return 1
