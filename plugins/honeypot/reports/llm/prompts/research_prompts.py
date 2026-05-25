"""Advanced Research Prompt Templates.

Ultra-professional prompts for academic-grade cybersecurity research reports
with MITRE ATT&CK mapping, statistical analysis, and research methodology.
"""

import json
from typing import Dict, Any, List


def build_abstract_prompt(context: Dict[str, Any]) -> str:
    """Build prompt for research abstract/summary.

    Args:
        context: Report context data

    Returns:
        Formatted prompt string
    """
    return f"""You are writing an abstract for a peer-reviewed cybersecurity research paper. Generate a professional research abstract based on honeypot data analysis.

**Dataset Context:**
{json.dumps(context, indent=2)}

**Instructions:**
1. Write in formal academic style (like IEEE, ACM, or USENIX papers)
2. Include: background, methodology, key findings, and significance
3. Quantify results with specific numbers
4. Keep to 150-250 words
5. Use passive voice where appropriate
6. End with implications for the field

**Format:**
## Abstract

[Your abstract text - single paragraph, 150-250 words]

**Keywords:** [5-7 relevant keywords separated by commas]

Generate the abstract now:"""


def build_key_findings_prompt(context: Dict[str, Any]) -> str:
    """Build prompt for key findings summary.

    Args:
        context: Report context data

    Returns:
        Formatted prompt string
    """
    return f"""You are a cybersecurity researcher summarizing key findings from honeypot data analysis. Generate a concise key findings section.

**Analysis Context:**
{json.dumps(context, indent=2)}

**Instructions:**
1. List 5-8 most significant findings
2. Each finding should be specific and quantified
3. Order by research significance (most important first)
4. Use bullet points with bold headers
5. Focus on patterns, anomalies, and novel observations
6. Avoid generic statements

**Format:**
## Key Findings

- **[Finding Title]:** Specific observation with numbers (e.g., "42% of traffic...")
- **[Finding Title]:** Another quantified observation
[Continue for 5-8 findings]

Generate the key findings now:"""


def build_mitre_attack_prompt(
    attack_categories: Dict[str, int],
    protocols: Dict[str, int],
    timeline_sample: List[Dict],
) -> str:
    """Build prompt for MITRE ATT&CK technique mapping.

    Args:
        attack_categories: Attack category distribution
        protocols: Protocol distribution
        timeline_sample: Sample of attack timeline events

    Returns:
        Formatted prompt string
    """
    context = {
        "attack_categories": attack_categories,
        "protocols": protocols,
        "sample_events": timeline_sample[:20],
    }

    return f"""You are a threat intelligence analyst mapping observed attack behaviors to the MITRE ATT&CK framework. Analyze the honeypot data and identify applicable techniques.

**Observed Attack Data:**
{json.dumps(context, indent=2)}

**Instructions:**
1. Map observed behaviors to specific MITRE ATT&CK techniques
2. Use official ATT&CK technique IDs (e.g., T1110, T1595)
3. Group by ATT&CK Tactics (Reconnaissance, Initial Access, Execution, etc.)
4. Estimate confidence level for each mapping (High/Medium/Low)
5. Include technique names and brief descriptions
6. Focus on techniques with clear evidence in the data

**Format:**
## MITRE ATT&CK Technique Mapping

### Reconnaissance
| Technique ID | Technique Name | Evidence | Confidence |
|--------------|----------------|----------|------------|
| T1595 | Active Scanning | [Evidence from data] | High/Medium/Low |

### Initial Access
[Continue for each relevant tactic]

### Summary
[Brief summary of dominant attack techniques observed]

Generate the ATT&CK mapping now:"""


def build_methodology_section() -> str:
    """Generate research methodology section (static template).

    Returns:
        Methodology section markdown
    """
    return """## Research Methodology

### Data Collection
Attack data was collected using a distributed honeypot infrastructure designed to capture malicious traffic across multiple protocols and services. The honeypot systems emulate vulnerable services to attract and log attack attempts without exposing actual production systems.

### Collection Environment
- **Honeypot Type:** High-interaction and low-interaction hybrid deployment
- **Protocols Monitored:** SSH, HTTP/HTTPS, FTP, SMTP, SMB, Telnet, and custom services
- **Data Captured:** Source IPs, timestamps, payloads, credentials, commands, and behavioral patterns

### Analysis Approach
1. **Event Aggregation:** Raw events were aggregated by source IP, time windows, and attack type
2. **Behavioral Clustering:** Machine learning techniques applied to identify coordinated attack patterns
3. **Geographic Attribution:** IP geolocation used to map attack origins
4. **CVE Correlation:** Attack payloads matched against known vulnerability signatures
5. **Botnet Detection:** Graph analysis used to identify command & control infrastructure

### Limitations
- Honeypot data represents attacks targeting vulnerable systems, not necessarily broader threat landscape
- Geographic attribution is based on IP geolocation, which may be affected by VPNs/proxies
- Some attack payloads may be truncated or obfuscated

### Ethical Considerations
All data collection was passive and did not involve active engagement with threat actors. No personally identifiable information (PII) was collected beyond IP addresses, which are treated as indicators of compromise (IOCs).
"""


