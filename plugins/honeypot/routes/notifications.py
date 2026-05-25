"""Notification System API Routes."""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel

from plugins.honeypot.config import get_honeypot_config
from plugins.honeypot.notifications import AttackNotification


router = APIRouter(tags=["Notifications"])


class NotificationConfigUpdate(BaseModel):
    """Configuration update model."""

    enable_notifications: bool
    min_severity: str
    cooldown_seconds: int


@router.get("/config")
async def get_notification_config():
    """Get current notification configuration."""
    config = get_honeypot_config()
    return {
        "enabled": config.enable_notifications,
        "min_severity": config.notification_min_severity,
        "cooldown_seconds": config.notification_cooldown_seconds,
        "providers": {
            "telegram": bool(config.telegram_bot_token and config.telegram_chat_id),
            "discord": bool(config.discord_webhook_url),
            "generic": bool(config.generic_webhook_url),
        },
    }


@router.post("/test")
async def send_test_notification(background_tasks: BackgroundTasks):
    """Send a test notification to all configured providers."""
    # We need to access the plugin instance to get the initialized NotificationManager
    # In a real app we'd use dependency injection or a global accessor
    # For now, we'll instantiate a temporary manager just for testing if needed,
    # or rely on the fact that the plugin initializes it.

    # NOTE: In this architecture, we might need a way to access the running plugin instance.
    # Often 'core' provides a way to get plugins.

    from core.plugin_manager import get_plugin_manager

    # Import locally to avoid circular dependency with plugin.py -> router.py -> notifications.py
    from plugins.honeypot.plugin import HoneypotPlugin

    manager = get_plugin_manager()
    plugin = manager.get_plugin("honeypot")

    if not plugin or not isinstance(plugin, HoneypotPlugin):
        raise HTTPException(status_code=500, detail="Honeypot plugin not found")

    if not plugin.notification_manager:
        raise HTTPException(
            status_code=500, detail="Notification manager not initialized"
        )

    # Create dummy notification
    import datetime

    notification = AttackNotification(
        event_id="test_event_123",
        honeypot_id="test-honeypot",
        protocol="test",
        source_ip="127.0.0.1",
        source_country="Testland",
        timestamp=datetime.datetime.now(),
        severity="high",
        category="test_category",
        detected_patterns=["test_pattern_1", "test_pattern_2"],
        payload="This is a test notification payload.",
        username="testuser",
        password="testpassword",
    )

    # We use the internal dispatch method to bypass rate limiting/filtering for the test
    # But dispatch is async.
    background_tasks.add_task(plugin.notification_manager._dispatch, notification)

    return {"status": "Test notification queued"}
