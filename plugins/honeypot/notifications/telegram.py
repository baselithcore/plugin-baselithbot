"""Telegram Notifier Implementation."""

from core.observability.logging import get_logger
import aiohttp

from .base import BaseNotifier
from .models import AttackNotification, NotificationResult, WebhookProvider
from .formatters import TelegramFormatter

logger = get_logger(__name__)


class TelegramNotifier(BaseNotifier):
    """Sends notifications via Telegram Bot API."""

    def __init__(self, bot_token: str, chat_id: str):
        super().__init__(provider=WebhookProvider.TELEGRAM)
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.api_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"

    async def send(self, notification: AttackNotification) -> NotificationResult:
        """Send formatted message to Telegram."""
        return await self._send_with_retry(self._send_message, notification)

    async def _send_message(self, notification: AttackNotification) -> bool:
        """Internal send method."""
        message = TelegramFormatter.format(notification)

        async with aiohttp.ClientSession() as session:
            payload = {
                "chat_id": self.chat_id,
                "text": message,
                "parse_mode": "Markdown",
                "disable_web_page_preview": True,
            }

            async with session.post(self.api_url, json=payload, timeout=10) as response:
                if response.status == 200:
                    return True

                resp_text = await response.text()
                logger.error(f"Telegram API error: {response.status} - {resp_text}")
                raise Exception(f"Telegram API returned {response.status}")
