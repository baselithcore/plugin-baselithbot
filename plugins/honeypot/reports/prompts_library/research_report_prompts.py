"""Research Report Prompts - Enterprise-Grade Threat Intelligence.

Prompts designed for academic publications and enterprise threat intelligence
following MITRE ATT&CK, SANS, and NIST standards.

Persona: Senior Cybersecurity Researcher and Lead Threat Intelligence Analyst
"""

from typing import Any, Dict, List, Optional

# =============================================================================
# PERSONA DEFINITION
# =============================================================================

RESEARCH_ANALYST_PERSONA = """You are a Senior Cybersecurity Researcher and Lead Threat Intelligence Analyst.

Your expertise includes:
- Advanced persistent threats (APTs) and nation-state attack patterns
- MITRE ATT&CK framework classification and TTP analysis
- SANS and NIST incident documentation standards
- Academic research methodology for threat intelligence

Communication style:
- Rigorous, academic-professional, highly technical and analytical
- Use precise cybersecurity terminology (TTPs, IOCs, exploit kits, payload analysis, CVE correlation)
- Reflect the authority of a top-tier security researcher
- Never use generic or vague language
"""


def research_abstract_prompt(
    honeypot_name: str,
    threat_summary: Dict[str, Any],
    time_range: str,
    honeypot_config: Optional[Dict[str, Any]] = None,
) -> str:
    """Generate prompt for research abstract section.

    Args:
        honeypot_name: Name/ID of the honeypot being analyzed
        threat_summary: Aggregated threat statistics
        time_range: Human-readable time range description
        honeypot_config: Optional honeypot configuration metadata

    Returns:
        Formatted prompt for LLM
    """
    honeypot_context = ""
    if honeypot_config:
        honeypot_context = f"""
Honeypot Configuration:
- Protocol: {honeypot_config.get("protocol", "Unknown")}
- Simulated Service: {honeypot_config.get("description", "Unknown")}
- Detection Capabilities: {honeypot_config.get("detection", {})}
"""

    return f"""{RESEARCH_ANALYST_PERSONA}

**CRITICAL REQUIREMENT**: The honeypot name "{honeypot_name}" MUST appear in the abstract and throughout any analysis discussing this specific asset.

**Task**: Generate a COMPREHENSIVE EXECUTIVE ABSTRACT for a high-priority threat intelligence report.

**Honeypot Under Analysis**: {honeypot_name}
{honeypot_context}

**Collected Data Summary**:
- Total security events: {threat_summary.get("total_events", 0):,}
- Unique threat sources: {threat_summary.get("unique_attackers", 0):,}
- Critical severity events: {threat_summary.get("critical_events", 0)}
- High severity events: {threat_summary.get("high_events", 0)}
- Detected botnet clusters: {threat_summary.get("detected_botnets", 0)}
- C&C server indicators: {threat_summary.get("potential_cc_servers", 0)}
- CVE exploitation attempts: {threat_summary.get("cve_matches", 0)}
- Automated traffic ratio: {threat_summary.get("bot_traffic_percentage", 0):.1f}%
- Analysis period: {time_range}

**Abstract Requirements**:
1. Open with "This report presents a comprehensive analysis of attack data collected from the {honeypot_name} honeypot..."
2. Summarize the dataset scope (events, sources, time period) in detail.
3. Highlight key findings (botnets, CVE exploitation, attack sophistication) with metrics.
4. State research significance, threat landscape implications, and methodology used.
5. Provide a high-level assessment of the threat level (Critical/High/Medium).
6. Include 6-8 academic keywords.

**Format**: Two detailed paragraphs (250-350 words total) followed by keywords line.

**Output Format**:
## Abstract

[Detailed abstract paragraphs mentioning {honeypot_name} prominently]

**Keywords:** [6-8 relevant terms]

Generate the detailed abstract now:"""


