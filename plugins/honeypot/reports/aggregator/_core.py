"""Report Data Aggregator core class.

Responsible for fetching and aggregating data from the DAO and persistence layers
for the report generation process.

Core aggregation methods are in this file. Discovery enrichment methods
are provided via EnrichmentAggregatorMixin from aggregator_enrichment.py.
"""

from datetime import datetime, timezone
from typing import Dict, List, Optional

from core.observability.logging import get_logger

from ..models import (
    AttackTimelineEntry,
    BotnetSummary,
    GeoDistribution,
    IOCEntry,
    PentestSummaryItem,
    ThreatSummary,
    VulnerabilityItem,  # NEW
)
from ..aggregator_enrichment import EnrichmentAggregatorMixin
from ._sequential import SequentialAnalysisMixin
from ._payload import PayloadSamplesMixin

logger = get_logger(__name__)


class ReportDataAggregator(
    SequentialAnalysisMixin, PayloadSamplesMixin, EnrichmentAggregatorMixin
):
    """Aggregates data for security reports."""

    def __init__(self, dao):
        """Initialize aggregator.

        Args:
            dao: HoneypotDAO instance
        """
        self.dao = dao

    async def build_threat_summary(
        self,
        honeypot_id: Optional[str],
        time_start: datetime,
    ) -> ThreatSummary:
        """Build threat summary statistics."""
        try:
            # Get stats from DAO
            stats = await self.dao.get_stats(honeypot_id=honeypot_id)

            severity_breakdown = stats.get("severity_breakdown", {})
            category_breakdown = stats.get("category_breakdown", {})
            protocol_breakdown = stats.get("protocol_breakdown", {})
            bot_breakdown = stats.get("bot_breakdown", {})

            # Calculate bot traffic percentage
            total_events = stats.get("total_events", 0)
            bot_count = bot_breakdown.get("bot", 0)
            bot_percentage = (
                (bot_count / total_events * 100) if total_events > 0 else 0.0
            )

            # Get geo stats
            top_attackers = stats.get("top_attacker_ips", [])
            country_counts: Dict[str, int] = {}
            for attacker in top_attackers:
                cc = attacker.get("country_code")
                if cc:
                    country_counts[cc] = country_counts.get(cc, 0) + attacker.get(
                        "count", 0
                    )

            # Try to get discovery stats
            botnet_count = 0
            cc_count = 0
            try:
                from ..discovery import DiscoveryService

                discovery_service = DiscoveryService(dao=self.dao)
                botnets = await discovery_service.detect_botnets(
                    honeypot_id=honeypot_id
                )
                botnet_count = len(botnets)
                hubs = await discovery_service.find_hub_nodes(honeypot_id=honeypot_id)
                cc_count = len([h for h in hubs if h.is_confirmed_cc])
            except Exception:
                pass

            return ThreatSummary(
                total_events=total_events,
                unique_attackers=stats.get("unique_ips", 0),
                critical_events=severity_breakdown.get("critical", 0),
                high_events=severity_breakdown.get("high", 0),
                medium_events=severity_breakdown.get("medium", 0),
                low_events=severity_breakdown.get("low", 0),
                top_attack_categories=category_breakdown,
                top_attacking_countries=country_counts,
                top_protocols=protocol_breakdown,
                detected_botnets=botnet_count,
                potential_cc_servers=cc_count,
                cve_matches=stats.get("cve_correlations", 0),
                bot_traffic_percentage=round(bot_percentage, 1),
            )
        except Exception:
            # Return empty summary on error
            return ThreatSummary()

    async def build_attack_timeline(
        self,
        honeypot_id: Optional[str],
        time_start: datetime,
    ) -> List[AttackTimelineEntry]:
        """Build attack timeline from events."""
        try:
            events, _ = await self.dao.get_events(
                honeypot_id=honeypot_id,
                page_size=100,
                severity="critical,high",
            )

            timeline = []
            for event in events:
                timeline.append(
                    AttackTimelineEntry(
                        timestamp=event.timestamp
                        if isinstance(event.timestamp, datetime)
                        else datetime.fromisoformat(
                            event.timestamp
                            if event.timestamp
                            else datetime.now(timezone.utc).isoformat()
                        ),
                        event_type=event.event_type or "unknown",
                        source_ip=event.source_ip or "unknown",
                        severity=event.severity.value
                        if hasattr(event.severity, "value")
                        else str(event.severity) or "medium",
                        category=event.category.value
                        if hasattr(event.category, "value")
                        else str(event.category) or "unknown",
                        description=event.ai_classification
                        or (event.raw_data[:200] if event.raw_data else ""),
                        country_code=event.geo.country_code if event.geo else None,
                    )
                )

            return sorted(timeline, key=lambda x: x.timestamp, reverse=True)[:50]
        except Exception:
            return []

    async def build_geo_distribution(
        self,
        honeypot_id: Optional[str],
        time_start: datetime,
    ) -> List[GeoDistribution]:
        """Build geographic distribution of attacks."""
        try:
            # Get attackers with geo data
            attackers = await self.dao.get_attackers(honeypot_id=honeypot_id, limit=500)

            # Aggregate by country
            country_data: Dict[str, Dict] = {}
            for attacker in attackers.get("attackers", []):
                cc = attacker.get("country_code")
                if not cc:
                    continue

                if cc not in country_data:
                    country_data[cc] = {
                        "country_code": cc,
                        "country_name": attacker.get("country", cc),
                        "attack_count": 0,
                        "unique_ips": 0,
                        "attack_types": set(),
                    }

                country_data[cc]["attack_count"] += attacker.get("event_count", 0)
                country_data[cc]["unique_ips"] += 1
                for protocol in attacker.get("protocols", []):
                    country_data[cc]["attack_types"].add(protocol)

            # Convert to list
            result = []
            for data in country_data.values():
                result.append(
                    GeoDistribution(
                        country_code=data["country_code"],
                        country_name=data["country_name"],
                        attack_count=data["attack_count"],
                        unique_ips=data["unique_ips"],
                        primary_attack_types=list(data["attack_types"])[:5],
                    )
                )

            return sorted(result, key=lambda x: x.attack_count, reverse=True)[:20]
        except Exception:
            return []

    async def build_botnet_summary(
        self,
        honeypot_id: Optional[str],
    ) -> List[BotnetSummary]:
        """Build botnet activity summary."""
        try:
            from ..discovery import DiscoveryService

            service = DiscoveryService(dao=self.dao)
            botnets = await service.detect_botnets(honeypot_id=honeypot_id)

            result = []
            for botnet in botnets[:10]:
                result.append(
                    BotnetSummary(
                        cluster_id=botnet.cluster_id,
                        member_count=botnet.size,
                        severity=botnet.severity,
                        attack_coordination_score=botnet.attack_coordination_score,
                        suspected_cc_servers=list(botnet.associated_cc_ips or [])[:5],
                        common_protocols=botnet.common_protocols,
                        first_detected=datetime.fromisoformat(botnet.first_detected),
                        last_activity=datetime.fromisoformat(botnet.last_activity),
                    )
                )
            return result
        except Exception:
            return []

    async def build_pentest_summary(self) -> List[PentestSummaryItem]:
        """Build pentest results summary."""
        try:
            from ..persistence import pentest as pentest_db

            pentests = await pentest_db.get_pentest_results(limit=10)

            result = []
            for pt in pentests:
                vulns = pt.get("vulnerabilities", [])
                critical = len([v for v in vulns if v.get("severity") == "critical"])
                high = len([v for v in vulns if v.get("severity") == "high"])

                result.append(
                    PentestSummaryItem(
                        pentest_id=pt.get("pentest_id", ""),
                        playbook_name=pt.get("playbook_name", "Unknown"),
                        security_score=pt.get("security_score", 0),
                        total_tests=pt.get("total_tests", 0),
                        passed_tests=pt.get("passed_tests", 0),
                        failed_tests=pt.get("failed_tests", 0),
                        critical_findings=critical,
                        high_findings=high,
                        status=pt.get("status", "unknown"),
                        completed_at=datetime.fromisoformat(pt["completed_at"])
                        if pt.get("completed_at")
                        else None,
                    )
                )
            return result
        except Exception:
            return []

    async def build_vulnerability_list(self) -> List[VulnerabilityItem]:
        """Build list of discovered vulnerabilities."""
        try:
            from ..persistence import pentest as pentest_db

            pentests = await pentest_db.get_pentest_results(limit=5)

            vulns = []
            for pt in pentests:
                for v in pt.get("vulnerabilities", []):
                    vulns.append(
                        VulnerabilityItem(
                            finding_id=v.get("finding_id", ""),
                            name=v.get("name", "Unknown"),
                            severity=v.get("severity", "medium"),
                            category=v.get("category", "unknown"),
                            description=v.get("description", ""),
                            remediation=v.get("remediation", ""),
                            cve_references=v.get("cve_references", []),
                            confidence=v.get("confidence", 0),
                        )
                    )

            # Sort by severity and deduplicate
            severity_order = {
                "critical": 0,
                "high": 1,
                "medium": 2,
                "low": 3,
                "info": 4,
            }
            vulns.sort(key=lambda x: severity_order.get(x.severity, 5))
            return vulns[:20]
        except Exception:
            return []

    async def build_ioc_list(
        self,
        honeypot_id: Optional[str],
        time_start: datetime,
    ) -> List[IOCEntry]:
        """Build Indicators of Compromise list."""
        try:
            # Get top attackers as IP IOCs
            attackers = await self.dao.get_attackers(honeypot_id=honeypot_id, limit=100)

            iocs = []
            for attacker in attackers.get("attackers", []):
                # Only include attackers with significant activity
                if attacker.get("event_count", 0) < 3:
                    continue

                severity = attacker.get("max_severity", "medium")
                threat_level = (
                    "critical"
                    if severity == "critical"
                    else "high"
                    if severity == "high"
                    else "medium"
                )

                iocs.append(
                    IOCEntry(
                        ioc_type="ip",
                        value=attacker.get("ip", ""),
                        first_seen=datetime.fromisoformat(attacker["first_seen"])
                        if attacker.get("first_seen")
                        else datetime.now(timezone.utc),
                        last_seen=datetime.fromisoformat(attacker["last_seen"])
                        if attacker.get("last_seen")
                        else datetime.now(timezone.utc),
                        confidence=min(
                            0.5 + (attacker.get("event_count", 0) * 0.05), 0.95
                        ),
                        threat_level=threat_level,
                    )
                )

            return sorted(iocs, key=lambda x: x.confidence, reverse=True)[:50]
        except Exception:
            return []

    async def get_enhanced_honeypot_context(
        self,
        honeypot_id: str,
    ) -> Optional[Dict]:
        """Get comprehensive honeypot context for report generation.

        Args:
            honeypot_id: Honeypot identifier

        Returns:
            Enhanced honeypot context dict or None
        """
        try:
            from ..honeypot_loader import get_registry

            registry = get_registry()
            definition = registry.get(honeypot_id)

            if not definition:
                return None

            # Build enhanced context
            context = {
                "id": definition.id,
                "name": definition.name,
                "description": definition.description,
                "protocol": definition.protocol.value,
                "port": definition.port,
                "tags": definition.tags,
                "category": definition.tags[0] if definition.tags else "General",
                "handler_type": definition.resolve_handler_type(),
                "enabled": definition.enabled,
                "priority": definition.priority,
            }

            # Add protocol-specific config details
            if definition.protocol.value == "http" and definition.http_config:
                context["emulated_app"] = definition.http_config.emulated_app
                context["server_header"] = definition.http_config.server_header
            elif definition.protocol.value == "ssh" and definition.ssh_config:
                context["ssh_version"] = definition.ssh_config.version
                context["shell_persona"] = definition.ssh_config.shell_persona
            elif definition.protocol.value == "tcp" and definition.tcp_config:
                context["protocol_name"] = definition.tcp_config.protocol_name

            # Add detection config
            context["detection"] = {
                "sql_injection": definition.detection.sql_injection,
                "command_injection": definition.detection.command_injection,
                "path_traversal": definition.detection.path_traversal,
                "xss": definition.detection.xss,
            }

            return context
        except Exception as e:
            logger.warning(f"Failed to get enhanced honeypot context: {e}")
            return None
