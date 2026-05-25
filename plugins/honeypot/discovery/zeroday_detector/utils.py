"""Zero-Day Detector Utilities."""

import hashlib
import math
import re
from collections import Counter
from datetime import datetime
from typing import Any, Optional

from ...models import AttackEvent


def calculate_entropy(text: str) -> float:
    """Calculate Shannon entropy."""
    if not text:
        return 0.0
    freq = Counter(text)
    length = len(text)
    return -sum(
        (count / length) * math.log2(count / length)
        for count in freq.values()
        if count > 0
    )


def parse_timestamp(ts: Any) -> Optional[datetime]:
    """Parse timestamp to datetime."""
    if isinstance(ts, datetime):
        return ts
    if isinstance(ts, str):
        try:
            return datetime.fromisoformat(ts.replace("Z", "+00:00"))
        except ValueError:
            return None
    return None


def extract_payload(event: AttackEvent) -> str:
    """Extract payload from event."""
    parts = []
    if event.raw_data:
        parts.append(event.raw_data)
    if event.command:
        parts.append(event.command)
    if hasattr(event, "http_body") and event.http_body:
        parts.append(event.http_body)
    if hasattr(event, "http_path") and event.http_path:
        parts.append(event.http_path)
    return " ".join(parts)


def create_payload_fingerprint(payload: str) -> str:
    """Create normalized fingerprint for payload clustering."""
    # Normalize variable parts
    normalized = payload.lower()

    # Replace IPs, timestamps, random strings
    normalized = re.sub(r"\d+\.\d+\.\d+\.\d+", "<IP>", normalized)
    normalized = re.sub(r"\d{10,}", "<NUM>", normalized)
    normalized = re.sub(r"[a-f0-9]{32,}", "<HASH>", normalized)

    # Keep first 500 chars for fingerprinting
    normalized = normalized[:500]

    return hashlib.md5(normalized.encode(), usedforsecurity=False).hexdigest()[:16]