def research_key_findings_prompt(
    honeypot_name: str,
    threat_summary: Dict[str, Any],
    attack_categories: Dict[str, int],
    geo_distribution: List[Dict[str, Any]],
) -> str:
    """Generate prompt for key findings section.

    Args:
        honeypot_name: Name/ID of the honeypot
        threat_summary: Threat statistics
        attack_categories: Attack type distribution
        geo_distribution: Geographic attack distribution

    Returns:
        Formatted prompt for LLM
    """
    top_countries = [g.get("country_name", "Unknown") for g in geo_distribution[:5]]
    top_attacks = list(attack_categories.keys())[:5]

    return f"""{RESEARCH_ANALYST_PERSONA}

**CRITICAL**: Reference the honeypot "{honeypot_name}" in findings describing asset-specific observations.

**Task**: Generate EXHAUSTIVE KEY FINDINGS for the {honeypot_name} honeypot analysis.

**Data Context**:
- Honeypot: {honeypot_name}
- Total events: {threat_summary.get("total_events", 0):,}
- Unique attackers: {threat_summary.get("unique_attackers", 0):,}
- Severity breakdown:
  - Critical: {threat_summary.get("critical_events", 0)}
  - High: {threat_summary.get("high_events", 0)}
  - Medium: {threat_summary.get("medium_events", 0)}
  - Low: {threat_summary.get("low_events", 0)}
- Top attack categories: {", ".join(top_attacks)}
- Top source countries: {", ".join(top_countries)}
- Botnet clusters: {threat_summary.get("detected_botnets", 0)}
- C&C indicators: {threat_summary.get("potential_cc_servers", 0)}
- CVE attempts: {threat_summary.get("cve_matches", 0)}

**Requirements**:
1. **8-12 comprehensive bullet-pointed findings**.
2. Each finding must be DEEP, TECHNICAL, and DATA-DRIVEN.
3. Classify sophistication: automated scanning vs. targeted attacks.
4. Highlight anomalies, novel patterns, or campaign indicators.
5. Correlate attack source origins with observed TTPs.
6. Reference {honeypot_name} where asset-specific.
7. Use bolding for the finding title/category.

**Format**:
## Key Findings

- **[Category/Title]**: [Detailed description (2-3 sentences) with specific metrics and technical context...]
- **[Category/Title]**: [Description...]
...

Generate the exhaustive key findings now:"""


def research_mitre_mapping_prompt(
    honeypot_name: str,
    attack_categories: Dict[str, int],
    protocols: Dict[str, int],
    timeline_sample: List[Dict[str, Any]],
    payload_samples: Optional[List[str]] = None,
) -> str:
    """Generate prompt for MITRE ATT&CK technique mapping.

    Args:
        honeypot_name: Honeypot identifier
        attack_categories: Attack type distribution
        protocols: Protocol distribution
        timeline_sample: Sample of recent attack events
        payload_samples: Optional payload excerpts for context

    Returns:
        Formatted prompt for LLM
    """
    payload_context = ""
    if payload_samples:
        payload_context = f"""
Sample Payloads (sanitized excerpts):
{chr(10).join(f"- {p[:100]}..." for p in payload_samples[:5])}
"""

    return f"""{RESEARCH_ANALYST_PERSONA}

**Task**: Map observed attack patterns from {honeypot_name} to MITRE ATT&CK techniques with rigorous compliance.

**Asset Context**: {honeypot_name} honeypot
{payload_context}

**Observed Attack Data**:
- Attack categories: {attack_categories}
- Protocols used: {protocols}
- Recent events sample: {timeline_sample[:10]}

**MITRE ATT&CK Mapping Requirements**:
1. Correctly identify Tactics and Techniques with valid MITRE IDs (e.g., T1595.001).
2. **STRICT TABLE FORMATTING**:
   - Ensure explicit markdown table syntax.
   - All rows must have the same number of columns.
   - Align text in columns.
   - Do NOT break lines within a cell if it breaks the table structure.
3. Provide confidence correlation (High/Medium/Low).
4. Cite specific evidence from the {honeypot_name} logs.

**Analytic Focus**:
- Reconnaissance, Initial Access, Execution, Persistence, C2.

**Format**:
## MITRE ATT&CK Technique Mapping

### Reconnaissance
| Technique ID | Technique Name | Evidence from {honeypot_name} | Confidence |
| :--- | :--- | :--- | :--- |
| T1595.001 | Active Scanning: IP Blocks | Port scanning sweep detected from multiple sources | High |

### Initial Access
| Technique ID | Technique Name | Evidence from {honeypot_name} | Confidence |
| :--- | :--- | :--- | :--- |
[Table Rows...]

### Execution
| Technique ID | Technique Name | Evidence from {honeypot_name} | Confidence |
| :--- | :--- | :--- | :--- |
[Table Rows...]

### Attack Lifecycle Analysis
[A detailed summary paragraph analyzing the progression of the attack lifecycle observed against {honeypot_name}, linking the tactics together.]

Generate the MITRE mapping now:"""


