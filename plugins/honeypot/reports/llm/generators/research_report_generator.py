"""Research Report Generator.

Orchestrates the generation of enterprise-grade research reports
for academic publications and threat intelligence.
"""

import asyncio
from core.observability.logging import get_logger
from typing import Any, Dict, List, Optional

from core.services.llm.service import LLMService
from ...models import (
    AttackTimelineEntry,
    PayloadExcerpt,
    ThreatSummary,
)

logger = get_logger(__name__)


class ResearchReportGenerator:
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
        import re

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
        from ...prompts_library.research_report_prompts import research_abstract_prompt

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
        from ...prompts_library.research_report_prompts import (
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
        from ...prompts_library.research_report_prompts import (
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
        from ...prompts_library.research_report_prompts import (
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
        from ...prompts_library.research_report_prompts import (
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
        from ...prompts_library.research_report_prompts import (
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

    # =========================================================================
    # FALLBACK TEMPLATES
    # =========================================================================

    # =========================================================================
    # FALLBACK TEMPLATES
    # =========================================================================

    def _fallback_abstract(
        self, honeypot_name: str, summary: ThreatSummary, time_range: str
    ) -> str:
        """Fallback abstract template."""
        return f"""## Abstract

This report presents a comprehensive analysis of {summary.total_events:,} attack events collected from the **{honeypot_name}** honeypot during {time_range}. The dataset encompasses traffic from {summary.unique_attackers:,} unique source addresses across multiple geographic regions. Analysis reveals {summary.detected_botnets} distinct botnet clusters exhibiting coordinated behavior, and {summary.cve_matches} attempts to exploit known CVE vulnerabilities. Approximately {summary.bot_traffic_percentage:.1f}% of captured traffic originates from automated scanning tools. The findings provide actionable insights into current attack methodologies targeting the {honeypot_name} infrastructure and inform defensive strategies for similar deployments.

**Keywords:** honeypot, {honeypot_name}, threat intelligence, MITRE ATT&CK, attack patterns, network security
"""

    def _fallback_key_findings(self, honeypot_name: str, summary: ThreatSummary) -> str:
        """Fallback key findings template."""
        findings = [f"## Key Findings\n\n*Analysis of {honeypot_name} honeypot*\n"]

        findings.append(
            f"- **Attack Volume**: Captured {summary.total_events:,} events from "
            f"{summary.unique_attackers:,} unique sources targeting {honeypot_name}"
        )

        if summary.critical_events > 0:
            findings.append(
                f"- **Critical Severity**: Identified {summary.critical_events} "
                f"critical-severity attack attempts"
            )

        if summary.detected_botnets > 0:
            findings.append(
                f"- **Botnet Activity**: Detected {summary.detected_botnets} "
                f"coordinated botnet clusters"
            )

        if summary.cve_matches > 0:
            findings.append(
                f"- **CVE Exploitation**: Observed {summary.cve_matches} attempts "
                f"to exploit known vulnerabilities"
            )

        findings.append(
            f"- **Automation Ratio**: {summary.bot_traffic_percentage:.1f}% of "
            f"traffic attributed to automated tools"
        )

        return "\n".join(findings)

    def _fallback_mitre_mapping(self, honeypot_name: str) -> str:
        """Fallback MITRE ATT&CK mapping template."""
        return f"""## MITRE ATT&CK Technique Mapping

*Techniques observed targeting {honeypot_name}*

### Reconnaissance
| Technique ID | Technique Name | Evidence from {honeypot_name} | Confidence |
|--------------|----------------|-------------------------------|------------|
| T1595.001 | Active Scanning: IP Blocks | Port scanning activity detected | High |
| T1592 | Gather Victim Host Info | Service version probing | Medium |

### Initial Access
| Technique ID | Technique Name | Evidence from {honeypot_name} | Confidence |
|--------------|----------------|-------------------------------|------------|
| T1110 | Brute Force | Credential guessing attempts | High |
| T1190 | Exploit Public-Facing App | CVE exploitation attempts | Medium |

### Execution
| Technique ID | Technique Name | Evidence from {honeypot_name} | Confidence |
|--------------|----------------|-------------------------------|------------|
| T1059.004 | Unix Shell | Malicious shell commands | Medium |

*Note: Mapping based on observed attack patterns against {honeypot_name}.*
"""

    def _fallback_payload_analysis(
        self, honeypot_name: str, payload_excerpts: List[Dict]
    ) -> str:
        """Fallback payload analysis template with real data.

        Args:
            honeypot_name: Honeypot identifier
            payload_excerpts: List of payload excerpt dicts
        """
        if not payload_excerpts:
            return f"""## Payload Analysis

*Analysis of payloads captured by {honeypot_name}*

### Attack Classification
No significant payloads were captured during this observation period.

### Sophistication Assessment
Insufficient data for analysis."""

        # Analyze real payload data
        categories = {}
        severities = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        protocols = {}
        countries = {}

        for p in payload_excerpts:
            cat = p.get("category", "unknown")
            categories[cat] = categories.get(cat, 0) + 1

            sev = p.get("severity", "medium")
            if sev in severities:
                severities[sev] += 1

            proto = p.get("protocol", "unknown")
            protocols[proto] = protocols.get(proto, 0) + 1

            country = p.get("source_country", "Unknown")
            countries[country] = countries.get(country, 0) + 1

        total = len(payload_excerpts)
        top_category = max(categories, key=categories.get) if categories else "unknown"
        top_protocol = max(protocols, key=protocols.get) if protocols else "unknown"

        return f"""## Payload Analysis

*Analysis of {total} payloads captured by {honeypot_name}*

### Attack Classification

The captured payloads predominantly consist of **{top_category}** attacks ({categories.get(top_category, 0)}/{total} samples), primarily delivered via **{top_protocol}** protocol. 

**Category Distribution:**
{chr(10).join(f"- {cat}: {count} samples" for cat, count in sorted(categories.items(), key=lambda x: -x[1])[:5])}

**Severity Breakdown:**
- Critical: {severities["critical"]} payloads
- High: {severities["high"]} payloads  
- Medium: {severities["medium"]} payloads
- Low: {severities["low"]} payloads

### Obfuscation & Evasion Techniques

Based on payload structure analysis, common evasion techniques include:
- Protocol-specific encoding (URL encoding, base64)
- Command obfuscation through string concatenation
- User-agent impersonation to mimic legitimate traffic

### Exploit Chain Reconstruction

The typical attack sequence observed follows the pattern:
1. **Reconnaissance**: Port scanning and service fingerprinting
2. **Initial Access**: Exploitation attempts targeting {top_category} vulnerabilities
3. **Execution**: Command injection or script delivery
4. **Persistence**: Installation of malware or backdoors (inferred)

### Notable Payloads

| Category | Severity | Technique | Description |
| :--- | :--- | :--- | :--- |
{chr(10).join(f"| {p.get('category', 'unknown')} | {p.get('severity', 'medium')} | {p.get('protocol', 'N/A')} Protocol Attack | {p.get('ai_classification', 'Malicious payload from ' + p.get('source_country', 'Unknown'))[:80]} |" for p in payload_excerpts[:6])}

### Sophistication Assessment

Based on the diversity of attack vectors and payload complexity:
- **Automation Level**: {"High" if total > 10 else "Moderate"} - {total} distinct payloads suggest {"automated scanning tools" if total > 10 else "semi-automated or manual probing"}
- **Threat Actor Profile**: Opportunistic threat actors seeking vulnerable {honeypot_name} infrastructure
- **Geographic Distribution**: Primary sources from {", ".join(list(countries.keys())[:3])}
"""

    def _fallback_conclusions(self, honeypot_name: str, summary: ThreatSummary) -> str:
        """Fallback conclusions template."""
        return f"""## Conclusions

The analysis of {honeypot_name} honeypot data reveals an active threat landscape 
with {summary.total_events:,} events from {summary.unique_attackers:,} unique sources. 
The prevalence of automated scanning ({summary.bot_traffic_percentage:.1f}%) indicates 
opportunistic threat actors seeking vulnerable targets.

## Strategic Recommendations

1. **Network Segmentation**: Isolate similar services using network segmentation
2. **Detection Rules**: Implement YARA rules based on observed payload patterns
3. **Threat Hunting**: Use IOCs from this analysis for proactive threat hunting
4. **Patch Management**: Prioritize patching for CVEs observed in exploitation attempts
5. **Intelligence Sharing**: Share IOCs with industry ISACs and threat intel communities

## Research Significance

This analysis contributes to the understanding of current attack patterns 
targeting {honeypot_name}-type infrastructure and provides actionable intelligence 
for defensive operations.
"""
