"""Honeypot Scraper Configuration.

Configuration for OSINT enrichment and web scraping within the honeypot plugin.
"""

from __future__ import annotations

from core.observability.logging import get_logger
from core.config.env import PROJECT_ENV_FILE
from typing import List, Optional, Self

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = get_logger(__name__)


class HoneypotScraperConfig(BaseSettings):
    """Configuration for honeypot OSINT scraping.

    All settings can be overridden via environment variables with HONEYPOT_OSINT_ prefix.
    """

    model_config = SettingsConfigDict(
        env_prefix="HONEYPOT_OSINT_",
        env_file=str(PROJECT_ENV_FILE),
        extra="ignore",
    )

    # Feature toggle
    enabled: bool = Field(
        default=False,
        description="Enable OSINT enrichment for threat intelligence",
    )

    # User-Agent configuration - BaselithCore for stealth
    user_agent_name: str = Field(
        default="BaselithCore",
        description="Name of the bot in the User-Agent string (e.g. 'BaselithCore')",
    )
    user_agent: str = Field(
        default="Mozilla/5.0 (compatible; BaselithCore/1.0; +security-research)",
        description="Custom User-Agent for OSINT queries",
    )
    stealth_user_agent: str = Field(
        default=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        description="Stealth User-Agent for C&C investigation (mimics real browser)",
    )

    # Rate limiting
    rate_limit_per_minute: int = Field(
        default=10,
        description="Maximum OSINT requests per minute globally",
        ge=1,
        le=60,
    )
    rate_limit_per_source: int = Field(
        default=5,
        description="Maximum requests per minute per source",
        ge=1,
        le=30,
    )

    # Caching
    cache_enabled: bool = Field(
        default=True,
        description="Enable response caching for OSINT queries",
    )
    cache_ttl_hours: int = Field(
        default=24,
        description="Cache TTL in hours for OSINT responses",
        ge=1,
        le=168,  # Max 1 week
    )

    # Enabled sources (no API key required)
    enabled_sources: List[str] = Field(
        default_factory=lambda: ["urlhaus", "threatfox", "ipinfo"],
        description="List of enabled OSINT sources",
    )

    # API keys (optional, for enhanced sources)
    abuseipdb_api_key: Optional[str] = Field(
        default=None,
        description="AbuseIPDB API key for IP reputation",
    )
    virustotal_api_key: Optional[str] = Field(
        default=None,
        description="VirusTotal API key for file/URL analysis",
    )
    alienvault_api_key: Optional[str] = Field(
        default=None,
        description="AlienVault OTX API key",
    )

    # Request settings
    timeout_seconds: float = Field(
        default=15.0,
        description="Timeout for OSINT requests",
        ge=5.0,
        le=60.0,
    )
    max_retries: int = Field(
        default=2,
        description="Maximum retry attempts for failed requests",
        ge=0,
        le=5,
    )

    # Enrichment limits
    max_ips_per_batch: int = Field(
        default=20,
        description="Maximum IPs to enrich in a single batch",
        ge=1,
        le=100,
    )
    max_domains_per_batch: int = Field(
        default=10,
        description="Maximum domains to enrich in a single batch",
        ge=1,
        le=50,
    )
    max_urls_per_batch: int = Field(
        default=10,
        description="Maximum URLs to enrich in a single batch",
        ge=1,
        le=50,
    )

    # Logging
    log_requests: bool = Field(
        default=True,
        description="Log OSINT requests for debugging",
    )

    @model_validator(mode="after")
    def construct_user_agent(self) -> Self:
        """Construct User-Agent from name if not explicitly set."""
        # Check if user_agent was set by env var or constructor
        # We assume if it equals the default string AND user_agent_name is set to something else,
        # we should update it.

        # Default string for comparison
        default_ua = "Mozilla/5.0 (compatible; BaselithCore/1.0; +security-research)"

        # If user_agent is still the default but user_agent_name has changed (e.g. via .env),
        # rebuild the string.
        if self.user_agent == default_ua and self.user_agent_name != "BaselithCore":
            self.user_agent = f"Mozilla/5.0 (compatible; {self.user_agent_name}/1.0; +security-research)"

        return self


# Singleton instance
_config_instance: Optional[HoneypotScraperConfig] = None


def get_scraper_config() -> HoneypotScraperConfig:
    """Get or create the honeypot scraper configuration singleton."""
    global _config_instance
    if _config_instance is None:
        _config_instance = HoneypotScraperConfig()
        logger.debug("Initialized HoneypotScraperConfig")
    return _config_instance
