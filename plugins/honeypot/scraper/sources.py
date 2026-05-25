"""OSINT Sources for threat intelligence enrichment.

Provides abstract base and concrete implementations for querying
external OSINT sources like URLhaus, ThreatFox, and more.
"""

from __future__ import annotations

from core.observability.logging import get_logger
from abc import ABC
from datetime import datetime
from typing import Dict, List, Optional, Protocol

from core.scraper import Scraper

from .config import HoneypotScraperConfig
from .models import (
    DomainIntel,
    IPReputation,
    MalwareType,
    ThreatLevel,
    URLAnalysis,
)

logger = get_logger(__name__)


class OSINTSource(Protocol):
    """Protocol for OSINT data sources."""

    name: str
    base_url: str

    async def query_ip(self, ip: str) -> Optional[IPReputation]:
        """Query IP reputation."""
        ...

    async def query_domain(self, domain: str) -> Optional[DomainIntel]:
        """Query domain intelligence."""
        ...

    async def query_url(self, url: str) -> Optional[URLAnalysis]:
        """Query URL analysis."""
        ...


class BaseOSINTSource(ABC):
    """Abstract base class for OSINT sources."""

    name: str = "base"
    base_url: str = ""
    supports_ip: bool = False
    supports_domain: bool = False
    supports_url: bool = False

    def __init__(
        self,
        config: HoneypotScraperConfig,
        scraper: Scraper,
    ):
        """Initialize OSINT source.

        Args:
            config: Honeypot scraper configuration.
            scraper: Scraper instance for HTTP requests.
        """
        self.config = config
        self.scraper = scraper

    async def query_ip(self, ip: str) -> Optional[IPReputation]:
        """Query IP reputation. Override in subclass."""
        return None

    async def query_domain(self, domain: str) -> Optional[DomainIntel]:
        """Query domain intelligence. Override in subclass."""
        return None

    async def query_url(self, url: str) -> Optional[URLAnalysis]:
        """Query URL analysis. Override in subclass."""
        return None

    def _log_query(self, ioc_type: str, value: str) -> None:
        """Log query if enabled."""
        if self.config.log_requests:
            logger.debug(f"[{self.name}] Querying {ioc_type}: {value[:50]}...")


class URLhausSource(BaseOSINTSource):
    """URLhaus malware URL database source.

    URLhaus is a project by abuse.ch that collects malicious URLs.
    Provides free API access without authentication.

    API Docs: https://urlhaus-api.abuse.ch/
    """

    name = "urlhaus"
    base_url = "https://urlhaus-api.abuse.ch/v1"
    supports_url = True
    supports_domain = True

    async def query_url(self, url: str) -> Optional[URLAnalysis]:
        """Query URLhaus for URL analysis."""
        self._log_query("url", url)

        try:
            # URLhaus uses POST for queries
            api_url = f"{self.base_url}/url/"

            page, data = await self.scraper.scrape(
                api_url,
                extractors=["text"],
            )

            if not page.is_success:
                return None

            # Parse JSON response from page text
            import json

            try:
                result = json.loads(data.text or "{}")
            except json.JSONDecodeError:
                return None

            if result.get("query_status") != "ok":
                return None

            # Map URLhaus data to our model
            threat = result.get("threat", "unknown").lower()
            malware_type = self._map_threat_type(threat)

            return URLAnalysis(
                url=url,
                threat_level=ThreatLevel.HIGH
                if result.get("url_status") == "online"
                else ThreatLevel.MEDIUM,
                is_malicious=True,
                malware_type=malware_type,
                malware_family=result.get("tags", [None])[0]
                if result.get("tags")
                else None,
                first_seen=self._parse_date(result.get("date_added")),
                last_seen=self._parse_date(result.get("last_online")),
                reporter=result.get("reporter"),
                tags=result.get("tags", []),
                sources=[self.name],
                raw_data=result,
            )

        except Exception as e:
            logger.warning(f"[{self.name}] URL query failed: {e}")
            return None

    async def query_domain(self, domain: str) -> Optional[DomainIntel]:
        """Query URLhaus for domain-associated malware."""
        self._log_query("domain", domain)

        try:
            api_url = f"{self.base_url}/host/"

            page, data = await self.scraper.scrape(
                api_url,
                extractors=["text"],
            )

            if not page.is_success or not data.text:
                return None

            import json

            result = json.loads(data.text)

            if result.get("query_status") != "ok":
                return None

            url_count = result.get("url_count", 0)
            urls = result.get("urls", [])

            # Extract malware families from associated URLs
            malware_families = list(
                set(tag for url in urls for tag in url.get("tags", []) if tag)
            )[:10]

            return DomainIntel(
                domain=domain,
                threat_level=ThreatLevel.HIGH if url_count > 5 else ThreatLevel.MEDIUM,
                is_malicious=url_count > 0,
                malware_families=malware_families,
                tags=[f"urls:{url_count}"],
                sources=[self.name],
                raw_data=result,
            )

        except Exception as e:
            logger.warning(f"[{self.name}] Domain query failed: {e}")
            return None

    def _map_threat_type(self, threat: str) -> MalwareType:
        """Map URLhaus threat string to MalwareType enum."""
        mapping = {
            "malware_download": MalwareType.DROPPER,
            "cryptominer": MalwareType.MINER,
            "ransomware": MalwareType.RANSOMWARE,
            "botnet_cc": MalwareType.BOTNET,
            "trojan": MalwareType.TROJAN,
        }
        return mapping.get(threat, MalwareType.UNKNOWN)

    def _parse_date(self, date_str: Optional[str]) -> Optional[datetime]:
        """Parse URLhaus date format."""
        if not date_str:
            return None
        try:
            return datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            return None


