from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

try:
    from dotenv import dotenv_values
except ImportError:  # pragma: no cover - used only before dependencies are installed
    dotenv_values = None


BASE_DIR = Path(__file__).resolve().parent


class ConfigError(ValueError):
    """Raised when required environment configuration is missing or invalid."""


@dataclass(frozen=True)
class AppConfig:
    lastfm_api_key: str
    lastfm_username: str
    spotify_client_id: str | None
    spotify_client_secret: str | None
    spotify_refresh_token: str | None
    spotify_playlist_id: str | None
    spotify_playlist_name: str
    playlist_url: str | None
    gmail_address: str | None
    gmail_app_password: str | None
    recipient_email: str | None
    send_email: bool
    enable_playlist: bool
    lookback_days: int
    database_path: Path
    output_dir: Path

    @property
    def spotify_enabled(self) -> bool:
        return bool(self.spotify_client_id and self.spotify_client_secret)

    @property
    def playlist_enabled(self) -> bool:
        return self.enable_playlist and self.spotify_enabled


def load_config(
    env_file: str | Path | None = None,
    environ: Mapping[str, str] | None = None,
) -> AppConfig:
    values = _load_values(env_file=env_file, environ=environ)

    send_email = _as_bool(values.get("SEND_EMAIL"), default=True)
    enable_playlist = _as_bool(values.get("ENABLE_PLAYLIST"), default=False)

    missing = _missing_required(values, ["LASTFM_API_KEY", "LASTFM_USERNAME"])
    if send_email:
        missing.extend(
            _missing_required(values, ["GMAIL_ADDRESS", "GMAIL_APP_PASSWORD", "RECIPIENT_EMAIL"])
        )

    if missing:
        joined = ", ".join(sorted(set(missing)))
        raise ConfigError(
            "Missing required environment values: "
            f"{joined}. Copy .env.example to .env and fill these values."
        )

    lookback_days = _as_positive_int(values.get("LOOKBACK_DAYS"), default=7, name="LOOKBACK_DAYS")

    return AppConfig(
        lastfm_api_key=_required(values, "LASTFM_API_KEY"),
        lastfm_username=_required(values, "LASTFM_USERNAME"),
        spotify_client_id=_optional(values, "SPOTIFY_CLIENT_ID"),
        spotify_client_secret=_optional(values, "SPOTIFY_CLIENT_SECRET"),
        spotify_refresh_token=_optional(values, "SPOTIFY_REFRESH_TOKEN"),
        spotify_playlist_id=_optional(values, "SPOTIFY_PLAYLIST_ID"),
        spotify_playlist_name=_optional(values, "SPOTIFY_PLAYLIST_NAME") or "Weekly Spotify Recap",
        playlist_url=_optional(values, "PLAYLIST_URL"),
        gmail_address=_optional(values, "GMAIL_ADDRESS"),
        gmail_app_password=_optional(values, "GMAIL_APP_PASSWORD"),
        recipient_email=_optional(values, "RECIPIENT_EMAIL"),
        send_email=send_email,
        enable_playlist=enable_playlist,
        lookback_days=lookback_days,
        database_path=_as_path(values.get("DATABASE_PATH"), default="spotify_wrapped.sqlite3"),
        output_dir=_as_path(values.get("OUTPUT_DIR"), default="output"),
    )


def _load_values(
    env_file: str | Path | None,
    environ: Mapping[str, str] | None,
) -> dict[str, str]:
    if environ is not None:
        return {key: str(value) for key, value in environ.items()}

    file_path = Path(env_file) if env_file else BASE_DIR / ".env"
    values: dict[str, str] = {}

    if file_path.exists():
        values.update(_read_env_file(file_path))

    values.update(os.environ)
    return values


def _read_env_file(path: Path) -> dict[str, str]:
    if dotenv_values is not None:
        raw_values = dotenv_values(path, encoding="utf-8-sig")
        return {key: str(value) for key, value in raw_values.items() if value is not None}

    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def _missing_required(values: Mapping[str, str], keys: list[str]) -> list[str]:
    return [key for key in keys if not values.get(key, "").strip()]


def _required(values: Mapping[str, str], key: str) -> str:
    value = values.get(key, "").strip()
    if not value:
        raise ConfigError(f"Missing required environment value: {key}")
    return value


def _optional(values: Mapping[str, str], key: str) -> str | None:
    value = values.get(key)
    if value is None:
        return None
    value = value.strip()
    return value or None


def _as_bool(value: str | None, default: bool) -> bool:
    if value is None or value.strip() == "":
        return default
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "y", "on"}:
        return True
    if normalized in {"0", "false", "no", "n", "off"}:
        return False
    raise ConfigError(f"Invalid boolean value: {value}")


def _as_positive_int(value: str | None, default: int, name: str) -> int:
    if value is None or value.strip() == "":
        return default
    try:
        parsed = int(value)
    except ValueError as exc:
        raise ConfigError(f"{name} must be a positive integer.") from exc
    if parsed <= 0:
        raise ConfigError(f"{name} must be greater than 0.")
    return parsed


def _as_path(value: str | None, default: str) -> Path:
    raw_path = value.strip() if value and value.strip() else default
    path = Path(raw_path)
    if path.is_absolute():
        return path
    return BASE_DIR / path
