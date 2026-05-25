"""Unit Tests for Correlation Analyzer Module.

Tests for attacker-to-attacker correlation detection.
"""

from datetime import datetime, timedelta, timezone

import pytest

from plugins.honeypot.discovery.correlation_analyzer import (
    CorrelationAnalyzer,
    CorrelationType,
    CorrelationConfig,
)
from plugins.honeypot.models import AttackEvent, HoneypotProtocol, AttackSeverity


def _create_event(
    source_ip: str,
    honeypot_id: str,
    timestamp: datetime,
    command: str = "ls -la",
) -> AttackEvent:
    """Helper to create test events."""
    return AttackEvent(
        event_id=f"test-{source_ip}-{int(timestamp.timestamp())}",
        session_id=f"session-{source_ip}",
        honeypot_id=honeypot_id,
        source_ip=source_ip,
        source_port=12345,
        protocol=HoneypotProtocol.SSH,
        severity=AttackSeverity.MEDIUM,
        timestamp=timestamp,
        command=command,
    )


class TestCorrelationAnalyzer:
    """Test CorrelationAnalyzer functionality."""

    @pytest.fixture
    def analyzer(self) -> CorrelationAnalyzer:
        """Create test analyzer instance."""
        return CorrelationAnalyzer()

    def test_timing_correlation_detection(self, analyzer: CorrelationAnalyzer):
        """Test detection of attackers hitting same honeypot within time window."""
        now = datetime.now(timezone.utc)

        events = [
            _create_event("192.168.1.1", "honeypot-1", now),
            _create_event("192.168.1.2", "honeypot-1", now + timedelta(seconds=30)),
            _create_event("192.168.1.3", "honeypot-1", now + timedelta(seconds=120)),
        ]

        correlations, metadata = analyzer.analyze(events)

        # IP1 and IP2 should be correlated (30s apart)
        timing_corrs = [
            c for c in correlations if c.correlation_type == CorrelationType.TIMING
        ]
        assert len(timing_corrs) >= 1

        # Check that at least one correlation involves IP1 and IP2
        ips_in_corrs = set()
        for c in timing_corrs:
            ips_in_corrs.add(c.source_ip)
            ips_in_corrs.add(c.target_ip)

        assert "192.168.1.1" in ips_in_corrs or "192.168.1.2" in ips_in_corrs

    def test_cross_honeypot_detection(self, analyzer: CorrelationAnalyzer):
        """Test detection of IPs targeting multiple honeypots."""
        now = datetime.now(timezone.utc)

        # Two IPs each targeting 2 honeypots
        events = [
            _create_event("10.0.0.1", "honeypot-1", now),
            _create_event("10.0.0.1", "honeypot-2", now + timedelta(minutes=5)),
            _create_event("10.0.0.2", "honeypot-1", now + timedelta(minutes=10)),
            _create_event("10.0.0.2", "honeypot-2", now + timedelta(minutes=15)),
        ]

        correlations, metadata = analyzer.analyze(events)

        multi_hp = analyzer.get_multi_honeypot_ips()
        assert "10.0.0.1" in multi_hp
        assert "10.0.0.2" in multi_hp

        # Both should have targeted 2 honeypots
        assert len(multi_hp["10.0.0.1"]) == 2
        assert len(multi_hp["10.0.0.2"]) == 2

    def test_pattern_correlation_detection(self, analyzer: CorrelationAnalyzer):
        """Test detection of attackers using similar commands."""
        now = datetime.now(timezone.utc)

        # Two IPs using same commands
        events = [
            _create_event("172.16.0.1", "honeypot-1", now, command="cat /etc/passwd"),
            _create_event(
                "172.16.0.1",
                "honeypot-1",
                now + timedelta(seconds=10),
                command="whoami",
            ),
            _create_event(
                "172.16.0.2",
                "honeypot-2",
                now + timedelta(minutes=60),
                command="cat /etc/passwd",
            ),
            _create_event(
                "172.16.0.2",
                "honeypot-2",
                now + timedelta(minutes=61),
                command="whoami",
            ),
        ]

        correlations, metadata = analyzer.analyze(events)

        pattern_corrs = [
            c for c in correlations if c.correlation_type == CorrelationType.PATTERN
        ]

        # Should detect pattern correlation
        assert len(pattern_corrs) >= 1

    def test_infrastructure_correlation_detection(self, analyzer: CorrelationAnalyzer):
        """Test detection of attackers from same subnet."""
        now = datetime.now(timezone.utc)

        # IPs from same /24 subnet
        events = [
            _create_event("192.168.100.10", "honeypot-1", now),
            _create_event("192.168.100.20", "honeypot-1", now + timedelta(hours=1)),
            _create_event("192.168.100.30", "honeypot-1", now + timedelta(hours=2)),
        ]

        correlations, metadata = analyzer.analyze(events)

        infra_corrs = [
            c
            for c in correlations
            if c.correlation_type == CorrelationType.INFRASTRUCTURE
        ]

        # Should detect infrastructure correlation (same /24)
        assert len(infra_corrs) >= 1

    def test_correlation_count_tracking(self, analyzer: CorrelationAnalyzer):
        """Test that correlation counts are tracked per IP."""
        now = datetime.now(timezone.utc)

        events = [
            _create_event("10.1.0.1", "hp-1", now),
            _create_event("10.1.0.1", "hp-2", now + timedelta(seconds=10)),
            _create_event("10.1.0.2", "hp-1", now + timedelta(seconds=20)),
            _create_event("10.1.0.2", "hp-2", now + timedelta(seconds=30)),
        ]

        analyzer.analyze(events)
        counts = analyzer.get_ip_correlation_count()

        # Both IPs should have correlation counts >= 1
        assert counts.get("10.1.0.1", 0) >= 1
        assert counts.get("10.1.0.2", 0) >= 1


class TestCorrelationConfig:
    """Test CorrelationConfig dataclass."""

    def test_default_values(self):
        """Test default configuration values."""
        config = CorrelationConfig()

        assert config.timing_window_seconds == 60.0
        assert config.min_pattern_similarity == 0.7
        assert config.min_cross_honeypot_count == 2
        assert config.same_subnet_mask == 24

    def test_custom_values(self):
        """Test custom configuration values."""
        config = CorrelationConfig(
            timing_window_seconds=120.0,
            min_pattern_similarity=0.8,
        )

        assert config.timing_window_seconds == 120.0
        assert config.min_pattern_similarity == 0.8


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
