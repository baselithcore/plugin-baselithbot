"""Network feature extraction."""

from typing import List, Set

from ...models import AttackEvent
from .models import AttackFeatureVector


def extract_network_features(
    features: AttackFeatureVector, events: List[AttackEvent]
) -> None:
    """Extract network behavior fingerprint."""
    ports: Set[int] = set()
    protocols: Set[str] = set()
    targets: Set[str] = set()

    for event in events:
        if event.source_port:
            ports.add(event.source_port)

        protocol = (
            event.protocol.value
            if hasattr(event.protocol, "value")
            else str(event.protocol)
        )
        protocols.add(protocol)

        if event.honeypot_id:
            targets.add(event.honeypot_id)

    features.unique_ports = len(ports)
    features.unique_protocols = len(protocols)
    features.unique_targets = len(targets)

    # Collect JA4 fingerprints
    for event in events:
        if hasattr(event, "ja4_fingerprint") and event.ja4_fingerprint:
            features.ja4_fingerprints.add(event.ja4_fingerprint)
        elif hasattr(event, "metadata") and event.metadata and "ja4" in event.metadata:
            features.ja4_fingerprints.add(event.metadata["ja4"])

    # Protocol fingerprint (sorted protocols)
    features.protocol_fingerprint = ",".join(sorted(protocols))
