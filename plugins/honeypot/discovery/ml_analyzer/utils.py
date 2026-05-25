"""Utilities for ML Analyzer."""

from core.observability.logging import get_logger
from datetime import datetime
from typing import Any, Optional

logger = get_logger(__name__)

# Try importing sklearn for ML algorithms
try:
    from sklearn.cluster import DBSCAN, KMeans
    from sklearn.ensemble import IsolationForest
    from sklearn.preprocessing import StandardScaler
    import numpy as np

    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False
    np = None
    DBSCAN = None
    KMeans = None
    IsolationForest = None
    StandardScaler = None


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
