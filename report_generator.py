from __future__ import annotations

import html
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_TRACK_DURATION_MS = 210_000


class ReportError(RuntimeError):
    """Raised when report generation fails."""


def calculate_statistics(
    tracks: list[dict[str, Any]],
    period_start: datetime,
    period_end: datetime,
) -> dict[str, Any]:
    song_counter: Counter[tuple[str, str]] = Counter()
    artist_counter: Counter[str] = Counter()
    representatives: dict[tuple[str, str], dict[str, Any]] = {}
    artist_representatives: dict[str, dict[str, Any]] = {}
    total_duration_ms = 0
    tracks_with_spotify_duration = 0

    for track in tracks:
        track_name = str(track.get("track_name", "")).strip()
        artist_name = str(track.get("artist_name", "")).strip()
        if not track_name or not artist_name:
            continue

        key = (track_name, artist_name)
        song_counter[key] += 1
        artist_counter[artist_name] += 1
        representatives.setdefault(key, track)
        artist_representatives.setdefault(artist_name, track)

        duration = track.get("spotify_duration_ms")
        if duration:
            total_duration_ms += int(duration)
            tracks_with_spotify_duration += 1
        else:
            total_duration_ms += DEFAULT_TRACK_DURATION_MS

    top_songs = []
    for (track_name, artist_name), plays in song_counter.most_common(10):
        representative = representatives[(track_name, artist_name)]
        top_songs.append(
            {
                "track_name": track_name,
                "artist_name": artist_name,
                "plays": plays,
                "spotify_track_id": representative.get("spotify_track_id"),
                "spotify_track_url": representative.get("spotify_track_url"),
                "cover_url": representative.get("spotify_cover_url"),
            }
        )

    top_artists = []
    for artist_name, plays in artist_counter.most_common(10):
        representative = artist_representatives.get(artist_name, {})
        top_artists.append(
            {
                "artist_name": artist_name,
                "plays": plays,
                "image_url": representative.get("spotify_artist_image_url")
                or representative.get("spotify_cover_url"),
            }
        )

    total_hours = round(total_duration_ms / 3_600_000, 1)

    return {
        "period_start": _as_utc(period_start),
        "period_end": _as_utc(period_end),
        "total_tracks": sum(song_counter.values()),
        "unique_tracks": len(song_counter),
        "unique_artists": len(artist_counter),
        "total_duration_ms": total_duration_ms,
        "total_minutes": round(total_duration_ms / 60_000, 1),
        "total_hours": total_hours,
        "total_time_label": _format_hours(total_hours),
        "tracks_with_spotify_duration": tracks_with_spotify_duration,
        "top_songs": top_songs,
        "top_artists": top_artists,
        "artist_names": set(artist_counter.keys()),
        "song_keys": set(song_counter.keys()),
    }


def compare_statistics(
    current_stats: dict[str, Any],
    previous_stats: dict[str, Any],
) -> dict[str, Any]:
    has_previous_data = previous_stats["total_tracks"] > 0
    if not has_previous_data:
        return {
            "has_previous_data": False,
            "message": "No previous week data yet. The comparison will appear after enough history is stored.",
            "metrics": [],
            "top_song_change": "No previous top song available yet.",
            "top_artist_change": "No previous top artist available yet.",
            "new_artists": [],
            "repeated_top_artists": [],
        }

    current_artists = set(current_stats.get("artist_names", set()))
    previous_artists = set(previous_stats.get("artist_names", set()))
    current_top_artists = {artist["artist_name"] for artist in current_stats["top_artists"]}
    previous_top_artists = {artist["artist_name"] for artist in previous_stats["top_artists"]}

    return {
        "has_previous_data": True,
        "message": _comparison_summary(current_stats, previous_stats),
        "metrics": [
            _comparison_metric(
                "Listening time",
                current_stats["total_duration_ms"],
                previous_stats["total_duration_ms"],
                current_stats["total_time_label"],
                previous_stats["total_time_label"],
            ),
            _comparison_metric(
                "Tracks played",
                current_stats["total_tracks"],
                previous_stats["total_tracks"],
                str(current_stats["total_tracks"]),
                str(previous_stats["total_tracks"]),
            ),
            _comparison_metric(
                "Unique tracks",
                current_stats["unique_tracks"],
                previous_stats["unique_tracks"],
                str(current_stats["unique_tracks"]),
                str(previous_stats["unique_tracks"]),
            ),
            _comparison_metric(
                "Unique artists",
                current_stats["unique_artists"],
                previous_stats["unique_artists"],
                str(current_stats["unique_artists"]),
                str(previous_stats["unique_artists"]),
            ),
        ],
        "top_song_change": _top_song_change(current_stats, previous_stats),
        "top_artist_change": _top_artist_change(current_stats, previous_stats),
        "new_artists": sorted(current_artists - previous_artists)[:6],
        "repeated_top_artists": sorted(current_top_artists & previous_top_artists)[:6],
    }


