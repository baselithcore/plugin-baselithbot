from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional
from core.observability.logging import get_logger

from ...models import AttackEvent, DiscoveryLog

if TYPE_CHECKING:
    from ..coordinator import HoneypotSwarmCoordinator

logger = get_logger(__name__)


def update_stats(coordinator: "HoneypotSwarmCoordinator", event: AttackEvent) -> None:
    """Update statistics from event.

    Args:
        coordinator: The coordinator instance
        event: The attack event
    """
    coordinator._stats.total_events += 1

    # Protocol breakdown
    proto = event.protocol.value
    if proto not in coordinator._stats.protocol_breakdown:
        coordinator._stats.protocol_breakdown[proto] = 0
    coordinator._stats.protocol_breakdown[proto] += 1

    # Severity breakdown
    sev = event.severity.value
    if sev not in coordinator._stats.severity_breakdown:
        coordinator._stats.severity_breakdown[sev] = 0
    coordinator._stats.severity_breakdown[sev] += 1

    # Category breakdown
    cat = event.category.value if event.category else "unknown"
    if cat not in coordinator._stats.category_breakdown:
        coordinator._stats.category_breakdown[cat] = 0
    coordinator._stats.category_breakdown[cat] += 1

    # Unique IPs (O(1) with set)
    if event.source_ip not in coordinator._seen_ips:
        coordinator._seen_ips.add(event.source_ip)
        coordinator._stats.unique_ips = len(coordinator._seen_ips)

    # Active sessions
    coordinator._stats.active_sessions = len(coordinator._sessions)


def is_high_activity_ip(coordinator: "HoneypotSwarmCoordinator", ip: str) -> bool:
    """Check if IP has high recent activity.

    Args:
        coordinator: The coordinator instance
        ip: The source IP to check

    Returns:
        True if IP is high activity
    """

    # deque doesn't support slicing, use islice on reversed iterator
    # to get the last 100 events
    events_list = list(coordinator._events)
    recent_events = [e for e in events_list[-100:] if e.source_ip == ip]
    return len(recent_events) >= 5


def add_discovery_log(
    coordinator: "HoneypotSwarmCoordinator",
    message: str,
    is_alert: bool = False,
    is_error: bool = False,
    country_code: Optional[str] = None,
    source_ip: Optional[str] = None,
) -> None:
    """Add a discovery log entry.

    Args:
        coordinator: The coordinator instance
        message: Log message
        is_alert: Whether it's an alert
        is_error: Whether it's an error
        country_code: ISO country code (optional)
        source_ip: Attacker IP address (optional)
    """
    log = DiscoveryLog(
        message=message,
        timestamp=datetime.now(timezone.utc),
        is_alert=is_alert,
        is_error=is_error,
        country_code=country_code,
        source_ip=source_ip,
    )
    coordinator._discovery_logs.append(log)

    # Keep last 1000 logs
    if len(coordinator._discovery_logs) > 1000:
        coordinator._discovery_logs = coordinator._discovery_logs[-500:]

    # Broadcast log event
    try:
        from plugins.honeypot.stream import get_stream_manager
        import asyncio

        stream_manager = get_stream_manager()
        # Use simple create_task which works in most async contexts
        # If this is called from sync context, it might need get_event_loop()
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(stream_manager.broadcast_log(log))
        except RuntimeError:
            # No running loop (sync context) - highly unlikely in this architecture but safe to handle
            logger.error("Attempted to broadcast log from sync context with no loop")
    except Exception as e:
        logger.error(f"Failed to broadcast discovery log: {e}")