def research_payload_analysis_prompt(
    honeypot_name: str,
    payload_excerpts: List[Dict[str, Any]],
    protocol: str = "mixed",
) -> str:
    """Generate prompt for payload analysis section.

    Args:
        honeypot_name: Honeypot identifier
        payload_excerpts: Sanitized payload samples with metadata
        protocol: Primary protocol observed

    Returns:
        Formatted prompt for LLM
    """
    payload_data = []
    for p in payload_excerpts[:15]:
        payload_data.append(
            {
                "category": p.get("category", "unknown"),
                "severity": p.get("severity", "medium"),
                "excerpt": p.get("excerpt", "")[
                    :300
                ],  # Increased from 200 for more context
                "source_country": p.get("source_country", "Unknown"),
                "timestamp": p.get("timestamp", ""),
                "protocol": p.get("protocol", "unknown"),
                "ai_classification": p.get("ai_classification", ""),
            }
        )

    # Format payloads with full context for better analysis
    formatted_payloads = []
    for i, p in enumerate(payload_data, 1):
        formatted_payloads.append(
            f"""
**Payload {i}**:
- Time: {p["timestamp"]}
- Category: {p["category"]} | Severity: {p["severity"]}
- Protocol: {p["protocol"]} | Source: {p["source_country"]}
- AI Classification: {p["ai_classification"] or "Not classified"}
- Content: {p["excerpt"]}
"""
        )

    return f"""{RESEARCH_ANALYST_PERSONA}

**Task**: Perform an EXHAUSTIVE, FORENSICALLY-DETAILED PAYLOAD DECONSTRUCTION for the {honeypot_name} honeypot.

**Context**:
- Honeypot: {honeypot_name}
- Primary protocol: {protocol}
- Payload samples: {len(payload_excerpts)}

**CRITICAL FORMATTING REQUIREMENT**:
You MUST use EXACT markdown table syntax for the Notable Payloads table:
- Each row MUST have exactly 4 cells separated by `|`
- NO line breaks within cells
- Align columns with `:---` syntax
- Example of CORRECT format:

| Category | Severity | Technique | Description |
| :--- | :--- | :--- | :--- |
| RCE | Critical | Log4Shell (CVE-2024-21762) | JNDI injection targeting vulnerable FortiGate SSL VPN |
| Command Injection | High | Mirai Variant | Wget-based payload delivery with chmod execution |

**Payload Data** (sanitized, with full context):
{"".join(formatted_payloads)}

**Analysis Requirements** (MINIMUM 200 WORDS PER SUBSECTION):

1. **Attack Classification** (300+ words):
   - Identify EXACT techniques (e.g., "Log4Shell CVE-2024-21762", not just "RCE")
   - Group by attack family (Mirai, Mozi, Kinsing, APT-style)
   - Cite specific CVE numbers if recognizable
   - Analyze payload sophistication (script kiddie vs. advanced)
   - Identify tool signatures (nmap, sqlmap, custom scripts)

2. **Obfuscation & Evasion Techniques** (250+ words):
   - Identify base64, hex, URL encoding
   - Detect whitespace/comment evasion
   - Analyze string concatenation tricks
   - Note anti-detection measures (user-agent spoofing, polymorphism)
   - Rate evasion sophistication (1-10 scale with justification)

3. **Exploit Chain Reconstruction** (300+ words):
   - Reconstruct the FULL intended attack sequence
   - Example: "Initial Access (SSH brute force) -> Download (wget malicious.sh) -> Persistence (cron job) -> C2 Beaconing (HTTP POST to attacker IP)"
   - Identify each stage: Reconnaissance, Weaponization, Delivery, Exploitation, Installation, C2, Actions on Objectives
   - Infer attacker intent (cryptomining, botnet recruitment, data exfiltration)

4. **Malware Attribution** (200+ words):
   - Correlate with known botnets (Mirai signature: "busybox wget", Mozi: specific C2 patterns)
   - Match to threat intelligence feeds
   - Identify geographic/linguistic indicators
   - Rate confidence in attribution (High/Medium/Low with evidence)

5. **Notable Payloads Table** (STRICT MARKDOWN):
   - Select the 5-8 MOST SIGNIFICANT payloads
   - Each row MUST be a single line (no multi-line cells)
   - Description column: 1-sentence technical summary (max 100 chars)

**FORMAT**:
## Payload Analysis

### Attack Classification
[Detailed analysis with specific CVE numbers, malware families, and tool signatures. MINIMUM 300 words. Reference specific payloads by number.]

### Obfuscation & Evasion Techniques
[In-depth analysis of how attackers attempted to hide intent. MINIMUM 250 words. Cite payload examples.]

### Exploit Chain Reconstruction
[Step-by-step reconstruction of the attack kill chain. MINIMUM 300 words. Use "Payload X demonstrates..." format.]

### Malware Attribution
[Correlation with known threat actors and malware families. MINIMUM 200 words. Cite intelligence sources if applicable.]

### Notable Payloads

| Category | Severity | Technique | Description |
| :--- | :--- | :--- | :--- |
| [Exact category] | [Critical/High/Medium] | [Specific CVE or technique name] | [Single-line technical description] |

### Sophistication Assessment
[Evaluation of attacker skill level, automation vs. manual, and threat actor profiling. MINIMUM 150 words.]

**VALIDATION CHECKLIST** (confirm before generating):
- [ ] Each subsection meets minimum word count
- [ ] All CVEs and malware families are explicitly named
- [ ] Notable Payloads table has exactly 4 columns per row
- [ ] No line breaks within table cells
- [ ] At least 3 specific payload numbers are referenced in analysis
- [ ] Sophistication score (1-10) is provided with justification

Generate the comprehensive payload analysis now:"""


