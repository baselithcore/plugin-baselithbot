from core.observability.logging import get_logger
from typing import TYPE_CHECKING

from ...models import AttackEvent, AttackSeverity

if TYPE_CHECKING:
    from ..coordinator import HoneypotSwarmCoordinator

logger = get_logger(__name__)


async def apply_sensibility(
    coordinator: "HoneypotSwarmCoordinator", event: AttackEvent
) -> str:
    """Apply HoneyDOC Sensibility classification to event.

    Per HoneyDOC Section IV-C1: Fine-grained traffic classification
    determines flow action (DROP, FORWARD, REDIRECT).

    Args:
        coordinator: The coordinator instance (for config and captor access)
        event: Attack event to classify

    Returns:
        Flow action string: 'drop', 'forward', or 'redirect'
    """
    if not coordinator.config.enable_sensibility:
        return coordinator.config.default_flow_action

    # Get payload for content matching
    payload = event.raw_data or event.command or event.http_path or ""

    # Classify using TrafficClassifier
    result = coordinator._captor_manager.classifier.classify(
        protocol=event.protocol.value,
        src_ip=event.source_ip,
        dst_port=event.source_port or 0,
        payload=payload,
    )

    # Log classification result
    if result.matched:
        rule = result.primary_rule
        logger.debug(
            f"Traffic classified: {event.event_id} -> "
            f"{rule.action.value if rule else 'default'} "
            f"(rule: {rule.sid if rule else 'none'})"
        )

        # Apply auto-block if threshold exceeded
        if coordinator.config.enable_flow_control:
            await check_auto_block(coordinator, event)

    return (
        result.action.value
        if result.matched
        else coordinator.config.default_flow_action
    )


async def check_auto_block(
    coordinator: "HoneypotSwarmCoordinator", event: AttackEvent
) -> None:
    """Check if IP should be auto-blocked based on activity.

    Args:
        coordinator: The coordinator instance
        event: Attack event to check
    """
    if event.severity not in (AttackSeverity.HIGH, AttackSeverity.CRITICAL):
        return

    # Count high-severity events from this IP
    high_sev_count = sum(
        1
        for e in coordinator._events[-500:]
        if e.source_ip == event.source_ip
        and e.severity in (AttackSeverity.HIGH, AttackSeverity.CRITICAL)
    )

    if high_sev_count >= coordinator.config.auto_block_threshold:
        # Auto-block the IP
        coordinator._captor_manager.flow_controller.block_ip(
            ip=event.source_ip,
            reason=f"Auto-blocked after {high_sev_count} high-severity events",
            duration_seconds=coordinator.config.banned_ip_timeout_minutes * 60,
        )
        coordinator._add_discovery_log(
            f"[AUTO-BLOCK] IP {event.source_ip} blocked after "
            f"{high_sev_count} high-severity events",
            is_alert=True,
        )
