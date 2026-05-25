"""Statistical Analyzer Utilities."""

from datetime import datetime
from typing import Any, Optional


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
