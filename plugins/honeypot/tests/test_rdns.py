"""Unit Tests for RDNS Resolution Module.

Tests async DNS resolution, caching, significance scoring,
and domain categorization.
"""

from datetime import datetime, timezone
from unittest.mock import patch

import pytest

from plugins.honeypot.discovery.rdns import (
    CacheEntry,
    RDNSResolver,
    RDNSResult,
    SignificanceLevel,
    get_rdns_resolver,
)


class TestRDNSResult:
    """Test RDNSResult Pydantic model."""

    def test_creation_minimal(self):
        """Test minimal RDNSResult creation."""
        result = RDNSResult(ip="192.168.1.1")
        assert result.ip == "192.168.1.1"
        assert result.hostname is None
        assert result.importance == "low"
        assert result.cached is False

    def test_creation_full(self):
        """Test full RDNSResult creation."""
        now = datetime.now(timezone.utc)
        result = RDNSResult(
            ip="8.8.8.8",
            hostname="dns.google",
            importance="high",
            category="isp",
            asn="AS15169",
            org="Google LLC",
            resolved_at=now,
            cached=True,
        )
        assert result.ip == "8.8.8.8"
        assert result.hostname == "dns.google"
        assert result.importance == "high"
        assert result.asn == "AS15169"


class TestRDNSResolver:
    """Test RDNSResolver class."""

    @pytest.fixture
    def resolver(self):
        """Create resolver instance for tests."""
        return RDNSResolver(
            timeout_seconds=1.0,
            max_concurrent=5,
            cache_ttl_seconds=60,
            max_cache_size=100,
        )

    def test_initialization(self, resolver):
        """Test resolver initialization."""
        assert resolver._timeout == 1.0
        assert resolver._cache_ttl == 60
        assert resolver._max_cache_size == 100
        assert len(resolver._cache) == 0

    def test_categorize_hostname_crawler(self, resolver):
        """Test crawler hostname categorization."""
        assert (
            resolver._categorize_hostname("crawl-66-249-66-1.googlebot.com")
            == "crawler"
        )
        assert (
            resolver._categorize_hostname("msnbot-157-55-39-1.search.msn.com")
            == "crawler"
        )

    def test_categorize_hostname_vpn(self, resolver):
        """Test VPN/proxy hostname categorization."""
        assert resolver._categorize_hostname("server1.m247.com") == "vpn_proxy"
        assert resolver._categorize_hostname("node-us.vultr.com") == "vpn_proxy"

    def test_categorize_hostname_hosting(self, resolver):
        """Test hosting hostname categorization."""
        assert (
            resolver._categorize_hostname("dedicated-server-123.example.com")
            == "hosting"
        )
        assert resolver._categorize_hostname("vps42.somehost.net") == "hosting"

    def test_categorize_hostname_isp(self, resolver):
        """Test ISP hostname categorization (default)."""
        assert resolver._categorize_hostname("user-123.isp.example.net") == "isp"
        assert resolver._categorize_hostname("dynamic-ip.residential.net") == "isp"

    def test_categorize_hostname_none(self, resolver):
        """Test None hostname handling."""
        assert resolver._categorize_hostname(None) == "unknown"


class TestSignificanceScoring:
    """Test significance scoring logic."""

    @pytest.fixture
    def resolver(self):
        """Create resolver for scoring tests."""
        return RDNSResolver()

    def test_high_event_count(self, resolver):
        """Test HIGH significance for high event count."""
        result = RDNSResult(ip="1.2.3.4")
        level = resolver.calculate_significance(
            ip="1.2.3.4",
            rdns_result=result,
            event_count=50,
        )
        assert level == SignificanceLevel.HIGH

    def test_suspicious_asn(self, resolver):
        """Test HIGH significance for suspicious ASN."""
        result = RDNSResult(ip="1.2.3.4")
        level = resolver.calculate_significance(
            ip="1.2.3.4",
            rdns_result=result,
            event_count=5,
            asn="AS9009",  # M247 - in SUSPICIOUS_ASNS
        )
        assert level == SignificanceLevel.HIGH

    def test_exploit_attempt(self, resolver):
        """Test MEDIUM significance for exploit attempt."""
        result = RDNSResult(ip="1.2.3.4")
        level = resolver.calculate_significance(
            ip="1.2.3.4",
            rdns_result=result,
            event_count=5,
            has_exploit_attempt=True,
        )
        assert level == SignificanceLevel.MEDIUM

    def test_datacenter_ip(self, resolver):
        """Test LOW significance for datacenter IP."""
        result = RDNSResult(ip="1.2.3.4")
        level = resolver.calculate_significance(
            ip="1.2.3.4",
            rdns_result=result,
            event_count=1,
            is_datacenter=True,
        )
        assert level == SignificanceLevel.LOW

    def test_no_signals(self, resolver):
        """Test NONE significance with no signals."""
        result = RDNSResult(ip="1.2.3.4")
        level = resolver.calculate_significance(
            ip="1.2.3.4",
            rdns_result=result,
            event_count=0,
        )
        assert level == SignificanceLevel.NONE

    def test_combined_signals(self, resolver):
        """Test combined signals yield HIGH significance."""
        result = RDNSResult(ip="1.2.3.4", category="vpn_proxy")
        level = resolver.calculate_significance(
            ip="1.2.3.4",
            rdns_result=result,
            event_count=15,  # +2 points
            has_exploit_attempt=True,  # +2 points
            is_vpn=True,  # +1 point
        )
        # Total: 5+ points → HIGH
        assert level == SignificanceLevel.HIGH


