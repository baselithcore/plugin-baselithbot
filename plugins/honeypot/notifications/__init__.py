"""Honeypot Notification System.

Handles dispatching attack alerts to external webhooks (Telegram, Discord, etc.).
"""

from .manager import NotificationManager
from .models import WebhookProvider, AttackNotification

__all__ = ["NotificationManager", "WebhookProvider", "AttackNotification"]
