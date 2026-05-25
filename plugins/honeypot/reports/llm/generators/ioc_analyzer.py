"""IOC (Indicators of Compromise) Analyzer.

Generates threat intelligence assessments from IOC data.
"""

from core.observability.logging import get_logger
from typing import List

from core.services.llm.service import LLMService
from ...models import ThreatSummary, IOCEntry

logger = get_logger(__name__)


class IOCAnalyzer:
    """Analyzes IOCs and generates intelligence assessments using LLM."""

    def __init__(self, llm_service: LLMService):
        """Initialize analyzer.

        Args:
            llm_service: LLM service instance
        """
        self.llm = llm_service

    async def generate(
        self,
        iocs: List[IOCEntry],
        threat_summary: ThreatSummary,
    ) -> str:
        """Generate IOC analysis.

        Args:
            iocs: List of IOC entries
            threat_summary: Threat statistics

        Returns:
            IOC analysis in markdown format
        """
        from ..prompts.builders import build_ioc_analysis_prompt
        import asyncio

        # Build context with IOC sampling and aggregation
        context = self._build_context(iocs, threat_summary)

        # Build prompt
        prompt = build_ioc_analysis_prompt(context)

        try:
            analysis = await asyncio.wait_for(
                self.llm.generate_response(prompt=prompt),
                timeout=60.0,  # 60 second timeout
            )
            return analysis.strip()
        except asyncio.TimeoutError:
            logger.warning("LLM IOC analysis timed out (60s), using fallback")
            from ..fallbacks.handlers import fallback_ioc_analysis

            unique_ips = len(set(ioc.value for ioc in iocs if ioc.ioc_type == "ip"))
            return fallback_ioc_analysis(len(iocs), unique_ips)
        except Exception as e:
            logger.error(f"LLM generation failed for IOC analysis: {e}")
            from ..fallbacks.handlers import fallback_ioc_analysis

            unique_ips = len(set(ioc.value for ioc in iocs if ioc.ioc_type == "ip"))
            return fallback_ioc_analysis(len(iocs), unique_ips)

    def _build_context(
        self, iocs: List[IOCEntry], threat_summary: ThreatSummary
    ) -> dict:
        """Build context data for IOC analysis.

        Samples and aggregates IOC data to prevent token overflow.

        Args:
            iocs: List of IOC entries
            threat_summary: Threat statistics

        Returns:
            Context dictionary with sampled IOC data
        """
        # Count IOCs by type
        ioc_by_type = {}
        for ioc in iocs:
            ioc_by_type[ioc.ioc_type] = ioc_by_type.get(ioc.ioc_type, 0) + 1

        # Collect high-confidence IOCs
        high_confidence = []
        campaigns = set()

        for ioc in iocs:
            if ioc.confidence > 0.7:
                high_confidence.append(
                    {
                        "type": ioc.ioc_type,
                        "value": ioc.value[:50],  # Truncate long values
                        "confidence": ioc.confidence,
                        "threat_level": ioc.threat_level,
                    }
                )
                if ioc.associated_campaigns:
                    campaigns.update(ioc.associated_campaigns)

        # Count unique IPs
        unique_ips = len(set(ioc.value for ioc in iocs if ioc.ioc_type == "ip"))

        return {
            "total_iocs": len(iocs),
            "unique_ips": unique_ips,
            "ioc_by_type": ioc_by_type,
            "high_confidence": len(high_confidence),
            "ioc_samples": high_confidence[:20],  # Top 20 high-confidence IOCs
            "campaigns": list(campaigns),
            "threat_context": {
                "botnets": threat_summary.detected_botnets,
                "cc_servers": threat_summary.potential_cc_servers,
                "total_events": threat_summary.total_events,
                "unique_attackers": threat_summary.unique_attackers,
            },
        }
