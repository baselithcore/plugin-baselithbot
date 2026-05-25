"""Core Threat Intel Generator."""

from __future__ import annotations

import hashlib
import json
from core.observability.logging import get_logger
import uuid
from collections import Counter, defaultdict
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Set, Tuple, Callable

from ...models import AttackEvent
from ..models import NetworkAnomaly
from .constants import EXCLUDE_DOMAINS, EXCLUDE_IPS
from .extractors import extract_domains, extract_urls
from .models import IOCBundle
from .scoring import calculate_confidence, determine_severity
from .utils import (
    fingerprint_payload,
    get_payload,
    hash_payload,
    normalize_command,
)
from .yara import create_yara_rule, find_common_strings
from ..dns_anomalies import DNSAnomaliesEngine

if TYPE_CHECKING:
    from ...scraper import ThreatIntelEnricher

logger = get_logger(__name__)


class ThreatIntelGenerator:
    """Generates threat intelligence from attack data."""

    def __init__(
        self,
        min_occurrences: int = 2,
        severity_threshold: str = "medium",
        enricher: Optional[ThreatIntelEnricher] = None,
        misp_status_provider: Optional[Callable[[], Dict[str, Any]]] = None,
    ):
        """Initialize threat intel generator.

        Args:
            min_occurrences: Minimum times an IOC must appear
            severity_threshold: Minimum severity to include
            enricher: Optional OSINT enricher for external data
            misp_status_provider: Optional callable that returns MISP bridge status
        """
        self.min_occurrences = min_occurrences
        self.severity_threshold = severity_threshold
        self._enricher = enricher
        self._misp_status_provider = misp_status_provider
        self._current_bundle: Optional[IOCBundle] = None
        self.dns_engine = DNSAnomaliesEngine()

    def generate_intel(
        self, events: List[AttackEvent]
    ) -> Tuple[List[NetworkAnomaly], Dict[str, Any]]:
        """Generate threat intelligence from events.

        Args:
            events: Attack events to analyze

        Returns:
            Tuple of (anomalies, metadata)
        """
        if not events:
            return [], {}

        anomalies: List[NetworkAnomaly] = []

        # Extract IOCs
        bundle = self._extract_iocs(events)
        self._current_bundle = bundle

        # Generate YARA rules for novel payloads
        yara_rules = self._generate_yara_rules(events)
        bundle.yara_rules = yara_rules

        # Enrich with external OSINT if enricher is available
        # Note: This is called synchronously; for async use enrich_async()
        if self._enricher:
            try:
                import asyncio

                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # Cannot await in sync context, skip enrichment
                    logger.debug("Skipping OSINT enrichment in sync context")
                else:
                    enrichment = loop.run_until_complete(
                        self._enricher.enrich(
                            ips=bundle.malicious_ips[:20],
                            domains=bundle.malicious_domains[:10],
                            urls=bundle.malicious_urls[:10],
                        )
                    )
                    bundle.osint_enrichment = enrichment.to_dict()
                    logger.info(
                        f"OSINT enrichment: {len(enrichment.high_risk_ips)} high-risk IPs, "
                        f"{len(enrichment.malicious_urls)} malicious URLs"
                    )
            except Exception as e:
                logger.warning(f"OSINT enrichment failed: {e}")

        # Create anomalies for significant intel
        if bundle.malicious_ips or bundle.payload_hashes:
            anomaly = NetworkAnomaly(
                anomaly_id=f"intel_{bundle.id[:8]}",
                anomaly_type="threat_intel_generated",
                severity="info",
                confidence=bundle.confidence,
                source_ips=bundle.malicious_ips[:5],
                description=(
                    f"Generated threat intel: {len(bundle.malicious_ips)} IPs, "
                    f"{len(bundle.payload_hashes)} hashes, {len(yara_rules)} YARA rules"
                ),
                details=bundle.to_dict(),
            )
            anomalies.append(anomaly)

        # Detect DNS Anomalies (DGA/Fast Flux)
        dns_anomalies = self._detect_dns_anomalies(events)
        anomalies.extend(dns_anomalies)

        logger.info(
            f"Threat intel: {len(bundle.malicious_ips)} IPs, "
            f"{len(bundle.malicious_domains)} domains, "
            f"{len(bundle.payload_hashes)} hashes"
        )

        meta = self._build_metadata(bundle)
        return anomalies, meta

    def _extract_iocs(self, events: List[AttackEvent]) -> IOCBundle:
        """Extract IOCs from events."""
        bundle = IOCBundle(
            id=str(uuid.uuid4()),
            generated_at=datetime.now(),
        )

        ip_counts: Counter = Counter()
        domain_counts: Counter = Counter()
        url_counts: Counter = Counter()
        payload_hashes: Dict[str, Dict[str, Any]] = {}
        command_patterns: Set[str] = set()
        user_agents: Set[str] = set()
        attack_types: Set[str] = set()

        for event in events:
            # Count source IPs
            if event.source_ip and event.source_ip not in EXCLUDE_IPS:
                ip_counts[event.source_ip] += 1

            # Extract domains from payloads
            payload = get_payload(event)
            if payload:
                # Extract domains
                domains = extract_domains(payload)
                for domain in domains:
                    if domain.lower() not in EXCLUDE_DOMAINS:
                        domain_counts[domain] += 1

                # Extract URLs
                urls = extract_urls(payload)
                for url in urls:
                    url_counts[url] += 1

                # Calculate payload hash
                p_hash = hash_payload(payload)
                if p_hash not in payload_hashes:
                    payload_hashes[p_hash] = {
                        "sha256": hashlib.sha256(payload.encode()).hexdigest(),
                        "md5": hashlib.md5(
                            payload.encode(), usedforsecurity=False
                        ).hexdigest(),
                        "size": len(payload),
                        "preview": payload[:100],
                    }

            # Extract commands
            if event.command:
                cmd_pattern = normalize_command(event.command)
                command_patterns.add(cmd_pattern)

            # Extract user agents
            if hasattr(event, "http_headers") and event.http_headers:
                ua = event.http_headers.get("User-Agent", "")
                if ua and len(ua) > 10:
                    user_agents.add(ua)

            # Track attack types
            if event.category:
                cat = (
                    event.category.value
                    if hasattr(event.category, "value")
                    else str(event.category)
                )
                attack_types.add(cat)

        # Filter by minimum occurrences
        bundle.malicious_ips = [
            ip
            for ip, count in ip_counts.most_common(100)
            if count >= self.min_occurrences
        ]

        bundle.malicious_domains = [
            domain
            for domain, count in domain_counts.most_common(50)
            if count >= self.min_occurrences
        ]

        bundle.malicious_urls = [
            url
            for url, count in url_counts.most_common(50)
            if count >= self.min_occurrences
        ]

        bundle.payload_hashes = list(payload_hashes.values())[:100]
        bundle.command_patterns = list(command_patterns)[:50]
        bundle.user_agents = list(user_agents)[:20]
        bundle.attack_types = list(attack_types)

        # Calculate overall confidence
        bundle.confidence = calculate_confidence(
            len(bundle.malicious_ips),
            len(bundle.payload_hashes),
            len(events),
        )

        # Determine severity
        bundle.severity = determine_severity(attack_types)

        return bundle

    def _generate_yara_rules(self, events: List[AttackEvent]) -> List[str]:
        """Generate YARA rules from attack payloads."""
        rules = []

        # Group payloads by similarity
        payload_groups: Dict[str, List[str]] = defaultdict(list)
        for event in events:
            payload = get_payload(event)
            if payload and len(payload) >= 20:
                fingerprint = fingerprint_payload(payload)
                payload_groups[fingerprint].append(payload)

        # Generate rules for significant groups
        rule_count = 0
        for fingerprint, payloads in payload_groups.items():
            if len(payloads) < self.min_occurrences:
                continue
            if rule_count >= 10:  # Limit rules
                break

            # Find common strings
            common_strings = find_common_strings(payloads)
            if not common_strings:
                continue

            # Generate YARA rule
            rule = create_yara_rule(
                name=f"Honeypot_Payload_{fingerprint[:8]}",
                strings=common_strings,
                description=f"Auto-generated from {len(payloads)} similar payloads",
            )
            rules.append(rule)
            rule_count += 1

        return rules

    def _detect_dns_anomalies(self, events: List[AttackEvent]) -> List[NetworkAnomaly]:
        """Detect DNS anomalies like DGA and Fast Flux."""
        domain_to_ips = defaultdict(set)
        total_payloads_checked = 0
        total_domains_found = 0

        # 1. Collect domains and associated IPs
        for event in events:
            payload = get_payload(event)
            if payload:
                total_payloads_checked += 1
                domains = extract_domains(payload)
                total_domains_found += len(domains)

                for domain in domains:
                    if domain.lower() not in EXCLUDE_DOMAINS:
                        if event.source_ip:
                            domain_to_ips[domain].add(event.source_ip)

        logger.info(
            f"DNS Anomaly Detection: Checked {total_payloads_checked} payloads, "
            f"found {total_domains_found} raw domains, "
            f"filtered to {len(domain_to_ips)} unique domains for analysis"
        )

        anomalies = []

        # 2. Analyze each unique domain
        for domain, ips in domain_to_ips.items():
            analysis = self.dns_engine.analyze_query(
                domain=domain,
                # In a real scenario we'd have resolved IPs, TTLs, etc.
                # Here we just analyze the domain string structure (DGA entropy)
                # and NXDOMAIN bursts if we had that data (we don't easily here)
            )

            if analysis.is_dga:
                logger.info(f"DGA detected: {domain} (entropy: {analysis.entropy:.2f})")
                anomalies.append(
                    NetworkAnomaly(
                        anomaly_id=f"dga_{hashlib.md5(domain.encode(), usedforsecurity=False).hexdigest()[:8]}",
                        anomaly_type="dga_domain_detection",
                        involved_ips=list(ips)[:10],
                        description=f"DGA pattern detected in domain: {domain}",
                        severity="high",
                        confidence=analysis.confidence,
                        metadata={
                            "domain": domain,
                            "entropy": analysis.entropy,
                            "tags": analysis.tags,
                            # Sinkhole tracking metadata
                            "sinkhole_status": "paused",  # Default: not yet sinkholed
                            "sinkhole_candidate": True,  # High-confidence DGAs are candidates
                            "request_count": 0,
                            "last_activity": "",
                        },
                    )
                )

            # If we had IP resolution data, we'd check analysis.is_fast_flux

        logger.info(f"DNS Anomaly Detection: Generated {len(anomalies)} DGA anomalies")
        return anomalies

    def _build_metadata(self, bundle: IOCBundle) -> Dict[str, Any]:
        """Build metadata summary."""
        metadata = {
            "ioc_count": {
                "ips": len(bundle.malicious_ips),
                "domains": len(bundle.malicious_domains),
                "urls": len(bundle.malicious_urls),
                "hashes": len(bundle.payload_hashes),
            },
            "yara_rules_generated": len(bundle.yara_rules),
            "confidence": round(bundle.confidence, 2),
            "severity": bundle.severity,
            "attack_types": bundle.attack_types,
        }

        # Include MISP status if provider is available
        if self._misp_status_provider:
            status = self._misp_status_provider()
            metadata["misp_status"] = status
            # For backward compatibility or specific frontend fields
            metadata["misp_sync_status"] = status.get("sync_percentage", 0)

        return metadata

    def get_current_bundle(self) -> Optional[IOCBundle]:
        """Get the current IOC bundle."""
        return self._current_bundle

    def export_stix(self) -> Optional[Dict[str, Any]]:
        """Export current intel as STIX 2.1."""
        if self._current_bundle:
            return self._current_bundle.to_stix()
        return None

    def export_json(self) -> Optional[str]:
        """Export current intel as JSON."""
        if self._current_bundle:
            return json.dumps(self._current_bundle.to_dict(), indent=2)
        return None
