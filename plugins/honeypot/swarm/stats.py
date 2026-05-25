"""Statistics and query methods mixin for HoneypotSwarmCoordinator.

This module has been refactored into focused sub-modules for better maintainability:
- stats_queries: Event and session queries
- stats_honeypots: Honeypot registry queries
- stats_intelligence: Discovery logs, CVE correlations, and AI analysis

The StatsMixin class composes all sub-mixins and provides backward compatibility.
"""

from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any, Dict, List

from ..models import HoneypotStats, HoneypotStatus
from .stats_honeypots import HoneypotRegistryMixin
from .stats_intelligence import IntelligenceMixin
from .stats_queries import EventQueriesMixin

if TYPE_CHECKING:
    from .coordinator import HoneypotSwarmCoordinator


class StatsMixin(EventQueriesMixin, HoneypotRegistryMixin, IntelligenceMixin):
    """Mixin providing statistics and query capabilities.

    Composes event queries, honeypot registry, and intelligence capabilities.
    """

    def get_status(self: "HoneypotSwarmCoordinator") -> HoneypotStatus:
        """Get current honeypot status."""
        return HoneypotStatus(
            is_running=self._is_running,
            ssh_enabled=self.config.enable_ssh_honeypot,
            http_enabled=self.config.enable_http_honeypot,
            ssh_port=self.config.ssh_port,
            http_port=self.config.http_port,
            active_sessions=len(
                [s for s in self._sessions.values() if s.ended_at is None]
            ),
            total_events_today=self._stats.total_events,
            unique_ips_today=self._stats.unique_ips,
            last_attack=(self._events[-1].timestamp if self._events else None),
        )

    async def get_historical_stats(
        self: "HoneypotSwarmCoordinator",
        honeypot_id: str | None = None,
        days: int = 7,
    ) -> HoneypotStats:
        """Get historical statistics from database.

        This method queries the PostgreSQL database directly, providing
        accurate stats that persist across application restarts.

        Args:
            honeypot_id: Optional filter by honeypot
            days: Number of days to include

        Returns:
            HoneypotStats from database
        """
        from ..persistence import HoneypotDAO

        db_stats = await HoneypotDAO.get_stats(honeypot_id=honeypot_id, days=days)

        return HoneypotStats(
            total_connections=db_stats.get("total_connections", 0),
            total_sessions=db_stats.get("total_sessions", 0),
            active_sessions=db_stats.get("active_sessions", 0),
            total_events=db_stats.get("total_events", 0),
            unique_ips=db_stats.get("unique_ips", 0),
            banned_ips=db_stats.get("banned_ips", 0),
            top_attacker_ips=db_stats.get("top_attacker_ips", []),
            protocol_breakdown=db_stats.get("protocol_breakdown", {}),
            severity_breakdown=db_stats.get("severity_breakdown", {}),
            bot_breakdown=db_stats.get(
                "bot_breakdown", {"bot": 0, "human": 0, "unknown": 0}
            ),
            category_breakdown=db_stats.get("category_breakdown", {}),
            cve_correlations=db_stats.get("cve_correlations", 0),
            top_matched_cves=db_stats.get("top_matched_cves", []),
            events_last_hour=db_stats.get("events_last_hour", 0),
            events_today=db_stats.get("events_today", 0),
            events_this_week=db_stats.get("events_this_week", 0),
            activity_history=db_stats.get("activity_history", []),
        )

    def get_stats(
        self: "HoneypotSwarmCoordinator", honeypot_id: str | None = None
    ) -> HoneypotStats:
        """Get current statistics from in-memory data, optionally filtered by honeypot.

        NOTE: This method uses in-memory data which is lost on restart.
        For persistent stats, use get_historical_stats() instead.
        """
        # Filter events and sessions if needed
        events = self._events
        sessions = list(self._sessions.values())

        if honeypot_id:
            events = [e for e in events if e.honeypot_id == honeypot_id]
            sessions = [s for s in sessions if s.honeypot_id == honeypot_id]

        # Calculate dynamic stats
        total_events = len(events)
        unique_ips = len(set(e.source_ip for e in events))
        active_sessions = len([s for s in sessions if s.ended_at is None])

        # Calculate time-based stats
        now = datetime.now(timezone.utc)
        one_hour_ago = now - timedelta(hours=1)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = now - timedelta(days=7)

        events_last_hour = 0
        events_today = 0
        events_this_week = 0

        protocol_breakdown: Dict[str, int] = {}
        severity_breakdown: Dict[str, int] = {}
        category_breakdown: Dict[str, int] = {}
        cve_correlations = 0
        cve_counts: Dict[str, int] = {}
        ip_counts: Dict[str, int] = {}

        for e in events:
            # Time stats
            ts = e.timestamp
            if not ts:
                continue

            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            if ts >= one_hour_ago:
                events_last_hour += 1
            if ts >= today_start:
                events_today += 1
            if ts >= week_start:
                events_this_week += 1

            # Breakdowns
            proto = e.protocol.value
            protocol_breakdown[proto] = protocol_breakdown.get(proto, 0) + 1

            sev = e.severity.value
            severity_breakdown[sev] = severity_breakdown.get(sev, 0) + 1

            if e.category:
                cat = e.category.value
                category_breakdown[cat] = category_breakdown.get(cat, 0) + 1

            # CVEs
            if e.matched_cves:
                cve_correlations += 1
                for cve in e.matched_cves:
                    cve_counts[cve] = cve_counts.get(cve, 0) + 1

            # IPs
            ip_counts[e.source_ip] = ip_counts.get(e.source_ip, 0) + 1

        # Calculate bot breakdown
        bot_breakdown = {"bot": 0, "human": 0, "unknown": 0}
        for e in events:
            if e.is_bot is True:
                bot_breakdown["bot"] += 1
            elif e.is_bot is False:
                bot_breakdown["human"] += 1
            else:
                bot_breakdown["unknown"] += 1

        # Post-process sorted lists
        top_cves = sorted(cve_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        top_matched_cves = [{"cve_id": cve, "count": count} for cve, count in top_cves]

        top_ips = sorted(ip_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        top_attacker_ips = [{"ip": ip, "count": count} for ip, count in top_ips]

        # Return new stats object
        return HoneypotStats(
            total_connections=total_events,  # Approximation
            total_sessions=len(sessions),
            active_sessions=active_sessions,
            total_events=total_events,
            unique_ips=unique_ips,
            banned_ips=self._stats.banned_ips,  # Global stat
            top_attacker_ips=top_attacker_ips,
            protocol_breakdown=protocol_breakdown,
            severity_breakdown=severity_breakdown,
            bot_breakdown=bot_breakdown,
            category_breakdown=category_breakdown,
            cve_correlations=cve_correlations,
            top_matched_cves=top_matched_cves,
            events_last_hour=events_last_hour,
            events_today=events_today,
            events_this_week=events_this_week,
            activity_history=self._get_activity_history(events),
        )

    def _get_activity_history(
        self: "HoneypotSwarmCoordinator",
        events: List[Any],
    ) -> List[Dict[str, Any]]:
        """Get activity history for the last hour from provided events."""
        now = datetime.now(timezone.utc)
        history = {}

        # Initialize last 60 minutes with 0
        for i in range(60):
            t = now - timedelta(minutes=i)
            t_bucket = t.replace(second=0, microsecond=0)
            time_key = t_bucket.isoformat()
            history[time_key] = 0

        # Bucket events by minute
        for event in events:
            event_time = event.timestamp
            if not event_time:
                continue

            if event_time.tzinfo is None:
                event_time = event_time.astimezone(timezone.utc)
            else:
                event_time = event_time.astimezone(timezone.utc)

            time_diff = now - event_time
            if time_diff.total_seconds() <= 3600:
                event_bucket = event_time.replace(second=0, microsecond=0)
                time_key = event_bucket.isoformat()

                if time_key in history:
                    history[time_key] = history.get(time_key, 0) + 1

        # Sort by time
        sorted_history = sorted(
            [{"time": k, "count": v} for k, v in history.items()],
            key=lambda x: x["time"],
        )

        return sorted_history


__all__ = ["StatsMixin"]
