"""Core Discovery Service."""

import asyncio
from core.observability.logging import get_logger
import uuid
from datetime import datetime, timezone
from typing import List, Optional, TYPE_CHECKING, Dict, Any

# Import analyzers (using relative imports where possible or absolute as needed)
from ..behavioral_analyzer import BehavioralAnalyzer
from ..botnet_detector import BotnetDetector
from ..botnet_profiler import BotnetProfiler
from ..cc_detector import CCDetector
from ..exploit_analyzer import ExploitAnalyzer
from ..feature_extractor import FeatureExtractor
from ..graph_analyzer import GraphAnalyzer
from ..ml_analyzer import MLAnalyzer

if TYPE_CHECKING:
    from ...persistence import HoneypotDAO
from ..statistical_analyzer import StatisticalAnalyzer
from ..threat_intel import ThreatIntelGenerator
from ..threat_intel.misp_bridge import MISPBridge
from ..zeroday_detector import ZeroDayDetector
from ..honeypot_suggester import HoneypotSuggestionEngine

# Import builder and models
from .builder import build_graph_data, build_summary
from .models import (
    BotnetCluster,
    DiscoveryGraphData,
    DiscoveryResult,
    HubNode,
    convert_numpy,
)
from ...config import get_honeypot_config

logger = get_logger(__name__)


