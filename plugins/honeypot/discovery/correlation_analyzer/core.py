"""Correlation Analyzer Core.

Implements advanced attacker correlation detection using cybersecurity best practices:
- Temporal correlation (MITRE ATT&CK timing analysis)
- TTP (Tactics, Techniques, Procedures) matching
- IOC (Indicators of Compromise) correlation
- Infrastructure analysis

References:
- MITRE ATT&CK Framework: https://attack.mitre.org/
- NIST SP 800-61r2: Computer Security Incident Handling Guide
"""

import ipaddress
from core.observability.logging import get_logger
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple

from plugins.honeypot.models import AttackEvent

from .models import (
    AttackerCorrelation,
    CorrelationConfig,
    CorrelationType,
    DEFAULT_CORRELATION_CONFIG,
)

logger = get_logger(__name__)


class CorrelationAnalyzer:
    """Analyzes attacker correlations for botnet and coordinated attack detection.

    Uses multiple correlation techniques based on threat intelligence best practices.
    """

    def __init__(self, config: Optional[CorrelationConfig] = None):
        """Initialize correlation analyzer.

        Args:
            config: Correlation configuration, uses defaults if not provided.
        """
        self.config = config or DEFAULT_CORRELATION_CONFIG
        self._correlations: List[AttackerCorrelation] = []
        self._ip_honeypot_map: Dict[str, Set[str]] = defaultdict(set)
        self._ip_events_map: Dict[str, List[AttackEvent]] = defaultdict(list)
        self._honeypot_timeline: Dict[str, List[Tuple[datetime, str]]] = defaultdict(
            list
        )

    def analyze(
        self, events: List[AttackEvent]
    ) -> Tuple[List[AttackerCorrelation], Dict[str, Any]]:
        """Run complete correlation analysis on events.

        Args:
            events: List of attack events to analyze.

        Returns:
            Tuple of (correlations list, metadata dict).
        """
        self._reset()
        self._index_events(events)

        # Run correlation detectors
        timing_corr = self._detect_timing_correlations()
        pattern_corr = self._detect_pattern_correlations()
        cross_hp_corr = self._detect_cross_honeypot_correlations()
        infra_corr = self._detect_infrastructure_correlations()

        # Combine all correlations
        all_correlations = timing_corr + pattern_corr + cross_hp_corr + infra_corr

        # Deduplicate by IP pair
        unique_correlations = self._deduplicate_correlations(all_correlations)

        self._correlations = unique_correlations

        metadata = {
            "total_correlations": len(unique_correlations),
            "timing_correlations": len(timing_corr),
            "pattern_correlations": len(pattern_corr),
            "cross_honeypot_correlations": len(cross_hp_corr),
            "infrastructure_correlations": len(infra_corr),
            "unique_ips_analyzed": len(self._ip_events_map),
            "honeypots_involved": len(self._honeypot_timeline),
        }

        logger.info(
            f"Correlation analysis complete: {len(unique_correlations)} correlations "
            f"({len(timing_corr)} timing, {len(pattern_corr)} pattern, "
            f"{len(cross_hp_corr)} cross-HP, {len(infra_corr)} infra)"
        )

        return unique_correlations, metadata

    def get_ip_correlation_count(self) -> Dict[str, int]:
        """Get count of correlations per IP for threat scoring.

        Returns:
            Dict mapping IP to number of correlations.
        """
        counts: Dict[str, int] = defaultdict(int)
        for corr in self._correlations:
            counts[corr.source_ip] += 1
            counts[corr.target_ip] += 1
        return dict(counts)

    def get_multi_honeypot_ips(self) -> Dict[str, Set[str]]:
        """Get IPs that targeted multiple honeypots.

        Returns:
            Dict mapping IP to set of honeypot IDs.
        """
        return {
            ip: honeypots
            for ip, honeypots in self._ip_honeypot_map.items()
            if len(honeypots) >= self.config.min_cross_honeypot_count
        }

    def _reset(self) -> None:
        """Reset internal state for new analysis."""
        self._correlations = []
        self._ip_honeypot_map = defaultdict(set)
        self._ip_events_map = defaultdict(list)
        self._honeypot_timeline = defaultdict(list)

    def _index_events(self, events: List[AttackEvent]) -> None:
        """Build indexes for efficient correlation detection.

        Args:
            events: Events to index.
        """
        for event in events:
            ip = event.source_ip
            honeypot_id = event.honeypot_id

            self._ip_honeypot_map[ip].add(honeypot_id)
            self._ip_events_map[ip].append(event)
            self._honeypot_timeline[honeypot_id].append((event.timestamp, ip))

        # Sort timelines chronologically
        for honeypot_id in self._honeypot_timeline:
            self._honeypot_timeline[honeypot_id].sort(key=lambda x: x[0])

    def _detect_timing_correlations(self) -> List[AttackerCorrelation]:
        """Detect attackers hitting same honeypot within time window.

        This is a key indicator of coordinated/botnet behavior (MITRE T1071).

        Returns:
            List of timing-based correlations.
        """
        correlations: List[AttackerCorrelation] = []
        seen_pairs: Set[Tuple[str, str]] = set()

        for honeypot_id, timeline in self._honeypot_timeline.items():
            if len(timeline) < 2:
                continue

            # Sliding window approach for O(n) complexity
            for i, (ts1, ip1) in enumerate(timeline):
                for j in range(i + 1, len(timeline)):
                    ts2, ip2 = timeline[j]

                    if ip1 == ip2:
                        continue

                    # Convert to seconds
                    delta = abs((ts2 - ts1).total_seconds())

                    if delta > self.config.timing_window_seconds:
                        break  # No need to check further (sorted list)

                    # Create pair key (sorted for dedup)
                    pair = tuple(sorted([ip1, ip2]))
                    if pair in seen_pairs:
                        continue
                    seen_pairs.add(pair)

                    # Calculate confidence based on time proximity
                    # Closer attacks = higher confidence
                    time_factor = 1.0 - (delta / self.config.timing_window_seconds)
                    confidence = max(
                        self.config.min_timing_confidence, time_factor * 0.8 + 0.2
                    )

                    correlations.append(
                        AttackerCorrelation(
                            correlation_id=str(uuid.uuid4()),
                            source_ip=pair[0],
                            target_ip=pair[1],
                            correlation_type=CorrelationType.TIMING,
                            confidence=confidence,
                            strength=time_factor,
                            shared_honeypots=[honeypot_id],
                            time_delta_seconds=delta,
                            detected_at=datetime.now(timezone.utc),
                            metadata={"honeypot": honeypot_id, "delta_seconds": delta},
                        )
                    )

        return correlations

    def _detect_pattern_correlations(self) -> List[AttackerCorrelation]:
        """Detect attackers using similar commands/payloads (TTP matching).

        Based on MITRE ATT&CK technique correlation principles.

        Returns:
            List of pattern-based correlations.
        """
        correlations: List[AttackerCorrelation] = []

        # Build command fingerprints per IP
        ip_commands: Dict[str, Set[str]] = {}
        for ip, events in self._ip_events_map.items():
            commands = set()
            for event in events:
                if event.command:
                    # Normalize command (lowercase, strip args for basic matching)
                    normalized = self._normalize_command(event.command)
                    commands.add(normalized)
            if commands:
                ip_commands[ip] = commands

        # Compare IPs pairwise (limit to prevent O(n²) explosion)
        ips = list(ip_commands.keys())
        if len(ips) > 100:
            # Focus on IPs with more commands (more likely bots)
            ips = sorted(ips, key=lambda x: len(ip_commands[x]), reverse=True)[:100]

        seen_pairs: Set[Tuple[str, str]] = set()
        for i, ip1 in enumerate(ips):
            for ip2 in ips[i + 1 :]:
                pair = tuple(sorted([ip1, ip2]))
                if pair in seen_pairs:
                    continue

                # Calculate Jaccard similarity
                cmds1 = ip_commands[ip1]
                cmds2 = ip_commands[ip2]
                shared = cmds1 & cmds2

                if len(shared) < self.config.min_shared_commands:
                    continue

                union = cmds1 | cmds2
                similarity = len(shared) / len(union) if union else 0

                if similarity < self.config.min_pattern_similarity:
                    continue

                seen_pairs.add(pair)

                correlations.append(
                    AttackerCorrelation(
                        correlation_id=str(uuid.uuid4()),
                        source_ip=pair[0],
                        target_ip=pair[1],
                        correlation_type=CorrelationType.PATTERN,
                        confidence=similarity,
                        strength=similarity,
                        pattern_similarity=similarity,
                        shared_commands=list(shared)[:10],  # Limit for payload
                        detected_at=datetime.now(timezone.utc),
                        metadata={
                            "jaccard_similarity": similarity,
                            "shared_command_count": len(shared),
                        },
                    )
                )

        return correlations

    def _detect_cross_honeypot_correlations(self) -> List[AttackerCorrelation]:
        """Detect IPs targeting multiple honeypots (reconnaissance behavior).

        Multi-honeypot targeting indicates systematic scanning/probing.

        Returns:
            List of cross-honeypot correlations.
        """
        correlations: List[AttackerCorrelation] = []
        multi_hp_ips = self.get_multi_honeypot_ips()

        if len(multi_hp_ips) < 2:
            return correlations

        # Find IPs that share multiple target honeypots
        ips = list(multi_hp_ips.keys())
        seen_pairs: Set[Tuple[str, str]] = set()

        for i, ip1 in enumerate(ips):
            for ip2 in ips[i + 1 :]:
                pair = tuple(sorted([ip1, ip2]))
                if pair in seen_pairs:
                    continue

                shared_honeypots = multi_hp_ips[ip1] & multi_hp_ips[ip2]

                if len(shared_honeypots) < self.config.min_cross_honeypot_count:
                    continue

                seen_pairs.add(pair)

                # Higher confidence for more shared targets
                confidence = min(1.0, len(shared_honeypots) / 4)  # Cap at 4 honeypots

                correlations.append(
                    AttackerCorrelation(
                        correlation_id=str(uuid.uuid4()),
                        source_ip=pair[0],
                        target_ip=pair[1],
                        correlation_type=CorrelationType.CROSS_HONEYPOT,
                        confidence=confidence,
                        strength=confidence,
                        shared_honeypots=list(shared_honeypots),
                        detected_at=datetime.now(timezone.utc),
                        metadata={"shared_honeypot_count": len(shared_honeypots)},
                    )
                )

        return correlations

    def _detect_infrastructure_correlations(self) -> List[AttackerCorrelation]:
        """Detect IPs from same infrastructure (subnet/ASN).

        Same-subnet attackers may be part of compromised infrastructure.

        Returns:
            List of infrastructure correlations.
        """
        correlations: List[AttackerCorrelation] = []

        # Group IPs by /24 subnet
        subnet_ips: Dict[str, List[str]] = defaultdict(list)
        for ip in self._ip_events_map.keys():
            try:
                ip_obj = ipaddress.ip_address(ip)
                if ip_obj.version == 4:
                    # Get /24 subnet
                    network = ipaddress.ip_network(
                        f"{ip}/{self.config.same_subnet_mask}", strict=False
                    )
                    subnet_ips[str(network)].append(ip)
            except ValueError:
                continue

        # Find subnets with multiple attacker IPs
        for subnet, ips in subnet_ips.items():
            if len(ips) < 2:
                continue

            seen_pairs: Set[Tuple[str, str]] = set()
            for i, ip1 in enumerate(ips):
                for ip2 in ips[i + 1 :]:
                    pair = tuple(sorted([ip1, ip2]))
                    if pair in seen_pairs:
                        continue
                    seen_pairs.add(pair)

                    correlations.append(
                        AttackerCorrelation(
                            correlation_id=str(uuid.uuid4()),
                            source_ip=pair[0],
                            target_ip=pair[1],
                            correlation_type=CorrelationType.INFRASTRUCTURE,
                            confidence=0.5,  # Moderate - same subnet doesn't always mean related
                            strength=0.5,
                            detected_at=datetime.now(timezone.utc),
                            metadata={"subnet": subnet, "ips_in_subnet": len(ips)},
                        )
                    )

        return correlations

    def _normalize_command(self, command: str) -> str:
        """Normalize command for pattern matching.

        Args:
            command: Raw command string.

        Returns:
            Normalized command fingerprint.
        """
        # Basic normalization: lowercase, first 2 words
        cmd = command.lower().strip()
        parts = cmd.split()[:2]
        return " ".join(parts)

    def _deduplicate_correlations(
        self, correlations: List[AttackerCorrelation]
    ) -> List[AttackerCorrelation]:
        """Deduplicate correlations, keeping highest confidence per pair.

        Args:
            correlations: Raw correlation list.

        Returns:
            Deduplicated correlations.
        """
        best: Dict[Tuple[str, str], AttackerCorrelation] = {}

        for corr in correlations:
            pair = tuple(sorted([corr.source_ip, corr.target_ip]))

            if pair not in best or corr.confidence > best[pair].confidence:
                best[pair] = corr

        return list(best.values())