class TestCaching:
    """Test RDNS caching behavior."""

    @pytest.fixture
    def resolver(self):
        """Create resolver with short TTL for testing."""
        return RDNSResolver(
            timeout_seconds=0.5,
            cache_ttl_seconds=60,
            max_cache_size=10,
        )

    @pytest.mark.asyncio
    async def test_cache_hit(self, resolver):
        """Test cache hit returns cached result."""
        now = datetime.now(timezone.utc)

        # Pre-populate cache
        resolver._cache["8.8.8.8"] = CacheEntry(
            hostname="dns.google",
            category="isp",
            resolved_at=now,
            ttl_seconds=60,
        )

        result = await resolver.resolve_ip("8.8.8.8")
        assert result.hostname == "dns.google"
        assert result.cached is True

    @pytest.mark.asyncio
    async def test_cache_stats(self, resolver):
        """Test cache statistics."""
        stats = resolver.get_cache_stats()
        assert stats["size"] == 0
        assert stats["max_size"] == 10
        assert stats["ttl_seconds"] == 60

    @pytest.mark.asyncio
    async def test_cache_clear(self, resolver):
        """Test cache clearing."""
        # Add entry
        now = datetime.now(timezone.utc)
        resolver._cache["1.1.1.1"] = CacheEntry(
            hostname="one.one.one.one",
            category="isp",
            resolved_at=now,
        )

        assert len(resolver._cache) == 1
        cleared = resolver.clear_cache()
        assert cleared == 1
        assert len(resolver._cache) == 0


class TestBatchResolution:
    """Test batch IP resolution."""

    @pytest.fixture
    def resolver(self):
        """Create resolver for batch tests."""
        return RDNSResolver(timeout_seconds=0.5, max_concurrent=3)

    @pytest.mark.asyncio
    async def test_batch_empty(self, resolver):
        """Test batch resolution with empty list."""
        results = await resolver.resolve_batch([])
        assert results == []

    @pytest.mark.asyncio
    async def test_batch_with_mocked_dns(self, resolver):
        """Test batch resolution with mocked DNS."""
        with patch.object(resolver, "_sync_resolve") as mock_resolve:
            mock_resolve.side_effect = [
                "dns.google",
                None,
                "one.one.one.one",
            ]

            results = await resolver.resolve_batch(
                ["8.8.8.8", "192.168.1.1", "1.1.1.1"]
            )

            assert len(results) == 3
            assert results[0].hostname == "dns.google"
            assert results[1].hostname is None
            assert results[2].hostname == "one.one.one.one"


class TestEnrichResult:
    """Test result enrichment."""

    @pytest.fixture
    def resolver(self):
        """Create resolver for enrichment tests."""
        return RDNSResolver()

    def test_enrich_high_threat(self, resolver):
        """Test enrichment sets correct importance."""
        base_result = RDNSResult(
            ip="1.2.3.4",
            hostname="malicious.botnet.net",
            category="hosting",
        )

        enriched = resolver.enrich_result(
            rdns_result=base_result,
            event_count=100,
            has_exploit_attempt=True,
            asn="AS9009",
            org="M247 Ltd",
        )

        assert enriched.importance == "high"
        assert enriched.asn == "AS9009"
        assert enriched.org == "M247 Ltd"


class TestSingletonResolver:
    """Test singleton resolver instance."""

    def test_get_rdns_resolver(self):
        """Test singleton resolver creation."""
        resolver1 = get_rdns_resolver()
        resolver2 = get_rdns_resolver()
        assert resolver1 is resolver2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
