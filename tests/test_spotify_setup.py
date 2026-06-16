import urllib.parse

import pytest

import spotify_setup
from spotify_setup import SpotifySetupError


def test_build_auth_url_contains_required_oauth_parameters() -> None:
    url = spotify_setup._build_auth_url(
        client_id="client-id",
        redirect_uri="http://127.0.0.1:8888/callback",
        scopes="playlist-modify-private playlist-modify-public",
        state="state-123",
    )

    parsed = urllib.parse.urlparse(url)
    params = urllib.parse.parse_qs(parsed.query)

    assert parsed.scheme == "https"
    assert parsed.netloc == "accounts.spotify.com"
    assert params["response_type"] == ["code"]
    assert params["client_id"] == ["client-id"]
    assert params["redirect_uri"] == ["http://127.0.0.1:8888/callback"]
    assert params["state"] == ["state-123"]
    assert params["show_dialog"] == ["true"]


def test_update_env_file_updates_existing_values_and_appends_missing_values(monkeypatch, tmp_path) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text(
        "LASTFM_API_KEY=lastfm-key\n"
        "SPOTIFY_REFRESH_TOKEN=old-token\n"
        "# keep this comment\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(spotify_setup, "ENV_PATH", env_path)

    spotify_setup._update_env_file(
        {
            "SPOTIFY_REFRESH_TOKEN": "new-token",
            "SPOTIFY_PLAYLIST_ID": "playlist-1",
            "PLAYLIST_URL": "https://open.spotify.com/playlist/playlist-1",
        }
    )

    content = env_path.read_text(encoding="utf-8")
    assert "LASTFM_API_KEY=lastfm-key" in content
    assert "SPOTIFY_REFRESH_TOKEN=new-token" in content
    assert "SPOTIFY_PLAYLIST_ID=playlist-1" in content
    assert "PLAYLIST_URL=https://open.spotify.com/playlist/playlist-1" in content
    assert "# keep this comment" in content


def test_required_raises_for_missing_value() -> None:
    with pytest.raises(SpotifySetupError, match="Missing required value"):
        spotify_setup._required({"SPOTIFY_CLIENT_ID": ""}, "SPOTIFY_CLIENT_ID")


def test_main_saves_refresh_token_and_creates_playlist_when_missing(monkeypatch) -> None:
    saved_updates = {}

    monkeypatch.setattr(
        spotify_setup,
        "_load_env_values",
        lambda: {
            "SPOTIFY_CLIENT_ID": "client-id",
            "SPOTIFY_CLIENT_SECRET": "client-secret",
            "SPOTIFY_REDIRECT_URI": "http://127.0.0.1:8888/callback",
            "SPOTIFY_PLAYLIST_NAME": "Weekly Playlist",
        },
    )
    monkeypatch.setattr(
        spotify_setup,
        "_wait_for_callback",
        lambda client_id, redirect_uri, scopes: {"code": "auth-code"},
    )
    monkeypatch.setattr(
        spotify_setup,
        "_exchange_code_for_tokens",
        lambda client_id, client_secret, code, redirect_uri: {
            "access_token": "access-token",
            "refresh_token": "refresh-token",
        },
    )
    monkeypatch.setattr(
        spotify_setup,
        "_create_playlist",
        lambda access_token, playlist_name: {
            "id": "playlist-1",
            "external_urls": {"spotify": "https://open.spotify.com/playlist/playlist-1"},
        },
    )
    monkeypatch.setattr(spotify_setup, "_update_env_file", lambda updates: saved_updates.update(updates))

    assert spotify_setup.main() == 0
    assert saved_updates["SPOTIFY_REFRESH_TOKEN"] == "refresh-token"
    assert saved_updates["SPOTIFY_PLAYLIST_ID"] == "playlist-1"
    assert saved_updates["ENABLE_PLAYLIST"] == "true"
