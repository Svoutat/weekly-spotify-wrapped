from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Iterable

import requests


LOGGER = logging.getLogger(__name__)
TOKEN_URL = "https://accounts.spotify.com/api/token"
API_BASE_URL = "https://api.spotify.com/v1"


class SpotifyError(RuntimeError):
    """Raised when Spotify data cannot be loaded."""


@dataclass(frozen=True)
class PlaylistResult:
    updated: bool
    url: str | None
    message: str


class SpotifyClient:
    def __init__(
        self,
        client_id: str,
        client_secret: str,
        refresh_token: str | None = None,
        session: requests.Session | None = None,
        timeout: int = 20,
    ):
        self.client_id = client_id
        self.client_secret = client_secret
        self.refresh_token = refresh_token
        self.session = session or requests.Session()
        self.timeout = timeout
        self._client_token: str | None = None
        self._client_token_expires_at = datetime.min.replace(tzinfo=timezone.utc)
        self._artist_cache: dict[str, dict[str, Any] | None] = {}

    def enrich_tracks(self, tracks: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
        enriched_tracks: list[dict[str, Any]] = []
        for track in tracks:
            try:
                enriched_tracks.append(self.enrich_track(track))
            except SpotifyError as exc:
                LOGGER.warning(
                    "Spotify enrichment skipped for '%s' by '%s': %s",
                    track.get("track_name"),
                    track.get("artist_name"),
                    exc,
                )
                enriched_tracks.append(dict(track))
        return enriched_tracks

    def enrich_track(self, track: dict[str, Any]) -> dict[str, Any]:
        result = self.search_track(
            track_name=str(track.get("track_name", "")),
            artist_name=str(track.get("artist_name", "")),
        )
        if result is None:
            return dict(track)

        enriched = dict(track)
        album = result.get("album", {}) or {}
        images = album.get("images", []) or []
        external_urls = result.get("external_urls", {}) or {}
        artist = _first_artist(result)
        artist_id = artist.get("id") if artist else None
        artist_image_url = self._artist_image_url(artist_id) if artist_id else None

        enriched.update(
            {
                "spotify_track_id": result.get("id"),
                "spotify_track_url": external_urls.get("spotify"),
                "spotify_duration_ms": result.get("duration_ms"),
                "spotify_album_name": album.get("name"),
                "spotify_cover_url": images[0].get("url") if images else None,
                "spotify_artist_id": artist_id,
                "spotify_artist_image_url": artist_image_url,
            }
        )
        return enriched

    def search_track(self, track_name: str, artist_name: str) -> dict[str, Any] | None:
        token = self._get_client_token()
        query = f'track:"{track_name}" artist:"{artist_name}"'
        payload = self._api_get(
            "/search",
            token=token,
            params={"q": query, "type": "track", "limit": 1},
        )
        items = payload.get("tracks", {}).get("items", [])

        if not items:
            fallback_query = f"{track_name} {artist_name}"
            payload = self._api_get(
                "/search",
                token=token,
                params={"q": fallback_query, "type": "track", "limit": 1},
            )
            items = payload.get("tracks", {}).get("items", [])

        return items[0] if items else None

    def _artist_image_url(self, artist_id: str) -> str | None:
        artist = self._get_artist(artist_id)
        if not artist:
            return None
        images = artist.get("images", []) or []
        return images[0].get("url") if images else None

    def _get_artist(self, artist_id: str) -> dict[str, Any] | None:
        if artist_id in self._artist_cache:
            return self._artist_cache[artist_id]

        token = self._get_client_token()
        payload = self._api_get(f"/artists/{artist_id}", token=token)
        self._artist_cache[artist_id] = payload
        return payload

    def update_playlist(
        self,
        playlist_id: str | None,
        track_ids: Iterable[str],
    ) -> PlaylistResult:
        clean_ids = list(dict.fromkeys(track_id for track_id in track_ids if track_id))
        if not clean_ids:
            return PlaylistResult(False, None, "No Spotify track IDs found for playlist update.")
        if not self.refresh_token:
            return PlaylistResult(False, None, "SPOTIFY_REFRESH_TOKEN is missing; playlist skipped.")
        if not playlist_id:
            return PlaylistResult(False, None, "SPOTIFY_PLAYLIST_ID is missing; playlist skipped.")

        token = self._get_user_token()
        uris = [f"spotify:track:{track_id}" for track_id in clean_ids[:100]]
        self._api_put(
            f"/playlists/{playlist_id}/tracks",
            token=token,
            json={"uris": uris},
        )
        url = f"https://open.spotify.com/playlist/{playlist_id}"
        return PlaylistResult(True, url, f"Playlist updated with {len(uris)} tracks.")

    def _get_client_token(self) -> str:
        now = datetime.now(timezone.utc)
        if self._client_token and now < self._client_token_expires_at:
            return self._client_token

        payload = self._request_token({"grant_type": "client_credentials"})
        access_token = payload.get("access_token")
        if not access_token:
            raise SpotifyError("Spotify client credentials token was missing.")

        expires_in = int(payload.get("expires_in", 3600))
        self._client_token = access_token
        self._client_token_expires_at = now + timedelta(seconds=max(60, expires_in - 60))
        return access_token

    def _get_user_token(self) -> str:
        if not self.refresh_token:
            raise SpotifyError("Spotify refresh token is missing.")
        payload = self._request_token(
            {
                "grant_type": "refresh_token",
                "refresh_token": self.refresh_token,
            }
        )
        access_token = payload.get("access_token")
        if not access_token:
            raise SpotifyError("Spotify user access token was missing.")
        return access_token

    def _request_token(self, data: dict[str, str]) -> dict[str, Any]:
        try:
            response = self.session.post(
                TOKEN_URL,
                data=data,
                auth=(self.client_id, self.client_secret),
                timeout=self.timeout,
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as exc:
            raise SpotifyError("Could not authenticate with Spotify.") from exc
        except ValueError as exc:
            raise SpotifyError("Spotify returned invalid token JSON.") from exc

    def _api_get(self, path: str, token: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        response = self._request_with_retry(
            "get",
            f"{API_BASE_URL}{path}",
            headers={"Authorization": f"Bearer {token}"},
            params=params or {},
        )
        return self._json_response(response, "Spotify API returned invalid JSON.")

    def _api_put(self, path: str, token: str, json: dict[str, Any]) -> dict[str, Any]:
        response = self._request_with_retry(
            "put",
            f"{API_BASE_URL}{path}",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json=json,
        )
        if response.text.strip():
            return self._json_response(response, "Spotify API returned invalid JSON.")
        return {}

    def _request_with_retry(self, method: str, url: str, **kwargs: Any) -> requests.Response:
        request_method = getattr(self.session, method)
        try:
            response = request_method(url, timeout=self.timeout, **kwargs)
            if response.status_code == 429:
                retry_after = int(response.headers.get("Retry-After", "1"))
                time.sleep(min(retry_after, 5))
                response = request_method(url, timeout=self.timeout, **kwargs)
            response.raise_for_status()
            return response
        except requests.RequestException as exc:
            response = getattr(exc, "response", None)
            if response is not None:
                raise SpotifyError(
                    f"Spotify API request failed with HTTP {response.status_code}: "
                    f"{_response_error_message(response)}"
                ) from exc
            raise SpotifyError("Spotify API request failed.") from exc

    def _json_response(self, response: requests.Response, error_message: str) -> dict[str, Any]:
        try:
            return response.json()
        except ValueError as exc:
            raise SpotifyError(error_message) from exc


def _response_error_message(response: requests.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        return response.text.strip()[:200] or "No response body"

    error = payload.get("error")
    if isinstance(error, dict):
        return str(error.get("message") or error.get("reason") or payload)[:200]
    return str(payload)[:200]


def _first_artist(track_payload: dict[str, Any]) -> dict[str, Any] | None:
    artists = track_payload.get("artists") or []
    if artists and isinstance(artists[0], dict):
        return artists[0]
    return None
