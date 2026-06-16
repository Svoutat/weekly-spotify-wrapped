from __future__ import annotations

import secrets
import sys
import threading
import time
import urllib.parse
import webbrowser
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

import requests
from dotenv import dotenv_values


BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"
AUTHORIZE_URL = "https://accounts.spotify.com/authorize"
TOKEN_URL = "https://accounts.spotify.com/api/token"
API_BASE_URL = "https://api.spotify.com/v1"
DEFAULT_REDIRECT_URI = "http://127.0.0.1:8888/callback"
SCOPES = "playlist-modify-private playlist-modify-public"


class SpotifySetupError(RuntimeError):
    """Raised when the one-time Spotify setup cannot be completed."""


def main() -> int:
    try:
        env_values = _load_env_values()
        client_id = _required(env_values, "SPOTIFY_CLIENT_ID")
        client_secret = _required(env_values, "SPOTIFY_CLIENT_SECRET")
        redirect_uri = env_values.get("SPOTIFY_REDIRECT_URI") or DEFAULT_REDIRECT_URI
        playlist_name = env_values.get("SPOTIFY_PLAYLIST_NAME") or "Weekly Spotify Recap"

        callback = _wait_for_callback(
            client_id=client_id,
            redirect_uri=redirect_uri,
            scopes=SCOPES,
        )
        token_payload = _exchange_code_for_tokens(
            client_id=client_id,
            client_secret=client_secret,
            code=callback["code"],
            redirect_uri=redirect_uri,
        )
        access_token = _required(token_payload, "access_token")
        refresh_token = token_payload.get("refresh_token") or env_values.get("SPOTIFY_REFRESH_TOKEN")
        if not refresh_token:
            raise SpotifySetupError(
                "Spotify did not return a refresh token. "
                "Remove this app from your Spotify account access list and run setup again."
            )

        playlist_id = env_values.get("SPOTIFY_PLAYLIST_ID")
        playlist_url = env_values.get("PLAYLIST_URL")
        if not playlist_id:
            playlist = _create_playlist(access_token=access_token, playlist_name=playlist_name)
            playlist_id = _required(playlist, "id")
            playlist_url = (playlist.get("external_urls") or {}).get("spotify")

        _update_env_file(
            {
                "SPOTIFY_REFRESH_TOKEN": refresh_token,
                "SPOTIFY_PLAYLIST_ID": playlist_id,
                "PLAYLIST_URL": playlist_url or f"https://open.spotify.com/playlist/{playlist_id}",
                "SPOTIFY_REDIRECT_URI": redirect_uri,
                "ENABLE_PLAYLIST": "true",
            }
        )

        print("Spotify setup completed.")
        print("Updated .env with Spotify refresh token and playlist values.")
        return 0
    except SpotifySetupError as exc:
        print(f"Spotify setup failed: {exc}", file=sys.stderr)
        return 1


def _load_env_values() -> dict[str, str]:
    if not ENV_PATH.exists():
        raise SpotifySetupError(".env file is missing. Copy .env.example to .env first.")
    raw_values = dotenv_values(ENV_PATH, encoding="utf-8-sig")
    return {key: str(value) for key, value in raw_values.items() if value is not None}


