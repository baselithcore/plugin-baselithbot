"""Payload feature extraction."""

import hashlib
from typing import List, Set

try:
    import ssdeep

    HAS_SSDEEP = True
except ImportError:
    HAS_SSDEEP = False
    ssdeep = None

from ...models import AttackEvent
from .models import AttackFeatureVector
from .utils import calculate_entropy, get_payload


def extract_payload_features(
    features: AttackFeatureVector, events: List[AttackEvent]
) -> None:
    """Extract payload similarity features."""
    payloads: List[str] = []
    payload_hashes: Set[str] = set()
    total_entropy = 0.0

    for event in events:
        payload = get_payload(event)
        if payload:
            payloads.append(payload)
            payload_hashes.add(
                hashlib.md5(payload.encode(), usedforsecurity=False).hexdigest()[:8]
            )
            total_entropy += calculate_entropy(payload)

    if not payloads:
        return

    # Average payload size
    features.avg_payload_size = sum(len(p) for p in payloads) / len(payloads)

    # Average entropy
    features.payload_entropy = total_entropy / len(payloads)

    # Unique payloads
    features.unique_payloads = len(payload_hashes)

    # Combined payload hash (fuzzy or md5)
    combined = "".join(payloads[:10])  # First 10 payloads
    if HAS_SSDEEP and len(combined) > 16:
        try:
            features.payload_hash = ssdeep.hash(combined.encode())
        except Exception:
            features.payload_hash = hashlib.sha256(combined.encode()).hexdigest()
    else:
        features.payload_hash = hashlib.sha256(combined.encode()).hexdigest()
