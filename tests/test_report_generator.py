from datetime import datetime, timezone

from report_generator import (
    DEFAULT_TRACK_DURATION_MS,
    ReportGenerator,
    calculate_statistics,
    compare_statistics,
)


def test_calculate_statistics_returns_top_songs_and_artists() -> None:
    start = datetime(2026, 5, 27, tzinfo=timezone.utc)
    end = datetime(2026, 6, 3, tzinfo=timezone.utc)
    tracks = [
        {
            "track_name": "Song A",
            "artist_name": "Artist A",
            "spotify_duration_ms": 180000,
            "spotify_track_id": "track-a",
            "spotify_cover_url": "https://example.com/song-a.jpg",
            "spotify_artist_image_url": "https://example.com/artist-a.jpg",
        },
        {
            "track_name": "Song A",
            "artist_name": "Artist A",
            "spotify_duration_ms": 180000,
            "spotify_track_id": "track-a",
            "spotify_cover_url": "https://example.com/song-a.jpg",
            "spotify_artist_image_url": "https://example.com/artist-a.jpg",
        },
        {
            "track_name": "Song B",
            "artist_name": "Artist B",
            "spotify_duration_ms": None,
        },
    ]

    stats = calculate_statistics(tracks, period_start=start, period_end=end)

    assert stats["total_tracks"] == 3
    assert stats["unique_tracks"] == 2
    assert stats["unique_artists"] == 2
    assert stats["top_songs"][0]["track_name"] == "Song A"
    assert stats["top_songs"][0]["plays"] == 2
    assert stats["top_songs"][0]["cover_url"] == "https://example.com/song-a.jpg"
    assert stats["top_artists"][0]["artist_name"] == "Artist A"
    assert stats["top_artists"][0]["image_url"] == "https://example.com/artist-a.jpg"
    assert stats["total_duration_ms"] == 360000 + DEFAULT_TRACK_DURATION_MS
    assert stats["total_hours"] == 0.2
    assert stats["total_time_label"] == "0.2 hours"


def test_report_generator_creates_and_saves_html(tmp_path) -> None:
    start = datetime(2026, 5, 27, tzinfo=timezone.utc)
    end = datetime(2026, 6, 3, tzinfo=timezone.utc)
    stats = calculate_statistics(
        [
            {
                "track_name": "Song A",
                "artist_name": "Artist A",
                "spotify_duration_ms": 180000,
                "spotify_track_url": "https://open.spotify.com/track/example",
                "spotify_cover_url": "https://example.com/song-a.jpg",
                "spotify_artist_image_url": "https://example.com/artist-a.jpg",
            }
        ],
        period_start=start,
        period_end=end,
    )

    generator = ReportGenerator(tmp_path)
    html_report, report_path = generator.generate(stats, playlist_url="https://open.spotify.com/playlist/example")

    assert "Your Weekly Spotify Wrapped" in html_report
    assert "Song A" in html_report
    assert "Artist A" in html_report
    assert "0.1 hours" in html_report
    assert "https://example.com/song-a.jpg" in html_report
    assert "https://example.com/artist-a.jpg" in html_report
    assert "Open weekly playlist" in html_report
    assert report_path.exists()
    assert report_path.name == "weekly_spotify_wrapped_2026-06-03.html"


def test_compare_statistics_returns_week_over_week_changes() -> None:
    previous_start = datetime(2026, 5, 20, tzinfo=timezone.utc)
    current_start = datetime(2026, 5, 27, tzinfo=timezone.utc)
    end = datetime(2026, 6, 3, tzinfo=timezone.utc)
    previous_stats = calculate_statistics(
        [
            {
                "track_name": "Old Top Song",
                "artist_name": "Artist A",
                "spotify_duration_ms": 180000,
            },
            {
                "track_name": "Old Song",
                "artist_name": "Artist B",
                "spotify_duration_ms": 180000,
            },
        ],
        period_start=previous_start,
        period_end=current_start,
    )
    current_stats = calculate_statistics(
        [
            {
                "track_name": "New Top Song",
                "artist_name": "Artist C",
                "spotify_duration_ms": 180000,
            },
            {
                "track_name": "New Top Song",
                "artist_name": "Artist C",
                "spotify_duration_ms": 180000,
            },
            {
                "track_name": "Shared Song",
                "artist_name": "Artist A",
                "spotify_duration_ms": 180000,
            },
        ],
        period_start=current_start,
        period_end=end,
    )

    comparison = compare_statistics(current_stats, previous_stats)

    assert comparison["has_previous_data"] is True
    assert comparison["metrics"][0]["label"] == "Listening time"
    assert comparison["metrics"][0]["change_label"] == "+50.0%"
    assert "Old Top Song by Artist A" in comparison["top_song_change"]
    assert "New Top Song by Artist C" in comparison["top_song_change"]
    assert comparison["new_artists"] == ["Artist C"]
    assert comparison["repeated_top_artists"] == ["Artist A"]


def test_compare_statistics_handles_missing_previous_week() -> None:
    start = datetime(2026, 5, 27, tzinfo=timezone.utc)
    end = datetime(2026, 6, 3, tzinfo=timezone.utc)
    current_stats = calculate_statistics(
        [{"track_name": "Song A", "artist_name": "Artist A"}],
        period_start=start,
        period_end=end,
    )
    previous_stats = calculate_statistics([], period_start=start, period_end=end)

    comparison = compare_statistics(current_stats, previous_stats)

    assert comparison["has_previous_data"] is False
    assert "No previous week data yet" in comparison["message"]


def test_report_generator_includes_week_over_week_section(tmp_path) -> None:
    previous_start = datetime(2026, 5, 20, tzinfo=timezone.utc)
    current_start = datetime(2026, 5, 27, tzinfo=timezone.utc)
    end = datetime(2026, 6, 3, tzinfo=timezone.utc)
    previous_stats = calculate_statistics(
        [{"track_name": "Song A", "artist_name": "Artist A", "spotify_duration_ms": 180000}],
        period_start=previous_start,
        period_end=current_start,
    )
    current_stats = calculate_statistics(
        [
            {"track_name": "Song B", "artist_name": "Artist B", "spotify_duration_ms": 180000},
            {"track_name": "Song C", "artist_name": "Artist C", "spotify_duration_ms": 180000},
        ],
        period_start=current_start,
        period_end=end,
    )
    comparison = compare_statistics(current_stats, previous_stats)

    html_report, _report_path = ReportGenerator(tmp_path).generate(
        current_stats,
        comparison=comparison,
    )

    assert "Compared with last week" in html_report
    assert "+100.0%" in html_report
    assert "New Artists" in html_report
    assert "Artist B" in html_report
