from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping


class DatabaseError(RuntimeError):
    """Raised when SQLite storage fails."""


class DatabaseManager:
    def __init__(self, database_path: str | Path):
        self.database_path = Path(database_path)

    def initialize(self) -> None:
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS track_plays (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    track_name TEXT NOT NULL,
                    artist_name TEXT NOT NULL,
                    album_name TEXT,
                    played_at TEXT NOT NULL,
                    lastfm_url TEXT,
                    spotify_track_id TEXT,
                    spotify_track_url TEXT,
                    spotify_duration_ms INTEGER,
                    spotify_album_name TEXT,
                    spotify_cover_url TEXT,
                    spotify_artist_id TEXT,
                    spotify_artist_image_url TEXT,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(track_name, artist_name, played_at)
                );

                CREATE INDEX IF NOT EXISTS idx_track_plays_played_at
                    ON track_plays (played_at);

                CREATE INDEX IF NOT EXISTS idx_track_plays_artist
                    ON track_plays (artist_name);
                """
            )
            self._ensure_column(connection, "spotify_artist_id", "TEXT")
            self._ensure_column(connection, "spotify_artist_image_url", "TEXT")

    def save_tracks(self, tracks: Iterable[Mapping[str, Any]]) -> tuple[int, int]:
        inserted = 0
        skipped = 0
        with self._connect() as connection:
            for track in tracks:
                if self._save_track(connection, track):
                    inserted += 1
                else:
                    skipped += 1
        return inserted, skipped

    def fetch_tracks_between(self, start: datetime, end: datetime) -> list[dict[str, Any]]:
        start_iso = _to_iso_utc(start)
        end_iso = _to_iso_utc(end)
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    id,
                    track_name,
                    artist_name,
                    album_name,
                    played_at,
                    lastfm_url,
                    spotify_track_id,
                    spotify_track_url,
                    spotify_duration_ms,
                    spotify_album_name,
                    spotify_cover_url,
                    spotify_artist_id,
                    spotify_artist_image_url
                FROM track_plays
                WHERE played_at >= ? AND played_at <= ?
                ORDER BY played_at DESC
                """,
                (start_iso, end_iso),
            ).fetchall()
        return [dict(row) for row in rows]

    def count_tracks(self) -> int:
        with self._connect() as connection:
            row = connection.execute("SELECT COUNT(*) AS total FROM track_plays").fetchone()
        return int(row["total"])

    def _save_track(self, connection: sqlite3.Connection, track: Mapping[str, Any]) -> bool:
        track_name = _clean_required(track, "track_name")
        artist_name = _clean_required(track, "artist_name")
        played_at = _to_iso_utc(track["played_at"])

        existing = connection.execute(
            """
            SELECT id
            FROM track_plays
            WHERE track_name = ? AND artist_name = ? AND played_at = ?
            """,
            (track_name, artist_name, played_at),
        ).fetchone()

        payload = (
            _clean_optional(track.get("album_name")),
            _clean_optional(track.get("lastfm_url")),
            _clean_optional(track.get("spotify_track_id")),
            _clean_optional(track.get("spotify_track_url")),
            _clean_int(track.get("spotify_duration_ms")),
            _clean_optional(track.get("spotify_album_name")),
            _clean_optional(track.get("spotify_cover_url")),
            _clean_optional(track.get("spotify_artist_id")),
            _clean_optional(track.get("spotify_artist_image_url")),
        )

        if existing:
            self._update_existing_metadata(connection, existing["id"], payload)
            return False

        connection.execute(
            """
            INSERT INTO track_plays (
                track_name,
                artist_name,
                album_name,
                played_at,
                lastfm_url,
                spotify_track_id,
                spotify_track_url,
                spotify_duration_ms,
                spotify_album_name,
                spotify_cover_url,
                spotify_artist_id,
                spotify_artist_image_url
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                track_name,
                artist_name,
                payload[0],
                played_at,
                payload[1],
                payload[2],
                payload[3],
                payload[4],
                payload[5],
                payload[6],
                payload[7],
                payload[8],
            ),
        )
        return True

    def _update_existing_metadata(
        self,
        connection: sqlite3.Connection,
        track_id: int,
        payload: tuple[
            str | None,
            str | None,
            str | None,
            str | None,
            int | None,
            str | None,
            str | None,
            str | None,
            str | None,
        ],
    ) -> None:
        connection.execute(
            """
            UPDATE track_plays
            SET
                album_name = COALESCE(?, album_name),
                lastfm_url = COALESCE(?, lastfm_url),
                spotify_track_id = COALESCE(?, spotify_track_id),
                spotify_track_url = COALESCE(?, spotify_track_url),
                spotify_duration_ms = COALESCE(?, spotify_duration_ms),
                spotify_album_name = COALESCE(?, spotify_album_name),
                spotify_cover_url = COALESCE(?, spotify_cover_url),
                spotify_artist_id = COALESCE(?, spotify_artist_id),
                spotify_artist_image_url = COALESCE(?, spotify_artist_image_url)
            WHERE id = ?
            """,
            (*payload, track_id),
        )

    def _ensure_column(self, connection: sqlite3.Connection, column_name: str, column_type: str) -> None:
        columns = {
            row["name"]
            for row in connection.execute("PRAGMA table_info(track_plays)").fetchall()
        }
        if column_name not in columns:
            connection.execute(f"ALTER TABLE track_plays ADD COLUMN {column_name} {column_type}")

    def _connect(self) -> sqlite3.Connection:
        try:
            connection = sqlite3.connect(self.database_path)
        except sqlite3.Error as exc:
            raise DatabaseError(f"Could not open database: {self.database_path}") from exc
        connection.row_factory = sqlite3.Row
        return connection


def _clean_required(track: Mapping[str, Any], key: str) -> str:
    value = str(track.get(key, "")).strip()
    if not value:
        raise DatabaseError(f"Track is missing required field: {key}")
    return value


def _clean_optional(value: Any) -> str | None:
    if value is None:
        return None
    cleaned = str(value).strip()
    return cleaned or None


def _clean_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise DatabaseError(f"Invalid integer value for spotify_duration_ms: {value}") from exc


def _to_iso_utc(value: Any) -> str:
    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, (int, float)):
        dt = datetime.fromtimestamp(value, tz=timezone.utc)
    elif isinstance(value, str):
        normalized = value.replace("Z", "+00:00")
        dt = datetime.fromisoformat(normalized)
    else:
        raise DatabaseError(f"Invalid datetime value: {value}")

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat()
