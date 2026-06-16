from datetime import datetime, timedelta, timezone

import pytest
import requests

from lastfm_client import LastFmClient, LastFmError


class FakeResponse:
    def __init__(self, payload=None, status_code: int = 200, json_error: Exception | None = None):
        self.payload = payload
        self.status_code = status_code
        self.json_error = json_error
        self.text = ""
        self.headers = {}

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            error = requests.HTTPError("HTTP error")
            error.response = self
            raise error

    def json(self):
        if self.json_error:
            raise self.json_error
        return self.payload


class FakeSession:
    def __init__(self, responses: list[FakeResponse]):
        self.responses = responses
        self.calls = []

    def get(self, url: str, **kwargs):
        self.calls.append((url, kwargs))
        return self.responses.pop(0)


def test_get_recent_tracks_normalizes_tracks_and_skips_currently_playing() -> None:
    now = datetime(2026, 6, 3, 12, 0, tzinfo=timezone.utc)
    played_at = now - timedelta(hours=1)
    session = FakeSession(
        [
            FakeResponse(
                {
                    "recenttracks": {
                        "@attr": {"totalPages": "1"},
                        "track": [
                            {
                                "name": " Song A ",
                                "artist": {"#text": "Artist A"},
                                "album": {"#text": "Album A"},
                                "date": {"uts": str(int(played_at.timestamp()))},
                                "url": "https://last.fm/song-a",
                            },
                            {
                                "name": "Currently Playing",
                                "artist": {"#text": "Artist B"},
                                "album": {"#text": "Album B"},
                            },
                        ],
                    }
                }
            )
        ]
    )

    client = LastFmClient(api_key="key", username="user", session=session)
    tracks = client.get_recent_tracks(days=7, now=now)

    assert len(tracks) == 1
    assert tracks[0]["track_name"] == "Song A"
    assert tracks[0]["artist_name"] == "Artist A"
    assert tracks[0]["album_name"] == "Album A"
    assert tracks[0]["played_at"] == played_at.replace(microsecond=0)
    assert session.calls[0][1]["params"]["from"] == int((now - timedelta(days=7)).timestamp())
    assert session.calls[0][1]["params"]["to"] == int(now.timestamp())


def test_get_recent_tracks_removes_duplicates_across_pages() -> None:
    now = datetime(2026, 6, 3, 12, 0, tzinfo=timezone.utc)
    played_at = now - timedelta(minutes=10)
    raw_track = {
        "name": "Song A",
        "artist": {"#text": "Artist A"},
        "date": {"uts": str(int(played_at.timestamp()))},
    }
    session = FakeSession(
        [
            FakeResponse({"recenttracks": {"@attr": {"totalPages": "2"}, "track": [raw_track]}}),
            FakeResponse({"recenttracks": {"@attr": {"totalPages": "2"}, "track": [raw_track]}}),
        ]
    )

    tracks = LastFmClient("key", "user", session=session).get_recent_tracks(now=now)

    assert len(tracks) == 1
    assert len(session.calls) == 2


def test_get_recent_tracks_raises_for_lastfm_api_error() -> None:
    session = FakeSession([FakeResponse({"error": 6, "message": "Invalid parameters"})])

    with pytest.raises(LastFmError, match="Invalid parameters"):
        LastFmClient("key", "user", session=session).get_recent_tracks()


def test_get_recent_tracks_raises_for_invalid_json() -> None:
    session = FakeSession([FakeResponse(json_error=ValueError("bad json"))])

    with pytest.raises(LastFmError, match="invalid JSON"):
        LastFmClient("key", "user", session=session).get_recent_tracks()