class ReportGenerator:
    def __init__(self, output_dir: str | Path):
        self.output_dir = Path(output_dir)

    def build_html_report(
        self,
        stats: dict[str, Any],
        playlist_url: str | None = None,
        comparison: dict[str, Any] | None = None,
    ) -> str:
        top_songs_html = _render_top_songs(stats["top_songs"])
        top_artists_html = _render_top_artists(stats["top_artists"])
        comparison_html = _render_comparison(comparison)
        top_song = stats["top_songs"][0] if stats["top_songs"] else None
        top_artist = stats["top_artists"][0] if stats["top_artists"] else None
        top_song_cover = _cover_image(
            top_song.get("cover_url") if top_song else None,
            top_song.get("track_name", "Top song") if top_song else "Top song",
            112,
            12,
        )
        top_artist_image = _cover_image(
            top_artist.get("image_url") if top_artist else None,
            top_artist.get("artist_name", "Top artist") if top_artist else "Top artist",
            112,
            56,
        )
        playlist_html = (
            f'<a class="spotify-button" href="{html.escape(playlist_url)}">Open weekly playlist</a>'
            if playlist_url
            else ""
        )
        period_start = _format_date(stats["period_start"])
        period_end = _format_date(stats["period_end"])
        top_song_name = html.escape(top_song["track_name"]) if top_song else "No song data"
        top_song_artist = html.escape(top_song["artist_name"]) if top_song else "No artist data"
        top_artist_name = html.escape(top_artist["artist_name"]) if top_artist else "No artist data"

        return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Your Weekly Spotify Wrapped</title>
  <style>
    body {{
      margin: 0;
      background: #0b0b0b;
      color: #ffffff;
      font-family: Arial, Helvetica, sans-serif;
      line-height: 1.5;
    }}
    .wrap {{
      max-width: 760px;
      margin: 0 auto;
      padding: 8px;
      background: #0b0b0b;
    }}
    .hero {{
      background: linear-gradient(135deg, #1db954 0%, #16833d 38%, #121212 100%);
      border-radius: 16px;
      padding: 22px;
      margin: 0 0 8px;
      box-shadow: 0 14px 42px rgba(0, 0, 0, 0.38);
    }}
    h1 {{
      color: #ffffff;
      font-size: 34px;
      line-height: 1.08;
      margin: 8px 0 12px;
      letter-spacing: 0;
    }}
    h2 {{
      color: #ffffff;
      font-size: 22px;
      font-weight: 700;
      margin: 0 0 14px;
      letter-spacing: 0;
    }}
    h3 {{
      font-size: 15px;
      margin: 0 0 8px;
      color: #b3b3b3;
      text-transform: uppercase;
    }}
    .muted {{
      color: #d7fbe3;
    }}
    .section-muted {{
      color: #b3b3b3;
    }}
    .stats {{
      width: 100%;
      border-spacing: 8px;
      margin: 0 0 8px;
    }}
    .stat {{
      background: #181818;
      border: 1px solid #282828;
      border-radius: 12px;
      padding: 14px;
      vertical-align: top;
      width: 50%;
    }}
    .stat strong {{
      display: block;
      font-size: 28px;
      color: #ffffff;
      line-height: 1.1;
    }}
    .section {{
      background: #181818;
      border: 1px solid #303030;
      border-radius: 16px;
      padding: 18px;
      margin: 0 0 8px;
    }}
    .feature-table {{
      width: 100%;
      border-spacing: 0 8px;
      margin: 0 0 8px;
    }}
    .feature-cell {{
      background: #181818;
      border: 1px solid #303030;
      border-radius: 16px;
      padding: 18px;
      width: 100%;
      vertical-align: top;
    }}
    .compare-table {{
      width: 100%;
      border-spacing: 6px;
      table-layout: fixed;
      margin-top: 8px;
    }}
    .compare-cell {{
      background: #202020;
      border: 1px solid #343434;
      border-radius: 12px;
      padding: 12px;
      vertical-align: top;
    }}
    .compare-value {{
      display: block;
      color: #ffffff;
      font-size: 22px;
      font-weight: bold;
      line-height: 1.1;
    }}
    .compare-change {{
      display: inline-block;
      margin-top: 8px;
      font-size: 13px;
      font-weight: bold;
    }}
    .trend-up {{
      color: #1ed760;
    }}
    .trend-down {{
      color: #ff8a65;
    }}
    .trend-flat {{
      color: #b3b3b3;
    }}
    .insight {{
      background: #202020;
      border-left: 4px solid #1ed760;
      border-radius: 8px;
      color: #e8f5ec;
      margin: 8px 0 0;
      padding: 12px;
    }}
    .pill {{
      display: inline-block;
      background: #282828;
      border-radius: 999px;
      color: #ffffff;
      font-size: 13px;
      margin: 4px 4px 0 0;
      padding: 5px 9px;
    }}
    .cover {{
      display: block;
      object-fit: cover;
      background: #282828;
    }}
    .row-table {{
      width: 100%;
      border-collapse: collapse;
      table-layout: fixed;
    }}
    .row-table td {{
      border-bottom: 1px solid #282828;
      padding: 10px 0;
      vertical-align: middle;
    }}
    .rank {{
      color: #1db954;
      font-weight: bold;
      width: 26px;
      text-align: center;
    }}
    .track-title {{
      color: #ffffff;
      font-weight: bold;
      overflow-wrap: anywhere;
      word-break: break-word;
    }}
    .plays {{
      color: #b3b3b3;
      text-align: right;
      font-size: 13px;
      width: 54px;
    }}
    .spotify-button {{
      display: inline-block;
      margin-top: 14px;
      padding: 11px 18px;
      background: #1ed760;
      color: #000000;
      border-radius: 999px;
      font-weight: bold;
      text-decoration: none;
    }}
    a {{
      color: #1ed760;
    }}
    @media only screen and (max-width: 480px) {{
      .wrap {{
        padding: 8px;
      }}
      .hero {{
        padding: 18px;
      }}
      h1 {{
        font-size: 29px;
      }}
      .section {{
        padding: 15px;
      }}
      .stat strong {{
        font-size: 24px;
      }}
      .plays {{
        font-size: 12px;
        width: 44px;
      }}
      .rank {{
        width: 22px;
      }}
      .compare-table {{
        border-spacing: 0 8px;
      }}
      .compare-cell {{
        display: block;
        width: auto;
        margin-bottom: 8px;
      }}
    }}
  </style>
</head>
<body>
  <main class="wrap">
    <section class="hero">
      <p class="muted">Weekly recap | {period_start} to {period_end}</p>
      <h1 style="color: #ffffff;">Your Weekly Spotify Wrapped</h1>
      <p>{_summary_sentence(stats)}</p>
      {playlist_html}
    </section>

    <table class="stats" role="presentation">
      <tr>
        <td class="stat"><span class="section-muted">Tracks played</span><strong>{stats["total_tracks"]}</strong></td>
        <td class="stat"><span class="section-muted">Listening time</span><strong>{html.escape(stats["total_time_label"])}</strong></td>
      </tr>
      <tr>
        <td class="stat"><span class="section-muted">Unique tracks</span><strong>{stats["unique_tracks"]}</strong></td>
        <td class="stat"><span class="section-muted">Unique artists</span><strong>{stats["unique_artists"]}</strong></td>
      </tr>
    </table>

    <table class="feature-table" role="presentation">
      <tr>
        <td class="feature-cell">
          <h3 style="color: #b3b3b3;">Top Song</h3>
          {top_song_cover}
          <p class="track-title">{top_song_name}</p>
          <p class="section-muted">{top_song_artist}</p>
        </td>
      </tr>
      <tr>
        <td class="feature-cell">
          <h3 style="color: #b3b3b3;">Top Artist</h3>
          {top_artist_image}
          <p class="track-title">{top_artist_name}</p>
          <p class="section-muted">{top_artist["plays"] if top_artist else 0} plays this week</p>
        </td>
      </tr>
    </table>

    {comparison_html}

    <section class="section">
      <h2 style="color: #ffffff;">Top Songs</h2>
      {top_songs_html}
    </section>

    <section class="section" style="margin: 0 0 8px;">
      <h2 style="color: #ffffff;">Top Artists</h2>
      {top_artists_html}
    </section>
  </main>
</body>
</html>
"""

    def save_html_report(self, html_report: str, period_end: datetime) -> Path:
        try:
            self.output_dir.mkdir(parents=True, exist_ok=True)
            file_name = f"weekly_spotify_wrapped_{_as_utc(period_end).date().isoformat()}.html"
            report_path = self.output_dir / file_name
            report_path.write_text(html_report, encoding="utf-8")
            return report_path
        except OSError as exc:
            raise ReportError("Could not save HTML report.") from exc

    def generate(
        self,
        stats: dict[str, Any],
        playlist_url: str | None = None,
        comparison: dict[str, Any] | None = None,
    ) -> tuple[str, Path]:
        html_report = self.build_html_report(stats, playlist_url=playlist_url, comparison=comparison)
        report_path = self.save_html_report(html_report, stats["period_end"])
        return html_report, report_path


def _render_top_songs(top_songs: list[dict[str, Any]]) -> str:
    if not top_songs:
        return "<p class=\"muted\">No songs found for this period.</p>"
    rows = []
    for index, song in enumerate(top_songs, 1):
        track_name = html.escape(song["track_name"])
        artist_name = html.escape(song["artist_name"])
        url = song.get("spotify_track_url")
        cover = _cover_image(song.get("cover_url"), song["track_name"], 52, 6)
        title = f'<span class="track-title">{track_name}</span><br><span class="section-muted">{artist_name}</span>'
        if url:
            title = f'<a href="{html.escape(url)}" style="text-decoration: none;">{title}</a>'
        rows.append(
            "<tr>"
            f'<td class="rank">{index}</td>'
            f"<td style=\"width: 62px;\">{cover}</td>"
            f"<td>{title}</td>"
            f'<td class="plays">{song["plays"]} plays</td>'
            "</tr>"
        )
    return '<table class="row-table" role="presentation">' + "".join(rows) + "</table>"


def _render_top_artists(top_artists: list[dict[str, Any]]) -> str:
    if not top_artists:
        return "<p class=\"muted\">No artists found for this period.</p>"
    rows = []
    for index, artist in enumerate(top_artists, 1):
        artist_name = html.escape(artist["artist_name"])
        image = _cover_image(artist.get("image_url"), artist["artist_name"], 52, 26)
        rows.append(
            "<tr>"
            f'<td class="rank">{index}</td>'
            f"<td style=\"width: 62px;\">{image}</td>"
            f'<td><span class="track-title">{artist_name}</span></td>'
            f'<td class="plays">{artist["plays"]} plays</td>'
            "</tr>"
        )
    return '<table class="row-table" role="presentation">' + "".join(rows) + "</table>"


def _render_comparison(comparison: dict[str, Any] | None) -> str:
    if not comparison:
        return ""

    if not comparison["has_previous_data"]:
        return (
            '<section class="section">'
            '<h2 style="color: #ffffff;">Compared with last week</h2>'
            f'<p class="section-muted">{html.escape(comparison["message"])}</p>'
            "</section>"
        )

    metric_cells = []
    for index, metric in enumerate(comparison["metrics"]):
        if index % 2 == 0:
            metric_cells.append("<tr>")
        metric_cells.append(
            '<td class="compare-cell">'
            f'<span class="section-muted">{html.escape(metric["label"])}</span>'
            f'<span class="compare-value">{html.escape(metric["current_label"])}</span>'
            f'<span class="compare-change trend-{html.escape(metric["trend"])}">'
            f'{html.escape(metric["change_label"])}</span>'
            f'<br><span class="section-muted">Last week: {html.escape(metric["previous_label"])}</span>'
            "</td>"
        )
        if index % 2 == 1:
            metric_cells.append("</tr>")
    if len(comparison["metrics"]) % 2 == 1:
        metric_cells.append('<td class="compare-cell"></td></tr>')

    new_artists = _render_pills(comparison["new_artists"], "No new artists compared with last week.")
    repeated_top_artists = _render_pills(
        comparison["repeated_top_artists"],
        "No repeated top artists in both weekly Top 10 lists.",
    )

    return (
        '<section class="section">'
        '<h2 style="color: #ffffff;">Compared with last week</h2>'
        f'<p class="section-muted">{html.escape(comparison["message"])}</p>'
        '<table class="compare-table" role="presentation">'
        + "".join(metric_cells)
        + "</table>"
        f'<p class="insight">{html.escape(comparison["top_song_change"])}</p>'
        f'<p class="insight">{html.escape(comparison["top_artist_change"])}</p>'
        '<h3 style="color: #b3b3b3; margin-top: 14px;">New Artists</h3>'
        f"{new_artists}"
        '<h3 style="color: #b3b3b3; margin-top: 14px;">Repeated Top Artists</h3>'
        f"{repeated_top_artists}"
        "</section>"
    )


def _render_pills(values: list[str], empty_message: str) -> str:
    if not values:
        return f'<p class="section-muted">{html.escape(empty_message)}</p>'
    return "".join(f'<span class="pill">{html.escape(value)}</span>' for value in values)


def _summary_sentence(stats: dict[str, Any]) -> str:
    if not stats["top_songs"]:
        return "No listening data was found this week, so the report is empty."
    top_song = stats["top_songs"][0]
    top_artist = stats["top_artists"][0]["artist_name"] if stats["top_artists"] else "unknown"
    return html.escape(
        "This week you played "
        f"{stats['total_tracks']} tracks for about {stats['total_time_label']}. "
        f"Your top song was {top_song['track_name']} by {top_song['artist_name']}, "
        f"and your top artist was {top_artist}."
    )


def _format_date(value: datetime) -> str:
    return _as_utc(value).strftime("%Y-%m-%d")


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).replace(microsecond=0)


def _format_hours(total_hours: float) -> str:
    return f"{total_hours:.1f} hours"


def _comparison_metric(
    label: str,
    current_value: int | float,
    previous_value: int | float,
    current_label: str,
    previous_label: str,
) -> dict[str, str]:
    difference = current_value - previous_value
    percent = _percent_change(current_value, previous_value)
    trend = "flat"
    if difference > 0:
        trend = "up"
    elif difference < 0:
        trend = "down"

    if percent is None:
        change_label = "new this week"
    elif percent == 0:
        change_label = "no change"
    elif percent > 0:
        change_label = f"+{percent:.1f}%"
    else:
        change_label = f"{percent:.1f}%"

    return {
        "label": label,
        "current_label": current_label,
        "previous_label": previous_label,
        "change_label": change_label,
        "trend": trend,
    }


def _percent_change(current_value: int | float, previous_value: int | float) -> float | None:
    if previous_value == 0:
        return None if current_value else 0.0
    return round(((current_value - previous_value) / previous_value) * 100, 1)


def _comparison_summary(current_stats: dict[str, Any], previous_stats: dict[str, Any]) -> str:
    hours_change = _percent_change(current_stats["total_duration_ms"], previous_stats["total_duration_ms"])
    if hours_change is None:
        return "This is the first week with enough data for a comparison."
    if hours_change > 0:
        return f"You listened {hours_change:.1f}% more than last week."
    if hours_change < 0:
        return f"You listened {abs(hours_change):.1f}% less than last week."
    return "Your listening time stayed the same as last week."


def _top_song_change(current_stats: dict[str, Any], previous_stats: dict[str, Any]) -> str:
    current_song = current_stats["top_songs"][0] if current_stats["top_songs"] else None
    previous_song = previous_stats["top_songs"][0] if previous_stats["top_songs"] else None
    if not current_song:
        return "No top song was found this week."
    current_label = f'{current_song["track_name"]} by {current_song["artist_name"]}'
    if not previous_song:
        return f"New top song this week: {current_label}."
    previous_label = f'{previous_song["track_name"]} by {previous_song["artist_name"]}'
    if current_label == previous_label:
        return f"Your top song stayed the same: {current_label}."
    return f"Your top song changed from {previous_label} to {current_label}."


def _top_artist_change(current_stats: dict[str, Any], previous_stats: dict[str, Any]) -> str:
    current_artist = current_stats["top_artists"][0]["artist_name"] if current_stats["top_artists"] else None
    previous_artist = previous_stats["top_artists"][0]["artist_name"] if previous_stats["top_artists"] else None
    if not current_artist:
        return "No top artist was found this week."
    if not previous_artist:
        return f"New top artist this week: {current_artist}."
    if current_artist == previous_artist:
        return f"Your top artist stayed the same: {current_artist}."
    return f"Your top artist changed from {previous_artist} to {current_artist}."


def _cover_image(url: str | None, alt: str, size: int, radius: int) -> str:
    if not url:
        return (
            f'<div class="cover" style="width: {size}px; height: {size}px; '
            f'border-radius: {radius}px; background: #282828;"></div>'
        )
    return (
        f'<img class="cover" src="{html.escape(url)}" alt="{html.escape(alt)}" '
        f'width="{size}" height="{size}" '
        f'style="width: {size}px; height: {size}px; border-radius: {radius}px;">'
    )
