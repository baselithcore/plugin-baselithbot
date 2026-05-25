"""Geographic IP Service.

Provides IP geolocation for attack visualization using
free IP geolocation APIs with caching.
"""

import asyncio
from core.observability.logging import get_logger
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx

from .models import GeoLocation

logger = get_logger(__name__)


# Free GeoIP API endpoints (no API key required)
GEOIP_APIS = [
    "http://ip-api.com/json/{ip}?fields=status,country,countryCode,city,lat,lon,isp,org",
    "https://ipapi.co/{ip}/json/",
]


class GeoIPService:
    """IP Geolocation service with caching."""

    def __init__(self, cache_ttl_seconds: int = 3600):
        """Initialize GeoIP service.

        Args:
            cache_ttl_seconds: Cache TTL in seconds (default: 1 hour)
        """
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._cache_ttl = cache_ttl_seconds
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=5.0)
        return self._client

    async def close(self) -> None:
        """Close HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def lookup(self, ip: str) -> Optional[GeoLocation]:
        """Lookup IP geolocation.

        Args:
            ip: IP address to lookup

        Returns:
            GeoLocation or None if lookup fails
        """
        # Skip private/local IPs
        if self._is_private_ip(ip):
            return None

        # Check cache
        cached = self._get_cached(ip)
        if cached:
            return cached

        # Try APIs in order
        for api_url in GEOIP_APIS:
            try:
                result = await self._query_api(api_url.format(ip=ip))
                if result:
                    geo = self._parse_result(result, api_url)
                    if geo:
                        self._cache_result(ip, geo)
                        return geo
            except Exception as e:
                logger.debug(f"GeoIP API failed: {e}")
                continue

        return None

    async def _query_api(self, url: str) -> Optional[Dict[str, Any]]:
        """Query GeoIP API."""
        client = await self._get_client()
        try:
            response = await client.get(url)
            if response.status_code == 200:
                return response.json()
        except Exception:
            pass  # nosec B110
        return None

    def _parse_result(
        self,
        data: Dict[str, Any],
        api_url: str,
    ) -> Optional[GeoLocation]:
        """Parse API response into GeoLocation."""
        try:
            if "ip-api.com" in api_url:
                if data.get("status") == "success":
                    return GeoLocation(
                        country=data.get("country"),
                        country_code=data.get("countryCode"),
                        city=data.get("city"),
                        latitude=data.get("lat"),
                        longitude=data.get("lon"),
                    )
            elif "ipapi.co" in api_url:
                if not data.get("error"):
                    return GeoLocation(
                        country=data.get("country_name"),
                        country_code=data.get("country_code"),
                        city=data.get("city"),
                        latitude=data.get("latitude"),
                        longitude=data.get("longitude"),
                    )
        except Exception as e:
            logger.debug(f"Failed to parse GeoIP result: {e}")

        return None

    def _get_cached(self, ip: str) -> Optional[GeoLocation]:
        """Get cached result if not expired."""
        if ip in self._cache:
            entry = self._cache[ip]
            if (
                datetime.now(timezone.utc).timestamp() - entry["timestamp"]
                < self._cache_ttl
            ):
                return entry["geo"]
            else:
                del self._cache[ip]
        return None

    def _cache_result(self, ip: str, geo: GeoLocation) -> None:
        """Cache lookup result."""
        self._cache[ip] = {
            "geo": geo,
            "timestamp": datetime.now(timezone.utc).timestamp(),
        }

        # Limit cache size
        if len(self._cache) > 10000:
            # Remove oldest entries
            oldest = sorted(
                self._cache.items(),
                key=lambda x: x[1]["timestamp"],
            )[:1000]
            for ip, _ in oldest:
                del self._cache[ip]

    def _is_private_ip(self, ip: str) -> bool:
        """Check if IP is private/local (supports both IPv4 and IPv6).

        Args:
            ip: IP address string

        Returns:
            True if IP is private, loopback, link-local, or otherwise non-routable
        """
        import ipaddress

        # Handle special cases
        if ip in ("localhost", "unknown", ""):
            return True

        try:
            addr = ipaddress.ip_address(ip)

            # Check for loopback (127.x.x.x for IPv4, ::1 for IPv6)
            if addr.is_loopback:
                return True

            # Check for private addresses (10.x, 172.16-31.x, 192.168.x, fc00::/fd00::)
            if addr.is_private:
                return True

            # Check for link-local addresses (169.254.x.x, fe80::)
            if addr.is_link_local:
                return True

            # Check for reserved addresses
            if addr.is_reserved:
                return True

            # Check for multicast
            if addr.is_multicast:
                return True

            # IPv6 specific: site-local (deprecated but still used)
            if isinstance(addr, ipaddress.IPv6Address):
                # Site-local is deprecated but fc00::/7 (unique local) is handled by is_private
                # Also check for IPv4-mapped IPv6 addresses like ::ffff:127.0.0.1
                if addr.ipv4_mapped:
                    return self._is_private_ip(str(addr.ipv4_mapped))

            return False

        except ValueError:
            # Invalid IP address format
            logger.debug(f"Invalid IP address format: {ip}")
            return True  # Treat invalid IPs as private (don't query APIs)

    async def bulk_lookup(self, ips: List[str]) -> Dict[str, Optional[GeoLocation]]:
        """Lookup multiple IPs.

        Args:
            ips: List of IP addresses

        Returns:
            Dict mapping IP to GeoLocation
        """
        results = {}
        tasks = []

        for ip in ips:
            tasks.append(self.lookup(ip))

        lookups = await asyncio.gather(*tasks, return_exceptions=True)

        for ip, result in zip(ips, lookups):
            if isinstance(result, Exception):
                results[ip] = None
            else:
                results[ip] = result

        return results


class AttackHeatmapGenerator:
    """Generates heatmap data for attack visualization."""

    def __init__(self, geo_service: Optional[GeoIPService] = None):
        """Initialize heatmap generator.

        Args:
            geo_service: Optional GeoIP service instance
        """
        self._geo = geo_service or GeoIPService()
        self._attack_counts: Dict[str, int] = {}  # country_code -> count

    async def add_attack(self, ip: str) -> Optional[str]:
        """Add attack from IP to heatmap.

        Args:
            ip: Attacker IP

        Returns:
            Country code or None
        """
        geo = await self._geo.lookup(ip)
        if geo and geo.country_code:
            code = geo.country_code
            self._attack_counts[code] = self._attack_counts.get(code, 0) + 1
            return code
        return None

    def get_heatmap_data(self) -> List[Dict[str, Any]]:
        """Get heatmap data for visualization.

        Returns:
            List of country attack data
        """
        return [
            {"country_code": code, "attack_count": count}
            for code, count in sorted(
                self._attack_counts.items(),
                key=lambda x: x[1],
                reverse=True,
            )
        ]

    def get_top_countries(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get top attacking countries.

        Args:
            limit: Maximum results

        Returns:
            List of country data
        """
        return self.get_heatmap_data()[:limit]

    def reset(self) -> None:
        """Reset attack counts."""
        self._attack_counts.clear()


# Global service instance
_geo_service: Optional[GeoIPService] = None


def get_geo_service() -> GeoIPService:
    """Get global GeoIP service instance."""
    global _geo_service
    if _geo_service is None:
        _geo_service = GeoIPService()
    return _geo_service
