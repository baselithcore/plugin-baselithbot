"""SMTP transport for transactional auth emails.

Uses stdlib ``smtplib`` executed off the event loop via ``asyncio.to_thread``.
When no SMTP host is configured (typical for local development) the message is
logged instead of sent, so flows remain testable without a mail server.
"""

from __future__ import annotations

import asyncio
import smtplib
import ssl
from email.message import EmailMessage

from core.observability.logging import get_logger
from plugins.auth.config import AuthConfig

logger = get_logger(__name__)


def _build_message(
    config: AuthConfig, to: str, subject: str, text_body: str, html_body: str
) -> EmailMessage:
    """Assemble a multipart (text + HTML) email message."""
    msg = EmailMessage()
    from_name = config.email_from_name
    msg["From"] = f"{from_name} <{config.smtp_from}>"
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(text_body)
    msg.add_alternative(html_body, subtype="html")
    return msg


def _send_sync(config: AuthConfig, msg: EmailMessage) -> None:
    """Blocking SMTP delivery (runs in a worker thread)."""
    host = config.smtp_host
    if not host:
        return
    password = config.smtp_password.get_secret_value() if config.smtp_password else None
    if config.smtp_use_tls:
        context = ssl.create_default_context()
        with smtplib.SMTP(host, config.smtp_port, timeout=15) as server:
            server.starttls(context=context)
            if config.smtp_username and password:
                server.login(config.smtp_username, password)
            server.send_message(msg)
    else:
        with smtplib.SMTP(host, config.smtp_port, timeout=15) as server:
            if config.smtp_username and password:
                server.login(config.smtp_username, password)
            server.send_message(msg)


async def deliver(
    config: AuthConfig, to: str, subject: str, text_body: str, html_body: str
) -> bool:
    """Send (or log, in dev mode) a transactional email.

    Returns:
        True if handed to SMTP (or logged in dev mode), False on transport error.
    """
    if not config.smtp_host:
        logger.info(
            "Email (dev mode, no SMTP configured) to=%s subject=%r\n%s",
            to,
            subject,
            text_body,
        )
        return True

    msg = _build_message(config, to, subject, text_body, html_body)
    try:
        await asyncio.to_thread(_send_sync, config, msg)
        logger.info("Sent email to=%s subject=%r", to, subject)
        return True
    except Exception as exc:  # pragma: no cover - transport failures are env-specific
        logger.error("Failed to send email to=%s: %s", to, exc)
        return False