class ThreatFoxSource(BaseOSINTSource):
    """ThreatFox IOC aggregator source.

    ThreatFox is a project by abuse.ch for sharing IOCs with the community.
    Free API without authentication.

    API Docs: https://threatfox-api.abuse.ch/
    """

    name = "threatfox"
    base_url = "https://threatfox-api.abuse.ch/api/v1"
    supports_ip = True
    supports_domain = True

    async def query_ip(self, ip: str) -> Optional[IPReputation]:
        """Query ThreatFox for IP IOCs."""
        self._log_query("ip", ip)

        try:
            page, data = await self.scraper.scrape(
                self.base_url,
                extractors=["text"],
            )

            if not page.is_success or not data.text:
                return None

            import json

            result = json.loads(data.text)

            if result.get("query_status") != "ok":
                return None

            iocs = result.get("data", [])
            if not iocs:
                return IPReputation(
                    ip=ip,
                    threat_level=ThreatLevel.CLEAN,
                    sources=[self.name],
                )

            # Aggregate data from all matching IOCs
            malware_families = list(
                set(
                    ioc.get("malware_printable", "")
                    for ioc in iocs
                    if ioc.get("malware_printable")
                )
            )
            tags = list(set(tag for ioc in iocs for tag in ioc.get("tags", [])))
            confidence_avg = sum(ioc.get("confidence_level", 0) for ioc in iocs) / len(
                iocs
            )

            return IPReputation(
                ip=ip,
                threat_level=self._confidence_to_threat(confidence_avg),
                abuse_score=confidence_avg,
                is_known_attacker=True,
                tags=tags[:20],
                sources=[self.name],
                raw_data={"iocs": iocs[:10], "malware_families": malware_families},
            )

        except Exception as e:
            logger.warning(f"[{self.name}] IP query failed: {e}")
            return None

    async def query_domain(self, domain: str) -> Optional[DomainIntel]:
        """Query ThreatFox for domain IOCs."""
        self._log_query("domain", domain)

        try:
            page, data = await self.scraper.scrape(
                self.base_url,
                extractors=["text"],
            )

            if not page.is_success or not data.text:
                return None

            import json

            result = json.loads(data.text)

            if result.get("query_status") != "ok":
                return None

            iocs = result.get("data", [])
            if not iocs:
                return DomainIntel(
                    domain=domain,
                    threat_level=ThreatLevel.CLEAN,
                    sources=[self.name],
                )

            malware_families = list(
                set(
                    ioc.get("malware_printable", "")
                    for ioc in iocs
                    if ioc.get("malware_printable")
                )
            )
            confidence_avg = sum(ioc.get("confidence_level", 0) for ioc in iocs) / len(
                iocs
            )

            return DomainIntel(
                domain=domain,
                threat_level=self._confidence_to_threat(confidence_avg),
                is_malicious=True,
                malware_families=malware_families[:10],
                sources=[self.name],
                raw_data={"iocs": iocs[:10]},
            )

        except Exception as e:
            logger.warning(f"[{self.name}] Domain query failed: {e}")
            return None

    def _confidence_to_threat(self, confidence: float) -> ThreatLevel:
        """Convert ThreatFox confidence level to ThreatLevel."""
        if confidence >= 80:
            return ThreatLevel.CRITICAL
        elif confidence >= 60:
            return ThreatLevel.HIGH
        elif confidence >= 40:
            return ThreatLevel.MEDIUM
        elif confidence > 0:
            return ThreatLevel.LOW
        return ThreatLevel.UNKNOWN


