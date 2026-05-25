"""Discord Notifier Implementation."""

from core.observability.logging import get_logger
import aiohttp

from .base import BaseNotifier
from .models import AttackNotification, NotificationResult, WebhookProvider
from .formatters import DiscordFormatter

logger = get_logger(__name__)


class DiscordNotifier(BaseNotifier):
    """Sends notifications via Discord Webhook."""

    def __init__(self, webhook_url: str):
        super().__init__(provider=WebhookProvider.DISCORD)
        self.webhook_url = webhook_url

    async def send(self, notification: AttackNotification) -> NotificationResult:
        """Send embed to Discord."""
        return await self._send_with_retry(self._send_webhook, notification)

    async def _send_webhook(self, notification: AttackNotification) -> bool:
        """Internal send method."""
        payload = DiscordFormatter.format(notification)

        async with aiohttp.ClientSession() as session:
            async with session.post(
                self.webhook_url, json=payload, timeout=10
            ) as response:
                if response.status in (200, 204):
                    return True

                resp_text = await response.text()
                logger.error(f"Discord Webhook error: {response.status} - {resp_text}")
                raise Exception(f"Discord API returned {response.status}")
