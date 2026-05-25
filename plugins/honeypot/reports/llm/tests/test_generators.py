"""Unit Tests for LLM Report Generators.

Tests the modular generator components.
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock

from ...models import (
    ThreatSummary,
    ReportConfig,
    ReportType,
    AttackTimelineEntry,
    GeoDistribution,
    BotnetSummary,
)
from ..generators import ExecutiveSummaryGenerator, ThreatAnalysisGenerator


@pytest.fixture
def mock_llm_service():
    """Create mock LLM service."""
    llm = Mock()
    llm.generate_response = AsyncMock(return_value="Generated content")
    return llm


@pytest.fixture
def sample_threat_summary():
    """Create sample threat summary."""
    return ThreatSummary(
        total_events=1000,
        total_attacks=800,
        unique_attackers=50,
        unique_ips=45,
        critical_events=5,
        high_events=20,
        detected_botnets=2,
        potential_cc_servers=3,
        cve_matches=10,
        bot_traffic_percentage=65.5,
        top_attack_categories={},
        top_attacking_countries={},
        top_protocols={},
    )


@pytest.fixture
def sample_report_config():
    """Create sample report config."""
    return ReportConfig(
        report_type=ReportType.TECHNICAL,
        sections=[],
        start_time=datetime.now(timezone.utc),
        end_time=datetime.now(timezone.utc),
        organization_name="Test Org",
    )


class TestExecutiveSummaryGenerator:
    """Test ExecutiveSummaryGenerator."""

    @pytest.mark.asyncio
    async def test_generate_success(
        self, mock_llm_service, sample_threat_summary, sample_report_config
    ):
        """Test successful executive summary generation."""
        generator = ExecutiveSummaryGenerator(mock_llm_service)

        result = await generator.generate(sample_threat_summary, sample_report_config)

        assert result == "Generated content"
        mock_llm_service.generate_response.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_with_timeline(
        self, mock_llm_service, sample_threat_summary, sample_report_config
    ):
        """Test generation with timeline data."""
        generator = ExecutiveSummaryGenerator(mock_llm_service)

        timeline = [
            AttackTimelineEntry(
                timestamp=datetime.now(timezone.utc),
                event_type="attack",
                source_ip="1.2.3.4",
                severity="high",
                category="brute_force",
                description="Brute force login attempt",
            )
        ]

        result = await generator.generate(
            sample_threat_summary, sample_report_config, timeline=timeline
        )

        assert result == "Generated content"
        mock_llm_service.generate_response.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_fallback_on_error(
        self, mock_llm_service, sample_threat_summary, sample_report_config
    ):
        """Test fallback when LLM fails."""
        mock_llm_service.generate_response = AsyncMock(
            side_effect=Exception("LLM Error")
        )
        generator = ExecutiveSummaryGenerator(mock_llm_service)

        result = await generator.generate(sample_threat_summary, sample_report_config)

        # Should return fallback content
        assert result is not None
        assert "Research Overview" in result or "Data Collection" in result

    def test_build_context(
        self, mock_llm_service, sample_threat_summary, sample_report_config
    ):
        """Test context building."""
        generator = ExecutiveSummaryGenerator(mock_llm_service)

        context = generator._build_context(
            sample_threat_summary, sample_report_config, None, None
        )

        assert "total_attacks" in context or "unique_sources" in context
        assert context.get("total_attacks", context.get("unique_sources")) is not None


class TestThreatAnalysisGenerator:
    """Test ThreatAnalysisGenerator."""

    @pytest.mark.asyncio
    async def test_generate_success(self, mock_llm_service, sample_threat_summary):
        """Test successful threat analysis generation."""
        generator = ThreatAnalysisGenerator(mock_llm_service)

        timeline = []
        geo_data = []
        botnet_data = []

        result = await generator.generate(
            sample_threat_summary, timeline, geo_data, botnet_data
        )

        assert result == "Generated content"
        mock_llm_service.generate_response.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_with_full_data(
        self, mock_llm_service, sample_threat_summary
    ):
        """Test generation with complete data."""
        generator = ThreatAnalysisGenerator(mock_llm_service)

        timeline = [
            AttackTimelineEntry(
                timestamp=datetime.now(timezone.utc),
                event_type="attack",
                source_ip="1.2.3.4",
                severity="critical",
                category="sql_injection",
                description="SQL injection attempt",
                country_code="US",
            )
        ]

        geo_data = [
            GeoDistribution(
                country="United States",
                country_code="US",
                country_name="United States",
                count=100,
                attack_count=100,
                unique_ips=10,
                primary_attack_types=["sql_injection"],
            )
        ]

        botnet_data = [
            BotnetSummary(
                cluster_id="bot-1",
                member_count=20,
                severity="high",
                attack_coordination_score=0.85,
                suspected_cc_servers=["1.2.3.4"],
                first_detected=datetime.now(timezone.utc),
                last_activity=datetime.now(timezone.utc),
            )
        ]

        result = await generator.generate(
            sample_threat_summary, timeline, geo_data, botnet_data
        )

        assert result == "Generated content"

    def test_build_context(self, mock_llm_service, sample_threat_summary):
        """Test context building with all data."""
        generator = ThreatAnalysisGenerator(mock_llm_service)

        timeline = []
        geo_data = []
        botnet_data = []

        context = generator._build_context(
            sample_threat_summary, timeline, geo_data, botnet_data
        )

        # Updated for research-focused context structure
        assert "dataset_summary" in context or "summary" in context
        assert "sample_events" in context or "recent_events" in context
        assert "geographic_analysis" in context or "geographic_distribution" in context
        assert "botnet_clusters" in context

    def test_build_prompt(self, mock_llm_service):
        """Test prompt building."""
        generator = ThreatAnalysisGenerator(mock_llm_service)

        context = {"summary": {"total_events": 100}}
        prompt = generator._build_prompt(context)

        assert "researcher" in prompt.lower() or "analyst" in prompt.lower()
        assert "attack pattern" in prompt.lower() or "research" in prompt.lower()
        assert "markdown" in prompt.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
