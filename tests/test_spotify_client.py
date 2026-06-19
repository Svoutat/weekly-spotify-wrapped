import requests

import spotify_client
from spotify_client import PlaylistResult, SpotifyClient, SpotifyError


class FakeResponse:
    def __init__(
        self,
        payload=None,
        status_code: int = 200,
        text: str = "{}",
        headers: dict[str, str] | None = None,
        json_error: Exception | None = None,
    ):
        self.payload = payload if payload is not None else {}
        self.status_code = status_code
        self.text = text
        self.headers = headers or {}
        self.json_error = json_error

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            error = requests.HTTPError("HTTP error")
            error.response = self
            raise error

    def json(self):
        if self.json_error:
            raise self.json_error
        return self.payload


def _track_payload() -> dict:
    return {
        "id": "track-1",
        "duration_ms": 185000,
        "external_urls": {"spotify": "https://open.spotify.com/track/track-1"},
        "album": {
            "name": "Album A",
            "images": [{"url": "https://example.com/cover.jpg"}],
        },
        "artists": [{"id": "artist-1", "name": "Artist A"}],
    }


class EnrichmentSession:
    def __init__(self):
        self.posts = []
        self.gets = []

    def post(self, url: str, **kwargs):
        self.posts.append((url, kwargs))
        return FakeResponse({"access_token": "client-token", "expires_in": 3600})

    def get(self, url: str, **kwargs):
        self.gets.append((url, kwargs))
        if url.endswith("/search"):
            return FakeResponse({"tracks": {"items": [_track_payload()]}})
        if url.endswith("/artists/artist-1"):
            return FakeResponse({"images": [{"url": "https://example.com/artist.jpg"}]})
        raise AssertionError(f"Unexpected URL: {url}")


def test_enrich_track_adds_spotify_metadata_and_artist_image() -> None:
    session = EnrichmentSession()
    client = SpotifyClient("client-id", "client-secret", session=session)

    enriched = client.enrich_track({"track_name": "Song A", "artist_name": "Artist A"})

    assert enriched["spotify_track_id"] == "track-1"
    assert enriched["spotify_track_url"] == "https://open.spotify.com/track/track-1"
    assert enriched["spotify_duration_ms"] == 185000
    assert enriched["spotify_album_name"] == "Album A"
    assert enriched["spotify_cover_url"] == "https://example.com/cover.jpg"
    assert enriched["spotify_artist_id"] == "artist-1"
    assert enriched["spotify_artist_image_url"] == "https://example.com/artist.jpg"
    assert session.posts[0][1]["data"]["grant_type"] == "client_credentials"


def test_enrich_tracks_reuses_cached_metadata_for_duplicate_tracks() -> None:
    session = EnrichmentSession()
    client = SpotifyClient("client-id", "client-secret", session=session)

    enriched = client.enrich_tracks(
        [
            {"track_name": "Song A", "artist_name": "Artist A", "played_at": "first"},
            {"track_name": "Song A", "artist_name": "Artist A", "played_at": "second"},
        ]
    )

    search_calls = [call for call in session.gets if call[0].endswith("/search")]
    artist_calls = [call for call in session.gets if call[0].endswith("/artists/artist-1")]
    assert len(search_calls) == 1
    assert len(artist_calls) == 1
    assert enriched[0]["spotify_track_id"] == "track-1"
    assert enriched[1]["spotify_track_id"] == "track-1"
    assert enriched[1]["played_at"] == "second"


class RateLimitSession:
    def __init__(self):
        self.posts = []
        self.gets = []

    def post(self, url: str, **kwargs):
        self.posts.append((url, kwargs))
        return FakeResponse({"access_token": "client-token", "expires_in": 3600})

    def get(self, url: str, **kwargs):
        self.gets.append((url, kwargs))
        return FakeResponse(
            {"error": {"message": "Too many requests"}},
            status_code=429,
            text='{"error":{"message":"Too many requests"}}',
            headers={"Retry-After": "0"},
        )


def test_enrich_tracks_stops_after_spotify_rate_limit() -> None:
    session = RateLimitSession()
    client = SpotifyClient("client-id", "client-secret", session=session)

    tracks = [
        {"track_name": "Song A", "artist_name": "Artist A"},
        {"track_name": "Song B", "artist_name": "Artist B"},
        {"track_name": "Song C", "artist_name": "Artist C"},
    ]

    enriched = client.enrich_tracks(tracks)

    assert enriched == tracks
    assert len(session.gets) == 2


class FallbackSearchSession(EnrichmentSession):
    def get(self, url: str, **kwargs):
        self.gets.append((url, kwargs))
        if url.endswith("/search") and len([call for call in self.gets if call[0].endswith("/search")]) == 1:
            return FakeResponse({"tracks": {"items": []}})
        if url.endswith("/search"):
            return FakeResponse({"tracks": {"items": [_track_payload()]}})
        if url.endswith("/artists/artist-1"):
            return FakeResponse({"images": []})
        raise AssertionError(f"Unexpected URL: {url}")


def test_search_track_uses_fallback_query_when_exact_search_has_no_results() -> None:
    session = FallbackSearchSession()
    client = SpotifyClient("client-id", "client-secret", session=session)

    result = client.search_track("Song A", "Artist A")

    search_calls = [call for call in session.gets if call[0].endswith("/search")]
    assert result["id"] == "track-1"
    assert len(search_calls) == 2
    assert search_calls[0][1]["params"]["q"] == 'track:"Song A" artist:"Artist A"'
    assert search_calls[1][1]["params"]["q"] == "Song A Artist A"


class PlaylistSession:
    def __init__(self):
        self.posts = []
        self.puts = []

    def post(self, url: str, **kwargs):
        self.posts.append((url, kwargs))
        return FakeResponse({"access_token": "user-token"})

    def put(self, url: str, **kwargs):
        self.puts.append((url, kwargs))
        return FakeResponse({}, text="")


def test_update_playlist_deduplicates_ids_and_sends_spotify_uris() -> None:
    session = PlaylistSession()
    client = SpotifyClient(
        "client-id",
        "client-secret",
        refresh_token="refresh-token",
        session=session,
    )

    result = client.update_playlist("playlist-1", ["track-1", "track-1", "", None, "track-2"])

    assert result == PlaylistResult(
        True,
        "https://open.spotify.com/playlist/playlist-1",
        "Playlist updated with 2 tracks.",
    )
    assert session.posts[0][1]["data"]["grant_type"] == "refresh_token"
    assert session.puts[0][1]["json"] == {
        "uris": ["spotify:track:track-1", "spotify:track:track-2"]
    }


def test_update_playlist_skips_when_no_track_ids_exist() -> None:
    client = SpotifyClient("client-id", "client-secret", refresh_token="refresh-token")

    result = client.update_playlist("playlist-1", ["", None])

    assert result.updated is False
    assert "No Spotify track IDs" in result.message


def test_api_error_includes_spotify_response_message() -> None:
    response = FakeResponse(
        {"error": {"message": "Forbidden"}},
        status_code=403,
        text='{"error":{"message":"Forbidden"}}',
    )

    assert "Forbidden" in spotify_client._response_error_message(response)

    class ErrorSession:
        def get(self, url: str, **kwargs):
            return response

    client = SpotifyClient("client-id", "client-secret", session=ErrorSession())

    try:
        client._api_get("/me", token="token")
    except SpotifyError as exc:
        assert "HTTP 403" in str(exc)
        assert "Forbidden" in str(exc)
    else:
        raise AssertionError("SpotifyError was not raised")
