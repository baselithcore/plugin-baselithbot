"""Notification System Models.

Data models for webhook configuration and notification payloads.
"""

from enum import Enum
from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, Field


class WebhookProvider(str, Enum):
    """Supported webhook providers."""

    TELEGRAM = "telegram"
    DISCORD = "discord"
    GENERIC = "generic"


class AttackNotification(BaseModel):
    """Standardized attack data for notifications."""

    event_id: str
    honeypot_id: str
    protocol: str
    source_ip: str
    source_country: Optional[str] = None
    source_country_code: Optional[str] = None
    source_city: Optional[str] = None
    timestamp: datetime

    severity: str
    category: str
    detected_patterns: List[str] = Field(default_factory=list)

    # Attack details
    payload: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    command: Optional[str] = None
    http_path: Optional[str] = None

    # Context
    matched_cves: List[str] = Field(default_factory=list)
    is_bot: bool = False

    def get_title(self) -> str:
        """Get notification title based on severity."""
        emoji = "🚨" if self.severity == "critical" else "⚠️"
        return f"{emoji} {self.severity.upper()} ATTACK DETECTED"


class NotificationResult(BaseModel):
    """Result of a notification delivery attempt."""

    provider: WebhookProvider
    success: bool
    error: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)
    duration_ms: float = 0.0
