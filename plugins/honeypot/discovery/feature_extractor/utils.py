"""Utilities for Feature Extractor."""

import math
import re
from collections import Counter
from datetime import datetime
from typing import Any, Optional

from ...models import AttackEvent


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


def calculate_entropy(text: str) -> float:
    """Calculate Shannon entropy."""
    if not text:
        return 0.0

    freq = Counter(text)
    length = len(text)
    entropy = 0.0

    for count in freq.values():
        if count > 0:
            prob = count / length
            entropy -= prob * math.log2(prob)

    return entropy


def normalize_command(command: str) -> str:
    """Normalize command for comparison."""
    # Remove variable parts
    normalized = command.strip()

    # Replace IPs
    normalized = re.sub(r"\d+\.\d+\.\d+\.\d+", "<IP>", normalized)

    # Replace timestamps/dates
    normalized = re.sub(r"\d{4}-\d{2}-\d{2}", "<DATE>", normalized)
    normalized = re.sub(r"\d{2}:\d{2}:\d{2}", "<TIME>", normalized)

    # Replace hex strings
    normalized = re.sub(r"\\x[0-9a-fA-F]{2}", "<HEX>", normalized)
    normalized = re.sub(r"0x[0-9a-fA-F]+", "<HEX>", normalized)

    # Replace long numbers
    normalized = re.sub(r"\d{6,}", "<NUM>", normalized)

    return normalized[:100]  # Truncate


def get_payload(event: AttackEvent) -> str:
    """Extract payload content from event."""
    parts = []
    if event.raw_data:
        parts.append(event.raw_data)
    if event.command:
        parts.append(event.command)
    if event.http_body:
        parts.append(event.http_body)
    return " ".join(parts)
