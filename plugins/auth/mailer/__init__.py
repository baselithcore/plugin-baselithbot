"""Transactional email for the auth plugin.

Single entry point ``get_mailer()`` returns a :class:`Mailer` that renders a
localized template and delivers it over SMTP (or logs it in dev mode). Locale is
resolved per-message (``en`` default, ``it`` supported) so emails honour the
recipient's ``Accept-Language``.
"""

from __future__ import annotations

from typing import Optional

from core.di.container import ServiceRegistry
from core.observability.logging import get_logger
from plugins.auth.config import AuthConfig
from plugins.auth.mailer import _templates
from plugins.auth.mailer._sender import deliver

logger = get_logger(__name__)


class Mailer:
    """Render + deliver localized transactional emails."""

    def _config(self) -> AuthConfig:
        return ServiceRegistry.get(AuthConfig)

    async def _send_template(
        self, template: str, to: str, link: str, locale: str
    ) -> bool:
        config = self._config()
        subject, text_body, html_body = _templates.render(template, link, locale)
        return await deliver(config, to, subject, text_body, html_body)

    async def send_password_reset(
        self, to: str, token: str, locale: str = "en"
    ) -> bool:
        link = f"{self._config().app_base_url}/auth/reset-password?token={token}"
        return await self._send_template("password_reset", to, link, locale)

    async def send_invitation(self, to: str, token: str, locale: str = "en") -> bool:
        link = f"{self._config().app_base_url}/auth/accept-invite?token={token}"
        return await self._send_template("invitation", to, link, locale)

    async def send_email_verification(
        self, to: str, token: str, locale: str = "en"
    ) -> bool:
        link = f"{self._config().app_base_url}/auth/verify-email?token={token}"
        return await self._send_template("email_verify", to, link, locale)


_mailer: Optional[Mailer] = None


def get_mailer() -> Mailer:
    """Get or create the global mailer instance."""
    global _mailer
    if _mailer is None:
        _mailer = Mailer()
    return _mailer


__all__ = ["Mailer", "get_mailer"]
