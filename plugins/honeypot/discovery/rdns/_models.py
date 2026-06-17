"""Pydantic models, dataclass, and utility functions for RDNS resolver."""

import ipaddress
import re
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, field_validator

from core.observability.logging import get_logger

from ._constants import MAX_HOSTNAME_LENGTH, HOSTNAME_PATTERN

logger = get_logger(__name__)


def validate_ip_address(ip: str) -> bool:
    """Validate IP address format to prevent injection attacks.

    Args:
        ip: IP address string to validate.

    Returns:
        True if valid IPv4 or IPv6 address.
    """
    try:
        ipaddress.ip_address(ip)
        return True
    except ValueError:
        return False


def sanitize_hostname(hostname: Optional[str]) -> Optional[str]:
    """Sanitize hostname from DNS response.

    Prevents malicious PTR records from injecting dangerous content.

    Args:
        hostname: Raw hostname from DNS lookup.

    Returns:
        Sanitized hostname or None if invalid.
    """
    if not hostname:
        return None

    # Truncate to max length
    hostname = hostname[:MAX_HOSTNAME_LENGTH]

    # Remove any control characters or null bytes
    hostname = re.sub(r"[\x00-\x1f\x7f-\x9f]", "", hostname)

    # Validate format
    if not HOSTNAME_PATTERN.match(hostname):
        # Log sanitized for security - don't log raw untrusted input
        logger.warning("Invalid hostname format detected, sanitizing")
        # Return None for invalid hostnames
        return None

    return hostname.lower()


class RDNSResult(BaseModel):
    """Result of Reverse DNS resolution with enrichment."""

    ip: str
    hostname: Optional[str] = None

    @field_validator("ip")
    @classmethod
    def validate_ip(cls, v: str) -> str:
        """Validate IP address format."""
        if not validate_ip_address(v):
            raise ValueError("Invalid IP address format")
        return v

    importance: str = "low"
    category: Optional[str] = None
    asn: Optional[str] = None
    org: Optional[str] = None
    resolved_at: Optional[datetime] = None
    cached: bool = False
    error: Optional[str] = None


class RDNSEnrichmentResponse(BaseModel):
    """Response containing batch RDNS enrichment results."""

    results: List[RDNSResult]
    total: int
    resolved_count: int
    cached_count: int
    processing_time_ms: float


@dataclass
class CacheEntry:
    """Cache entry for RDNS results."""

    hostname: Optional[str]
    category: Optional[str]
    resolved_at: datetime
    ttl_seconds: int = 3600  # 1 hour default
