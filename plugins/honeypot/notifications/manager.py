"""Notification Manager.

Central component for handling attack events and dispatching notifications.
"""

from core.observability.logging import get_logger
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Set

from plugins.honeypot.config import get_honeypot_config, HoneypotConfig
from plugins.honeypot.events import emit_honeypot_event, get_event_bus, HoneypotEvents
from .models import AttackNotification
from .telegram import TelegramNotifier
from .discord import DiscordNotifier
from .generic import GenericWebhookNotifier
from .base import BaseNotifier

logger = get_logger(__name__)


class NotificationManager:
    """Manages attack notifications and webhook dispatch."""

    def __init__(self):
        self.config: HoneypotConfig = get_honeypot_config()
        self.notifiers: List[BaseNotifier] = []
        self._sent_notifications: Dict[str, datetime] = {}  # key -> timestamp
        self._running = False
        self._event_bus = None

        # Cache ignored credentials for faster lookup
        self._ignored_creds: Set[str] = set()
        self._ignored_categories: Set[str] = set()

    def initialize(self):
        """Initialize notifiers based on config."""
        self._init_notifiers()
        self._ignored_creds = set(self.config.notification_ignore_credentials)
        self._ignored_categories = set(self.config.notification_ignore_categories)
        self._subscribe_events()
        self._running = True
        logger.info(
            f"NotificationManager initialized with {len(self.notifiers)} notifiers"
        )

    def _init_notifiers(self):
        """Setup enabled notifiers."""
        self.notifiers = []

        # Telegram
        if self.config.telegram_bot_token and self.config.telegram_chat_id:
            try:
                self.notifiers.append(
                    TelegramNotifier(
                        bot_token=self.config.telegram_bot_token,
                        chat_id=self.config.telegram_chat_id,
                    )
                )
                logger.info("Telegram notifier enabled")
            except Exception as e:
                logger.error(f"Failed to init Telegram notifier: {e}")

        # Discord
        if self.config.discord_webhook_url:
            self.notifiers.append(
                DiscordNotifier(webhook_url=self.config.discord_webhook_url)
            )
            logger.info("Discord notifier enabled")

        # Generic
        if self.config.generic_webhook_url:
            self.notifiers.append(
                GenericWebhookNotifier(
                    url=self.config.generic_webhook_url,
                    headers=self.config.generic_webhook_headers,
                )
            )
            logger.info("Generic webhook notifier enabled")

    def _subscribe_events(self):
        """Subscribe to attack events."""
        self._event_bus = get_event_bus()
        if not self._event_bus:
            logger.warning("EventBus not available, notifications will not work")
            return

        # Subscribe to new attack detection events
        # We listen to ATTACK_DETECTED and filter internally,
        # or we could listen to ATTACK_HIGH_SEVERITY if that covers strict requirements
        self._event_bus.on(HoneypotEvents.ATTACK_DETECTED)(self._handle_attack_event)
        self._event_bus.on(HoneypotEvents.ATTACK_HIGH_SEVERITY)(
            self._handle_attack_event
        )

    async def _handle_attack_event(self, data: Dict) -> None:
        """Process incoming attack event."""
        if not self._running or not self.config.enable_notifications:
            return

        try:
            # 1. Severity Filter
            severity = data.get("severity", "info").lower()
            if severity not in ("high", "critical"):
                return

            # 2. Category Filter (User Request)
            category = data.get("category", "")
            if category in self._ignored_categories:
                return

            # 3. Noise Reduction (User Request)
            # Filter simple brute force with common creds for HIGH severity
            # Critical events always go through unless explicitly ignored
            if severity == "high":
                username = data.get("username")
                password = data.get("password")
                if username and password:
                    combo = f"{username}:{password}"
                    if combo in self._ignored_creds:
                        # Log that we suppressed noise
                        # logger.debug(f"Suppressed notification for ignored creds: {combo}")
                        return

            # 4. Rate Limiting (Deduplication)
            source_ip = data.get("source_ip")
            if self._is_rate_limited(source_ip):
                return

            # Create Notification Model
            notification = AttackNotification(
                event_id=str(data.get("event_id")),
                honeypot_id=str(data.get("honeypot_id")),
                protocol=str(data.get("protocol")),
                source_ip=str(source_ip),
                source_country=data.get("geo", {}).get("country"),
                source_country_code=data.get("geo", {}).get("country_code"),
                source_city=data.get("geo", {}).get("city"),
                timestamp=datetime.fromisoformat(data.get("timestamp"))
                if data.get("timestamp")
                else datetime.now(),
                severity=severity,
                category=category,
                detected_patterns=data.get("detected_patterns", []),
                payload=data.get("raw_data")
                or data.get("command")
                or data.get("http_body"),
                username=data.get("username"),
                password=data.get("password"),
                matched_cves=data.get("matched_cves", []),
            )

            # Dispatch
            await self._dispatch(notification)

        except Exception as e:
            logger.error(f"Error handling notification event: {e}", exc_info=True)

    def _is_rate_limited(self, source_ip: str) -> bool:
        """Check if IP is rate limited for notifications."""
        now = datetime.now()
        cooldown = timedelta(seconds=self.config.notification_cooldown_seconds)

        last_sent = self._sent_notifications.get(source_ip)
        if last_sent and (now - last_sent) < cooldown:
            return True

        self._sent_notifications[source_ip] = now

        # Cleanup old entries (simple mechanism)
        if len(self._sent_notifications) > 1000:
            cutoff = now - cooldown
            self._sent_notifications = {
                k: v for k, v in self._sent_notifications.items() if v > cutoff
            }

        return False

    async def _dispatch(self, notification: AttackNotification):
        """Send notification to all providers."""
        tasks = [n.send(notification) for n in self.notifiers]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        success_count = 0
        for res in results:
            if isinstance(res, Exception):
                logger.error(f"Notification dispatch failed: {res}")
            elif res and res.success:
                success_count += 1

        if success_count > 0:
            await emit_honeypot_event(
                "honeypot.notification.sent",
                {"event_id": notification.event_id, "count": success_count},
            )

    def stop(self):
        """Stop notification manager."""
        self._running = False
        self._event_bus = None