def build_statistical_analysis_prompt(
    context: Dict[str, Any],
    total_events: int,
    unique_sources: int,
) -> str:
    """Build prompt for statistical analysis section.

    Args:
        context: Full context data
        total_events: Total event count
        unique_sources: Unique source count

    Returns:
        Formatted prompt string
    """
    return f"""You are a data scientist analyzing cybersecurity honeypot data. Generate a statistical analysis section with proper metrics.

**Dataset Statistics:**
- Total Events: {total_events:,}
- Unique Sources: {unique_sources:,}

**Full Context:**
{json.dumps(context, indent=2)}

**Instructions:**
1. Calculate and present key statistical metrics
2. Include percentages, ratios, and distributions
3. Discuss statistical significance where applicable
4. Use proper statistical terminology
5. Present data in tables where appropriate
6. Note any outliers or anomalies
7. Be precise with numbers (use appropriate decimal places)

**Format:**
## Statistical Analysis

### Dataset Overview
| Metric | Value | Notes |
|--------|-------|-------|
| Total Events | {total_events:,} | ... |
| Unique Sources | {unique_sources:,} | ... |
[Additional computed metrics]

### Distribution Analysis
[Analysis of attack type, severity, and geographic distributions]

### Temporal Patterns
[Analysis of time-based patterns if available]

### Correlation Analysis
[Notable correlations between variables]

### Statistical Observations
[Key statistical insights]

Generate the statistical analysis now:"""


def build_trend_analysis_prompt(
    timeline_data: List[Dict],
    time_range: str,
) -> str:
    """Build prompt for temporal trend analysis.

    Args:
        timeline_data: Timeline event data
        time_range: Time range description

    Returns:
        Formatted prompt string
    """
    # Aggregate by hour/day for trend analysis
    return f"""You are analyzing temporal trends in honeypot attack data. Generate a trend analysis section.

**Time Range:** {time_range}
**Event Timeline Sample:**
{json.dumps(timeline_data[:50], indent=2)}

**Instructions:**
1. Identify temporal patterns (hourly, daily, weekly cycles)
2. Note any attack spikes or unusual activity periods
3. Discuss potential correlations with external events
4. Identify sustained campaigns vs. opportunistic scanning
5. Use trend terminology (increasing, stable, decreasing, cyclical)

**Format:**
## Temporal Trend Analysis

### Activity Patterns
[Description of time-based patterns]

### Notable Events
[Specific time periods with unusual activity]

### Campaign Analysis
[Evidence of sustained attack campaigns]

### Trend Summary
[Overall trend assessment]

Generate the trend analysis now:"""


def build_references_section(attack_categories: Dict[str, int]) -> str:
    """Generate references and further reading section.

    Args:
        attack_categories: Attack types to reference

    Returns:
        References section markdown
    """
    # Standard cybersecurity references
    references = """## References & Further Reading

### Frameworks & Standards
1. MITRE ATT&CK Framework - https://attack.mitre.org/
2. NIST Cybersecurity Framework - https://www.nist.gov/cyberframework
3. OWASP Top Ten - https://owasp.org/Top10/

### Threat Intelligence Resources
4. CISA Known Exploited Vulnerabilities Catalog - https://www.cisa.gov/known-exploited-vulnerabilities-catalog
5. AlienVault OTX - https://otx.alienvault.com/
6. VirusTotal - https://www.virustotal.com/

### Research Publications
7. Verizon Data Breach Investigations Report (DBIR) - Annual industry threat analysis
8. Mandiant M-Trends Report - Advanced threat research findings
9. CrowdStrike Global Threat Report - Threat actor intelligence

### Honeypot Research
10. The Honeynet Project - https://www.honeynet.org/
11. "Know Your Enemy" book series - Comprehensive honeypot methodology

### CVE Databases
12. National Vulnerability Database (NVD) - https://nvd.nist.gov/
13. CVE Details - https://www.cvedetails.com/
"""
    return references


def build_appendix_prompt(context: Dict[str, Any]) -> str:
    """Build prompt for appendix data summary.

    Args:
        context: Full report context

    Returns:
        Formatted prompt string
    """
    return f"""You are preparing an appendix for a cybersecurity research report. Summarize the raw data in a format suitable for an appendix.

**Data Context:**
{json.dumps(context, indent=2)}

**Instructions:**
1. Create summary tables of raw data
2. List top N items for each category
3. Format IOCs in a shareable format
4. Include data quality notes
5. Keep technical and precise

**Format:**
## Appendix A: Raw Data Summary

### A.1 Top Source IP Addresses
[Table of top IPs with counts]

### A.2 Attack Category Breakdown
[Detailed category list]

### A.3 Protocol Distribution
[Protocol statistics]

### A.4 IOC Export Format
[IOCs in a format suitable for threat intel sharing]

Generate the appendix summary now:"""
