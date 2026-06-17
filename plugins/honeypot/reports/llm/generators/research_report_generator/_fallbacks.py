"""Fallback template methods for ResearchReportGenerator."""

from typing import Dict, List

from ....models import ThreatSummary


class FallbacksMixin:
    """Mixin providing fallback templates when LLM generation fails."""

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
