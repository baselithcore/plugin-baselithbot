"""Threat Intelligence Enricher.

Main facade for OSINT enrichment. Orchestrates queries across
multiple sources and aggregates results.
"""

from __future__ import annotations

import asyncio
from core.observability.logging import get_logger
from datetime import datetime
from typing import Dict, List, Optional, Set

from core.config.scraper import ScraperConfig
from core.scraper import Scraper

from .config import HoneypotScraperConfig, get_scraper_config
from .models import (
    DomainIntel,
    EnrichmentResult,
    IPReputation,
    ThreatLevel,
    URLAnalysis,
)
from .sources import BaseOSINTSource, get_enabled_sources

logger = get_logger(__name__)


class ThreatIntelEnricher:
    """Enriches threat intelligence with external OSINT data.

    This class orchestrates queries to multiple OSINT sources,
    aggregates results, and provides a unified view of IOC reputation.

    Example:
        ```python
        enricher = ThreatIntelEnricher()
        await enricher.initialize()

        result = await enricher.enrich(
            ips=["1.2.3.4", "5.6.7.8"],
            domains=["malware.example.com"],
            urls=["http://evil.com/payload.exe"],
        )

        print(f"High-risk IPs: {result.high_risk_ips}")
        ```
    """

    def __init__(
        self,
        config: Optional[HoneypotScraperConfig] = None,
    ):
        """Initialize the enricher.

        Args:
            config: Optional custom configuration. Uses singleton if not provided.
        """
        self.config = config or get_scraper_config()
        self._scraper: Optional[Scraper] = None
        self._sources: List[BaseOSINTSource] = []
        self._cache: Dict[str, any] = {}
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize scraper and sources.

        Must be called before using the enricher.
        """
        if self._initialized:
            return

        if not self.config.enabled:
            logger.info("OSINT enrichment is disabled")
            return

        # Create custom scraper config with BaselithCore User-Agent
        scraper_config = ScraperConfig(
            user_agent=self.config.user_agent,
            timeout_seconds=self.config.timeout_seconds,
            max_retries=self.config.max_retries,
            rate_limit_enabled=True,
            rate_limit_requests=self.config.rate_limit_per_minute,
            cache_enabled=self.config.cache_enabled,
            cache_ttl_seconds=self.config.cache_ttl_hours * 3600,
        )

        self._scraper = Scraper(config=scraper_config)
        self._sources = get_enabled_sources(self.config, self._scraper)
        self._initialized = True

        logger.info(
            f"ThreatIntelEnricher initialized with {len(self._sources)} sources "
            f"(User-Agent: {self.config.user_agent[:40]}...)"
        )

    async def close(self) -> None:
        """Close resources."""
        if self._scraper:
            await self._scraper.close()
        self._initialized = False

    async def __aenter__(self) -> "ThreatIntelEnricher":
        """Async context manager entry."""
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.close()

    async def enrich(
        self,
        ips: Optional[List[str]] = None,
        domains: Optional[List[str]] = None,
        urls: Optional[List[str]] = None,
    ) -> EnrichmentResult:
        """Enrich IOCs with OSINT data.

        Args:
            ips: List of IP addresses to enrich.
            domains: List of domains to enrich.
            urls: List of URLs to enrich.

        Returns:
            EnrichmentResult with aggregated data from all sources.
        """
        if not self._initialized or not self.config.enabled:
            return EnrichmentResult()

        result = EnrichmentResult(started_at=datetime.now())

        # Limit batch sizes
        ips = (ips or [])[: self.config.max_ips_per_batch]
        domains = (domains or [])[: self.config.max_domains_per_batch]
        urls = (urls or [])[: self.config.max_urls_per_batch]

        # Run enrichments concurrently
        tasks = []

        if ips:
            tasks.append(self._enrich_ips(ips))
        if domains:
            tasks.append(self._enrich_domains(domains))
        if urls:
            tasks.append(self._enrich_urls(urls))

        if not tasks:
            result.completed_at = datetime.now()
            return result

        try:
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Merge results
            for r in results:
                if isinstance(r, Exception):
                    logger.error(f"Enrichment task failed: {r}")
                    continue
                if isinstance(r, dict):
                    if "ips" in r:
                        result.ip_reputations.update(r["ips"])
                    elif "domains" in r:
                        result.domain_intel.update(r["domains"])
                    elif "urls" in r:
                        result.url_analyses.update(r["urls"])

        except Exception as e:
            logger.error(f"Enrichment failed: {e}")

        result.completed_at = datetime.now()

        logger.info(
            f"Enrichment complete: {len(result.ip_reputations)} IPs, "
            f"{len(result.domain_intel)} domains, "
            f"{len(result.url_analyses)} URLs "
            f"in {result.duration_seconds:.2f}s"
        )

        return result

    async def enrich_ips(self, ips: List[str]) -> Dict[str, IPReputation]:
        """Enrich only IP addresses.

        Args:
            ips: List of IP addresses.

        Returns:
            Dict mapping IP to reputation data.
        """
        result = await self._enrich_ips(ips)
        return result.get("ips", {})

    async def enrich_domains(self, domains: List[str]) -> Dict[str, DomainIntel]:
        """Enrich only domains.

        Args:
            domains: List of domain names.

        Returns:
            Dict mapping domain to intelligence data.
        """
        result = await self._enrich_domains(domains)
        return result.get("domains", {})

    async def enrich_urls(self, urls: List[str]) -> Dict[str, URLAnalysis]:
        """Enrich only URLs.

        Args:
            urls: List of URLs.

        Returns:
            Dict mapping URL to analysis data.
        """
        result = await self._enrich_urls(urls)
        return result.get("urls", {})

    async def _enrich_ips(self, ips: List[str]) -> Dict[str, Dict[str, IPReputation]]:
        """Internal IP enrichment."""
        reputations: Dict[str, IPReputation] = {}

        for ip in ips:
            # Check cache
            cache_key = f"ip:{ip}"
            if cache_key in self._cache:
                reputations[ip] = self._cache[cache_key]
                continue

            # Query all sources that support IP
            source_results: List[IPReputation] = []
            for source in self._sources:
                if source.supports_ip:
                    try:
                        result = await source.query_ip(ip)
                        if result:
                            source_results.append(result)
                    except Exception as e:
                        logger.warning(f"Source {source.name} failed for IP {ip}: {e}")

            # Aggregate results
            if source_results:
                aggregated = self._aggregate_ip_results(ip, source_results)
                reputations[ip] = aggregated
                self._cache[cache_key] = aggregated
            else:
                # No data from any source
                reputations[ip] = IPReputation(ip=ip, threat_level=ThreatLevel.UNKNOWN)

        return {"ips": reputations}

    async def _enrich_domains(
        self, domains: List[str]
    ) -> Dict[str, Dict[str, DomainIntel]]:
        """Internal domain enrichment."""
        intel: Dict[str, DomainIntel] = {}

        for domain in domains:
            cache_key = f"domain:{domain}"
            if cache_key in self._cache:
                intel[domain] = self._cache[cache_key]
                continue

            source_results: List[DomainIntel] = []
            for source in self._sources:
                if source.supports_domain:
                    try:
                        result = await source.query_domain(domain)
                        if result:
                            source_results.append(result)
                    except Exception as e:
                        logger.warning(
                            f"Source {source.name} failed for domain {domain}: {e}"
                        )

            if source_results:
                aggregated = self._aggregate_domain_results(domain, source_results)
                intel[domain] = aggregated
                self._cache[cache_key] = aggregated
            else:
                intel[domain] = DomainIntel(
                    domain=domain, threat_level=ThreatLevel.UNKNOWN
                )

        return {"domains": intel}

    async def _enrich_urls(self, urls: List[str]) -> Dict[str, Dict[str, URLAnalysis]]:
        """Internal URL enrichment."""
        analyses: Dict[str, URLAnalysis] = {}

        for url in urls:
            cache_key = f"url:{url}"
            if cache_key in self._cache:
                analyses[url] = self._cache[cache_key]
                continue

            source_results: List[URLAnalysis] = []
            for source in self._sources:
                if source.supports_url:
                    try:
                        result = await source.query_url(url)
                        if result:
                            source_results.append(result)
                    except Exception as e:
                        logger.warning(
                            f"Source {source.name} failed for URL {url}: {e}"
                        )

            if source_results:
                aggregated = self._aggregate_url_results(url, source_results)
                analyses[url] = aggregated
                self._cache[cache_key] = aggregated
            else:
                analyses[url] = URLAnalysis(url=url, threat_level=ThreatLevel.UNKNOWN)

        return {"urls": analyses}

    def _aggregate_ip_results(
        self, ip: str, results: List[IPReputation]
    ) -> IPReputation:
        """Aggregate IP reputation from multiple sources."""
        # Take highest threat level
        threat_levels = [r.threat_level for r in results]
        max_threat = max(threat_levels, key=lambda t: list(ThreatLevel).index(t))

        # Average abuse scores
        abuse_scores = [r.abuse_score for r in results if r.abuse_score > 0]
        avg_abuse = sum(abuse_scores) / len(abuse_scores) if abuse_scores else 0

        # Merge tags and sources
        all_tags: Set[str] = set()
        all_sources: Set[str] = set()
        for r in results:
            all_tags.update(r.tags)
            all_sources.update(r.sources)

        # Take any positive signal for boolean flags
        return IPReputation(
            ip=ip,
            threat_level=max_threat,
            abuse_score=avg_abuse,
            is_known_attacker=any(r.is_known_attacker for r in results),
            is_tor_exit=any(r.is_tor_exit for r in results),
            is_vpn=any(r.is_vpn for r in results),
            is_proxy=any(r.is_proxy for r in results),
            is_datacenter=any(r.is_datacenter for r in results),
            tags=list(all_tags)[:20],
            reports_count=sum(r.reports_count for r in results),
            country=next((r.country for r in results if r.country), None),
            asn=next((r.asn for r in results if r.asn), None),
            org=next((r.org for r in results if r.org), None),
            sources=list(all_sources),
            raw_data={"aggregated_from": [r.raw_data for r in results]},
        )

    def _aggregate_domain_results(
        self, domain: str, results: List[DomainIntel]
    ) -> DomainIntel:
        """Aggregate domain intelligence from multiple sources."""
        threat_levels = [r.threat_level for r in results]
        max_threat = max(threat_levels, key=lambda t: list(ThreatLevel).index(t))

        all_malware_families: Set[str] = set()
        all_tags: Set[str] = set()
        all_sources: Set[str] = set()
        all_ips: Set[str] = set()

        for r in results:
            all_malware_families.update(r.malware_families)
            all_tags.update(r.tags)
            all_sources.update(r.sources)
            all_ips.update(r.associated_ips)

        return DomainIntel(
            domain=domain,
            threat_level=max_threat,
            is_malicious=any(r.is_malicious for r in results),
            is_dga=any(r.is_dga for r in results),
            is_newly_registered=any(r.is_newly_registered for r in results),
            associated_ips=list(all_ips)[:20],
            malware_families=list(all_malware_families)[:10],
            tags=list(all_tags)[:20],
            sources=list(all_sources),
            raw_data={"aggregated_from": [r.raw_data for r in results]},
        )

    def _aggregate_url_results(
        self, url: str, results: List[URLAnalysis]
    ) -> URLAnalysis:
        """Aggregate URL analysis from multiple sources."""
        threat_levels = [r.threat_level for r in results]
        max_threat = max(threat_levels, key=lambda t: list(ThreatLevel).index(t))

        all_tags: Set[str] = set()
        all_sources: Set[str] = set()

        for r in results:
            all_tags.update(r.tags)
            all_sources.update(r.sources)

        # Take first non-null malware info
        malware_type = next(
            (r.malware_type for r in results if r.malware_type.value != "unknown"),
            results[0].malware_type,
        )
        malware_family = next(
            (r.malware_family for r in results if r.malware_family),
            None,
        )

        return URLAnalysis(
            url=url,
            threat_level=max_threat,
            is_malicious=any(r.is_malicious for r in results),
            malware_type=malware_type,
            malware_family=malware_family,
            payload_sha256=next(
                (r.payload_sha256 for r in results if r.payload_sha256), None
            ),
            first_seen=min(
                (r.first_seen for r in results if r.first_seen), default=None
            ),
            last_seen=max((r.last_seen for r in results if r.last_seen), default=None),
            tags=list(all_tags)[:20],
            sources=list(all_sources),
            raw_data={"aggregated_from": [r.raw_data for r in results]},
        )

    def clear_cache(self) -> None:
        """Clear the enrichment cache."""
        self._cache.clear()
        logger.info("Enrichment cache cleared")
