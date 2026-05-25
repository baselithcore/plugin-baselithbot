"""Threat Analysis Generator.

Generates research-focused attack pattern analysis for honeypot reports.
"""

from core.observability.logging import get_logger
import json
from typing import List

from core.services.llm.service import LLMService
from ...models import (
    ThreatSummary,
    AttackTimelineEntry,
    GeoDistribution,
    BotnetSummary,
)

logger = get_logger(__name__)


class ThreatAnalysisGenerator:
    """Generates attack pattern research analysis using LLM."""

    def __init__(self, llm_service: LLMService):
        """Initialize generator.

        Args:
            llm_service: LLM service instance
        """
        self.llm = llm_service

    async def generate(
        self,
        threat_summary: ThreatSummary,
        timeline: List[AttackTimelineEntry],
        geo_data: List[GeoDistribution],
        botnet_data: List[BotnetSummary],
    ) -> str:
        """Generate attack pattern research analysis.

        Args:
            threat_summary: Aggregated threat statistics
            timeline: Attack timeline entries
            geo_data: Geographic distribution
            botnet_data: Botnet activity summaries

        Returns:
            Research analysis in markdown format
        """
        # Build context
        import asyncio

        context = self._build_context(threat_summary, timeline, geo_data, botnet_data)

        # Build prompt
        prompt = self._build_prompt(context)

        try:
            analysis = await asyncio.wait_for(
                self.llm.generate_response(prompt=prompt),
                timeout=90.0,  # 90 second timeout
            )
            return analysis.strip()
        except asyncio.TimeoutError:
            logger.warning("LLM threat analysis timed out (90s), using fallback")
            from ..fallbacks.handlers import fallback_threat_analysis

            return fallback_threat_analysis(threat_summary)
        except Exception as e:
            logger.error(f"LLM generation failed for threat analysis: {e}")
            # Fallback
            from ..fallbacks.handlers import fallback_threat_analysis

            return fallback_threat_analysis(threat_summary)

    def _build_context(
        self,
        threat_summary: ThreatSummary,
        timeline: List[AttackTimelineEntry],
        geo_data: List[GeoDistribution],
        botnet_data: List[BotnetSummary],
    ) -> dict:
        """Build context data for prompt.

        Args:
            threat_summary: Threat statistics
            timeline: Timeline data
            geo_data: Geographic data
            botnet_data: Botnet data

        Returns:
            Context dictionary
        """
        return {
            "dataset_summary": {
                "total_events": threat_summary.total_events,
                "unique_sources": threat_summary.unique_attackers,
                "critical_severity_events": threat_summary.critical_events,
                "high_severity_events": threat_summary.high_events,
                "botnet_clusters_detected": threat_summary.detected_botnets,
                "cc_servers_identified": threat_summary.potential_cc_servers,
                "cve_exploitation_attempts": threat_summary.cve_matches,
                "automated_traffic_ratio": threat_summary.bot_traffic_percentage,
            },
            "attack_category_distribution": threat_summary.top_attack_categories,
            "geographic_source_distribution": threat_summary.top_attacking_countries,
            "protocol_distribution": threat_summary.top_protocols,
            "sample_events": [
                {
                    "timestamp": e.timestamp.isoformat(),
                    "type": e.event_type,
                    "source_ip": e.source_ip,
                    "severity": e.severity,
                    "category": e.category,
                    "origin_country": e.country_code,
                }
                for e in timeline[:10]  # Sample of 10 events
            ],
            "geographic_analysis": [
                {
                    "country": g.country_name,
                    "event_count": g.attack_count,
                    "unique_sources": g.unique_ips,
                    "primary_attack_types": g.primary_attack_types,
                }
                for g in geo_data[:10]  # Top 10 countries
            ],
            "botnet_clusters": [
                {
                    "cluster_id": b.cluster_id,
                    "member_count": b.member_count,
                    "severity_classification": b.severity,
                    "coordination_score": b.attack_coordination_score,
                    "suspected_cc_servers": b.suspected_cc_servers,
                }
                for b in botnet_data
            ],
        }

    def _build_prompt(self, context: dict) -> str:
        """Build LLM prompt for research analysis.

        Args:
            context: Context dictionary

        Returns:
            Formatted prompt string
        """
        return f"""You are a cybersecurity researcher analyzing honeypot data for academic study. Generate a comprehensive Attack Pattern Research Analysis.

**Collected Dataset:**
{json.dumps(context, indent=2)}

**Instructions:**
1. Write in academic research style (like IEEE/ACM security papers)
2. Identify and describe key attack patterns and behavioral clusters
3. Analyze geographic distribution patterns and their significance
4. Examine botnet coordination behaviors and infrastructure patterns
5. Highlight novel or unusual patterns worthy of further investigation
6. Use research terminology (behavioral clustering, temporal correlation, etc.)
7. Use markdown formatting with proper headers (###)
8. Include quantitative observations where relevant
9. Focus on patterns and insights, not defensive recommendations
10. Be thorough but objective (300-500 words)

**Format:**
### Attack Pattern Research Analysis

#### Dataset Characteristics
[Overview of the collected data]

#### Observed Attack Patterns
[Key patterns and techniques identified]

#### Behavioral Clustering Analysis
[Coordination patterns and botnet behaviors]

#### Geographic Distribution Insights
[Patterns in attack origins]

#### Notable Observations
[Unusual patterns or findings worthy of deeper study]

Generate the research analysis now:"""
