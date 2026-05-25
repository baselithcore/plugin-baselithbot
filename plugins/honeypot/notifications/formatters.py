"""Notification Formatters.

Converts AttackNotification models into provider-specific message formats.
"""

from typing import Dict, Any
from .models import AttackNotification


class TelegramFormatter:
    """Formats notifications for Telegram (Markdown)."""

    @staticmethod
    def _escape(text: str) -> str:
        """Escape markdown special characters for Telegram (Legacy)."""
        if not text:
            return ""
        # Characters that can break Telegram Markdown V1: _ * ` [
        return (
            text.replace("_", "\\_")
            .replace("*", "\\*")
            .replace("`", "'")
            .replace("[", "\\[")
        )

    @staticmethod
    def _get_flag_emoji(country_code: str) -> str:
        """Convert country code to flag emoji."""
        if not country_code:
            return ""
        try:
            return "".join(chr(ord(c) + 127397) for c in country_code.upper())
        except Exception:
            return ""

    @staticmethod
    def format(notification: AttackNotification) -> str:
        """Create Markdown message for Telegram."""
        title = notification.get_title()
        # Escape the title as it might contain honeypot IDs with underscores
        title = TelegramFormatter._escape(title)

        # Basic info
        lines = [
            f"*{title}*",
            "",
            f"📍 *Honeypot:* `{notification.honeypot_id}` ({notification.protocol})",
            f"🌐 *Source:* `{notification.source_ip}`",
        ]

        # Location with Flag
        location_parts = []
        if notification.source_country_code:
            flag = TelegramFormatter._get_flag_emoji(notification.source_country_code)
            location_parts.append(flag)

        if notification.source_city:
            location_parts.append(TelegramFormatter._escape(notification.source_city))

        if notification.source_country:
            country = TelegramFormatter._escape(notification.source_country)
            location_parts.append(country)

        if location_parts:
            lines.append(f"🏴 *Location:* {' '.join(location_parts)}")

        lines.append(
            f"⏰ *Time:* {notification.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}"
        )
        lines.append("")

        # Attack Details
        # Wrap category in backticks as it often contains underscores (e.g. brute_force)
        lines.append(f"🎯 *Category:* `{notification.category}`")
        lines.append(f"📊 *Severity:* *{notification.severity.upper()}*")

        if notification.detected_patterns:
            lines.append("🔍 *Detected Patterns:*")
            for pattern in notification.detected_patterns[:5]:  # Limit to 5
                # Escape pattern or wrap in backticks
                p_escaped = TelegramFormatter._escape(pattern)
                lines.append(f"• `{p_escaped}`")
            if len(notification.detected_patterns) > 5:
                lines.append(
                    f"• _...and {len(notification.detected_patterns) - 5} more_"
                )

        # Payload section
        if notification.payload:
            # Increase limit to 3000 chars for Telegram
            limit = 3000
            payload_preview = (
                (notification.payload[:limit] + "...")
                if len(notification.payload) > limit
                else notification.payload
            )
            # Escape backticks to prevent breaking markdown code blocks
            payload_preview = payload_preview.replace("`", "'")
            lines.append("")
            lines.append("💻 *Payload:*")
            lines.append(f"```\n{payload_preview}\n```")

        # CVEs
        if notification.matched_cves:
            lines.append("")
            cves = ", ".join(notification.matched_cves)
            lines.append(f"📌 *CVEs:* `{cves}`")

        return "\n".join(lines)


class DiscordFormatter:
    """Formats notifications for Discord (Embeds)."""

    @staticmethod
    def format(notification: AttackNotification) -> Dict[str, Any]:
        """Create Discord Embed payload."""
        color_map = {
            "critical": 0xFF0000,  # Red
            "high": 0xFFA500,  # Orange
            "medium": 0xFFFF00,  # Yellow
            "low": 0x00FF00,  # Green
            "info": 0x3498DB,  # Blue
        }

        fields = [
            {
                "name": "Honeypot",
                "value": f"{notification.honeypot_id} ({notification.protocol})",
                "inline": True,
            },
            {"name": "Source IP", "value": notification.source_ip, "inline": True},
            {"name": "Category", "value": notification.category, "inline": True},
        ]

        if notification.source_country:
            fields.insert(
                2,
                {
                    "name": "Country",
                    "value": notification.source_country,
                    "inline": True,
                },
            )

        if notification.detected_patterns:
            patterns = "\n".join([f"`{p}`" for p in notification.detected_patterns[:5]])
            if len(notification.detected_patterns) > 5:
                patterns += f"\n...and {len(notification.detected_patterns) - 5} more"
            fields.append(
                {"name": "Detected Patterns", "value": patterns, "inline": False}
            )

        if notification.matched_cves:
            fields.append(
                {
                    "name": "Correlated CVEs",
                    "value": ", ".join(notification.matched_cves),
                    "inline": False,
                }
            )

        # Add payload if present, but truncated for embed limits
        if notification.payload:
            payload_preview = (
                (notification.payload[:500] + "...")
                if len(notification.payload) > 500
                else notification.payload
            )
            fields.append(
                {
                    "name": "Payload",
                    "value": f"```\n{payload_preview}\n```",
                    "inline": False,
                }
            )

        return {
            "embeds": [
                {
                    "title": notification.get_title(),
                    "color": color_map.get(notification.severity.lower(), 0x3498DB),
                    "timestamp": notification.timestamp.isoformat(),
                    "fields": fields,
                    "footer": {"text": f"Event ID: {notification.event_id}"},
                }
            ]
        }


class GenericFormatter:
    """Formats notifications for generic webhooks (JSON)."""

    @staticmethod
    def format(notification: AttackNotification) -> Dict[str, Any]:
        """Create generic JSON payload."""
        return notification.model_dump()
