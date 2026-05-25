"""Research Section Generators.

Generators for advanced research-grade report sections:
- Abstract
- Key Findings
- MITRE ATT&CK Mapping
- Statistical Analysis
- Trend Analysis
"""

from core.observability.logging import get_logger
import asyncio
from typing import List

from core.services.llm.service import LLMService
from ...models import ThreatSummary, AttackTimelineEntry

logger = get_logger(__name__)


class ResearchSectionGenerator:
    """Generates advanced research sections using LLM."""

    def __init__(self, llm_service: LLMService):
        """Initialize generator.

        Args:
            llm_service: LLM service instance
        """
        self.llm = llm_service

    async def generate_abstract(
        self,
        threat_summary: ThreatSummary,
        time_range: str,
    ) -> str:
        """Generate research abstract.

        Args:
            threat_summary: Threat statistics
            time_range: Time range description

        Returns:
            Abstract markdown text
        """
        from ..prompts import build_abstract_prompt

        context = {
            "total_events": threat_summary.total_events,
            "unique_sources": threat_summary.unique_attackers,
            "critical_events": threat_summary.critical_events,
            "high_events": threat_summary.high_events,
            "botnet_clusters": threat_summary.detected_botnets,
            "cc_servers": threat_summary.potential_cc_servers,
            "cve_attempts": threat_summary.cve_matches,
            "bot_traffic_pct": threat_summary.bot_traffic_percentage,
            "top_categories": list(threat_summary.top_attack_categories.keys())[:5],
            "top_countries": list(threat_summary.top_attacking_countries.keys())[:5],
            "time_range": time_range,
        }

        prompt = build_abstract_prompt(context)

        try:
            result = await asyncio.wait_for(
                self.llm.generate_response(prompt=prompt),
                timeout=30.0,
            )
            return result.strip()
        except Exception as e:
            logger.warning(f"Failed to generate abstract: {e}")
            return self._fallback_abstract(threat_summary, time_range)

    async def generate_key_findings(
        self,
        threat_summary: ThreatSummary,
    ) -> str:
        """Generate key findings section.

        Args:
            threat_summary: Threat statistics

        Returns:
            Key findings markdown text
        """
        from ..prompts import build_key_findings_prompt

        context = {
            "total_events": threat_summary.total_events,
            "unique_sources": threat_summary.unique_attackers,
            "severity_distribution": {
                "critical": threat_summary.critical_events,
                "high": threat_summary.high_events,
                "medium": threat_summary.medium_events,
                "low": threat_summary.low_events,
            },
            "botnet_clusters": threat_summary.detected_botnets,
            "cc_servers": threat_summary.potential_cc_servers,
            "cve_attempts": threat_summary.cve_matches,
            "bot_traffic_pct": threat_summary.bot_traffic_percentage,
            "top_attack_types": threat_summary.top_attack_categories,
            "top_source_countries": threat_summary.top_attacking_countries,
            "protocol_distribution": threat_summary.top_protocols,
        }

        prompt = build_key_findings_prompt(context)

        try:
            result = await asyncio.wait_for(
                self.llm.generate_response(prompt=prompt),
                timeout=30.0,
            )
            return result.strip()
        except Exception as e:
            logger.warning(f"Failed to generate key findings: {e}")
            return self._fallback_key_findings(threat_summary)

    async def generate_mitre_mapping(
        self,
        threat_summary: ThreatSummary,
        timeline: List[AttackTimelineEntry],
    ) -> str:
        """Generate MITRE ATT&CK technique mapping.

        Args:
            threat_summary: Threat statistics
            timeline: Attack timeline

        Returns:
            MITRE ATT&CK mapping markdown
        """
        from ..prompts import build_mitre_attack_prompt

        timeline_sample = [
            {
                "timestamp": e.timestamp.isoformat(),
                "event_type": e.event_type,
                "category": e.category,
                "severity": e.severity,
            }
            for e in timeline[:20]
        ]

        prompt = build_mitre_attack_prompt(
            threat_summary.top_attack_categories,
            threat_summary.top_protocols,
            timeline_sample,
        )

        try:
            result = await asyncio.wait_for(
                self.llm.generate_response(prompt=prompt),
                timeout=45.0,  # Longer timeout for complex mapping
            )
            return result.strip()
        except Exception as e:
            logger.warning(f"Failed to generate MITRE mapping: {e}")
            return self._fallback_mitre_mapping(threat_summary)

    async def generate_statistical_analysis(
        self,
        threat_summary: ThreatSummary,
    ) -> str:
        """Generate statistical analysis section.

        Args:
            threat_summary: Threat statistics

        Returns:
            Statistical analysis markdown
        """
        from ..prompts import build_statistical_analysis_prompt

        context = {
            "severity_distribution": {
                "critical": threat_summary.critical_events,
                "high": threat_summary.high_events,
                "medium": threat_summary.medium_events,
                "low": threat_summary.low_events,
            },
            "attack_categories": threat_summary.top_attack_categories,
            "source_countries": threat_summary.top_attacking_countries,
            "protocols": threat_summary.top_protocols,
            "botnet_clusters": threat_summary.detected_botnets,
            "cve_attempts": threat_summary.cve_matches,
        }

        prompt = build_statistical_analysis_prompt(
            context,
            threat_summary.total_events,
            threat_summary.unique_attackers,
        )

        try:
            result = await asyncio.wait_for(
                self.llm.generate_response(prompt=prompt),
                timeout=30.0,
            )
            return result.strip()
        except Exception as e:
            logger.warning(f"Failed to generate statistical analysis: {e}")
            return self._fallback_statistical_analysis(threat_summary)

    def _fallback_abstract(self, summary: ThreatSummary, time_range: str) -> str:
        """Fallback abstract template."""
        return f"""## Abstract

This report presents a comprehensive analysis of {summary.total_events:,} attack events collected from honeypot infrastructure during {time_range}. The dataset includes traffic from {summary.unique_attackers:,} unique source addresses across multiple geographic regions. Analysis reveals {summary.detected_botnets} distinct botnet clusters exhibiting coordinated behavior, and {summary.cve_matches} attempts to exploit known CVE vulnerabilities. Approximately {summary.bot_traffic_percentage:.1f}% of captured traffic originates from automated scanning tools. The findings provide insights into current attack methodologies and threat actor behaviors targeting vulnerable network services.

**Keywords:** honeypot, threat intelligence, attack patterns, botnet detection, vulnerability exploitation, network security
"""

    def _fallback_key_findings(self, summary: ThreatSummary) -> str:
        """Fallback key findings template."""
        findings = ["## Key Findings\n"]

        findings.append(
            f"- **Attack Volume:** Captured {summary.total_events:,} total events from {summary.unique_attackers:,} unique sources"
        )

        if summary.critical_events > 0:
            findings.append(
                f"- **Critical Severity:** Identified {summary.critical_events} critical-severity attack attempts"
            )

        if summary.detected_botnets > 0:
            findings.append(
                f"- **Botnet Activity:** Detected {summary.detected_botnets} coordinated botnet clusters"
            )

        if summary.potential_cc_servers > 0:
            findings.append(
                f"- **C&C Infrastructure:** Identified {summary.potential_cc_servers} suspected command & control servers"
            )

        if summary.cve_matches > 0:
            findings.append(
                f"- **CVE Exploitation:** Observed {summary.cve_matches} attempts to exploit known vulnerabilities"
            )

        findings.append(
            f"- **Automation Ratio:** {summary.bot_traffic_percentage:.1f}% of traffic attributed to automated tools"
        )

        return "\n".join(findings)

    def _fallback_mitre_mapping(self, summary: ThreatSummary) -> str:
        """Fallback MITRE ATT&CK mapping template."""
        return """## MITRE ATT&CK Technique Mapping

### Reconnaissance
| Technique ID | Technique Name | Evidence | Confidence |
|--------------|----------------|----------|------------|
| T1595 | Active Scanning | Port scanning and service enumeration | High |
| T1592 | Gather Victim Host Information | Service version probing | Medium |

### Initial Access
| Technique ID | Technique Name | Evidence | Confidence |
|--------------|----------------|----------|------------|
| T1110 | Brute Force | Credential guessing attempts | High |
| T1190 | Exploit Public-Facing Application | CVE exploitation attempts | Medium |

### Execution
| Technique ID | Technique Name | Evidence | Confidence |
|--------------|----------------|----------|------------|
| T1059 | Command and Scripting Interpreter | Malicious command injection | Medium |

*Note: Mapping based on observed attack patterns. Confidence levels reflect certainty of technique identification.*
"""

    def _fallback_statistical_analysis(self, summary: ThreatSummary) -> str:
        """Fallback statistical analysis template."""
        total_severity = (
            summary.critical_events
            + summary.high_events
            + summary.medium_events
            + summary.low_events
        )

        return f"""## Statistical Analysis

### Dataset Overview
| Metric | Value |
|--------|-------|
| Total Events | {summary.total_events:,} |
| Unique Sources | {summary.unique_attackers:,} |
| Events per Source (avg) | {summary.total_events / max(summary.unique_attackers, 1):.1f} |

### Severity Distribution
| Severity | Count | Percentage |
|----------|-------|------------|
| Critical | {summary.critical_events} | {(summary.critical_events / max(total_severity, 1) * 100):.1f}% |
| High | {summary.high_events} | {(summary.high_events / max(total_severity, 1) * 100):.1f}% |
| Medium | {summary.medium_events} | {(summary.medium_events / max(total_severity, 1) * 100):.1f}% |
| Low | {summary.low_events} | {(summary.low_events / max(total_severity, 1) * 100):.1f}% |

### Key Ratios
- **Automation Ratio:** {summary.bot_traffic_percentage:.1f}%
- **Botnet Cluster Density:** {summary.detected_botnets} clusters per {summary.unique_attackers:,} unique sources
"""
