"""Generic Webhook Notifier Implementation."""

from core.observability.logging import get_logger
import aiohttp
from typing import Dict, Optional

from .base import BaseNotifier
from .models import AttackNotification, NotificationResult, WebhookProvider
from .formatters import GenericFormatter

logger = get_logger(__name__)


class GenericWebhookNotifier(BaseNotifier):
    """Sends notifications via generic HTTP POST."""

    def __init__(self, url: str, headers: Optional[Dict[str, str]] = None):
        super().__init__(provider=WebhookProvider.GENERIC)
        self.url = url
        self.headers = headers or {}
        if "Content-Type" not in self.headers:
            self.headers["Content-Type"] = "application/json"

    async def send(self, notification: AttackNotification) -> NotificationResult:
        """Send JSON payload to webhook."""
        return await self._send_with_retry(self._post_webhook, notification)

    async def _post_webhook(self, notification: AttackNotification) -> bool:
        """Internal send method."""
        payload = GenericFormatter.format(notification)

        async with aiohttp.ClientSession() as session:
            async with session.post(
                self.url, json=payload, headers=self.headers, timeout=10
            ) as response:
                if response.status in (200, 201, 202, 204):
                    return True

                logger.warning(f"Generic webhook returned status {response.status}")
                # We consider 4xx and 5xx as errors that might warrant a retry (esp 5xx)
                if response.status >= 500:
                    raise Exception(f"Server error {response.status}")

                return False  # 4xx errors usually shouldn't be retried indefinitely
