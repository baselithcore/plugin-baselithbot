"""Utilities for Behavioral Analyzer."""

from datetime import datetime
from typing import Any, Optional

from ...models import AttackEvent


def parse_timestamp(ts: Any) -> Optional[datetime]:
    """Parse timestamp to datetime.

    Args:
        ts: Timestamp (datetime or ISO string)

    Returns:
        Optional[datetime]: Parsed datetime object or None
    """
    if isinstance(ts, datetime):
        return ts
    if isinstance(ts, str):
        try:
            return datetime.fromisoformat(ts.replace("Z", "+00:00"))
        except ValueError:
            return None
    return None


def calculate_severity(
    count: int, low_threshold: int, medium_threshold: int, high_threshold: int
) -> str:
    """Calculate severity based on count thresholds."""
    if count >= high_threshold:
        return "high"
    if count >= medium_threshold:
        return "medium"
    if count >= low_threshold:
        return "low"
    return "info"


def extract_payload(event: AttackEvent) -> Optional[str]:
    """Extract payload content from event."""
    # Try different payload sources
    if event.raw_data and len(event.raw_data) > 5:
        return event.raw_data
    if event.command:
        return event.command
    if event.http_body:
        return event.http_body
    if event.http_path:
        return event.http_path
    return None
