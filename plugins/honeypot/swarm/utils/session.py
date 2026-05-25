from core.observability.logging import get_logger
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from ...models import AttackEvent, AttackSeverity, HoneypotSession

if TYPE_CHECKING:
    from ..coordinator import HoneypotSwarmCoordinator

logger = get_logger(__name__)


async def update_session(
    coordinator: "HoneypotSwarmCoordinator", event: AttackEvent
) -> None:
    """Update or create session for event.

    Args:
        coordinator: The coordinator instance
        event: The attack event
    """
    from ...persistence import HoneypotDAO

    if event.session_id not in coordinator._sessions:
        coordinator._sessions[event.session_id] = HoneypotSession(
            session_id=event.session_id,
            protocol=event.protocol,
            source_ip=event.source_ip,
            source_port=event.source_port,
            started_at=datetime.now(timezone.utc),
        )

    session = coordinator._sessions[event.session_id]
    session.events_count += 1
    session.last_activity = datetime.now(timezone.utc)

    # Update max severity
    severity_order = [
        AttackSeverity.INFO,
        AttackSeverity.LOW,
        AttackSeverity.MEDIUM,
        AttackSeverity.HIGH,
        AttackSeverity.CRITICAL,
    ]
    if severity_order.index(event.severity) > severity_order.index(
        session.max_severity
    ):
        session.max_severity = event.severity

    if event.command:
        session.commands.append(event.command)

    # Persist session update
    try:
        await HoneypotDAO.save_session(session)
    except Exception as e:
        logger.error(f"Failed to persist session update: {e}")
