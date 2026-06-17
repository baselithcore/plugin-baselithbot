"""Webhook notification field group for HoneypotConfig."""

from typing import Dict, List, Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class _NotificationFields(BaseSettings):
    """Mixin: Webhook Notifications fields."""

    model_config = {
        "env_prefix": "HONEYPOT_",
        "extra": "ignore",
    }

    # =========================================================================
    # Webhook Notifications
    # =========================================================================

    enable_notifications: bool = Field(
        default=False,
        description="Enable external webhook notifications",
    )
    notification_min_severity: str = Field(
        default="high",
        description="Minimum severity to trigger notification (high, critical)",
    )
    notification_cooldown_seconds: int = Field(
        default=30,
        description="Cooldown seconds between notifications for same IP",
    )
    notification_ignore_credentials: List[str] = Field(
        default_factory=lambda: [
            "admin:password",
            "admin:123456",
            "root:root",
            "admin:admin",
        ],
        description="Username:password combinations to ignore for noise reduction",
    )
    notification_ignore_categories: List[str] = Field(
        default_factory=lambda: ["credential_harvesting"],
        description="Attack categories to ignore (e.g. credential_harvesting)",
    )
    telegram_bot_token: Optional[str] = Field(
        default=None,
        description="Telegram Bot API Token",
    )
    telegram_chat_id: Optional[str] = Field(
        default=None,
        description="Telegram Chat ID",
    )
    discord_webhook_url: Optional[str] = Field(
        default=None,
        description="Discord Webhook URL",
    )
    generic_webhook_url: Optional[str] = Field(
        default=None,
        description="Generic Webhook URL",
    )
    generic_webhook_headers: Dict[str, str] = Field(
        default_factory=dict,
        description="Custom headers for generic webhook",
    )
