"""Discovery and intelligence query methods for HoneypotSwarmCoordinator.

Handles discovery logs, CVE correlations, attack patterns, and AI analysis.
"""

from core.observability.logging import get_logger
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from ..models import AttackSeverity, DiscoveryLog

if TYPE_CHECKING:
    from .coordinator import HoneypotSwarmCoordinator

logger = get_logger(__name__)


class IntelligenceMixin:
    """Mixin providing discovery and intelligence query capabilities."""

    async def get_discovery_logs(
        self: "HoneypotSwarmCoordinator", limit: int = 100
    ) -> List[DiscoveryLog]:
        """Get recent discovery logs (including historical from DB)."""
        from ..persistence import HoneypotDAO

        # 1. Fetch persisted events
        events_list, _ = await HoneypotDAO.get_events(page=1, page_size=limit)
        logger.info(
            f"DEBUG: get_discovery_logs fetched {len(events_list)} events from DB"
        )

        # 2. Convert to DiscoveryLog objects
        hydrated_logs: List[DiscoveryLog] = []
        for event in events_list:
            # Filter out duplicated IPv6 localhost events if requested
            if event.source_ip == "::1":
                continue

            try:
                # Reconstruct log message similar to _add_discovery_log
                proto = (
                    event.protocol.value
                    if hasattr(event.protocol, "value")
                    else str(event.protocol)
                )
                cat = (
                    event.category.value
                    if hasattr(event.category, "value")
                    else str(event.category)
                )
                sev = (
                    event.severity.value
                    if hasattr(event.severity, "value")
                    else str(event.severity)
                )

                # Check for critical severity
                is_alert = event.severity in (
                    AttackSeverity.HIGH,
                    AttackSeverity.CRITICAL,
                )
                if isinstance(event.severity, str):
                    is_alert = event.severity in ("high", "critical")

                log = DiscoveryLog(
                    message=f"[{proto.upper()}] Attack from {event.source_ip}: {cat} ({sev})",
                    timestamp=event.timestamp,
                    is_alert=is_alert,
                    is_error=False,
                    agent_type="system",
                )
                hydrated_logs.append(log)
            except Exception as e:
                logger.error(f"DEBUG: Failed to hydrate event {event.event_id}: {e}")
                continue

        logger.info(f"DEBUG: Hydrated {len(hydrated_logs)} logs")

        # 3. Combine with in-memory logs with deduplication
        # Prefer in-memory logs as they are the source of truth for "live" state
        existing_signatures = {
            (
                log.timestamp.replace(microsecond=0),  # Ignore microsecond differences
                log.message,
            )
            for log in self._discovery_logs
        }

        unique_hydrated = []
        for log in hydrated_logs:
            sig = (log.timestamp.replace(microsecond=0), log.message)
            if sig not in existing_signatures:
                unique_hydrated.append(log)
                existing_signatures.add(sig)

        combined = self._discovery_logs + unique_hydrated

        # 4. Sort by timestamp descending
        combined.sort(key=lambda x: x.timestamp, reverse=True)

        # 5. Return limit
        return combined[:limit]

    def get_cve_correlations(
        self: "HoneypotSwarmCoordinator", limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get CVE correlations."""
        return self._cve_correlator.get_correlations()[:limit]

    def get_top_attackers(
        self: "HoneypotSwarmCoordinator", limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get top attacker IPs."""
        ip_counts: Dict[str, int] = {}
        for event in self._events:
            ip_counts[event.source_ip] = ip_counts.get(event.source_ip, 0) + 1

        top_ips = sorted(ip_counts.items(), key=lambda x: x[1], reverse=True)[:limit]
        return [{"ip": ip, "count": count} for ip, count in top_ips]

    def get_attack_patterns(
        self: "HoneypotSwarmCoordinator",
    ) -> List[Dict[str, Any]]:
        """Get detected attack patterns and frequencies."""
        pattern_counts: Dict[str, int] = {}
        for event in self._events:
            for pattern in event.detected_patterns or []:
                pattern_counts[pattern] = pattern_counts.get(pattern, 0) + 1

        return [
            {"pattern": p, "count": c}
            for p, c in sorted(
                pattern_counts.items(), key=lambda x: x[1], reverse=True
            )[:20]
        ]

    async def analyze_event(
        self: "HoneypotSwarmCoordinator", event_id: str
    ) -> Optional[Dict[str, Any]]:
        """Analyze event with AI."""
        from .utils import analysis

        return await analysis.analyze_event(self, event_id)

    async def analyze_session(
        self: "HoneypotSwarmCoordinator", session_id: str
    ) -> Optional[Dict[str, Any]]:
        """Analyze session with AI."""
        session = await self.get_session(session_id)
        if not session:
            return None

        # Simple session analysis
        return {
            "session_id": session_id,
            "commands_analyzed": len(session.commands),
            "max_severity": session.max_severity.value,
            "duration_seconds": (
                (session.last_activity - session.started_at).total_seconds()
                if session.last_activity
                else 0
            ),
        }


__all__ = ["IntelligenceMixin"]