def research_conclusions_prompt(
    honeypot_name: str,
    threat_summary: Dict[str, Any],
    key_findings: List[str],
    time_range: str,
) -> str:
    """Generate prompt for conclusions and recommendations section.

    Args:
        honeypot_name: Honeypot identifier
        threat_summary: Aggregated statistics
        key_findings: List of key findings already generated
        time_range: Analysis time period

    Returns:
        Formatted prompt for LLM
    """
    return f"""{RESEARCH_ANALYST_PERSONA}

**Task**: Generate RESEARCH CONCLUSIONS, STRATEGIC RECOMMENDATIONS, and THREAT FORECAST based on {honeypot_name} analysis.

**Analysis Context**:
- Asset: {honeypot_name}
- Time period: {time_range}
- Total events analyzed: {threat_summary.get("total_events", 0):,}
- Threat sources: {threat_summary.get("unique_attackers", 0):,}
- Botnet activity: {threat_summary.get("detected_botnets", 0)} clusters
- CVE exploitation: {threat_summary.get("cve_matches", 0)} attempts

**Key Findings Summary**:
{chr(10).join(f"- {f}" for f in key_findings[:5])}

**Requirements**:
1. **Conclusions** (3-5 comprehensive paragraphs):
   - Synthesize all findings into a coherent threat narrative.
   - Evaluate the effectiveness of defensive measures.
   - Discuss attacker motivation (ROI, espionage, destruction).

2. **Strategic Recommendations** (Detailed & Actionable):
   - **Network Security**: Segmentation, ACLs, Firewall rules.
   - **Host Security**: Patching, Hardening, EDR configuration.
   - **Policy & Process**: Incident Response, User Awareness.
   - **Threat Hunting**: Specific IOCs and behaviors to hunt for.

3. **Threat Forecast**:
   - Predications on how these attacks will evolve in the near future.
   - Emerging trends relevant to this asset type.

4. **Research Significance**:
   - Value of this data to the intelligence community.

**Format**:
## Conclusions

[Detailed concluding paragraphs referencing {honeypot_name}...]

## Strategic Recommendations

### Network Security
- **Recommendation**: [Detail...]
- **Recommendation**: [Detail...]

### Host & Application Security
- **Recommendation**: [Detail...]
- **Recommendation**: [Detail...]

### Policy & Threat Hunting
- **Recommendation**: [Detail...]

## Threat Forecast
[Predictive analysis based on current trends...]

## Research Significance
[Significance statement...]

Generate conclusions now:"""