def _wait_for_callback(client_id: str, redirect_uri: str, scopes: str) -> dict[str, str]:
    parsed_redirect = urllib.parse.urlparse(redirect_uri)
    if parsed_redirect.scheme != "http" or parsed_redirect.hostname != "127.0.0.1":
        raise SpotifySetupError(
            "SPOTIFY_REDIRECT_URI must be http://127.0.0.1:8888/callback for this setup helper."
        )
    if not parsed_redirect.port:
        raise SpotifySetupError("SPOTIFY_REDIRECT_URI must include a port.")

    state = secrets.token_urlsafe(24)
    callback_data: dict[str, str] = {}

    class CallbackHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802 - required by BaseHTTPRequestHandler
            parsed = urllib.parse.urlparse(self.path)
            params = urllib.parse.parse_qs(parsed.query)

            if parsed.path != parsed_redirect.path:
                self.send_response(404)
                self.end_headers()
                return

            callback_data["state"] = params.get("state", [""])[0]
            callback_data["code"] = params.get("code", [""])[0]
            callback_data["error"] = params.get("error", [""])[0]

            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(
                b"<h1>Spotify setup received.</h1><p>You can close this browser tab.</p>"
            )

        def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
            return

    server = ThreadingHTTPServer((parsed_redirect.hostname, parsed_redirect.port), CallbackHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    auth_url = _build_auth_url(client_id=client_id, redirect_uri=redirect_uri, scopes=scopes, state=state)
    print("Opening Spotify authorization in your browser.")
    print("If the browser does not open, paste this URL manually:")
    print(auth_url)
    webbrowser.open(auth_url)

    start = time.time()
    try:
        while time.time() - start < 180:
            if callback_data:
                break
            time.sleep(0.2)
    finally:
        server.shutdown()
        server.server_close()

    if not callback_data:
        raise SpotifySetupError("Timed out while waiting for Spotify browser authorization.")
    if callback_data.get("error"):
        raise SpotifySetupError(f"Spotify authorization returned an error: {callback_data['error']}")
    if callback_data.get("state") != state:
        raise SpotifySetupError("Spotify OAuth state mismatch.")
    if not callback_data.get("code"):
        raise SpotifySetupError("Spotify authorization code was missing.")

    return callback_data


def _build_auth_url(client_id: str, redirect_uri: str, scopes: str, state: str) -> str:
    query = urllib.parse.urlencode(
        {
            "response_type": "code",
            "client_id": client_id,
            "scope": scopes,
            "redirect_uri": redirect_uri,
            "state": state,
            "show_dialog": "true",
        }
    )
    return f"{AUTHORIZE_URL}?{query}"


def _exchange_code_for_tokens(
    client_id: str,
    client_secret: str,
    code: str,
    redirect_uri: str,
) -> dict[str, Any]:
    try:
        response = requests.post(
            TOKEN_URL,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": redirect_uri,
            },
            auth=(client_id, client_secret),
            timeout=20,
        )
        response.raise_for_status()
        return response.json()
    except requests.RequestException as exc:
        raise SpotifySetupError("Could not exchange Spotify authorization code for tokens.") from exc
    except ValueError as exc:
        raise SpotifySetupError("Spotify token response was not valid JSON.") from exc


def _create_playlist(access_token: str, playlist_name: str) -> dict[str, Any]:
    description = (
        "Automatically created by Weekly Spotify Wrapped on "
        f"{datetime.now(timezone.utc).date().isoformat()}."
    )
    try:
        response = requests.post(
            f"{API_BASE_URL}/me/playlists",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            },
            json={
                "name": playlist_name,
                "public": False,
                "description": description,
            },
            timeout=20,
        )
        response.raise_for_status()
        return response.json()
    except requests.RequestException as exc:
        raise SpotifySetupError("Could not create Spotify playlist.") from exc
    except ValueError as exc:
        raise SpotifySetupError("Spotify playlist response was not valid JSON.") from exc


def _update_env_file(updates: dict[str, str]) -> None:
    lines = ENV_PATH.read_text(encoding="utf-8-sig").splitlines()
    existing_keys = set()
    new_lines: list[str] = []

    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in line:
            new_lines.append(line)
            continue

        key, _value = line.split("=", 1)
        key = key.strip()
        if key in updates:
            new_lines.append(f"{key}={updates[key]}")
            existing_keys.add(key)
        else:
            new_lines.append(line)

    for key, value in updates.items():
        if key not in existing_keys:
            new_lines.append(f"{key}={value}")

    ENV_PATH.write_text("\n".join(new_lines) + "\n", encoding="utf-8")


def _required(values: dict[str, Any], key: str) -> str:
    value = str(values.get(key, "")).strip()
    if not value:
        raise SpotifySetupError(f"Missing required value: {key}")
    return value


if __name__ == "__main__":
    raise SystemExit(main())
