"""Core Zero-Day Detector."""

from core.observability.logging import get_logger
import uuid
from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from ...models import AttackEvent
from ..models import NetworkAnomaly
from .chains import detect_novel_chains, detect_protocol_anomalies
from .indicators import extract_indicators
from .models import ZeroDayCandidate
from .scoring import calculate_confidence, calculate_novelty_score, estimate_severity
from .signatures import check_cve_matches, detect_attack_vector
from .utils import create_payload_fingerprint, extract_payload, parse_timestamp

logger = get_logger(__name__)


class ZeroDayDetector:
    """Detects potential zero-day exploits from attack patterns."""

    def __init__(
        self,
        novelty_threshold: float = 0.6,
        min_occurrences: int = 2,
        known_cve_patterns: Optional[Dict[str, List[str]]] = None,
    ):
        """Initialize zero-day detector.

        Args:
            novelty_threshold: Minimum novelty score to flag as candidate
            min_occurrences: Minimum times a pattern must appear
            known_cve_patterns: Additional CVE patterns to check against
        """
        self.novelty_threshold = novelty_threshold
        self.min_occurrences = min_occurrences
        self.known_cve_patterns = known_cve_patterns or {}
        self._candidates: List[ZeroDayCandidate] = []
        self._payload_cache: Dict[str, Dict[str, Any]] = {}

    def analyze_all(
        self, events: List[AttackEvent]
    ) -> Tuple[List[NetworkAnomaly], Dict[str, Any]]:
        """Analyze events for potential zero-day exploits.

        Args:
            events: Attack events to analyze

        Returns:
            Tuple of (anomalies, metadata)
        """
        if not events:
            return [], {}

        self._candidates = []
        anomalies: List[NetworkAnomaly] = []

        # Extract and analyze payloads
        payload_groups = self._group_similar_payloads(events)

        # Analyze each payload group
        for payload_hash, group_data in payload_groups.items():
            candidate = self._analyze_payload_group(payload_hash, group_data)
            if candidate and candidate.novelty_score >= self.novelty_threshold:
                self._candidates.append(candidate)

                # Create anomaly for high-confidence candidates
                if candidate.confidence >= 0.5:
                    # Build a rich description with actionable context
                    vector_desc = (
                        candidate.attack_vector
                        if candidate.attack_vector != "unknown"
                        else "novel pattern"
                    )

                    # Include payload preview (sanitized for display)
                    payload_snippet = (
                        candidate.payload_preview[:100].replace("\n", " ").strip()
                    )
                    if len(candidate.payload_preview) > 100:
                        payload_snippet += "..."

                    # Build description with context
                    desc_parts = [
                        f"Potential zero-day exploit: {vector_desc}",
                        f"• Novelty: {candidate.novelty_score:.0%}",
                        f"• Sources: {len(candidate.source_ips)} unique IPs",
                        f"• Targets: {', '.join(candidate.target_services[:3])}",
                        f"• Occurrences: {candidate.occurrence_count}",
                    ]

                    # Add matched CVEs if relevant
                    if candidate.matched_cves:
                        desc_parts.append(
                            f"• Related CVEs: {', '.join(candidate.matched_cves[:3])}"
                        )

                    # Add key indicators
                    if candidate.indicators:
                        indicator_keys = list(candidate.indicators.keys())[:3]
                        if indicator_keys:
                            desc_parts.append(
                                f"• Indicators: {', '.join(indicator_keys)}"
                            )

                    # Create anomaly with enriched data
                    anomaly = NetworkAnomaly(
                        anomaly_id=f"zeroday_{candidate.id[:8]}",
                        anomaly_type="potential_zeroday",
                        severity=candidate.severity_estimate,
                        confidence=candidate.confidence,
                        involved_ips=candidate.source_ips[:10],
                        description="\n".join(desc_parts),
                        metadata={
                            "candidate_id": candidate.id,
                            "attack_vector": candidate.attack_vector,
                            "novelty_score": round(candidate.novelty_score, 3),
                            "payload_preview": payload_snippet,
                            "payload_hash": candidate.payload_hash,
                            "target_services": candidate.target_services,
                            "occurrence_count": candidate.occurrence_count,
                            "matched_cves": candidate.matched_cves,
                            "first_seen": candidate.first_seen.isoformat(),
                            "last_seen": candidate.last_seen.isoformat(),
                            "indicators": candidate.indicators,
                        },
                    )
                    anomalies.append(anomaly)

        # Detect novel attack chains
        chain_anomalies = detect_novel_chains(events)
        anomalies.extend(chain_anomalies)

        # Detect unknown protocol abuse
        protocol_anomalies = detect_protocol_anomalies(events)
        anomalies.extend(protocol_anomalies)

        logger.info(
            f"Zero-day analysis: {len(self._candidates)} candidates, "
            f"{len(anomalies)} anomalies"
        )

        meta = self._build_metadata()
        return anomalies, meta

    def _group_similar_payloads(
        self, events: List[AttackEvent]
    ) -> Dict[str, Dict[str, Any]]:
        """Group events by similar payloads."""
        groups: Dict[str, Dict[str, Any]] = defaultdict(
            lambda: {
                "payloads": [],
                "events": [],
                "ips": set(),
                "services": set(),
                "first_seen": None,
                "last_seen": None,
            }
        )

        for event in events:
            payload = extract_payload(event)
            if not payload or len(payload) < 10:
                continue

            # Create fingerprint (normalized hash)
            fingerprint = create_payload_fingerprint(payload)

            group = groups[fingerprint]
            group["payloads"].append(payload)
            group["events"].append(event)
            group["ips"].add(event.source_ip)

            service = f"{event.protocol.value}:{event.honeypot_id or 'unknown'}"
            group["services"].add(service)

            ts = parse_timestamp(event.timestamp)
            if ts:
                if not group["first_seen"] or ts < group["first_seen"]:
                    group["first_seen"] = ts
                if not group["last_seen"] or ts > group["last_seen"]:
                    group["last_seen"] = ts

        return groups

    def _analyze_payload_group(
        self, payload_hash: str, group_data: Dict[str, Any]
    ) -> Optional[ZeroDayCandidate]:
        """Analyze a group of similar payloads for zero-day indicators."""
        payloads = group_data["payloads"]
        if len(payloads) < self.min_occurrences:
            return None

        # Get representative payload
        representative = max(payloads, key=len)

        # Detect attack vector
        attack_vector, pattern_matches = detect_attack_vector(representative)

        # Calculate novelty score
        novelty_score = calculate_novelty_score(
            representative, attack_vector, pattern_matches
        )

        # Check against known CVEs
        matched_cves = check_cve_matches(representative, self.known_cve_patterns)

        # If matches known CVEs with high confidence, reduce novelty
        if matched_cves:
            novelty_score *= 0.3

        # Estimate severity
        severity = estimate_severity(representative, attack_vector)

        # Calculate confidence
        confidence = calculate_confidence(
            len(payloads),
            len(group_data["ips"]),
            novelty_score,
            attack_vector,
        )

        # Extract indicators
        indicators = extract_indicators(representative)

        return ZeroDayCandidate(
            id=str(uuid.uuid4()),
            payload_hash=payload_hash,
            payload_preview=representative[:500],
            source_ips=list(group_data["ips"]),
            target_services=list(group_data["services"]),
            first_seen=group_data["first_seen"] or datetime.now(timezone.utc),
            last_seen=group_data["last_seen"] or datetime.now(timezone.utc),
            occurrence_count=len(payloads),
            novelty_score=novelty_score,
            severity_estimate=severity,
            attack_vector=attack_vector,
            confidence=confidence,
            matched_cves=matched_cves,
            indicators=indicators,
        )

    def _build_metadata(self) -> Dict[str, Any]:
        """Build analysis metadata."""
        if not self._candidates:
            return {
                "zeroday_candidates": 0,
                "high_confidence_count": 0,
            }

        high_confidence = [c for c in self._candidates if c.confidence >= 0.7]
        by_vector = Counter(c.attack_vector for c in self._candidates)

        return {
            "zeroday_candidates": len(self._candidates),
            "high_confidence_count": len(high_confidence),
            "attack_vectors": dict(by_vector),
            "severity_breakdown": {
                sev: len([c for c in self._candidates if c.severity_estimate == sev])
                for sev in ["critical", "high", "medium", "low"]
            },
        }

    def get_candidates(self) -> List[ZeroDayCandidate]:
        """Get all zero-day candidates."""
        return self._candidates

    def get_high_priority_candidates(self) -> List[ZeroDayCandidate]:
        """Get candidates that warrant immediate attention."""
        return [
            c
            for c in self._candidates
            if c.novelty_score >= 0.8 and c.confidence >= 0.6
        ]
