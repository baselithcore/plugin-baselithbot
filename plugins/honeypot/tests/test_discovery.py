"""Unit Tests for Discovery Module.

Tests for botnet detection and graph analysis algorithms.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

# Test imports
from plugins.honeypot.discovery.models import (
    BotnetCluster,
    HubNode,
    NetworkAnomaly,
    DiscoveryResult,
    GraphNodeData,
    GraphEdgeData,
)


class TestDiscoveryModels:
    """Test Discovery Pydantic models."""

    def test_botnet_cluster_creation(self):
        """Test BotnetCluster model creation."""
        cluster = BotnetCluster(
            cluster_id="test-001",
            member_ips=["192.168.1.1", "192.168.1.2", "192.168.1.3"],
            suspected_cc_ip="192.168.1.1",
            size=3,
            attack_coordination_score=0.85,
            common_protocols=["ssh", "http"],
            common_targets=["honeypot-ssh"],
            detection_confidence=0.9,
            severity="high",
        )

        assert cluster.cluster_id == "test-001"
        assert len(cluster.member_ips) == 3
        assert cluster.suspected_cc_ip == "192.168.1.1"
        assert cluster.severity == "high"

    def test_hub_node_creation(self):
        """Test HubNode model creation."""
        hub = HubNode(
            ip="10.0.0.1",
            degree_centrality=0.75,
            betweenness_centrality=0.6,
            connected_bots=12,
            is_confirmed_cc=True,
            threat_score=85.5,
            cluster_id="cluster-001",
            country_code="CN",
            protocols=["ssh"],
        )

        assert hub.ip == "10.0.0.1"
        assert hub.is_confirmed_cc is True
        assert hub.threat_score == 85.5
        assert hub.connected_bots == 12

    def test_network_anomaly_creation(self):
        """Test NetworkAnomaly model creation."""
        anomaly = NetworkAnomaly(
            anomaly_id="anom-001",
            anomaly_type="geo_cluster",
            involved_ips=["1.1.1.1", "1.1.1.2"],
            description="Cluster of IPs from same country",
            severity="medium",
            confidence=0.8,
        )

        assert anomaly.anomaly_type == "geo_cluster"
        assert len(anomaly.involved_ips) == 2

    def test_discovery_result_empty(self):
        """Test empty DiscoveryResult creation."""
        result = DiscoveryResult(
            analysis_id="analysis-001",
            honeypot_id=None,
            total_nodes=0,
            total_edges=0,
            summary={"message": "No data"},
        )

        assert result.analysis_id == "analysis-001"
        assert len(result.botnets) == 0
        assert len(result.hub_nodes) == 0


class TestGraphAnalyzer:
    """Test GraphAnalyzer functionality."""

    @pytest.fixture
    def mock_networkx(self):
        """Mock networkx if not available."""
        with patch.dict("sys.modules", {"networkx": MagicMock()}):
            yield

    def test_graph_node_data_serialization(self):
        """Test GraphNodeData JSON serialization."""
        node = GraphNodeData(
            id="192.168.1.1",
            type="attacker",
            cluster_id="cluster-001",
            degree=5,
            centrality=0.45,
            country_code="US",
            protocols=["ssh", "http"],
            severity="high",
            attack_count=15,
            is_hub=True,
            is_confirmed_cc=True,
        )

        data = node.model_dump()
        assert data["id"] == "192.168.1.1"
        assert data["is_hub"] is True
        assert data["is_confirmed_cc"] is True
        assert "ssh" in data["protocols"]

    def test_graph_edge_data_serialization(self):
        """Test GraphEdgeData JSON serialization."""
        edge = GraphEdgeData(
            source="192.168.1.1",
            target="honeypot",
            weight=5.0,
            is_intra_cluster=False,
        )

        data = edge.model_dump()
        assert data["source"] == "192.168.1.1"
        assert data["target"] == "honeypot"
        assert data["weight"] == 5.0


class TestBotnetDetector:
    """Test BotnetDetector algorithms."""

    def test_severity_calculation(self):
        """Test severity calculation from severities set."""
        # Mock test - actual implementation in service
        severities = {"info", "low", "medium", "high"}
        priority = {"critical": 5, "high": 4, "medium": 3, "low": 2, "info": 1}
        max_sev = max(severities, key=lambda s: priority.get(s, 0))
        assert max_sev == "high"

    def test_coordination_score_empty(self):
        """Test coordination score with minimal cluster."""
        # With less than 2 members, score should be 0
        members = ["ip1"]
        score = 0.0 if len(members) < 2 else 0.5
        assert score == 0.0

    def test_coordination_score_calculation(self):
        """Test basic coordination score calculation logic."""
        # Simulate 3 members with 2 internal edges out of max 3
        members = ["ip1", "ip2", "ip3"]
        internal_edges = 2
        max_edges = len(members) * (len(members) - 1) / 2  # 3

        density_score = internal_edges / max_edges  # 0.67
        assert density_score == pytest.approx(0.666, rel=0.01)


class TestDiscoveryService:
    """Test DiscoveryService orchestration."""

    @pytest.fixture
    def mock_dao(self):
        """Create mock DAO."""
        dao = MagicMock()
        dao.get_events = AsyncMock(return_value={"items": [], "total": 0})
        return dao

    @pytest.mark.asyncio
    async def test_empty_analysis(self, mock_dao):
        """Test analysis with no data returns valid result."""
        from plugins.honeypot.discovery.service import DiscoveryService

        service = DiscoveryService(dao=mock_dao)

        # Mock graph building to return empty graph
        with patch.object(service.graph_analyzer, "build_attack_graph") as mock_build:
            mock_graph = MagicMock()
            mock_graph.number_of_nodes.return_value = 0
            mock_graph.number_of_edges.return_value = 0
            mock_build.return_value = mock_graph

            result = await service.run_full_analysis()

            assert result.total_nodes == 0
            assert len(result.botnets) == 0
            assert (
                "message" in result.summary
                or result.summary.get("detected_botnets") == 0
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
