from __future__ import annotations

import re
import smtplib
from email.message import EmailMessage

from config import AppConfig


class EmailDeliveryError(RuntimeError):
    """Raised when the weekly report email cannot be sent."""


class EmailSender:
    def __init__(self, config: AppConfig, smtp_host: str = "smtp.gmail.com", smtp_port: int = 465):
        self.config = config
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port

    def send_html_report(self, subject: str, html_report: str) -> None:
        if not self.config.gmail_address or not self.config.gmail_app_password:
            raise EmailDeliveryError("Gmail credentials are missing.")
        if not self.config.recipient_email:
            raise EmailDeliveryError("Recipient email is missing.")

        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = self.config.gmail_address
        message["To"] = self.config.recipient_email
        message.set_content(_html_to_text(html_report))
        message.add_alternative(html_report, subtype="html")

        try:
            with smtplib.SMTP_SSL(self.smtp_host, self.smtp_port, timeout=30) as smtp:
                smtp.login(self.config.gmail_address, self.config.gmail_app_password)
                smtp.send_message(message)
        except smtplib.SMTPException as exc:
            raise EmailDeliveryError("Could not send email via Gmail SMTP.") from exc
        except OSError as exc:
            raise EmailDeliveryError("Could not connect to Gmail SMTP.") from exc


def _html_to_text(html_report: str) -> str:
    text = re.sub(r"<style.*?</style>", "", html_report, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()
