from pathlib import Path

import pytest

from config import AppConfig
from email_sender import EmailDeliveryError, EmailSender, _html_to_text


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
        "gmail_address": "sender@example.com",
        "gmail_app_password": "app-password",
        "recipient_email": "recipient@example.com",
        "send_email": True,
        "enable_playlist": False,
        "lookback_days": 7,
        "database_path": tmp_path / "wrapped.sqlite3",
        "output_dir": tmp_path / "output",
    }
    values.update(overrides)
    return AppConfig(**values)


def test_html_to_text_removes_styles_tags_and_extra_spaces() -> None:
    text = _html_to_text("<style>body{color:red}</style><h1>Hello</h1><p>Weekly report</p>")

    assert text == "Hello Weekly report"


def test_send_html_report_logs_in_and_sends_multipart_message(monkeypatch, tmp_path) -> None:
    sent_messages = []

    class FakeSMTP:
        def __init__(self, host: str, port: int, timeout: int):
            self.host = host
            self.port = port
            self.timeout = timeout
            self.login_args = None

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback) -> None:
            return None

        def login(self, address: str, password: str) -> None:
            self.login_args = (address, password)

        def send_message(self, message) -> None:
            sent_messages.append((self.login_args, message))

    monkeypatch.setattr("email_sender.smtplib.SMTP_SSL", FakeSMTP)

    sender = EmailSender(_config(tmp_path), smtp_host="smtp.example.com", smtp_port=465)
    sender.send_html_report("Weekly Test", "<h1>Your Weekly Spotify Wrapped</h1>")

    assert len(sent_messages) == 1
    login_args, message = sent_messages[0]
    assert login_args == ("sender@example.com", "app-password")
    assert message["Subject"] == "Weekly Test"
    assert message["From"] == "sender@example.com"
    assert message["To"] == "recipient@example.com"
    assert "Your Weekly Spotify Wrapped" in message.get_body(preferencelist=("plain",)).get_content()
    assert "<h1>Your Weekly Spotify Wrapped</h1>" in message.get_body(preferencelist=("html",)).get_content()


def test_send_html_report_requires_gmail_credentials(tmp_path) -> None:
    sender = EmailSender(_config(tmp_path, gmail_app_password=None))

    with pytest.raises(EmailDeliveryError, match="Gmail credentials"):
        sender.send_html_report("Weekly Test", "<h1>Report</h1>")


def test_send_html_report_requires_recipient(tmp_path) -> None:
    sender = EmailSender(_config(tmp_path, recipient_email=None))

    with pytest.raises(EmailDeliveryError, match="Recipient email"):
        sender.send_html_report("Weekly Test", "<h1>Report</h1>")
