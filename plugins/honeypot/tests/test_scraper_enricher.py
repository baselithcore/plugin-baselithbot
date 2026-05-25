"""Tests for Honeypot Scraper Enricher Module.

Unit tests for the ThreatIntelEnricher and OSINT sources.
"""

from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock


from plugins.honeypot.scraper.config import HoneypotScraperConfig
from plugins.honeypot.scraper.enricher import ThreatIntelEnricher
from plugins.honeypot.scraper.models import (
    EnrichmentResult,
    IPReputation,
    MalwareType,
    ThreatLevel,
    URLAnalysis,
)
from plugins.honeypot.scraper.sources import (
    get_enabled_sources,
)


class TestThreatLevel:
    """Test ThreatLevel enum."""

    def test_threat_level_values(self) -> None:
        """Test all threat level enum values exist."""
        assert ThreatLevel.UNKNOWN.value == "unknown"
        assert ThreatLevel.CLEAN.value == "clean"
        assert ThreatLevel.LOW.value == "low"
        assert ThreatLevel.MEDIUM.value == "medium"
        assert ThreatLevel.HIGH.value == "high"
        assert ThreatLevel.CRITICAL.value == "critical"


class TestMalwareType:
    """Test MalwareType enum."""

    def test_malware_type_values(self) -> None:
        """Test key malware type enum values exist."""
        assert MalwareType.BOTNET.value == "botnet"
        assert MalwareType.RANSOMWARE.value == "ransomware"
        assert MalwareType.MINER.value == "miner"


class TestIPReputation:
    """Test IPReputation dataclass."""

    def test_ip_reputation_defaults(self) -> None:
        """Test default values for IPReputation."""
        rep = IPReputation(ip="1.2.3.4")
        assert rep.ip == "1.2.3.4"
        assert rep.threat_level == ThreatLevel.UNKNOWN
        assert rep.abuse_score == 0.0
        assert rep.is_known_attacker is False
        assert rep.tags == []
        assert rep.sources == []

    def test_is_suspicious_low_score(self) -> None:
        """Test is_suspicious returns False for low scores."""
        rep = IPReputation(ip="1.2.3.4", abuse_score=10.0)
        assert rep.is_suspicious is False

    def test_is_suspicious_high_score(self) -> None:
        """Test is_suspicious returns True for high scores."""
        rep = IPReputation(ip="1.2.3.4", abuse_score=50.0)
        assert rep.is_suspicious is True

    def test_is_suspicious_known_attacker(self) -> None:
        """Test is_suspicious returns True for known attackers."""
        rep = IPReputation(ip="1.2.3.4", is_known_attacker=True)
        assert rep.is_suspicious is True

    def test_is_suspicious_high_threat_level(self) -> None:
        """Test is_suspicious returns True for high threat level."""
        rep = IPReputation(ip="1.2.3.4", threat_level=ThreatLevel.HIGH)
        assert rep.is_suspicious is True


class TestEnrichmentResult:
    """Test EnrichmentResult dataclass."""

    def test_empty_result(self) -> None:
        """Test empty enrichment result."""
        result = EnrichmentResult()
        assert result.ip_reputations == {}
        assert result.domain_intel == {}
        assert result.url_analyses == {}
        assert result.total_queries == 0

    def test_high_risk_ips(self) -> None:
        """Test high_risk_ips property."""
        result = EnrichmentResult(
            ip_reputations={
                "1.1.1.1": IPReputation(ip="1.1.1.1", threat_level=ThreatLevel.LOW),
                "2.2.2.2": IPReputation(ip="2.2.2.2", threat_level=ThreatLevel.HIGH),
                "3.3.3.3": IPReputation(
                    ip="3.3.3.3", threat_level=ThreatLevel.CRITICAL
                ),
            }
        )
        high_risk = result.high_risk_ips
        assert len(high_risk) == 2
        assert "2.2.2.2" in high_risk
        assert "3.3.3.3" in high_risk

    def test_malicious_urls(self) -> None:
        """Test malicious_urls property."""
        result = EnrichmentResult(
            url_analyses={
                "http://good.com": URLAnalysis(
                    url="http://good.com", is_malicious=False
                ),
                "http://evil.com": URLAnalysis(
                    url="http://evil.com", is_malicious=True
                ),
            }
        )
        malicious = result.malicious_urls
        assert len(malicious) == 1
        assert "http://evil.com" in malicious

    def test_duration_calculation(self) -> None:
        """Test duration_seconds property."""
        start = datetime(2024, 1, 1, 12, 0, 0)
        end = datetime(2024, 1, 1, 12, 0, 5)
        result = EnrichmentResult(started_at=start, completed_at=end)
        assert result.duration_seconds == 5.0

    def test_to_dict(self) -> None:
        """Test to_dict method."""
        result = EnrichmentResult(
            ip_reputations={
                "1.1.1.1": IPReputation(
                    ip="1.1.1.1",
                    threat_level=ThreatLevel.HIGH,
                    abuse_score=85.0,
                    is_known_attacker=True,
                    tags=["scanner"],
                    country="US",
                )
            }
        )
        data = result.to_dict()
        assert "ip_reputations" in data
        assert "1.1.1.1" in data["ip_reputations"]
        assert data["ip_reputations"]["1.1.1.1"]["threat_level"] == "high"


