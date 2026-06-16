from pathlib import Path

from config import AppConfig, ConfigError
import main as app_main


def _config(tmp_path: Path, **overrides: object) -> AppConfig:
    values = {
        "lastfm_api_key": "lastfm-key",
        "lastfm_username": "listener",
        "spotify_client_id": None,
        "spotify_client_secret": None,
        "spotify_refresh_token": None,
        "spotify_playlist_id": None,
        "spotify_playlist_name": "Weekly Spotify Recap",
        "playlist_url": None,
        "gmail_address": None,
        "gmail_app_password": None,
        "recipient_email": None,
        "send_email": False,
        "enable_playlist": False,
        "lookback_days": 7,
        "database_path": tmp_path / "wrapped.sqlite3",
        "output_dir": tmp_path / "output",
    }
    values.update(overrides)
    return AppConfig(**values)


def test_main_returns_2_when_configuration_is_invalid(monkeypatch) -> None:
    monkeypatch.setattr(app_main, "load_config", lambda: (_ for _ in ()).throw(ConfigError("missing")))

    assert app_main.main() == 2


def test_main_runs_weekly_report_workflow_without_real_services(monkeypatch, tmp_path) -> None:
    events = []
    source_tracks = [{"track_name": "Song A", "artist_name": "Artist A"}]
    stored_tracks = [{"track_name": "Song A", "artist_name": "Artist A", "spotify_duration_ms": 180000}]
    previous_tracks = [{"track_name": "Song B", "artist_name": "Artist B", "spotify_duration_ms": 180000}]
    fetch_calls = []

    class FakeDatabaseManager:
        def __init__(self, database_path):
            events.append(("database_path", database_path))

        def initialize(self) -> None:
            events.append(("initialize",))

        def save_tracks(self, tracks):
            events.append(("save_tracks", tracks))
            return len(tracks), 0

        def fetch_tracks_between(self, start, end):
            events.append(("fetch_tracks_between", start, end))
            fetch_calls.append((start, end))
            return stored_tracks if len(fetch_calls) == 1 else previous_tracks

    class FakeLastFmClient:
        def __init__(self, api_key: str, username: str):
            events.append(("lastfm_client", api_key, username))

        def get_recent_tracks(self, days: int, now):
            events.append(("recent_tracks", days))
            return source_tracks

    class FakeReportGenerator:
        def __init__(self, output_dir):
            events.append(("report_generator", output_dir))

        def generate(self, stats, playlist_url=None, comparison=None):
            events.append(("generate_report", stats, playlist_url, comparison))
            return "<html>Report</html>", tmp_path / "report.html"

    def fake_calculate_statistics(tracks, period_start, period_end):
        events.append(("calculate_statistics", tracks))
        return {
            "period_start": period_start,
            "period_end": period_end,
            "total_tracks": len(tracks),
            "top_songs": [],
            "top_artists": [],
        }

    def fake_compare_statistics(current_stats, previous_stats):
        events.append(("compare_statistics", current_stats, previous_stats))
        return {"has_previous_data": True}

    monkeypatch.setattr(app_main, "load_config", lambda: _config(tmp_path))
    monkeypatch.setattr(app_main, "DatabaseManager", FakeDatabaseManager)
    monkeypatch.setattr(app_main, "LastFmClient", FakeLastFmClient)
    monkeypatch.setattr(app_main, "ReportGenerator", FakeReportGenerator)
    monkeypatch.setattr(app_main, "calculate_statistics", fake_calculate_statistics)
    monkeypatch.setattr(app_main, "compare_statistics", fake_compare_statistics)

    assert app_main.main() == 0
    assert ("initialize",) in events
    assert ("recent_tracks", 14) in events
    assert ("save_tracks", source_tracks) in events
    assert ("calculate_statistics", stored_tracks) in events
    assert ("calculate_statistics", previous_tracks) in events
    assert any(event[0] == "compare_statistics" for event in events)


def test_main_continues_when_optional_playlist_update_fails(monkeypatch, tmp_path) -> None:
    class FakeDatabaseManager:
        def __init__(self, database_path):
            pass

        def initialize(self) -> None:
            return None

        def save_tracks(self, tracks):
            return len(tracks), 0

        def fetch_tracks_between(self, start, end):
            return [{"track_name": "Song A", "artist_name": "Artist A"}]

    class FakeLastFmClient:
        def __init__(self, api_key: str, username: str):
            pass

        def get_recent_tracks(self, days: int, now):
            return [{"track_name": "Song A", "artist_name": "Artist A"}]

    class FakeSpotifyClient:
        def __init__(self, client_id: str, client_secret: str, refresh_token: str | None):
            pass

        def enrich_tracks(self, tracks):
            return tracks

        def update_playlist(self, playlist_id, track_ids):
            raise app_main.SpotifyError("Forbidden")

    class FakeReportGenerator:
        def __init__(self, output_dir):
            pass

        def generate(self, stats, playlist_url=None, comparison=None):
            return "<html>Report</html>", tmp_path / "report.html"

    monkeypatch.setattr(
        app_main,
        "load_config",
        lambda: _config(
            tmp_path,
            spotify_client_id="spotify-id",
            spotify_client_secret="spotify-secret",
            spotify_refresh_token="refresh-token",
            spotify_playlist_id="playlist-1",
            playlist_url="https://open.spotify.com/playlist/playlist-1",
            enable_playlist=True,
        ),
    )
    monkeypatch.setattr(app_main, "DatabaseManager", FakeDatabaseManager)
    monkeypatch.setattr(app_main, "LastFmClient", FakeLastFmClient)
    monkeypatch.setattr(app_main, "SpotifyClient", FakeSpotifyClient)
    monkeypatch.setattr(app_main, "ReportGenerator", FakeReportGenerator)
    monkeypatch.setattr(
        app_main,
        "calculate_statistics",
        lambda tracks, period_start, period_end: {
            "period_start": period_start,
            "period_end": period_end,
            "total_tracks": len(tracks),
            "top_songs": [{"spotify_track_id": "track-1"}],
            "top_artists": [],
        },
    )
    monkeypatch.setattr(app_main, "compare_statistics", lambda current_stats, previous_stats: {})

    assert app_main.main() == 0
