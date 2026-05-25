"""Utilities for C&C Detector."""

import math
import re
from collections import Counter
from datetime import datetime
from typing import Any, Optional, Set

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
    """Calculate Shannon entropy of text."""
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


def is_safe_domain(domain: str) -> bool:
    """Check if domain is known-safe (CDN, major services, etc.)."""
    safe_patterns = [
        "google.com",
        "googleapis.com",
        "gstatic.com",
        "microsoft.com",
        "windows.com",
        "azure.com",
        "amazon.com",
        "amazonaws.com",
        "cloudfront.net",
        "cloudflare.com",
        "akamai.net",
        "facebook.com",
        "fbcdn.net",
        "github.com",
        "githubusercontent.com",
        "jquery.com",
        "cdnjs.com",
        "localhost",
        "local",
    ]
    return any(pattern in domain for pattern in safe_patterns)


def extract_domains(event: AttackEvent) -> Set[str]:
    """Extract domain names from event data."""
    domains: Set[str] = set()

    # Domain regex pattern
    domain_pattern = r"(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}"

    # Search in various fields
    search_fields = [
        event.raw_data,
        event.command,
        event.http_path,
        event.http_body,
    ]

    # Also check HTTP headers
    if event.http_headers:
        search_fields.append(str(event.http_headers))

    for field in search_fields:
        if field:
            matches = re.findall(domain_pattern, field)
            for match in matches:
                # Filter out common/safe domains
                if not is_safe_domain(match.lower()):
                    domains.add(match.lower())

    return domains