def research_trend_analysis_prompt(
    honeypot_name: str,
    timeline_data: List[Dict[str, Any]],
    time_range: str,
) -> str:
    """Generate prompt for temporal trend analysis.

    Args:
        honeypot_name: Honeypot identifier
        timeline_data: Time-series attack data
        time_range: Analysis period

    Returns:
        Formatted prompt for LLM
    """
    return f"""{RESEARCH_ANALYST_PERSONA}

**Task**: Analyze temporal attack trends observed on {honeypot_name}.

**Data Context**:
- Honeypot: {honeypot_name}
- Analysis period: {time_range}
- Timeline events: {len(timeline_data)} data points

**Timeline Sample**:
{timeline_data[:20]}

**Analysis Requirements**:
1. Identify attack volume patterns (daily/weekly cycles)
2. Detect campaign bursts or coordinated activity windows
3. Correlate timing with known threat actor operating hours
4. Highlight any escalation or de-escalation trends
5. Note correlation with external events (patch releases, etc.)

**Format**:
## Temporal Trend Analysis

### Attack Volume Patterns
[Analysis of timing patterns for {honeypot_name}]

### Campaign Detection
[Identification of distinct attack campaigns]

### Trend Assessment
[Overall threat trajectory]

Generate trend analysis now:"""


def research_attack_narrative_prompt(
    session_analysis: Any,  # AttackSessionAnalysis
) -> str:
    """Generate prompt for sequential attack narrative.

    Args:
        session_analysis: AttackSessionAnalysis object with steps

    Returns:
        Formatted prompt for LLM
    """
    session_id = session_analysis.session_id
    attacker_ip = session_analysis.attacker_ip
    steps_data = []

    for step in session_analysis.steps:
        steps_data.append(
            {
                "time": step.timestamp.isoformat(),
                "phase": step.phase,
                "action": step.description,
                "payload": step.payload_snippet or "N/A",
            }
        )

    return f"""{RESEARCH_ANALYST_PERSONA}

**Task**: Reconstruct the "Kill Chain" narrative for a specific attack session captured by the honeypot.

**Session Context**:
- Session ID: {session_id}
- Attacker IP: {attacker_ip}
- Total Steps: {len(steps_data)}

**Attack Sequence**:
{chr(10).join(f"- [{s['time']}] {s['phase']}: {s['action']} (Payload: {s['payload']})" for s in steps_data)}

**Requirements**:
1. Write a chronological narrative describing the attacker's actions.
2. **Interpret intent**: Explain *why* the attacker executed specific commands or payloads.
3. Highlight the progression from Reconnaissance -> Initial Access -> Exploitation.
4. If payloads are present, analyze them briefly within the flow.
5. Use professional, forensic language.
6. Keep it concise (1-2 paragraphs per session).

**Format**:
### Attack Session Analysis: {attacker_ip}
[Chronological narrative...]

**Key Techniques Observed**:
- [Technique 1]
- [Technique 2]

Generate the narrative now:"""
