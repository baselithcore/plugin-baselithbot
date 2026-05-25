"""Core Honeypot Suggestion Engine.

Main class for analyzing attack patterns and generating
honeypot suggestions based on ZeroDayDetector findings,
behavioral clusters, and network anomalies.
"""

from core.observability.logging import get_logger
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set

from ..models import NetworkAnomaly
from ..zeroday_detector.models import ZeroDayCandidate
from .models import (
    HoneypotSuggestion,
    SuggestionListResponse,
    SuggestionPriority,
    SuggestionSummary,
    SuggestionType,
    SuggestedProtocol,
)
from .strategies import (
    calculate_priority,
    determine_protocol_from_vector,
    estimate_catch_rate,
    generate_detection_patterns,
    generate_rationale,
    generate_tags,
)
from .filters import (
    calculate_investigation_value,
    calculate_sophistication_level,
    generate_investigation_rationale,
    generate_descriptive_title,
    filter_and_rank_suggestions,
    is_generic_pattern,
)

logger = get_logger(__name__)


class HoneypotSuggestionEngine:
    """Analyzes attack patterns to suggest custom honeypots.

    Uses data from ZeroDayDetector, behavioral analysis, and threat
    intel to recommend honeypots that would help capture emerging
    attack techniques not yet cataloged as CVEs.
    """

    # Thresholds for suggestion generation (raised for quality over quantity)
    MIN_NOVELTY_SCORE = 0.65  # Raised: Only genuinely novel patterns
    MIN_CONFIDENCE = 0.55  # Raised: Require moderate confidence
    MIN_OCCURRENCES = 4  # Raised: Require pattern persistence
    MAX_SUGGESTIONS = 15  # Maximum suggestions to return after filtering

    def __init__(
        self,
        existing_honeypot_ids: Optional[List[str]] = None,
        existing_patterns: Optional[Set[str]] = None,
    ):
        """Initialize suggestion engine.

        Args:
            existing_honeypot_ids: List of active honeypot IDs to avoid duplicates
            existing_patterns: Set of pattern fingerprints already covered
        """
        self.existing_honeypot_ids = set(existing_honeypot_ids or [])
        self.existing_patterns = existing_patterns or set()
        self._suggestions: List[HoneypotSuggestion] = []
        self._seen_fingerprints: Set[str] = set()

    async def analyze_and_suggest(
        self,
        zeroday_candidates: Optional[List[ZeroDayCandidate]] = None,
        behavioral_clusters: Optional[Dict[str, Any]] = None,
        network_anomalies: Optional[List[NetworkAnomaly]] = None,
    ) -> List[HoneypotSuggestion]:
        """Generate honeypot suggestions from analysis results.

        Args:
            zeroday_candidates: Candidates from ZeroDayDetector
            behavioral_clusters: Cluster data from BehavioralAnalyzer
            network_anomalies: Anomalies from various detectors

        Returns:
            List of honeypot suggestions
        """
        self._suggestions = []
        self._seen_fingerprints = set()

        # Process zero-day candidates
        if zeroday_candidates:
            for candidate in zeroday_candidates:
                suggestion = self._suggest_from_zeroday(candidate)
                if suggestion:
                    self._suggestions.append(suggestion)

        # Process behavioral clusters
        if behavioral_clusters:
            clusters = behavioral_clusters.get("clusters", [])
            for cluster in clusters:
                suggestion = self._suggest_from_behavior(cluster)
                if suggestion:
                    self._suggestions.append(suggestion)

        # Process protocol anomalies
        if network_anomalies:
            for anomaly in network_anomalies:
                if anomaly.anomaly_type in ("protocol_anomaly", "unknown_protocol"):
                    suggestion = self._suggest_from_protocol(anomaly)
                    if suggestion:
                        self._suggestions.append(suggestion)

        # Sort by priority and confidence
        self._suggestions.sort(
            key=lambda s: (
                self._priority_order(s.priority),
                -s.confidence,
            )
        )

        # Apply final filtering: deduplicate, remove noise, limit count
        raw_count = len(self._suggestions)
        self._suggestions = filter_and_rank_suggestions(
            self._suggestions,
            max_suggestions=self.MAX_SUGGESTIONS,
        )

        logger.info(
            f"Generated {len(self._suggestions)} honeypot suggestions "
            f"(filtered from {raw_count} raw) "
            f"from {len(zeroday_candidates or [])} zero-day candidates, "
            f"{len(behavioral_clusters.get('clusters', []) if behavioral_clusters else [])} clusters, "
            f"{len(network_anomalies or [])} anomalies"
        )

        return self._suggestions

    def _suggest_from_zeroday(
        self, candidate: ZeroDayCandidate
    ) -> Optional[HoneypotSuggestion]:
        """Create suggestion from a zero-day candidate.

        Args:
            candidate: Zero-day candidate from detector

        Returns:
            HoneypotSuggestion if criteria met, None otherwise
        """
        # Check thresholds
        if candidate.novelty_score < self.MIN_NOVELTY_SCORE:
            return None
        if candidate.confidence < self.MIN_CONFIDENCE:
            return None
        if candidate.occurrence_count < self.MIN_OCCURRENCES:
            return None

        # Skip if pattern already seen
        if candidate.payload_hash in self._seen_fingerprints:
            return None
        self._seen_fingerprints.add(candidate.payload_hash)

        # Skip if too similar to existing honeypot
        if self._is_covered_by_existing(
            candidate.attack_vector, candidate.target_services
        ):
            return None

        # Determine protocol and port
        protocol, port = determine_protocol_from_vector(
            candidate.attack_vector, candidate.payload_preview
        )

        # Calculate priority
        priority = calculate_priority(
            candidate.novelty_score,
            candidate.confidence,
            candidate.occurrence_count,
        )

        # Generate detection patterns
        detection_patterns = generate_detection_patterns(
            candidate.payload_preview,
            candidate.attack_vector,
            candidate.indicators,
        )

        # Generate tags
        tags = generate_tags(
            candidate.attack_vector,
            candidate.indicators,
            [candidate.payload_hash],
        )

        # Generate descriptive title (avoid generic "Unknown Detector")
        title = generate_descriptive_title(
            candidate.attack_vector,
            candidate.target_services,
            detection_patterns,
            candidate.occurrence_count,
            len(candidate.source_ips),
        )

        # Skip if title would be too generic
        if is_generic_pattern(candidate.attack_vector, title):
            return None

        # Generate description
        description = (
            f"Honeypot designed to capture {candidate.attack_vector.replace('_', ' ')} attacks "
            f"similar to a novel pattern observed {candidate.occurrence_count} times from "
            f"{len(candidate.source_ips)} unique sources."
        )

        # Generate rationale
        rationale = generate_rationale(
            SuggestionType.ZERODAY_PATTERN,
            candidate.attack_vector,
            candidate.occurrence_count,
            len(candidate.source_ips),
            candidate.novelty_score,
        )

        # Estimate catch rate
        catch_rate = estimate_catch_rate(
            candidate.occurrence_count,
            len(candidate.source_ips),
            candidate.novelty_score,
        )

        # Calculate new metrics
        relevance_score = calculate_investigation_value(
            candidate.novelty_score,
            candidate.confidence,
            candidate.occurrence_count,
            len(candidate.source_ips),
            candidate.attack_vector,
            candidate.indicators,
        )

        sophistication_level = calculate_sophistication_level(
            candidate.attack_vector,
            candidate.indicators,
            detection_patterns,
        )

        investigation_rationale = generate_investigation_rationale(
            SuggestionType.ZERODAY_PATTERN.value,
            candidate.attack_vector,
            candidate.occurrence_count,
            len(candidate.source_ips),
            candidate.novelty_score,
            sophistication_level,
        )

        try:
            return HoneypotSuggestion(
                id=str(uuid.uuid4()),
                suggestion_type=SuggestionType.ZERODAY_PATTERN,
                confidence=candidate.confidence,
                priority=priority,
                title=title,
                description=description,
                rationale=rationale,
                suggested_protocol=protocol,
                suggested_port=port,
                detection_patterns=detection_patterns,
                tags=tags,
                source_anomaly_ids=[f"zeroday_{candidate.id[:8]}"],
                source_patterns=[candidate.payload_hash],
                source_ips=list(candidate.source_ips)[:10],
                estimated_catch_rate=catch_rate,
                occurrence_count=candidate.occurrence_count,
                relevance_score=relevance_score,
                sophistication_level=sophistication_level,
                investigation_rationale=investigation_rationale,
                created_at=datetime.now(timezone.utc),
            )
        except Exception as e:
            logger.error(
                f"Failed to create HoneypotSuggestion from zeroday: {e}, "
                f"confidence={candidate.confidence}, port={port}, protocol={protocol}"
            )
            return None

    def _suggest_from_behavior(
        self, cluster: Dict[str, Any]
    ) -> Optional[HoneypotSuggestion]:
        """Create suggestion from behavioral cluster.

        Args:
            cluster: Cluster data from behavioral analyzer

        Returns:
            HoneypotSuggestion if criteria met, None otherwise
        """
        # Extract cluster metrics
        member_count = len(cluster.get("member_ips", []))
        commands = cluster.get("common_commands", [])
        protocols = cluster.get("protocols", [])

        # Need sufficient data
        if member_count < 3 or not commands:
            return None

        # Create fingerprint from commands
        fingerprint = "_".join(sorted(commands[:5]))
        if fingerprint in self._seen_fingerprints:
            return None
        self._seen_fingerprints.add(fingerprint)

        # Determine protocol (default SSH for command-based)
        protocol = SuggestedProtocol.SSH
        port = 2222
        if "http" in protocols or "HTTP" in protocols:
            protocol = SuggestedProtocol.HTTP
            port = 8080

        # Generate detection patterns from commands
        detection_patterns = []
        for cmd in commands[:5]:
            detection_patterns.append(
                {
                    "name": f"cluster_cmd_{len(detection_patterns)}",
                    "regex": cmd.replace("*", ".*"),
                    "severity": "high",
                    "category": "behavioral_cluster",
                }
            )

        title = f"Coordinated Attack Pattern Detector ({member_count} sources)"
        description = (
            f"Honeypot targeting a behavioral cluster of {member_count} coordinated "
            f"attackers executing similar command patterns."
        )

        rationale = generate_rationale(
            SuggestionType.BEHAVIORAL_CLUSTER,
            "coordinated_attack",
            member_count,
            member_count,
            0.7,  # Behavioral clusters have implied novelty
        )

        return HoneypotSuggestion(
            id=str(uuid.uuid4()),
            suggestion_type=SuggestionType.BEHAVIORAL_CLUSTER,
            confidence=0.7,
            priority=SuggestionPriority.HIGH
            if member_count > 5
            else SuggestionPriority.MEDIUM,
            title=title,
            description=description,
            rationale=rationale,
            suggested_protocol=protocol,
            suggested_port=port,
            detection_patterns=detection_patterns,
            tags=["behavioral", "coordinated", "cluster"],
            source_anomaly_ids=[cluster.get("cluster_id", "")],
            source_patterns=[fingerprint],
            source_ips=cluster.get("member_ips", [])[:10],
            estimated_catch_rate=0.6,
            occurrence_count=member_count,
            created_at=datetime.now(timezone.utc),
        )

    def _suggest_from_protocol(
        self, anomaly: NetworkAnomaly
    ) -> Optional[HoneypotSuggestion]:
        """Create suggestion from protocol anomaly.

        Args:
            anomaly: Protocol anomaly from detector

        Returns:
            HoneypotSuggestion if criteria met, None otherwise
        """
        if anomaly.confidence < self.MIN_CONFIDENCE:
            return None

        # Skip if already seen
        if anomaly.anomaly_id in self._seen_fingerprints:
            return None
        self._seen_fingerprints.add(anomaly.anomaly_id)

        # Extract port from metadata if available
        port = anomaly.metadata.get("port", 9999)

        title = f"Unknown Protocol Detector (Port {port})"
        description = (
            f"Honeypot for capturing traffic on port {port} using an "
            f"unrecognized protocol pattern. {anomaly.description}"
        )

        rationale = generate_rationale(
            SuggestionType.PROTOCOL_ANOMALY,
            "unknown_protocol",
            1,
            len(anomaly.involved_ips),
            0.8,  # Protocol anomalies are highly novel
        )

        return HoneypotSuggestion(
            id=str(uuid.uuid4()),
            suggestion_type=SuggestionType.PROTOCOL_ANOMALY,
            confidence=anomaly.confidence,
            priority=SuggestionPriority.MEDIUM,
            title=title,
            description=description,
            rationale=rationale,
            suggested_protocol=SuggestedProtocol.TCP,
            suggested_port=port,
            detection_patterns=[],
            tags=["protocol-anomaly", "unknown", f"port-{port}"],
            source_anomaly_ids=[anomaly.anomaly_id],
            source_patterns=[],
            source_ips=anomaly.involved_ips[:10],
            estimated_catch_rate=0.5,
            occurrence_count=1,
            created_at=datetime.now(timezone.utc),
        )

    def _is_covered_by_existing(
        self, attack_vector: str, target_services: List[str]
    ) -> bool:
        """Check if attack pattern is already covered by existing honeypots.

        Args:
            attack_vector: The attack vector type
            target_services: Target services from the pattern

        Returns:
            True if already covered
        """
        # Check service names against existing honeypot IDs
        for service in target_services:
            service_lower = service.lower()
            for honeypot_id in self.existing_honeypot_ids:
                if any(
                    keyword in honeypot_id.lower()
                    for keyword in service_lower.split(":")
                ):
                    return True
        return False

    def _priority_order(self, priority: SuggestionPriority) -> int:
        """Convert priority to sortable integer (lower = higher priority)."""
        order = {
            SuggestionPriority.CRITICAL: 0,
            SuggestionPriority.HIGH: 1,
            SuggestionPriority.MEDIUM: 2,
            SuggestionPriority.LOW: 3,
        }
        return order.get(priority, 4)

    def get_suggestions(self) -> List[HoneypotSuggestion]:
        """Get all generated suggestions."""
        return self._suggestions

    def get_summary(self) -> SuggestionSummary:
        """Get summary of generated suggestions."""
        active = [s for s in self._suggestions if not s.dismissed and not s.applied]

        by_priority: Dict[str, int] = {}
        by_type: Dict[str, int] = {}

        for s in active:
            by_priority[s.priority.value] = by_priority.get(s.priority.value, 0) + 1
            by_type[s.suggestion_type.value] = (
                by_type.get(s.suggestion_type.value, 0) + 1
            )

        return SuggestionSummary(
            total_suggestions=len(self._suggestions),
            active_suggestions=len(active),
            by_priority=by_priority,
            by_type=by_type,
            top_suggestions=active[:5],
            last_analysis=datetime.now(timezone.utc),
        )

    def to_list_response(
        self, page: int = 1, page_size: int = 20
    ) -> SuggestionListResponse:
        """Convert suggestions to paginated API response.

        Args:
            page: Page number (1-indexed)
            page_size: Items per page

        Returns:
            Paginated response
        """
        start = (page - 1) * page_size
        end = start + page_size

        return SuggestionListResponse(
            suggestions=self._suggestions[start:end],
            total=len(self._suggestions),
            page=page,
            page_size=page_size,
            summary=self.get_summary(),
        )
