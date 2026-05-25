import asyncio
import logging
import os
import sys
from core.observability.logging import get_logger
from datetime import datetime

# Add project root to path
sys.path.append("/app")

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = get_logger("vps_test")

from plugins.honeypot.config import HoneypotConfig  # noqa: E402
from plugins.honeypot.notifications.manager import NotificationManager  # noqa: E402


async def test_vps_webhook():
    print("\n🔍 --- VPS WEBHOOK DIAGNOSTIC --- 🔍\n")

    # 1. Check Configuration
    config = HoneypotConfig()
    print("📡 Configuration:")
    print(f"   - Notifications Enabled: {config.enable_notifications}")
    print(
        f"   - Discord URL: {'✅ Present' if config.discord_webhook_url else '❌ Missing'}"
    )
    print(
        f"   - Telegram Token: {'✅ Present' if config.telegram_bot_token else '❌ Missing'}"
    )
    print(f"   - Environment: {os.getenv('ENV_NAME', 'prod')}")

    # 2. Test Connection (DNS/Network check)
    print("\n🌐 Connectivity Check:")
    import socket

    try:
        if config.discord_webhook_url:
            host = "discord.com"
            socket.gethostbyname(host)
            print(f"   - DNS Resolution {host}: ✅ Success")
        if config.telegram_bot_token:
            host = "api.telegram.org"
            socket.gethostbyname(host)
            print(f"   - DNS Resolution {host}: ✅ Success")
    except Exception as e:
        print(f"   - DNS Resolution: ❌ Failed ({e})")
        print("     (Possibile problema di DNS nel container Docker)")

    # 3. Simulate Event
    print("\n📨 Initializing Notifiers...")
    manager = NotificationManager()
    manager.initialize()
    print(f"   - Active Notifiers: {len(manager.notifiers)}")

    mock_event = {
        "event_id": "vps-test-001",
        "honeypot_id": "vps-honeypot",
        "protocol": "ssh",
        "source_ip": "8.8.8.8",
        "geo": {"country": "VPN_TEST"},
        "severity": "high",
        "category": "manual_vps_test",
        "timestamp": datetime.now().isoformat(),
        "username": "vps_tester",
        "password": "testing_webhooks",
        "detected_patterns": ["vps_manual_trigger"],
        "raw_data": "Testing connectivity from VPS Docker container",
    }

    print("\n🚀 Sending Test Event (High Severity)...")
    await manager._handle_attack_event(mock_event)

    print("\n⏳ Waiting for async tasks (3s)...")
    await asyncio.sleep(3)
    print("\n🏁 Diagnostic Finished. Check your channels.")


if __name__ == "__main__":
    asyncio.run(test_vps_webhook())