class IPInfoSource(BaseOSINTSource):
    """IPinfo.io for basic IP geolocation and ASN data.

    Provides free tier with rate limits.

    API Docs: https://ipinfo.io/developers
    """

    name = "ipinfo"
    base_url = "https://ipinfo.io"
    supports_ip = True

    async def query_ip(self, ip: str) -> Optional[IPReputation]:
        """Query IPinfo for IP metadata (not reputation, but enrichment)."""
        self._log_query("ip", ip)

        try:
            api_url = f"{self.base_url}/{ip}/json"

            page, data = await self.scraper.scrape(
                api_url,
                extractors=["text"],
            )

            if not page.is_success or not data.text:
                return None

            import json

            result = json.loads(data.text)

            if "error" in result:
                return None

            # IPinfo provides enrichment, not reputation
            # We mark datacenter/hosting IPs as slightly suspicious
            org = result.get("org", "")
            is_datacenter = any(
                kw in org.lower()
                for kw in ["hosting", "datacenter", "cloud", "aws", "azure", "google"]
            )

            return IPReputation(
                ip=ip,
                threat_level=ThreatLevel.LOW if is_datacenter else ThreatLevel.UNKNOWN,
                is_datacenter=is_datacenter,
                country=result.get("country"),
                asn=result.get("org", "").split(" ")[0] if result.get("org") else None,
                org=result.get("org"),
                sources=[self.name],
                raw_data=result,
            )

        except Exception as e:
            logger.warning(f"[{self.name}] IP query failed: {e}")
            return None


class AbuseIPDBSource(BaseOSINTSource):
    """AbuseIPDB source (requires API key).

    Premier IP reputation database with confidence scores.

    API Docs: https://docs.abuseipdb.com/
    """

    name = "abuseipdb"
    base_url = "https://api.abuseipdb.com/api/v2"
    supports_ip = True

    async def query_ip(self, ip: str) -> Optional[IPReputation]:
        """Query AbuseIPDB for IP reputation."""
        if not self.config.abuseipdb_api_key:
            return None

        self._log_query("ip", ip)

        try:
            _api_url = f"{self.base_url}/check?ipAddress={ip}&maxAgeInDays=90&verbose"

            # Note: Would need custom headers for API key
            # For now, return None if no key
            # This is a placeholder for when user adds API key

            return None

        except Exception as e:
            logger.warning(f"[{self.name}] IP query failed: {e}")
            return None


# Registry of available sources
OSINT_SOURCES: Dict[str, type[BaseOSINTSource]] = {
    "urlhaus": URLhausSource,
    "threatfox": ThreatFoxSource,
    "ipinfo": IPInfoSource,
    "abuseipdb": AbuseIPDBSource,
}


def get_enabled_sources(
    config: HoneypotScraperConfig,
    scraper: Scraper,
) -> List[BaseOSINTSource]:
    """Get list of enabled OSINT sources.

    Args:
        config: Honeypot scraper configuration.
        scraper: Scraper instance for HTTP requests.

    Returns:
        List of initialized OSINT source instances.
    """
    sources = []
    for source_name in config.enabled_sources:
        source_class = OSINT_SOURCES.get(source_name)
        if source_class:
            sources.append(source_class(config, scraper))
            logger.debug(f"Enabled OSINT source: {source_name}")
        else:
            logger.warning(f"Unknown OSINT source: {source_name}")
    return sources
