"""Zero-Day Detector Indicators."""

import hashlib
import re
from typing import Any, Dict


def extract_indicators(payload: str) -> Dict[str, Any]:
    """Extract IOCs and indicators from payload."""
    indicators: Dict[str, Any] = {}

    # Extract IPs
    ips = re.findall(r"\d+\.\d+\.\d+\.\d+", payload)
    if ips:
        indicators["embedded_ips"] = list(set(ips))[:10]

    # Extract URLs
    urls = re.findall(r'https?://[^\s<>"\']+', payload)
    if urls:
        indicators["urls"] = list(set(urls))[:10]

    # Extract domains
    domains = re.findall(
        r"(?i)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,}", payload
    )
    if domains:
        indicators["domains"] = list(set(domains))[:10]

    # Extract file paths
    paths = re.findall(r"(?:/[a-zA-Z0-9._-]+){2,}", payload)
    if paths:
        indicators["file_paths"] = list(set(paths))[:10]

    # Calculate payload hash
    indicators["sha256"] = hashlib.sha256(
        payload.encode(), usedforsecurity=False
    ).hexdigest()

    return indicators
