from datetime import datetime, timedelta, timezone

from database import DatabaseManager


def test_database_prevents_duplicate_tracks(tmp_path) -> None:
    database = DatabaseManager(tmp_path / "wrapped.sqlite3")
    database.initialize()

    track = {
        "track_name": "Song A",
        "artist_name": "Artist A",
        "album_name": "Album A",
        "played_at": datetime(2026, 6, 1, 12, 0, tzinfo=timezone.utc),
        "lastfm_url": "https://last.fm/music/artist/song",
    }

    inserted, skipped = database.save_tracks([track, track])

    assert inserted == 1
    assert skipped == 1
    assert database.count_tracks() == 1


def test_fetch_tracks_between_returns_only_requested_period(tmp_path) -> None:
    database = DatabaseManager(tmp_path / "wrapped.sqlite3")
    database.initialize()

    now = datetime(2026, 6, 3, 12, 0, tzinfo=timezone.utc)
    database.save_tracks(
        [
            {
                "track_name": "Inside",
                "artist_name": "Artist A",
                "played_at": now - timedelta(days=1),
            },
            {
                "track_name": "Outside",
                "artist_name": "Artist B",
                "played_at": now - timedelta(days=10),
            },
        ]
    )

    tracks = database.fetch_tracks_between(now - timedelta(days=7), now)

    assert len(tracks) == 1
    assert tracks[0]["track_name"] == "Inside"


def test_existing_duplicate_can_receive_spotify_metadata(tmp_path) -> None:
    database = DatabaseManager(tmp_path / "wrapped.sqlite3")
    database.initialize()
    played_at = datetime(2026, 6, 1, 12, 0, tzinfo=timezone.utc)

    database.save_tracks(
        [
            {
                "track_name": "Song A",
                "artist_name": "Artist A",
                "played_at": played_at,
            }
        ]
    )
    inserted, skipped = database.save_tracks(
        [
            {
                "track_name": "Song A",
                "artist_name": "Artist A",
                "played_at": played_at,
                "spotify_track_id": "spotify-id",
                "spotify_duration_ms": 180000,
            }
        ]
    )
    tracks = database.fetch_tracks_between(played_at - timedelta(minutes=1), played_at + timedelta(minutes=1))

    assert inserted == 0
    assert skipped == 1
    assert tracks[0]["spotify_track_id"] == "spotify-id"
    assert tracks[0]["spotify_duration_ms"] == 180000
