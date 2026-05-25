"""RDNS (Reverse DNS) Resolver Module.

Provides async Reverse DNS resolution for IP addresses with caching,
timeout handling, and significance scoring for threat intelligence.

This module is non-blocking and designed for integration with the
Discovery tab to display domain associations for intercepted IPs.
"""

import asyncio
import ipaddress
from core.observability.logging import get_logger
import re
import socket
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, field_validator

logger = get_logger(__name__)

# Known malicious/suspicious ASN patterns
SUSPICIOUS_ASNS = frozenset(
    {
        "AS9009",  # M247 - Known for VPN/proxy abuse
        "AS16276",  # OVH - Frequently used for scanning
        "AS14061",  # DigitalOcean - High abuse volume
        "AS45102",  # Alibaba - Cloud abuse
        "AS398101",  # GoHost - Bulletproof hosting
        "AS49981",  # WorldStream - Bulletproof provider
        "AS206898",  # Stark Industries - Bulletproof hosting
        "AS44477",  # Stark Industries Solutions
        "AS202425",  # IP Volume - Known abuse
        "AS51852",  # Private Layer - Anonymous hosting
    }
)

# Known crawler/bot domain patterns
CRAWLER_PATTERNS = frozenset(
    {
        "googlebot.com",
        "search.msn.com",
        "crawl.baidu.com",
        "yandex.ru",
        "yandex.com",
        "sogou.com",
        "bingbot.com",
    }
)

VPN_PROXY_PATTERNS = frozenset(
    {
        "m247.com",
        "vultr.com",
        "linode.com",
        "digitalocean.com",
        "amazonaws.com",
        "azure.com",
        "cloudflare.com",
    }
)