class TestHoneypotScraperConfig:
    """Test HoneypotScraperConfig."""

    def test_default_config(self) -> None:
        """Test default configuration values."""
        config = HoneypotScraperConfig()
        assert config.enabled is False  # Disabled by default
        assert "BaselithCore" in config.user_agent
        assert config.cache_ttl_hours == 24
        assert config.rate_limit_per_minute == 10
        assert "urlhaus" in config.enabled_sources

    def test_stealth_user_agent(self) -> None:
        """Test stealth User-Agent is Chrome-like."""
        config = HoneypotScraperConfig()
        assert "Chrome" in config.stealth_user_agent
        assert "Mozilla/5.0" in config.stealth_user_agent


class TestOSINTSources:
    """Test OSINT source registry."""

    def test_get_enabled_sources(self) -> None:
        """Test get_enabled_sources returns correct sources."""
        config = HoneypotScraperConfig(enabled_sources=["urlhaus", "ipinfo"])
        mock_scraper = MagicMock()

        sources = get_enabled_sources(config, mock_scraper)

        assert len(sources) == 2
        source_names = [s.name for s in sources]
        assert "urlhaus" in source_names
        assert "ipinfo" in source_names

    def test_unknown_source_ignored(self) -> None:
        """Test unknown source names are ignored."""
        config = HoneypotScraperConfig(enabled_sources=["urlhaus", "nonexistent"])
        mock_scraper = MagicMock()

        sources = get_enabled_sources(config, mock_scraper)

        assert len(sources) == 1
        assert sources[0].name == "urlhaus"


class TestThreatIntelEnricher:
    """Test ThreatIntelEnricher."""

    def test_enricher_not_initialized(self) -> None:
        """Test enricher returns empty result when not initialized."""
        enricher = ThreatIntelEnricher()
        # Call without initializing should return empty
        import asyncio

        result = asyncio.get_event_loop().run_until_complete(
            enricher.enrich(ips=["1.1.1.1"])
        )
        assert result.ip_reputations == {}

    def test_enricher_disabled(self) -> None:
        """Test enricher returns empty when disabled."""
        config = HoneypotScraperConfig(enabled=False)
        enricher = ThreatIntelEnricher(config=config)

        import asyncio

        asyncio.get_event_loop().run_until_complete(enricher.initialize())
        result = asyncio.get_event_loop().run_until_complete(
            enricher.enrich(ips=["1.1.1.1"])
        )
        assert result.ip_reputations == {}

    def test_aggregation_takes_highest_threat(self) -> None:
        """Test aggregation picks highest threat level."""
        enricher = ThreatIntelEnricher()

        results = [
            IPReputation(ip="1.1.1.1", threat_level=ThreatLevel.LOW, sources=["a"]),
            IPReputation(ip="1.1.1.1", threat_level=ThreatLevel.HIGH, sources=["b"]),
            IPReputation(ip="1.1.1.1", threat_level=ThreatLevel.MEDIUM, sources=["c"]),
        ]

        aggregated = enricher._aggregate_ip_results("1.1.1.1", results)

        assert aggregated.threat_level == ThreatLevel.HIGH
        assert len(aggregated.sources) == 3

    def test_aggregation_averages_abuse_score(self) -> None:
        """Test aggregation averages abuse scores."""
        enricher = ThreatIntelEnricher()

        results = [
            IPReputation(ip="1.1.1.1", abuse_score=80.0),
            IPReputation(ip="1.1.1.1", abuse_score=60.0),
        ]

        aggregated = enricher._aggregate_ip_results("1.1.1.1", results)

        assert aggregated.abuse_score == 70.0

    def test_cache_clear(self) -> None:
        """Test cache clearing."""
        enricher = ThreatIntelEnricher()
        enricher._cache["test"] = "value"
        enricher.clear_cache()
        assert enricher._cache == {}
