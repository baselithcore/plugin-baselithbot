"""ResearchReportGenerator — core class."""

import asyncio
import re
from typing import Any, Dict, List, Optional

from core.observability.logging import get_logger
from core.services.llm.service import LLMService

from ....models import (
    AttackTimelineEntry,
    PayloadExcerpt,
    ThreatSummary,
)
from ._fallbacks import FallbacksMixin

logger = get_logger(__name__)


class ResearchReportGenerator(FallbacksMixin):
    """Generates comprehensive research reports with enterprise-grade analysis.

    Integrates with ResearchSectionGenerator and uses specialized prompts
    for MITRE ATT&CK mapping, payload analysis, and trend analysis.
    """

    def __init__(self, llm_service: LLMService):
        """Initialize generator.

        Args:
            llm_service: LLM service for text generation
        """
        self.llm = llm_service

    def _clean_markdown_output(self, text: str) -> str:
        """Post-process LLM-generated markdown to fix formatting issues.

        Args:
            text: Raw LLM output

        Returns:
            Cleaned markdown text with proper formatting
        """
        if not text:
            return text

        # 1. Fix escaped newlines (\\n -> actual newline)
        text = text.replace("\\n", "\n")

        # 2. Ensure proper spacing around tables
        # Add blank line before table if missing
        text = re.sub(r"([^\n])\n(\|[^\n]+\|)", r"\1\n\n\2", text)
        # Add blank line after table if missing
        text = re.sub(r"(\|[^\n]+\|)\n([^\n|])", r"\1\n\n\2", text)

        # 3. Remove redundant escape characters
        text = text.replace("\\|", "|")
        text = text.replace("\\-", "-")

        # 4. Normalize whitespace (remove trailing spaces)
        lines = [line.rstrip() for line in text.split("\n")]
        text = "\n".join(lines)

        # 5. Remove excessive blank lines (more than 2 consecutive)
        text = re.sub(r"\n{3,}", "\n\n", text)

        return text.strip()

    async def generate_abstract(
        self,
        honeypot_name: str,
        threat_summary: ThreatSummary,
        time_range: str,
        honeypot_config: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Generate research abstract with honeypot context.

        Args:
            honeypot_name: Name/ID of the honeypot
            threat_summary: Aggregated threat statistics
            time_range: Human-readable time range
            honeypot_config: Optional honeypot configuration

        Returns:
            Markdown abstract text
        """
        from ....prompts_library.research_report_prompts import (
            research_abstract_prompt,
        )

        summary_dict = {
            "total_events": threat_summary.total_events,
            "unique_attackers": threat_summary.unique_attackers,
            "critical_events": threat_summary.critical_events,
            "high_events": threat_summary.high_events,
            "detected_botnets": threat_summary.detected_botnets,
            "potential_cc_servers": threat_summary.potential_cc_servers,
            "cve_matches": threat_summary.cve_matches,
            "bot_traffic_percentage": threat_summary.bot_traffic_percentage,
        }

        prompt = research_abstract_prompt(
            honeypot_name=honeypot_name,
            threat_summary=summary_dict,
            time_range=time_range,
            honeypot_config=honeypot_config,
        )

        try:
            result = await asyncio.wait_for(
                self.llm.generate_response(prompt=prompt),
                timeout=25.0,
            )
            return self._clean_markdown_output(result.strip())
        except asyncio.TimeoutError:
            logger.warning("Timeout while generating research abstract")
            return self._fallback_abstract(honeypot_name, threat_summary, time_range)
        except Exception as e:
            logger.warning(f"Failed to generate research abstract: {e}")
            return self._fallback_abstract(honeypot_name, threat_summary, time_range)

    async def generate_key_findings(
        self,
        honeypot_name: str,
        threat_summary: ThreatSummary,
        attack_categories: Dict[str, int],
        geo_distribution: List[Dict[str, Any]],
    ) -> str:
        """Generate key findings section.

        Args:
            honeypot_name: Honeypot identifier
            threat_summary: Threat statistics
            attack_categories: Attack type distribution
            geo_distribution: Geographic distribution data

        Returns:
            Markdown key findings text
        """
        from ....prompts_library.research_report_prompts import (
            research_key_findings_prompt,
        )

        summary_dict = {
            "total_events": threat_summary.total_events,
            "unique_attackers": threat_summary.unique_attackers,
            "critical_events": threat_summary.critical_events,
            "high_events": threat_summary.high_events,
            "medium_events": threat_summary.medium_events,
            "low_events": threat_summary.low_events,
            "detected_botnets": threat_summary.detected_botnets,
            "potential_cc_servers": threat_summary.potential_cc_servers,
            "cve_matches": threat_summary.cve_matches,
        }

        prompt = research_key_findings_prompt(
            honeypot_name=honeypot_name,
            threat_summary=summary_dict,
            attack_categories=attack_categories,
            geo_distribution=geo_distribution,
        )

        try:
            result = await asyncio.wait_for(
                self.llm.generate_response(prompt=prompt),
                timeout=25.0,
            )
            return self._clean_markdown_output(result.strip())
        except asyncio.TimeoutError:
            logger.warning("Timeout while generating key findings")
            return self._fallback_key_findings(honeypot_name, threat_summary)
        except Exception as e:
            logger.warning(f"Failed to generate key findings: {e}")
            return self._fallback_key_findings(honeypot_name, threat_summary)

    async def generate_mitre_mapping(
        self,
        honeypot_name: str,
        attack_categories: Dict[str, int],
        protocols: Dict[str, int],
        timeline: List[AttackTimelineEntry],
        payload_samples: Optional[List[str]] = None,
    ) -> str:
        """Generate MITRE ATT&CK technique mapping.

        Args:
            honeypot_name: Honeypot identifier
            attack_categories: Attack type distribution
            protocols: Protocol distribution
            timeline: Attack timeline entries
            payload_samples: Optional payload excerpts

        Returns:
            Markdown MITRE mapping with tables
        """
        from ....prompts_library.research_report_prompts import (
            research_mitre_mapping_prompt,
        )

        timeline_sample = [
            {
                "timestamp": e.timestamp.isoformat(),
                "event_type": e.event_type,
                "category": e.category,
                "severity": e.severity,
            }
            for e in timeline[:15]
        ]

        prompt = research_mitre_mapping_prompt(
            honeypot_name=honeypot_name,
            attack_categories=attack_categories,
            protocols=protocols,
            timeline_sample=timeline_sample,
            payload_samples=payload_samples,
        )

        try:
            result = await asyncio.wait_for(
                self.llm.generate_response(prompt=prompt),
                timeout=35.0,  # Strict timeout to avoid Gateway 504
            )
            return self._clean_markdown_output(result.strip())
        except asyncio.TimeoutError:
            logger.warning("Timeout while generating MITRE mapping")
            return self._fallback_mitre_mapping(honeypot_name)
        except Exception as e:
            logger.warning(f"Failed to generate MITRE mapping: {e}")
            return self._fallback_mitre_mapping(honeypot_name)

    async def generate_payload_analysis(
        self,
        honeypot_name: str,
        payload_excerpts: List[PayloadExcerpt],
        protocol: str = "mixed",
    ) -> str:
        """Generate payload analysis section.

        Args:
            honeypot_name: Honeypot identifier
            payload_excerpts: List of sanitized payload samples
            protocol: Primary protocol

        Returns:
            Markdown payload analysis
        """
        from ....prompts_library.research_report_prompts import (
            research_payload_analysis_prompt,
        )

        payload_data = [
            {
                "category": p.category,
                "severity": p.severity,
                "excerpt": p.excerpt,
                "source_country": p.source_country,
            }
            for p in payload_excerpts[:15]
        ]

        prompt = research_payload_analysis_prompt(
            honeypot_name=honeypot_name,
            payload_excerpts=payload_data,
            protocol=protocol,
        )

        try:
            result = await asyncio.wait_for(
                self.llm.generate_response(prompt=prompt),
                timeout=25.0,
            )
            return self._clean_markdown_output(result.strip())
        except asyncio.TimeoutError:
            logger.warning("Timeout while generating payload analysis")
            return self._fallback_payload_analysis(honeypot_name, payload_data)
        except Exception as e:
            logger.warning(f"Failed to generate payload analysis: {e}")
            return self._fallback_payload_analysis(honeypot_name, payload_data)

    async def generate_conclusions(
        self,
        honeypot_name: str,
        threat_summary: ThreatSummary,
        key_findings: List[str],
        time_range: str,
    ) -> str:
        """Generate conclusions and recommendations section.

        Args:
            honeypot_name: Honeypot identifier
            threat_summary: Aggregated statistics
            key_findings: Previously generated key findings
            time_range: Analysis time period

        Returns:
            Markdown conclusions and recommendations
        """
        from ....prompts_library.research_report_prompts import (
            research_conclusions_prompt,
        )

        summary_dict = {
            "total_events": threat_summary.total_events,
            "unique_attackers": threat_summary.unique_attackers,
            "detected_botnets": threat_summary.detected_botnets,
            "cve_matches": threat_summary.cve_matches,
        }

        prompt = research_conclusions_prompt(
            honeypot_name=honeypot_name,
            threat_summary=summary_dict,
            key_findings=key_findings,
            time_range=time_range,
        )

        try:
            result = await asyncio.wait_for(
                self.llm.generate_response(prompt=prompt),
                timeout=25.0,
            )
            return self._clean_markdown_output(result.strip())
        except asyncio.TimeoutError:
            logger.warning("Timeout while generating conclusions")
            return self._fallback_conclusions(honeypot_name, threat_summary)
        except Exception as e:
            logger.warning(f"Failed to generate conclusions: {e}")
            return self._fallback_conclusions(honeypot_name, threat_summary)

    async def generate_attack_narrative(
        self,
        session_analysis: Any,  # AttackSessionAnalysis
    ) -> str:
        """Generate narrative for an attack session.

        Args:
            session_analysis: AttackSessionAnalysis object

        Returns:
            Markdown narrative
        """
        from ....prompts_library.research_report_prompts import (
            research_attack_narrative_prompt,
        )

        prompt = research_attack_narrative_prompt(session_analysis)

        try:
            result = await asyncio.wait_for(
                self.llm.generate_response(prompt=prompt),
                timeout=40.0,
            )
            return self._clean_markdown_output(result.strip())
        except asyncio.TimeoutError:
            logger.warning(
                f"Timeout generating narrative for session {session_analysis.session_id}"
            )
            return f"### Attack Session Analysis: {session_analysis.attacker_ip}\n\n*Analysis timed out. Raw steps available in data.*"
        except Exception as e:
            logger.warning(f"Failed to generate narrative: {e}")
            return f"### Attack Session Analysis: {session_analysis.attacker_ip}\n\n*Analysis failed: {e}*"
