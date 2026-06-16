from pathlib import Path

import pytest

from config import ConfigError, load_config


def test_load_config_with_required_lastfm_values_and_email_disabled() -> None:
    config = load_config(
        environ={
            "LASTFM_API_KEY": "lastfm-key",
            "LASTFM_USERNAME": "listener",
            "SEND_EMAIL": "false",
            "DATABASE_PATH": "test.sqlite3",
            "OUTPUT_DIR": "output",
        }
    )

    assert config.lastfm_api_key == "lastfm-key"
    assert config.lastfm_username == "listener"
    assert config.send_email is False
    assert config.lookback_days == 7
    assert isinstance(config.database_path, Path)


def test_load_config_requires_lastfm_values() -> None:
    with pytest.raises(ConfigError) as error:
        load_config(environ={"SEND_EMAIL": "false"})

    assert "LASTFM_API_KEY" in str(error.value)
    assert "LASTFM_USERNAME" in str(error.value)


def test_load_config_requires_gmail_when_email_is_enabled() -> None:
    with pytest.raises(ConfigError) as error:
        load_config(
            environ={
                "LASTFM_API_KEY": "lastfm-key",
                "LASTFM_USERNAME": "listener",
                "SEND_EMAIL": "true",
            }
        )

    message = str(error.value)
    assert "GMAIL_ADDRESS" in message
    assert "GMAIL_APP_PASSWORD" in message
    assert "RECIPIENT_EMAIL" in message


def test_spotify_enabled_when_client_id_and_secret_exist() -> None:
    config = load_config(
        environ={
            "LASTFM_API_KEY": "lastfm-key",
            "LASTFM_USERNAME": "listener",
            "SEND_EMAIL": "false",
            "SPOTIFY_CLIENT_ID": "spotify-id",
            "SPOTIFY_CLIENT_SECRET": "spotify-secret",
        }
    )

    assert config.spotify_enabled is True


def test_load_config_handles_utf8_bom_env_file(tmp_path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "\ufeffLASTFM_API_KEY=lastfm-key\nLASTFM_USERNAME=listener\nSEND_EMAIL=false\n",
        encoding="utf-8",
    )

    config = load_config(env_file=env_file)

    assert config.lastfm_api_key == "lastfm-key"
