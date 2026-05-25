"""Feature Extractor Core Module."""

from core.observability.logging import get_logger
from collections import defaultdict
from typing import Any, Dict, List

try:
    import ssdeep

    HAS_SSDEEP = True
except ImportError:
    HAS_SSDEEP = False
    ssdeep = None

from ...models import AttackEvent
from .credentials import extract_credential_features
from .models import AttackFeatureVector
from .network import extract_network_features
from .payload import extract_payload_features
from .sequence import extract_sequence_features
from .similarity import compute_cosine_similarity, compute_payload_similarity
from .statistical import extract_statistical_features
from .temporal import extract_temporal_features
from .tls import extract_ja4

logger = get_logger(__name__)


class FeatureExtractor:
    """Extracts comprehensive features from attack events."""

    def __init__(self):
        """Initialize feature extractor."""
        self._feature_vectors: Dict[str, AttackFeatureVector] = {}
        self._payload_hashes: Dict[str, str] = {}

    def extract_features(
        self, events: List[AttackEvent]
    ) -> Dict[str, AttackFeatureVector]:
        """Extract features for all attackers from events.

        Args:
            events: Attack events to analyze

        Returns:
            Dictionary mapping IP to feature vector
        """
        if not events:
            return {}

        # Group events by IP
        ip_events: Dict[str, List[AttackEvent]] = defaultdict(list)
        for event in events:
            ip_events[event.source_ip].append(event)

        # Extract features per IP
        for ip, ip_event_list in ip_events.items():
            features = self._extract_ip_features(ip, ip_event_list)
            self._feature_vectors[ip] = features

        logger.info(f"Extracted features for {len(self._feature_vectors)} IPs")

        return self._feature_vectors

    def _extract_ip_features(
        self, ip: str, events: List[AttackEvent]
    ) -> AttackFeatureVector:
        """Extract all features for a single IP."""
        features = AttackFeatureVector(ip=ip)

        # Extract each feature group
        extract_temporal_features(features, events)
        extract_payload_features(features, events)
        extract_sequence_features(features, events)
        extract_network_features(features, events)
        extract_statistical_features(features, events)
        extract_credential_features(features, events)

        # Extract JA4 fingerprints
        for event in events:
            ja4 = extract_ja4(event)
            if ja4:
                features.ja4_fingerprints.add(ja4)

        return features

    def compute_similarity(self, ip1: str, ip2: str) -> float:
        """Compute feature similarity between two IPs."""
        if ip1 not in self._feature_vectors or ip2 not in self._feature_vectors:
            return 0.0

        v1 = self._feature_vectors[ip1].to_vector()
        v2 = self._feature_vectors[ip2].to_vector()

        # Normalize and compute cosine similarity
        return compute_cosine_similarity(v1, v2)

    def compute_payload_similarity(self, payload1: str, payload2: str) -> float:
        """Compute fuzzy similarity between two payloads."""
        return compute_payload_similarity(payload1, payload2)

    def get_feature_vectors(self) -> Dict[str, AttackFeatureVector]:
        """Get all extracted feature vectors."""
        return self._feature_vectors

    def get_feature_summary(self) -> Dict[str, Any]:
        """Get summary of extracted features."""
        if not self._feature_vectors:
            return {"total_ips": 0}

        vectors = list(self._feature_vectors.values())

        return {
            "total_ips": len(vectors),
            "avg_events_per_ip": sum(v.event_count for v in vectors) / len(vectors),
            "avg_payload_entropy": sum(v.payload_entropy for v in vectors)
            / len(vectors),
            "avg_unique_commands": sum(v.unique_commands for v in vectors)
            / len(vectors),
            "total_credentials_attempts": sum(v.credential_attempts for v in vectors),
            "ssdeep_available": HAS_SSDEEP,
            "top_ja4_fingerprints": self._get_top_ja4_fingerprints(vectors),
        }

    def _get_top_ja4_fingerprints(
        self, vectors: List[AttackFeatureVector], limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get most frequent JA4 fingerprints from feature vectors."""
        ja4_counts: Dict[str, int] = defaultdict(int)

        # Count occurrences across all vectors
        for v in vectors:
            for ja4 in v.ja4_fingerprints:
                ja4_counts[ja4] += 1

        # Sort by frequency
        sorted_ja4 = sorted(ja4_counts.items(), key=lambda x: x[1], reverse=True)[
            :limit
        ]

        return [{"fingerprint": ja4, "count": count} for ja4, count in sorted_ja4]