class DiscoveryService:
    """Orchestrates discovery analysis operations."""

    def __init__(self, dao: Optional["HoneypotDAO"] = None):
        """Initialize service with data access object."""
        self.dao = dao
        self.config = get_honeypot_config()

        # Initialize MISP Bridge if enabled
        self.misp_bridge = None
        if self.config.misp_enabled:
            self.misp_bridge = MISPBridge(
                api_url=self.config.misp_url,
                api_key=self.config.misp_key,
                verify_ssl=self.config.misp_verify_ssl,
            )

        self.graph_analyzer = GraphAnalyzer(dao)
        self.botnet_detector = BotnetDetector()
        self.behavioral_analyzer = BehavioralAnalyzer()
        self.statistical_analyzer = StatisticalAnalyzer()
        self.cc_detector = CCDetector()
        self.botnet_profiler = BotnetProfiler()
        self.ml_analyzer = MLAnalyzer()
        self.feature_extractor = FeatureExtractor()
        self.zeroday_detector = ZeroDayDetector()
        self.threat_intel = ThreatIntelGenerator(
            misp_status_provider=self.misp_bridge.get_status
            if self.misp_bridge
            else None
        )
        self.exploit_analyzer = ExploitAnalyzer()
        self.honeypot_suggester: Optional[HoneypotSuggestionEngine] = None
        self._last_result: Optional[DiscoveryResult] = None

    async def run_full_analysis(
        self,
        honeypot_id: Optional[str] = None,
        time_window_hours: int = 168,
        min_cluster_size: int = 2,
        resolution: float = 1.0,
    ) -> DiscoveryResult:
        """Run complete discovery analysis.

        Args:
            honeypot_id: Filter events by honeypot (None = all)
            time_window_hours: Time window for analysis
            min_cluster_size: Minimum cluster size to report
            resolution: Louvain resolution parameter

        Returns:
            DiscoveryResult with detected botnets, hubs, and anomalies
        """
        analysis_id = str(uuid.uuid4())[:12]
        logger.info(f"Starting discovery analysis {analysis_id}")

        try:
            # 1. Build attack graph
            G = await self.graph_analyzer.build_attack_graph(
                honeypot_id=honeypot_id,
                time_window_hours=time_window_hours,
            )

            if G.number_of_nodes() == 0:
                logger.info("No nodes in graph, returning empty result")
                return DiscoveryResult(
                    analysis_id=analysis_id,
                    honeypot_id=honeypot_id,
                    analyzed_at=datetime.now(timezone.utc),
                    total_nodes=0,
                    total_edges=0,
                    summary={"message": "No attack data available for analysis"},
                )

            # 2. Compute centrality metrics
            degree_centrality = self.graph_analyzer.compute_degree_centrality(G)
            betweenness_centrality = self.graph_analyzer.compute_betweenness_centrality(
                G
            )

            # 3. Detect communities using Louvain
            partition, modularity = self.botnet_detector.detect_communities_louvain(
                G, resolution=resolution
            )

            # 4. Identify hub nodes (potential C&C servers)
            node_metadata = {
                node: self.graph_analyzer.get_node_metadata(node) for node in G.nodes()
            }
            hub_nodes = self.botnet_detector.identify_hub_nodes(
                G=G,
                partition=partition,
                degree_centrality=degree_centrality,
                betweenness_centrality=betweenness_centrality,
                node_metadata=node_metadata,
            )

            # 5. Build botnet clusters
            botnets = self.botnet_detector.build_clusters(
                G=G,
                partition=partition,
                hub_nodes=hub_nodes,
                node_metadata=node_metadata,
                min_cluster_size=min_cluster_size,
            )

            # 6. Detect graph-based anomalies
            anomalies = self.botnet_detector.detect_anomalies(
                G=G,
                partition=partition,
                node_metadata=node_metadata,
            )

            # 7. Run behavioral correlation analysis
            events = self.graph_analyzer.get_events()
            behavioral_meta = {}
            statistical_meta = {}
            cc_meta = {}
            botnet_profiles = []
            ml_meta = {}
            feature_meta = {}
            zeroday_meta = {}
            exploit_meta = {}
            intel_meta = {}
            suggestions = []

            if events:
                # Run independent analyzers in parallel for better performance
                logger.info("Running parallel analyzers...")

                # Execute all analyzers concurrently using asyncio.to_thread
                (
                    behavioral_result,
                    statistical_result,
                    cc_result,
                    ml_result,
                    zeroday_result,
                    exploit_result,
                    intel_result,
                ) = await asyncio.gather(
                    asyncio.to_thread(self.behavioral_analyzer.analyze_all, events),
                    asyncio.to_thread(self.statistical_analyzer.analyze_all, events),
                    asyncio.to_thread(self.cc_detector.analyze_all, events),
                    asyncio.to_thread(self.ml_analyzer.analyze_all, events),
                    asyncio.to_thread(self.zeroday_detector.analyze_all, events),
                    asyncio.to_thread(self.exploit_analyzer.analyze_all, events),
                    asyncio.to_thread(self.threat_intel.generate_intel, events),
                )

                # Unpack results
                behavioral_anomalies, behavioral_meta = behavioral_result
                statistical_anomalies, statistical_meta = statistical_result
                cc_anomalies, cc_meta = cc_result
                ml_anomalies, ml_meta = ml_result
                zeroday_anomalies, zeroday_meta = zeroday_result
                exploit_anomalies, exploit_meta = exploit_result
                intel_anomalies, intel_meta = intel_result

                # Aggregate all anomalies
                anomalies.extend(behavioral_anomalies)
                anomalies.extend(statistical_anomalies)
                anomalies.extend(cc_anomalies)
                anomalies.extend(ml_anomalies)
                anomalies.extend(zeroday_anomalies)
                anomalies.extend(exploit_anomalies)
                anomalies.extend(intel_anomalies)

                logger.info(
                    f"Parallel analysis complete: "
                    f"behavioral={len(behavioral_anomalies)}, "
                    f"statistical={len(statistical_anomalies)}, "
                    f"cc={len(cc_anomalies)}, "
                    f"ml={len(ml_anomalies)}, "
                    f"zeroday={len(zeroday_anomalies)}, "
                    f"exploit={len(exploit_anomalies)}, "
                    f"intel={len(intel_anomalies)}"
                )

                # 10. Profile detected botnets (depends on botnets from earlier step)
                for botnet in botnets:
                    profile = self.botnet_profiler.profile_cluster(
                        cluster=botnet,
                        events=events,
                        hub_nodes=hub_nodes,
                    )
                    botnet_profiles.append(profile)
                logger.info(f"Profiled {len(botnet_profiles)} botnets")

                # 11. Extract features (for reference, not critical path)
                _ = self.feature_extractor.extract_features(events)
                feature_meta = self.feature_extractor.get_feature_summary()

                # 16. Generate honeypot suggestions from analysis results
                suggestions = []
                suggestions_count = 0
                try:
                    existing_honeypots = await self._get_active_honeypot_ids()
                    self.honeypot_suggester = HoneypotSuggestionEngine(
                        existing_honeypot_ids=existing_honeypots
                    )
                    zeroday_candidates = self.zeroday_detector.get_candidates()
                    suggestions = await self.honeypot_suggester.analyze_and_suggest(
                        zeroday_candidates=zeroday_candidates,
                        behavioral_clusters=behavioral_meta,
                        network_anomalies=anomalies,
                    )
                    suggestions_count = len(suggestions)
                    logger.info(f"Honeypot suggestions: {suggestions_count} generated")
                except Exception as e:
                    logger.warning(
                        f"Honeypot suggestion generation failed (non-fatal): {e}"
                    )
                    # Continue with empty suggestions - don't fail the whole analysis

            # 11. Build graph data for visualization
            graph_data = build_graph_data(
                G=G,
                partition=partition,
                hub_nodes=hub_nodes,
                degree_centrality=degree_centrality,
                node_metadata=node_metadata,
            )

            # 16. Build summary (include all metadata)
            summary = build_summary(
                total_attackers=len(self.graph_analyzer.get_attacker_nodes()),
                total_edges=G.number_of_edges(),
                botnets=botnets,
                hub_nodes=hub_nodes,
                anomalies=anomalies,
                modularity=modularity,
                behavioral_meta=behavioral_meta,
                statistical_meta=statistical_meta,
                cc_meta=cc_meta,
                botnet_profiles=botnet_profiles,
                ml_meta=ml_meta,
                feature_meta=feature_meta,
                zeroday_meta=zeroday_meta,
                exploit_meta=exploit_meta,
                intel_meta=intel_meta,
            )

            # 17. Sanitize all data to ensure no numpy types cause serialization errors
            # This is a defense-in-depth measure even if models have sanitizers
            result = DiscoveryResult(
                analysis_id=analysis_id,
                honeypot_id=honeypot_id,
                analyzed_at=datetime.now(timezone.utc),
                total_nodes=G.number_of_nodes(),
                total_edges=G.number_of_edges(),
                botnets=convert_numpy(botnets),
                hub_nodes=convert_numpy(hub_nodes),
                anomalies=convert_numpy(anomalies),
                graph_data=convert_numpy(graph_data),
                summary=convert_numpy(summary),
                suggestions=(
                    [s.model_dump() for s in suggestions]
                    if self.honeypot_suggester and suggestions
                    else []
                ),
            )

            self._last_result = result
            logger.info(
                f"Analysis complete: {len(botnets)} botnets, "
                f"{len(hub_nodes)} hubs, {len(anomalies)} anomalies"
            )

            # Persist result
            if self.dao:
                await self.dao.save_discovery_result(result)

            return result

        except Exception as e:
            logger.error(f"Discovery analysis failed: {e}", exc_info=True)
            return DiscoveryResult(
                analysis_id=analysis_id,
                honeypot_id=honeypot_id,
                analyzed_at=datetime.now(timezone.utc),
                summary={"error": str(e)},
            )

    async def detect_botnets(
        self, honeypot_id: Optional[str] = None
    ) -> List[BotnetCluster]:
        """Get detected botnets from last analysis or run new analysis."""
        last = await self.get_last_result(honeypot_id)
        if last and last.honeypot_id == honeypot_id:
            return last.botnets

        result = await self.run_full_analysis(honeypot_id=honeypot_id)
        return result.botnets

    async def find_hub_nodes(self, honeypot_id: Optional[str] = None) -> List[HubNode]:
        """Get hub nodes from last analysis or run new analysis."""
        last = await self.get_last_result(honeypot_id)
        if last and last.honeypot_id == honeypot_id:
            return last.hub_nodes

        result = await self.run_full_analysis(honeypot_id=honeypot_id)
        return result.hub_nodes

    async def get_network_graph_data(
        self, honeypot_id: Optional[str] = None
    ) -> Optional[DiscoveryGraphData]:
        """Get graph data for visualization."""
        last = await self.get_last_result(honeypot_id)
        if last and last.honeypot_id == honeypot_id:
            return last.graph_data

        result = await self.run_full_analysis(honeypot_id=honeypot_id)
        return result.graph_data

    async def get_last_result(
        self, honeypot_id: Optional[str] = None
    ) -> Optional[DiscoveryResult]:
        """Get cached result from last analysis."""
        # 1. Check memory cache
        if self._last_result:
            # Basic cache validity check - if honeypot_id requested, it must match or be None (if we consider global analysis applicable)
            if honeypot_id is None or self._last_result.honeypot_id == honeypot_id:
                return self._last_result

        # 2. Check database
        if self.dao:
            result = await self.dao.get_latest_discovery_result(honeypot_id)
            if result:
                self._last_result = result
                return result

        return None

    async def _get_active_honeypot_ids(self) -> List[str]:
        """Get list of currently active honeypot IDs.

        Used to avoid suggesting honeypots similar to existing ones.
        """
        if self.dao:
            try:
                # Try to get honeypots from DAO if method exists
                if hasattr(self.dao, "get_active_honeypots"):
                    honeypots = await self.dao.get_active_honeypots()
                    return [h.id for h in honeypots if hasattr(h, "id")]
            except Exception as e:
                logger.warning(f"Could not get active honeypots: {e}")

        return []

    async def get_suggestions(self) -> List[Dict[str, Any]]:
        """Get honeypot suggestions from the last analysis.

        Returns:
            List of suggestion dictionaries
        """
        if self._last_result:
            return self._last_result.suggestions
        return []
