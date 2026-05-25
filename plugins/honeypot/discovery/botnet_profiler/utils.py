"""Utility functions for Botnet Profiler."""

from datetime import datetime, timezone
from typing import Any, Optional


def parse_timestamp(ts: Any) -> Optional[datetime]:
    """Parse timestamp to datetime (always timezone-aware).

    Args:
        ts: Timestamp (datetime or ISO string)

    Returns:
        Optional[datetime]: Parsed timezone-aware datetime object or None
    """
    if isinstance(ts, datetime):
        # Ensure timezone-aware: add UTC if naive
        if ts.tzinfo is None:
            return ts.replace(tzinfo=timezone.utc)
        return ts
    if isinstance(ts, str):
        try:
            dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            # Ensure timezone-aware
            if dt.tzinfo is None:
                return dt.replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            return None
    return None
