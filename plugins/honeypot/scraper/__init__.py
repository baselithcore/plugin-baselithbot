"""Honeypot Scraper Module.

Provides OSINT enrichment for threat intelligence via web scraping.
Uses the core/scraper/ module for web requests with custom User-Agent.
"""

from .config import HoneypotScraperConfig, get_scraper_config
from .enricher import ThreatIntelEnricher
from .models import DomainIntel, EnrichmentResult, IPReputation, URLAnalysis

__all__ = [
    "ThreatIntelEnricher",
    "HoneypotScraperConfig",
    "get_scraper_config",
    "IPReputation",
    "DomainIntel",
    "URLAnalysis",
    "EnrichmentResult",
]
