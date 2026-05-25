"""Discovery Enrichment Aggregator Methods.

Specialized aggregator methods for extracting enrichment data from
discovery analysis, MISP integration, threat intelligence, and
credential analysis.

Split from aggregator.py for modularity (Phase 3 enrichment methods).
"""

from typing import Dict, List, Optional

from core.observability.logging import get_logger

from .models import (
    AttackerCorrelation,
    CredentialAnalysis,
    DiscoveryEnrichment,
    MISPStatus,
    PayloadExcerpt,
    ThreatIntelSummary,
)

logger = get_logger(__name__)


class EnrichmentAggregatorMixin:
    """Mixin providing enrichment aggregation methods.

    This mixin is designed to be used with ReportDataAggregator,
    providing methods for discovery enrichment data collection.

    Requires:
        self.dao: HoneypotDAO instance
    """

    async def build_discovery_enrichment(
        self,
        honeypot_id: Optional[str],
    ) -> Optional[DiscoveryEnrichment]:
        """Build discovery enrichment data from latest analysis.

        Fetches the most recent discovery analysis result and extracts
        all analyzer metadata for comprehensive report enrichment.

        Args:
            honeypot_id: Optional honeypot filter

        Returns:
            DiscoveryEnrichment with all analyzer metadata, or None
        """
        try:
            from ..persistence import get_latest_discovery_result

            result = await get_latest_discovery_result(honeypot_id=honeypot_id)
            if not result:
                logger.debug("No discovery result found for enrichment")
                return None

            summary = result.summary or {}

            # Extract malware families from botnet profiles
            malware_families = []
            botnet_profiles = []
            if hasattr(result, "botnets") and result.botnets:
                for botnet in result.botnets:
                    profile = {
                        "cluster_id": botnet.cluster_id,
                        "size": botnet.size,
                        "severity": botnet.severity,
                        "coordination_score": botnet.attack_coordination_score,
                        "protocols": botnet.common_protocols,
                        "targets": botnet.common_targets[:5]
                        if botnet.common_targets
                        else [],
                    }
                    botnet_profiles.append(profile)

            # Extract from summary metadata
            behavioral_meta = summary.get("behavioral_meta", {})
            statistical_meta = summary.get("statistical_meta", {})
            cc_meta = summary.get("cc_meta", {})
            ml_meta = summary.get("ml_meta", {})
            zeroday_meta = summary.get("zeroday_meta", {})
            exploit_meta = summary.get("exploit_meta", {})
            threat_intel_meta = summary.get("intel_meta", {})

            # Extract malware families from threat intel
            if "malware_families" in threat_intel_meta:
                malware_families = threat_intel_meta.get("malware_families", [])

            return DiscoveryEnrichment(
                analysis_id=result.analysis_id,
                analyzed_at=result.analyzed_at,
                behavioral_meta=behavioral_meta,
                statistical_meta=statistical_meta,
                cc_meta=cc_meta,
                ml_meta=ml_meta,
                zeroday_meta=zeroday_meta,
                exploit_meta=exploit_meta,
                threat_intel_meta=threat_intel_meta,
                botnet_profiles=botnet_profiles,
                identified_malware_families=malware_families,
            )
        except Exception as e:
            logger.warning(f"Failed to build discovery enrichment: {e}")
            return None

    async def build_correlations(
        self,
        honeypot_id: Optional[str],
    ) -> List[AttackerCorrelation]:
        """Extract attacker correlations from discovery analysis.

        Identifies coordinated attack patterns based on timing, payload
        similarity, infrastructure, and cross-honeypot targeting.

        Args:
            honeypot_id: Optional honeypot filter

        Returns:
            List of AttackerCorrelation objects
        """
        try:
            from ..persistence import get_latest_discovery_result

            result = await get_latest_discovery_result(honeypot_id=honeypot_id)
            if not result:
                return []

            correlations = []
            summary = result.summary or {}

            # Extract correlations from behavioral meta
            behavioral = summary.get("behavioral_meta", {})

            # Timing correlations
            timing_clusters = behavioral.get("timing_clusters", [])
            for cluster in timing_clusters[:5]:
                if isinstance(cluster, dict) and cluster.get("ips"):
                    correlations.append(
                        AttackerCorrelation(
                            correlation_type="timing",
                            involved_ips=cluster.get("ips", [])[:10],
                            confidence=cluster.get("confidence", 0.7),
                            evidence=f"Synchronized attacks within {cluster.get('window_seconds', 60)}s window",
                        )
                    )

            # Payload similarity correlations
            payload_groups = behavioral.get("payload_similarity_groups", [])
            for group in payload_groups[:5]:
                if isinstance(group, dict) and group.get("ips"):
                    correlations.append(
                        AttackerCorrelation(
                            correlation_type="pattern",
                            involved_ips=group.get("ips", [])[:10],
                            confidence=group.get("similarity", 0.8),
                            evidence=f"Similar payloads ({group.get('similarity', 0) * 100:.0f}% match)",
                        )
                    )

            # Cross-honeypot targeting
            target_correlations = behavioral.get("target_correlations", [])
            for tc in target_correlations[:3]:
                if isinstance(tc, dict) and tc.get("ips"):
                    correlations.append(
                        AttackerCorrelation(
                            correlation_type="cross_honeypot",
                            involved_ips=tc.get("ips", [])[:10],
                            confidence=tc.get("confidence", 0.75),
                            evidence=f"Targeting {tc.get('honeypot_count', 2)}+ honeypots",
                        )
                    )

            # Infrastructure correlations (same subnet/ASN)
            infra_clusters = behavioral.get("infrastructure_clusters", [])
            for ic in infra_clusters[:3]:
                if isinstance(ic, dict) and ic.get("ips"):
                    correlations.append(
                        AttackerCorrelation(
                            correlation_type="infrastructure",
                            involved_ips=ic.get("ips", [])[:10],
                            confidence=ic.get("confidence", 0.65),
                            evidence=f"Shared infrastructure ({ic.get('subnet', 'unknown')})",
                        )
                    )

            return correlations[:15]  # Limit to top 15
        except Exception as e:
            logger.warning(f"Failed to build correlations: {e}")
            return []

    async def build_misp_status(self) -> MISPStatus:
        """Get MISP integration status.

        Returns:
            MISPStatus with connection and sync information
        """
        try:
            from ..discovery.threat_intel.misp_bridge import get_misp_bridge

            bridge = get_misp_bridge()
            if not bridge:
                return MISPStatus(enabled=False, status="not_configured")

            status = bridge.get_status()
            return MISPStatus(
                enabled=status.get("enabled", False),
                status=status.get("status", "unknown"),
                sync_percentage=status.get("sync_percentage", 0),
                exported_iocs_count=status.get("exported_count", 0),
            )
        except ImportError:
            return MISPStatus(enabled=False, status="not_configured")
        except Exception as e:
            logger.warning(f"Failed to get MISP status: {e}")
            return MISPStatus(enabled=False, status="error")

    async def build_threat_intel_summary(
        self,
        honeypot_id: Optional[str],
    ) -> ThreatIntelSummary:
        """Build threat intelligence summary from discovery analysis.

        Extracts YARA rules, command patterns, user agents, and IOC counts.

        Args:
            honeypot_id: Optional honeypot filter

        Returns:
            ThreatIntelSummary with extracted threat intel
        """
        try:
            from ..persistence import get_latest_discovery_result

            result = await get_latest_discovery_result(honeypot_id=honeypot_id)
            if not result:
                return ThreatIntelSummary()

            summary = result.summary or {}
            intel_meta = summary.get("intel_meta", {})

            # Extract YARA rules
            yara_rules = intel_meta.get("yara_rules", [])
            if isinstance(yara_rules, list):
                yara_rules = yara_rules[:5]  # Limit to 5 rules

            # Extract command patterns
            command_patterns = intel_meta.get("command_patterns", [])
            if isinstance(command_patterns, list):
                command_patterns = [str(p) for p in command_patterns[:10]]

            # Extract user agents
            user_agents = intel_meta.get("user_agents", [])
            if isinstance(user_agents, list):
                user_agents = [str(ua) for ua in user_agents[:10]]

            # Extract IOC counts
            ioc_counts = {
                "ips": intel_meta.get("malicious_ips_count", 0),
                "domains": intel_meta.get("malicious_domains_count", 0),
                "urls": intel_meta.get("malicious_urls_count", 0),
                "hashes": intel_meta.get("payload_hashes_count", 0),
            }

            return ThreatIntelSummary(
                yara_rules=yara_rules,
                yara_rules_count=len(yara_rules),
                command_patterns=command_patterns,
                user_agents=user_agents,
                ioc_counts=ioc_counts,
            )
        except Exception as e:
            logger.warning(f"Failed to build threat intel summary: {e}")
            return ThreatIntelSummary()

    async def build_payload_excerpts(
        self,
        honeypot_id: Optional[str],
        max_excerpts: int = 10,
    ) -> List[PayloadExcerpt]:
        """Build sanitized payload excerpts for report.

        Extracts diverse payload samples across attack categories,
        sanitized for safe inclusion in reports.

        Args:
            honeypot_id: Optional honeypot filter
            max_excerpts: Maximum excerpts to return

        Returns:
            List of PayloadExcerpt objects
        """
        try:
            from ..security import sanitize_for_llm

            # Get events with diverse categories
            events, _ = await self.dao.get_events(
                honeypot_id=honeypot_id,
                page_size=200,
                severity="critical,high,medium",
            )

            excerpts = []
            seen_categories = set()
            seen_patterns = set()

            for event in events:
                if len(excerpts) >= max_excerpts:
                    break

                raw_data = event.raw_data or ""
                category = (
                    event.category.value
                    if hasattr(event.category, "value")
                    else str(event.category) or "unknown"
                )

                # Skip if no payload or too short
                if not raw_data or len(raw_data.strip()) < 10:
                    continue

                # Ensure diversity - prefer different categories
                pattern_sig = f"{category}:{raw_data[:30]}"
                if pattern_sig in seen_patterns:
                    continue

                # Limit per category for diversity
                if list(seen_categories).count(category) >= 2:
                    continue

                seen_patterns.add(pattern_sig)
                seen_categories.add(category)

                # Sanitize payload
                sanitized = sanitize_for_llm(
                    raw_data[:500],
                    max_length=500,
                    replacement="[FILTERED]",
                )

                excerpts.append(
                    PayloadExcerpt(
                        category=category,
                        severity=event.severity.value
                        if hasattr(event.severity, "value")
                        else str(event.severity) or "medium",
                        excerpt=sanitized,
                        source_country=event.geo.country if event.geo else "Unknown",
                        protocol=event.protocol.value
                        if hasattr(event.protocol, "value")
                        else str(event.protocol) or "unknown",
                        ai_classification=event.ai_classification,
                        timestamp=event.timestamp,
                    )
                )

            return excerpts
        except Exception as e:
            logger.warning(f"Failed to build payload excerpts: {e}")
            return []

    async def build_credential_analysis(
        self,
        honeypot_id: Optional[str],
    ) -> CredentialAnalysis:
        """Build credential attack analysis.

        Analyzes brute force and credential stuffing patterns.
        NOTE: Actual passwords are NOT included - only patterns/counts.

        Args:
            honeypot_id: Optional honeypot filter

        Returns:
            CredentialAnalysis with attack statistics
        """
        try:
            # Get SSH/brute force events
            events, _ = await self.dao.get_events(
                honeypot_id=honeypot_id,
                page_size=1000,
                severity="critical,high,medium,low",
            )

            usernames: Dict[str, int] = {}
            passwords_masked: Dict[str, int] = {}
            pairs_count = 0

            for event in events:
                # Check for credential data
                # AttackEvent meta is handled differently if it's already an object?
                # Meta is inside event object. But wait, `event.meta`?
                # Checking events.py, AttackEvent has `username`, `password` fields directly!
                username = event.username
                password = event.password

                if username:
                    usernames[username] = usernames.get(username, 0) + 1

                if password:
                    # Mask password for security - only show length/pattern
                    masked = f"[{len(password)} chars]"
                    if password.isdigit():
                        masked = f"[numeric, {len(password)} digits]"
                    elif password.isalpha():
                        masked = f"[alpha, {len(password)} chars]"
                    passwords_masked[masked] = passwords_masked.get(masked, 0) + 1

                if username and password:
                    pairs_count += 1

            # Build top lists
            top_usernames = sorted(
                [{"username": u, "count": c} for u, c in usernames.items()],
                key=lambda x: x["count"],
                reverse=True,
            )[:10]

            top_passwords = sorted(
                [{"pattern": p, "count": c} for p, c in passwords_masked.items()],
                key=lambda x: x["count"],
                reverse=True,
            )[:10]

            return CredentialAnalysis(
                total_attempts=pairs_count,
                unique_usernames=len(usernames),
                unique_passwords=len(passwords_masked),
                top_usernames=top_usernames,
                top_passwords=top_passwords,
                credential_pairs_count=pairs_count,
            )
        except Exception as e:
            logger.warning(f"Failed to build credential analysis: {e}")
            return CredentialAnalysis()
