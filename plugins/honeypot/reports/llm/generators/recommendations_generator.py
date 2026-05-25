"""Research Insights Generator.

Generates AI-powered research insights based on attack pattern analysis.
"""

from core.observability.logging import get_logger
from typing import List

from core.services.llm.service import LLMService
from ...models import ThreatSummary, VulnerabilityItem, BotnetSummary, ReportType

logger = get_logger(__name__)


class RecommendationsGenerator:
    """Generates research insights using LLM.

    Note: Kept class name for backward compatibility, but now generates
    research insights instead of security recommendations.
    """

    def __init__(self, llm_service: LLMService):
        """Initialize generator.

        Args:
            llm_service: LLM service instance
        """
        self.llm = llm_service

    async def generate(
        self,
        threat_summary: ThreatSummary,
        vulnerabilities: List[VulnerabilityItem],
        botnet_data: List[BotnetSummary],
    ) -> List[str]:
        """Generate research insights.

        Args:
            threat_summary: Aggregated threat statistics
            vulnerabilities: List of vulnerabilities
            botnet_data: Botnet summaries

        Returns:
            List of research insight strings
        """
        from ..prompts.builders import build_research_insights_prompt
        import asyncio

        # Build context
        context = self._build_context(threat_summary, vulnerabilities, botnet_data)

        # Build prompt
        prompt = build_research_insights_prompt(context, ReportType.TECHNICAL)

        try:
            response = await asyncio.wait_for(
                self.llm.generate_response(prompt=prompt),
                timeout=60.0,  # 60 second timeout
            )
            # Parse bullet points from markdown
            insights = self._parse_insights(response)
            return insights[:10]  # Max 10 insights
        except asyncio.TimeoutError:
            logger.warning("LLM insights timed out (60s), using fallback")
            from ..fallbacks.handlers import fallback_research_insights

            return fallback_research_insights(threat_summary)
        except Exception as e:
            logger.error(f"LLM generation failed for research insights: {e}")
            from ..fallbacks.handlers import fallback_research_insights

            return fallback_research_insights(threat_summary)

    def _build_context(
        self,
        threat_summary: ThreatSummary,
        vulnerabilities: List[VulnerabilityItem],
        botnet_data: List[BotnetSummary],
    ) -> dict:
        """Build context for insights prompt.

        Args:
            threat_summary: Threat statistics
            vulnerabilities: Vulnerability list
            botnet_data: Botnet summaries

        Returns:
            Context dictionary
        """
        return {
            "dataset_size": threat_summary.total_events,
            "unique_sources": threat_summary.unique_attackers,
            "severity_distribution": {
                "critical": threat_summary.critical_events,
                "high": threat_summary.high_events,
                "medium": threat_summary.medium_events,
                "low": threat_summary.low_events,
            },
            "botnet_clusters": threat_summary.detected_botnets,
            "cc_infrastructure": threat_summary.potential_cc_servers,
            "cve_exploitation_attempts": threat_summary.cve_matches,
            "automated_traffic_ratio": threat_summary.bot_traffic_percentage,
            "vulnerability_patterns": [
                {
                    "cve": v.cve_references[0] if v.cve_references else v.name,
                    "severity": v.severity,
                    "type": v.name,
                }
                for v in vulnerabilities[:10]
            ],
            "botnet_characteristics": [
                {
                    "cluster_id": b.cluster_id,
                    "size": b.member_count,
                    "coordination_score": b.attack_coordination_score,
                }
                for b in botnet_data[:5]
            ],
        }

    def _parse_insights(self, response: str) -> List[str]:
        """Parse insights from LLM response.

        Extracts markdown bullet points and cleans them up.

        Args:
            response: LLM response text

        Returns:
            List of insight strings
        """
        insights = []

        for line in response.split("\n"):
            line = line.strip()
            # Match markdown bullets (-, *, or numbered lists)
            if line.startswith(("-", "*")) or (
                len(line) > 2 and line[0].isdigit() and line[1:3] in (". ", ") ")
            ):
                # Remove bullet/number prefix
                if line.startswith(("-", "*")):
                    insight = line[1:].strip()
                else:
                    # Remove number prefix (e.g., "1. " or "1) ")
                    insight = line.split(None, 1)[1] if " " in line else line

                # Remove markdown bold markers (**text**)
                insight = insight.replace("**", "")

                if insight:
                    insights.append(insight)

        return insights
