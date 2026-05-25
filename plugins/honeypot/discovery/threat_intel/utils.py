"""Threat Intel Utilities."""

import hashlib
import re

from ...models import AttackEvent


def get_payload(event: AttackEvent) -> str:
    """Extract payload from event."""
    parts = []
    if event.raw_data:
        parts.append(event.raw_data)
    if event.command:
        parts.append(event.command)
    if hasattr(event, "http_body") and event.http_body:
        parts.append(event.http_body)
    return " ".join(parts)


def hash_payload(payload: str) -> str:
    """Create fingerprint hash."""
    return hashlib.md5(payload.encode(), usedforsecurity=False).hexdigest()[:16]


def fingerprint_payload(payload: str) -> str:
    """Create normalized fingerprint for grouping."""
    # Normalize variable parts
    normalized = re.sub(r"\d+\.\d+\.\d+\.\d+", "<IP>", payload)
    normalized = re.sub(r"\d{10,}", "<NUM>", normalized)
    normalized = normalized[:200].lower()
    return hashlib.md5(normalized.encode(), usedforsecurity=False).hexdigest()[:12]


def normalize_command(command: str) -> str:
    """Normalize command for pattern matching."""
    # Remove variable parts
    normalized = re.sub(r"\d+\.\d+\.\d+\.\d+", "*", command)
    normalized = re.sub(r"/tmp/[^\s]+", "/tmp/*", normalized)  # nosec B108
    normalized = re.sub(r"http[s]?://[^\s]+", "http://*", normalized)
    return normalized[:100]
