"""Payload similarity logic for Behavioral Analyzer."""

import hashlib
import uuid
from collections import defaultdict
from datetime import datetime
from difflib import SequenceMatcher
from typing import Dict, List, Optional, Set, Tuple

from ...models import AttackEvent
from ..models import NetworkAnomaly
from .utils import calculate_severity, extract_payload

# Try importing ssdeep for fuzzy hashing
try:
    import ssdeep

    HAS_SSDEEP = True
except ImportError:
    HAS_SSDEEP = False
    ssdeep = None


def detect_payload_similarity(
    events: List[AttackEvent],
    payload_similarity_threshold: float,
    min_correlation_group_size: int,
    threshold: Optional[float] = None,
) -> List[NetworkAnomaly]:
    """Detect similar payloads across different IPs using fuzzy hashing.

    Groups attacks with payloads that have high similarity scores,
    indicating malware/script reuse across botnet members.

    Args:
        events: Attack events to analyze
        payload_similarity_threshold: Default similarity threshold (0-1)
        min_correlation_group_size: Minimum IPs to form a correlation group
        threshold: Override similarity threshold

    Returns:
        List of payload similarity anomalies
    """
    threshold = threshold or payload_similarity_threshold
    anomalies: List[NetworkAnomaly] = []

    # Extract payloads with their source IPs
    payloads: List[Tuple[str, str, str]] = []  # (ip, payload_hash, raw_payload)

    for event in events:
        payload = extract_payload(event)
        if payload and len(payload) >= 10:  # Minimum payload length
            payload_hash = compute_payload_hash(payload)
            payloads.append((event.source_ip, payload_hash, payload))

    if len(payloads) < 2:
        return anomalies

    # Group by exact hash first (fast)
    hash_groups: Dict[str, Set[str]] = defaultdict(set)
    for ip, phash, _ in payloads:
        hash_groups[phash].add(ip)

    # Report exact matches
    for phash, ips in hash_groups.items():
        if len(ips) >= min_correlation_group_size:
            anomaly = NetworkAnomaly(
                anomaly_id=str(uuid.uuid4())[:8],
                anomaly_type="payload_identical",
                involved_ips=list(ips),
                description=(
                    f"{len(ips)} IPs sent identical payloads (hash: {phash[:12]}...)"
                ),
                severity="high" if len(ips) >= 5 else "medium",
                confidence=1.0,  # Exact match
                detected_at=datetime.now(),
                metadata={
                    "payload_hash": phash,
                    "ip_count": len(ips),
                    "match_type": "exact",
                },
            )
            anomalies.append(anomaly)

    # Fuzzy matching for similar (not identical) payloads
    fuzzy_clusters = fuzzy_cluster_payloads(payloads, threshold)
    for cluster in fuzzy_clusters:
        if len(cluster["ips"]) >= min_correlation_group_size:
            anomaly = NetworkAnomaly(
                anomaly_id=str(uuid.uuid4())[:8],
                anomaly_type="payload_similarity",
                involved_ips=list(cluster["ips"]),
                description=(
                    f"{len(cluster['ips'])} IPs sent similar payloads "
                    f"(similarity: {cluster['similarity']:.0%})"
                ),
                severity=calculate_severity(len(cluster["ips"]), 3, 5, 8),
                confidence=cluster["similarity"],
                detected_at=datetime.now(),
                metadata={
                    "similarity": cluster["similarity"],
                    "ip_count": len(cluster["ips"]),
                    "match_type": "fuzzy",
                },
            )
            anomalies.append(anomaly)

    return anomalies


def fuzzy_cluster_payloads(
    payloads: List[Tuple[str, str, str]], threshold: float
) -> List[Dict]:
    """Cluster payloads by fuzzy similarity.

    Uses ssdeep if available, otherwise falls back to SequenceMatcher.
    """
    clusters: List[Dict] = []
    processed: Set[int] = set()

    for i, (ip1, hash1, raw1) in enumerate(payloads):
        if i in processed:
            continue

        cluster_ips = {ip1}
        cluster_similarity = 1.0

        for j, (ip2, hash2, raw2) in enumerate(payloads[i + 1 :], i + 1):
            if j in processed or ip1 == ip2:
                continue

            similarity = compute_similarity(raw1, raw2)

            if similarity >= threshold:
                cluster_ips.add(ip2)
                cluster_similarity = min(cluster_similarity, similarity)
                processed.add(j)

        if len(cluster_ips) > 1:
            clusters.append(
                {
                    "ips": cluster_ips,
                    "similarity": cluster_similarity,
                }
            )
            processed.add(i)

    return clusters


def compute_similarity(payload1: str, payload2: str) -> float:
    """Compute similarity between two payloads."""
    if HAS_SSDEEP:
        try:
            hash1 = ssdeep.hash(payload1.encode())
            hash2 = ssdeep.hash(payload2.encode())
            score = ssdeep.compare(hash1, hash2)
            return score / 100.0  # Normalize to 0-1
        except Exception:
            pass

    # Fallback to SequenceMatcher
    return SequenceMatcher(None, payload1, payload2).ratio()


def compute_payload_hash(payload: str) -> str:
    """Compute hash for payload."""
    if HAS_SSDEEP:
        try:
            return ssdeep.hash(payload.encode())
        except Exception:
            pass

    # Fallback to SHA256
    return hashlib.sha256(payload.encode()).hexdigest()
