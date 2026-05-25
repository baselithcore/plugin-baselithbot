"""TLS Feature Extractor.

Extracts TLS fingerprinting features (JA4/JA3) from connection events.
"""

import hashlib
from typing import Dict, Any, List

from ...models import AttackEvent


def extract_ja4(event: AttackEvent) -> str:
    """
    Extract/Construct JA4 fingerprint from event data.

    In a real implementation, this would parse raw TLS handshake bytes or
    use pcap data. Here we simulate a fingerprint based on available metadata
    to demonstrate the flow.
    """
    # Check if we have raw TLS data in metadata
    if event.metadata:
        tls_data = event.metadata.get("tls", {})
        if tls_data.get("ja4"):
            return tls_data.get("ja4")

    # Heuristic construction if no raw JA4
    # Format: ppppcc_iii_iii (Protocol+Version+Ciphers_Extensions_Algo)
    # This is a MOCK/SIMULATION for when we don't have deep packet inspection
    proto = "t"  # TCP
    version = "13"  # TLS 1.3 default assumption for modern bots

    # We use source IP and port to generate a stable mock fingerprint
    # for the same attacker, if real one isn't available
    if event.source_ip:
        seed = f"{event.source_ip}{event.protocol}"
        h = hashlib.md5(seed.encode(), usedforsecurity=False).hexdigest()
        return f"{proto}{version}d{h[:2]}_{h[2:14]}_{h[14:26]}"

    return ""


def extract_tls_features(events: List[AttackEvent]) -> Dict[str, Any]:
    """Extract aggregated TLS features from a list of events."""
    ja4_counts = {}

    for event in events:
        ja4 = extract_ja4(event)
        if ja4:
            ja4_counts[ja4] = ja4_counts.get(ja4, 0) + 1

    # Sort by frequency
    sorted_ja4 = sorted(ja4_counts.items(), key=lambda x: x[1], reverse=True)

    return {
        "top_ja4_fingerprints": [
            {"fingerprint": fp, "count": count} for fp, count in sorted_ja4[:10]
        ],
        "unique_ja4_count": len(ja4_counts),
    }
