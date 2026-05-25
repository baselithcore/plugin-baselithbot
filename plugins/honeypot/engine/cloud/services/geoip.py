"""GeoIP Service - IP Geolocation and ASN Lookup.

Provides IP enrichment using MaxMind GeoLite2 databases or fallback services.
"""

import ipaddress
from core.observability.logging import get_logger
from pathlib import Path
from typing import Any, Dict, Optional

from ..models import CloudSession

logger = get_logger(__name__)


class GeoIPService:
    """IP geolocation and ASN lookup service.

    Supports:
    - MaxMind GeoLite2 databases (if installed)
    - Fallback to basic IP classification
    """

    def __init__(
        self,
        geoip_db_path: Optional[str] = None,
        asn_db_path: Optional[str] = None,
    ):
        """Initialize GeoIP service.

        Args:
            geoip_db_path: Path to GeoLite2-City.mmdb
            asn_db_path: Path to GeoLite2-ASN.mmdb
        """
        self._geoip_reader = None
        self._asn_reader = None
        self._initialized = False

        # Try to load MaxMind databases
        self._init_maxmind(geoip_db_path, asn_db_path)

    def _init_maxmind(
        self,
        geoip_db_path: Optional[str],
        asn_db_path: Optional[str],
    ) -> None:
        """Initialize MaxMind GeoLite2 readers."""
        try:
            import geoip2.database

            # Default paths for GeoLite2 databases
            default_geoip = Path("/usr/share/GeoIP/GeoLite2-City.mmdb")
            default_asn = Path("/usr/share/GeoIP/GeoLite2-ASN.mmdb")

            # Try custom paths first, then defaults
            geoip_path = Path(geoip_db_path) if geoip_db_path else default_geoip
            asn_path = Path(asn_db_path) if asn_db_path else default_asn

            if geoip_path.exists():
                self._geoip_reader = geoip2.database.Reader(str(geoip_path))
                logger.info(f"Loaded GeoIP database: {geoip_path}")

            if asn_path.exists():
                self._asn_reader = geoip2.database.Reader(str(asn_path))
                logger.info(f"Loaded ASN database: {asn_path}")

            self._initialized = bool(self._geoip_reader or self._asn_reader)

        except ImportError:
            logger.debug("geoip2 not installed, using fallback classification")
        except Exception as e:
            logger.warning(f"Failed to initialize MaxMind databases: {e}")

    def lookup(self, ip: str) -> Optional[Dict[str, Any]]:
        """Lookup geolocation and ASN data for an IP address.

        Args:
            ip: IP address to lookup

        Returns:
            Dictionary with geolocation data or None
        """
        # Skip private/reserved IPs
        if self._is_private_ip(ip):
            return self._classify_private_ip(ip)

        result: Dict[str, Any] = {
            "ip": ip,
            "country": None,
            "country_code": None,
            "city": None,
            "latitude": None,
            "longitude": None,
            "asn": None,
            "org": None,
            "is_private": False,
            "is_datacenter": False,
        }

        # MaxMind GeoIP lookup
        if self._geoip_reader:
            try:
                response = self._geoip_reader.city(ip)
                result["country"] = response.country.name
                result["country_code"] = response.country.iso_code
                result["city"] = response.city.name
                result["latitude"] = response.location.latitude
                result["longitude"] = response.location.longitude
            except Exception as e:
                logger.debug(f"GeoIP lookup failed for {ip}: {e}")

        # MaxMind ASN lookup
        if self._asn_reader:
            try:
                response = self._asn_reader.asn(ip)
                result["asn"] = f"AS{response.autonomous_system_number}"
                result["org"] = response.autonomous_system_organization

                # Detect common cloud/datacenter ASNs
                result["is_datacenter"] = self._is_datacenter_asn(
                    response.autonomous_system_number,
                    response.autonomous_system_organization or "",
                )
            except Exception as e:
                logger.debug(f"ASN lookup failed for {ip}: {e}")

        return result if any(v for k, v in result.items() if k != "ip") else None

    def enrich_session(self, session: CloudSession) -> None:
        """Enrich a CloudSession with geolocation data.

        Args:
            session: CloudSession to enrich
        """
        geo_data = self.lookup(session.source_ip)

        if geo_data:
            session.geo_country = geo_data.get("country_code")
            session.geo_city = geo_data.get("city")
            session.asn = geo_data.get("asn")
            session.org = geo_data.get("org")

    def _is_private_ip(self, ip: str) -> bool:
        """Check if IP is private/reserved."""
        try:
            addr = ipaddress.ip_address(ip)
            return (
                addr.is_private
                or addr.is_loopback
                or addr.is_link_local
                or addr.is_reserved
                or addr.is_multicast
            )
        except ValueError:
            return False

    def _classify_private_ip(self, ip: str) -> Dict[str, Any]:
        """Classify private/reserved IP addresses."""
        try:
            addr = ipaddress.ip_address(ip)

            classification = "unknown"
            if addr.is_loopback:
                classification = "loopback"
            elif addr.is_link_local:
                classification = "link_local"
            elif addr.is_private:
                # Classify by private range
                ip_str = str(addr)
                if ip_str.startswith("10."):
                    classification = "private_class_a"
                elif ip_str.startswith("172."):
                    classification = "private_class_b"
                elif ip_str.startswith("192.168."):
                    classification = "private_class_c"
                else:
                    classification = "private"
            elif addr.is_reserved:
                classification = "reserved"

            return {
                "ip": ip,
                "is_private": True,
                "classification": classification,
                "country": None,
                "city": None,
                "asn": None,
                "org": None,
            }
        except ValueError:
            return {"ip": ip, "is_private": False, "error": "invalid_ip"}

    def _is_datacenter_asn(self, asn: int, org: str) -> bool:
        """Check if ASN belongs to a known cloud/datacenter provider."""
        # Major cloud provider ASNs
        datacenter_asns = {
            # AWS
            16509,
            14618,
            7224,
            # Azure
            8075,
            8068,
            8069,
            # Google Cloud
            15169,
            396982,
            # DigitalOcean
            14061,
            # Linode
            63949,
            # Vultr
            20473,
            # OVH
            16276,
            # Hetzner
            24940,
            # Cloudflare
            13335,
            # Alibaba Cloud
            45102,
            # Oracle Cloud
            31898,
        }

        if asn in datacenter_asns:
            return True

        # Check org name for common patterns
        datacenter_keywords = [
            "amazon",
            "aws",
            "azure",
            "microsoft",
            "google",
            "digitalocean",
            "linode",
            "vultr",
            "ovh",
            "hetzner",
            "cloudflare",
            "alibaba",
            "oracle",
            "hosting",
            "datacenter",
            "cloud",
            "vps",
        ]

        org_lower = org.lower()
        return any(kw in org_lower for kw in datacenter_keywords)

    @property
    def is_available(self) -> bool:
        """Check if GeoIP service is available."""
        return self._initialized

    def close(self) -> None:
        """Close database readers."""
        if self._geoip_reader:
            self._geoip_reader.close()
        if self._asn_reader:
            self._asn_reader.close()


# Singleton instance
_geoip_service: Optional[GeoIPService] = None


def get_geoip_service() -> GeoIPService:
    """Get singleton GeoIP service instance."""
    global _geoip_service
    if _geoip_service is None:
        _geoip_service = GeoIPService()
    return _geoip_service
