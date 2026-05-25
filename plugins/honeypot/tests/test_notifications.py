import pytest
import datetime
import sys
import os
from unittest.mock import MagicMock, AsyncMock, patch

# Add project root to path
sys.path.append(os.getcwd())

from plugins.honeypot.notifications.models import AttackNotification
from plugins.honeypot.notifications.formatters import (
    TelegramFormatter,
    DiscordFormatter,
)
from plugins.honeypot.notifications.manager import NotificationManager
from plugins.honeypot.config import HoneypotConfig


@pytest.fixture
def mock_config():
    """Mock configuration."""
    config = MagicMock(spec=HoneypotConfig)
    config.enable_notifications = True
    config.notification_min_severity = "high"
    config.notification_cooldown_seconds = 60
    config.notification_ignore_credentials = ["admin:password"]
    config.notification_ignore_categories = ["credential_harvesting"]
    config.telegram_bot_token = "test_token"
    config.telegram_chat_id = "test_chat"
    config.discord_webhook_url = "http://discord"
    config.generic_webhook_url = None
    return config


class TestFormatters:
    """Test message formatters."""

    def test_telegram_format(self):
        """Test Telegram Markdown formatting."""
        notification = AttackNotification(
            event_id="evt_1",
            honeypot_id="ssh",
            protocol="ssh",
            source_ip="1.2.3.4",
            source_country="Italy",
            timestamp=datetime.datetime.now(),
            severity="critical",
            category="brute_force",
            detected_patterns=["pattern1"],
            payload="rm -rf /",
            matched_cves=["CVE-2024-1234"],
        )

        msg = TelegramFormatter.format(notification)
        assert "CRITICAL ATTACK DETECTED" in msg
        assert "Italy" in msg
        assert "rm -rf /" in msg
        assert "CVE-2024-1234" in msg

    def test_discord_format(self):
        """Test Discord Embed formatting."""
        notification = AttackNotification(
            event_id="evt_1",
            honeypot_id="ssh",
            protocol="ssh",
            source_ip="1.2.3.4",
            source_country="Italy",
            timestamp=datetime.datetime.now(),
            severity="critical",
            category="brute_force",
            detected_patterns=["pattern1"],
            payload="rm -rf /",
            matched_cves=["CVE-2024-1234"],
        )

        payload = DiscordFormatter.format(notification)
        embed = payload["embeds"][0]
        assert "CRITICAL ATTACK DETECTED" in embed["title"]
        assert embed["color"] == 0xFF0000  # Red


class TestNotificationManager:
    """Test filtering and dispatch logic."""

    @pytest.mark.asyncio
    async def test_filtering_logic(self, mock_config):
        """Test severity and credential filtering."""
        with (
            patch(
                "plugins.honeypot.notifications.manager.get_honeypot_config",
                return_value=mock_config,
            ),
            patch("plugins.honeypot.notifications.manager.TelegramNotifier"),
        ):
            manager = NotificationManager()
            manager.initialize()

            # Mock dispatch to verification
            manager._dispatch = AsyncMock()

            # Case 1: Low severity (Should be ignored)
            await manager._handle_attack_event(
                {"severity": "low", "category": "recon", "source_ip": "1.1.1.1"}
            )
            manager._dispatch.assert_not_called()

            # Case 2: Ignored category (credential_harvesting)
            await manager._handle_attack_event(
                {
                    "severity": "critical",
                    "category": "credential_harvesting",
                    "source_ip": "2.2.2.2",
                }
            )
            manager._dispatch.assert_not_called()

            # Case 3: Ignored credentials (admin:password)
            await manager._handle_attack_event(
                {
                    "severity": "high",
                    "category": "brute_force",
                    "source_ip": "3.3.3.3",
                    "username": "admin",
                    "password": "password",
                }
            )
            manager._dispatch.assert_not_called()

            # Case 4: Valid Critical Attack
            await manager._handle_attack_event(
                {
                    "severity": "critical",
                    "category": "exploit",
                    "source_ip": "4.4.4.4",
                    "event_id": "evt_4",
                    "honeypot_id": "ssh",
                    "protocol": "ssh",
                    "timestamp": datetime.datetime.now().isoformat(),
                }
            )
            assert manager._dispatch.called
            args = manager._dispatch.call_args[0][0]
            assert isinstance(args, AttackNotification)
            assert args.source_ip == "4.4.4.4"

    @pytest.mark.asyncio
    async def test_rate_limiting(self, mock_config):
        """Test IP-based rate limiting."""
        with patch(
            "plugins.honeypot.notifications.manager.get_honeypot_config",
            return_value=mock_config,
        ):
            manager = NotificationManager()
            manager.initialize()
            manager._dispatch = AsyncMock()

            event = {
                "severity": "critical",
                "category": "exploit",
                "source_ip": "5.5.5.5",
                "event_id": "evt_5",
                "honeypot_id": "ssh",
                "protocol": "ssh",
                "timestamp": datetime.datetime.now().isoformat(),
            }

            # First call: Should pass
            await manager._handle_attack_event(event)
            assert manager._dispatch.call_count == 1

            # Second call immediately: Should be rate limited
            await manager._handle_attack_event(event)
            assert manager._dispatch.call_count == 1  # No change
