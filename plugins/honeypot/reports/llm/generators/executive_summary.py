"""Executive Summary Generator.

Generates AI-powered executive summaries for security reports.
"""

from core.observability.logging import get_logger
from datetime import datetime, timedelta, timezone
from typing import Optional, List

from core.services.llm.service import LLMService
from ...models import (
    ThreatSummary,
    ReportConfig,
    AttackTimelineEntry,
    GeoDistribution,
)

logger = get_logger(__name__)


class ExecutiveSummaryGenerator:
    """Generates executive summaries using LLM."""

    def __init__(self, llm_service: LLMService):
        """Initialize generator.

        Args:
            llm_service: LLM service instance
        """
        self.llm = llm_service

    async def generate(
        self,
        threat_summary: ThreatSummary,
        config: ReportConfig,
        title: Optional[str] = None,
        timeline: Optional[List[AttackTimelineEntry]] = None,
        geo_data: Optional[List[GeoDistribution]] = None,
        honeypot_context: Optional[dict] = None,
        payload_samples: Optional[list] = None,
    ) -> str:
        """Generate executive summary.

        Args:
            threat_summary: Aggregated threat statistics
            config: Report configuration
            title: Optional custom title
            timeline: Optional attack timeline data
            geo_data: Optional geographic distribution data
            honeypot_context: Optional honeypot metadata
            payload_samples: Optional payload samples for attack analysis

        Returns:
            Executive summary in markdown format
        """
        from ..prompts.builders import build_executive_summary_prompt

        # Build context
        context = self._build_context(
            threat_summary,
            config,
            timeline,
            geo_data,
            honeypot_context,
            payload_samples,
        )

        # Build prompt
        import asyncio

        prompt = build_executive_summary_prompt(
            context, config.report_type, config.organization_name
        )

        try:
            summary = await asyncio.wait_for(
                self.llm.generate_response(prompt=prompt),
                timeout=60.0,  # 60 second timeout
            )
            return summary.strip()
        except asyncio.TimeoutError:
            logger.warning("LLM executive summary timed out (60s), using fallback")
            from ..fallbacks.handlers import fallback_executive_summary

            return fallback_executive_summary(threat_summary, config)
        except Exception as e:
            logger.error(f"LLM generation failed for executive summary: {e}")
            # Fallback
            from ..fallbacks.handlers import fallback_executive_summary

            return fallback_executive_summary(threat_summary, config)

    def _build_context(
        self,
        threat_summary: ThreatSummary,
        config: ReportConfig,
        timeline: Optional[List[AttackTimelineEntry]],
        geo_data: Optional[List[GeoDistribution]],
        honeypot_context: Optional[dict] = None,
        payload_samples: Optional[list] = None,
    ) -> dict:
        """Build context data for prompt.

        Args:
            threat_summary: Threat statistics
            config: Report configuration
            timeline: Optional timeline data
            geo_data: Optional geo data
            honeypot_context: Optional honeypot metadata
            payload_samples: Optional payload samples for attack analysis

        Returns:
            Context dictionary
        """
        # Calculate time range
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(hours=config.time_range_hours)

        context = {
            "total_attacks": threat_summary.total_events,
            "unique_ips": threat_summary.unique_attackers,
            "unique_countries": len(threat_summary.top_attacking_countries),
            "critical_threats": threat_summary.critical_events,
            "high_threats": threat_summary.high_events,
            "time_range": f"{start_time.strftime('%Y-%m-%d')} to {end_time.strftime('%Y-%m-%d')}",
            "top_attacks": list(threat_summary.top_attack_categories.keys())[:3],
            "top_countries": list(threat_summary.top_attacking_countries.keys())[:5],
            "botnets_detected": threat_summary.detected_botnets,
        }

        # Add timeline insights if available
        # Note: AttackTimelineEntry represents individual events, so we can't easily find "peak time"
        # without aggregation. For now, we just pass the count context.
        if timeline:
            context["timeline_event_count"] = len(timeline)

        # Add geo insights
        if geo_data:
            total_geo_attacks = sum(g.attack_count for g in geo_data)
            if total_geo_attacks > 0 and len(geo_data) > 0:
                top_geo = geo_data[0]
                context["primary_source"] = top_geo.country_name
                context["primary_source_percentage"] = (
                    top_geo.attack_count / total_geo_attacks
                ) * 100

        # Add honeypot specific context
        if honeypot_context:
            context["target_infrastructure"] = {
                "name": honeypot_context.get("name"),
                "type": f"{honeypot_context.get('protocol')} Service",
                "description": honeypot_context.get("description"),
                "tags": honeypot_context.get("tags", []),
            }

        # Add payload samples for detailed attack analysis
        if payload_samples:
            context["attack_samples"] = [
                {
                    "category": sample.get("category", "unknown"),
                    "severity": sample.get("severity", "medium"),
                    "payload_preview": sample.get("payload", "")[
                        :200
                    ],  # First 200 chars
                    "source_country": sample.get("country", "Unknown"),
                    "protocol": sample.get("protocol", "unknown"),
                }
                for sample in payload_samples[:5]  # Top 5 samples
            ]

        return context