class SignificanceLevel(str, Enum):
    """Significance level for RDNS results."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    NONE = "none"


class IPCategory(str, Enum):
    """Category classification for IP addresses."""

    CRAWLER = "crawler"
    VPN_PROXY = "vpn_proxy"
    HOSTING = "hosting"
    ISP = "isp"
    MALICIOUS = "malicious"
    UNKNOWN = "unknown"


# Maximum hostname length to prevent memory exhaustion
MAX_HOSTNAME_LENGTH = 255

# Regex to validate hostname format (RFC 1123)
HOSTNAME_PATTERN = re.compile(
    r"^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?"
    r"(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*$"
)


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


class RDNSResolver:
    """Async Reverse DNS resolver with caching and significance scoring.

    Features:
    - Async DNS resolution with configurable timeout
    - LRU cache with TTL for resolved hostnames
    - Batch resolution with concurrency control
    - Significance scoring based on hit count, ASN, and exploit attempts
    - Domain categorization (crawler, VPN, hosting, etc.)

    Example:
        resolver = RDNSResolver()
        result = await resolver.resolve_ip("8.8.8.8")
        print(result.hostname)  # dns.google
    """

    def __init__(
        self,
        timeout_seconds: float = 2.0,
        max_concurrent: int = 20,
        cache_ttl_seconds: int = 3600,
        max_cache_size: int = 10000,
    ):
        """Initialize RDNS resolver.

        Args:
            timeout_seconds: Timeout for each DNS lookup.
            max_concurrent: Maximum concurrent DNS queries.
            cache_ttl_seconds: Cache TTL in seconds.
            max_cache_size: Maximum cache entries.
        """
        self._timeout = timeout_seconds
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._cache_ttl = cache_ttl_seconds
        self._max_cache_size = max_cache_size
        self._cache: Dict[str, CacheEntry] = {}
        self._lock = asyncio.Lock()

    async def resolve_ip(
        self,
        ip: str,
        use_cache: bool = True,
    ) -> RDNSResult:
        """Resolve a single IP address to its hostname.

        Args:
            ip: IP address to resolve.
            use_cache: Whether to use cached results.

        Returns:
            RDNSResult with hostname and metadata.
        """
        now = datetime.now(timezone.utc)

        # Check cache
        if use_cache and ip in self._cache:
            entry = self._cache[ip]
            age = (now - entry.resolved_at).total_seconds()
            if age < entry.ttl_seconds:
                category = entry.category or self._categorize_hostname(entry.hostname)
                return RDNSResult(
                    ip=ip,
                    hostname=entry.hostname,
                    category=category,
                    resolved_at=entry.resolved_at,
                    cached=True,
                )

        # Perform DNS lookup
        hostname = None
        error = None

        try:
            async with self._semaphore:
                hostname = await asyncio.wait_for(
                    asyncio.get_event_loop().run_in_executor(
                        None,
                        self._sync_resolve,
                        ip,
                    ),
                    timeout=self._timeout,
                )
        except asyncio.TimeoutError:
            error = "timeout"
            logger.debug(f"RDNS timeout for {ip}")
        except Exception as e:
            error = str(e)
            logger.debug(f"RDNS error for {ip}: {e}")

        # Update cache
        category = self._categorize_hostname(hostname) if hostname else None
        await self._update_cache(ip, hostname, category, now)

        return RDNSResult(
            ip=ip,
            hostname=hostname,
            category=category,
            resolved_at=now,
            cached=False,
            error=error,
        )

    def _sync_resolve(self, ip: str) -> Optional[str]:
        """Synchronous DNS resolution (runs in executor).

        Security: Validates IP before lookup and sanitizes response.
        """
        # Validate IP to prevent SSRF via crafted input
        if not validate_ip_address(ip):
            logger.warning("Invalid IP rejected in RDNS lookup")
            return None

        try:
            hostname, _, _ = socket.gethostbyaddr(ip)
            # Sanitize hostname from untrusted DNS response
            return sanitize_hostname(hostname)
        except (socket.herror, socket.gaierror):
            return None

    async def _update_cache(
        self,
        ip: str,
        hostname: Optional[str],
        category: Optional[str],
        resolved_at: datetime,
    ) -> None:
        """Update cache with new entry."""
        async with self._lock:
            # Evict old entries if cache is full
            if len(self._cache) >= self._max_cache_size:
                # Remove oldest 10%
                sorted_entries = sorted(
                    self._cache.items(),
                    key=lambda x: x[1].resolved_at,
                )
                to_remove = len(self._cache) // 10
                for key, _ in sorted_entries[:to_remove]:
                    del self._cache[key]

            self._cache[ip] = CacheEntry(
                hostname=hostname,
                category=category,
                resolved_at=resolved_at,
                ttl_seconds=self._cache_ttl,
            )

    def _categorize_hostname(self, hostname: Optional[str]) -> str:
        """Categorize hostname based on known patterns."""
        if not hostname:
            return IPCategory.UNKNOWN.value

        hostname_lower = hostname.lower()

        # Check crawler patterns
        for pattern in CRAWLER_PATTERNS:
            if pattern in hostname_lower:
                return IPCategory.CRAWLER.value

        # Check VPN/proxy patterns
        for pattern in VPN_PROXY_PATTERNS:
            if pattern in hostname_lower:
                return IPCategory.VPN_PROXY.value

        # Check for generic hosting indicators
        hosting_indicators = ["vps", "server", "host", "cloud", "dedicated"]
        if any(ind in hostname_lower for ind in hosting_indicators):
            return IPCategory.HOSTING.value

        return IPCategory.ISP.value

    async def resolve_batch(
        self,
        ips: List[str],
        use_cache: bool = True,
    ) -> List[RDNSResult]:
        """Resolve multiple IPs concurrently.

        Args:
            ips: List of IP addresses to resolve.
            use_cache: Whether to use cached results.

        Returns:
            List of RDNSResult objects.
        """
        if not ips:
            return []

        tasks = [self.resolve_ip(ip, use_cache=use_cache) for ip in ips]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Handle any exceptions
        processed = []
        for ip, result in zip(ips, results):
            if isinstance(result, Exception):
                processed.append(
                    RDNSResult(
                        ip=ip,
                        error=str(result),
                    )
                )
            else:
                processed.append(result)

        return processed

    def calculate_significance(
        self,
        ip: str,
        rdns_result: RDNSResult,
        event_count: int = 0,
        has_exploit_attempt: bool = False,
        asn: Optional[str] = None,
        is_datacenter: bool = False,
        is_vpn: bool = False,
        is_proxy: bool = False,
    ) -> SignificanceLevel:
        """Calculate significance level for an IP based on multiple signals.

        Scoring:
        - Event count >= 50: +3 points (high-frequency attacker)
        - Event count >= 10: +2 points (medium-frequency)
        - Known malicious ASN: +3 points
        - Exploit attempt detected: +2 points
        - Datacenter/VPN/Proxy: +1 point

        Thresholds:
        - Score >= 3: HIGH
        - Score >= 2: MEDIUM
        - Score >= 1: LOW
        - Score < 1: NONE

        Args:
            ip: The IP address.
            rdns_result: The RDNS resolution result.
            event_count: Number of events from this IP.
            has_exploit_attempt: Whether exploit attempts were detected.
            asn: Autonomous System Number.
            is_datacenter: Whether IP is from a datacenter.
            is_vpn: Whether IP is a known VPN exit.
            is_proxy: Whether IP is a known proxy.

        Returns:
            SignificanceLevel enum value.
        """
        score = 0

        # Event count scoring
        if event_count >= 50:
            score += 3
        elif event_count >= 10:
            score += 2

        # ASN scoring
        if asn and asn.upper() in SUSPICIOUS_ASNS:
            score += 3

        # Exploit attempt scoring
        if has_exploit_attempt:
            score += 2

        # Infrastructure type scoring
        if is_datacenter or is_vpn or is_proxy:
            score += 1

        # Category-based adjustment
        if rdns_result.category == IPCategory.MALICIOUS.value:
            score += 2
        elif rdns_result.category == IPCategory.VPN_PROXY.value:
            score += 1

        # Determine level
        if score >= 3:
            return SignificanceLevel.HIGH
        elif score >= 2:
            return SignificanceLevel.MEDIUM
        elif score >= 1:
            return SignificanceLevel.LOW
        else:
            return SignificanceLevel.NONE

    def enrich_result(
        self,
        rdns_result: RDNSResult,
        event_count: int = 0,
        has_exploit_attempt: bool = False,
        asn: Optional[str] = None,
        org: Optional[str] = None,
        is_datacenter: bool = False,
        is_vpn: bool = False,
        is_proxy: bool = False,
    ) -> RDNSResult:
        """Enrich RDNS result with significance and additional metadata.

        Args:
            rdns_result: Base RDNS resolution result.
            event_count: Number of events from this IP.
            has_exploit_attempt: Whether exploit attempts were detected.
            asn: Autonomous System Number.
            org: Organization name.
            is_datacenter: Whether IP is from a datacenter.
            is_vpn: Whether IP is a known VPN exit.
            is_proxy: Whether IP is a known proxy.

        Returns:
            Enriched RDNSResult with importance set.
        """
        significance = self.calculate_significance(
            ip=rdns_result.ip,
            rdns_result=rdns_result,
            event_count=event_count,
            has_exploit_attempt=has_exploit_attempt,
            asn=asn,
            is_datacenter=is_datacenter,
            is_vpn=is_vpn,
            is_proxy=is_proxy,
        )

        return RDNSResult(
            ip=rdns_result.ip,
            hostname=rdns_result.hostname,
            importance=significance.value,
            category=rdns_result.category,
            asn=asn,
            org=org,
            resolved_at=rdns_result.resolved_at,
            cached=rdns_result.cached,
            error=rdns_result.error,
        )

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics.

        Returns:
            Dict with cache size, hit rate, etc.
        """
        return {
            "size": len(self._cache),
            "max_size": self._max_cache_size,
            "ttl_seconds": self._cache_ttl,
        }

    def clear_cache(self) -> int:
        """Clear the cache.

        Returns:
            Number of entries cleared.
        """
        count = len(self._cache)
        self._cache.clear()
        return count


# Singleton resolver instance
_resolver: Optional[RDNSResolver] = None


def get_rdns_resolver() -> RDNSResolver:
    """Get or create the singleton RDNS resolver instance."""
    global _resolver
    if _resolver is None:
        _resolver = RDNSResolver()
    return _resolver
