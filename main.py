from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from config import ConfigError, load_config
from database import DatabaseManager
from email_sender import EmailDeliveryError, EmailSender
from lastfm_client import LastFmClient, LastFmError
from report_generator import ReportGenerator, calculate_statistics, compare_statistics
from spotify_client import SpotifyClient, SpotifyError


LOGGER = logging.getLogger(__name__)


def main() -> int:
    _configure_logging()

    try:
        config = load_config()
    except ConfigError as exc:
        LOGGER.error("%s", exc)
        return 2

    now = datetime.now(timezone.utc)
    period_start = now - timedelta(days=config.lookback_days)
    previous_period_start = period_start - timedelta(days=config.lookback_days)
    fetch_days = config.lookback_days * 2

    try:
        database = DatabaseManager(config.database_path)
        database.initialize()

        lastfm_client = LastFmClient(
            api_key=config.lastfm_api_key,
            username=config.lastfm_username,
        )
        tracks = lastfm_client.get_recent_tracks(days=fetch_days, now=now)
        LOGGER.info("Loaded %s tracks from Last.fm.", len(tracks))

        spotify_client = None
        if config.spotify_enabled:
            spotify_client = SpotifyClient(
                client_id=config.spotify_client_id or "",
                client_secret=config.spotify_client_secret or "",
                refresh_token=config.spotify_refresh_token,
            )
            tracks = spotify_client.enrich_tracks(tracks)
            LOGGER.info("Spotify enrichment finished.")
        else:
            LOGGER.warning("Spotify credentials missing; continuing with Last.fm data only.")

        inserted, skipped = database.save_tracks(tracks)
        LOGGER.info("Database saved %s new tracks and skipped %s duplicates.", inserted, skipped)

        stored_tracks = database.fetch_tracks_between(period_start, now)
        previous_tracks = database.fetch_tracks_between(previous_period_start, period_start)
        stats = calculate_statistics(stored_tracks, period_start=period_start, period_end=now)
        previous_stats = calculate_statistics(
            previous_tracks,
            period_start=previous_period_start,
            period_end=period_start,
        )
        comparison = compare_statistics(stats, previous_stats)

        playlist_url = config.playlist_url
        if config.playlist_enabled and spotify_client is not None:
            try:
                playlist_result = spotify_client.update_playlist(
                    playlist_id=config.spotify_playlist_id,
                    track_ids=[song.get("spotify_track_id") for song in stats["top_songs"]],
                )
                LOGGER.info("%s", playlist_result.message)
                playlist_url = playlist_result.url or playlist_url
            except SpotifyError as exc:
                LOGGER.warning("Playlist update failed; continuing without playlist changes: %s", exc)
        elif config.enable_playlist:
            LOGGER.warning("Playlist update requested but Spotify is not fully configured.")

        report_generator = ReportGenerator(config.output_dir)
        html_report, report_path = report_generator.generate(
            stats,
            playlist_url=playlist_url,
            comparison=comparison,
        )
        LOGGER.info("Report saved to %s", report_path)

        if config.send_email:
            email_sender = EmailSender(config)
            email_sender.send_html_report("Your Weekly Spotify Wrapped", html_report)
            LOGGER.info("Weekly report email sent to %s.", config.recipient_email)
        else:
            LOGGER.info("SEND_EMAIL=false; email sending skipped.")

        return 0

    except LastFmError as exc:
        LOGGER.error("Last.fm step failed: %s", exc)
        return 1
    except EmailDeliveryError as exc:
        LOGGER.error("Report was created, but email sending failed: %s", exc)
        return 1
    except Exception:
        LOGGER.exception("Unexpected error while creating the weekly report.")
        return 1


def _configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


if __name__ == "__main__":
    raise SystemExit(main())
