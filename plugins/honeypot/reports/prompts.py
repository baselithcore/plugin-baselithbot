"""Professional Prompt Templates for LLM Report Generation.

High-quality prompts for generating cybersecurity reports that match
enterprise-grade security platforms (CrowdStrike, Splunk, etc.).
"""

from typing import Dict, Any


class ReportPrompts:
    """Collection of prompt templates for different report sections."""

    @staticmethod
    def vulnerability_analysis_prompt(vulnerabilities_data: Dict[str, Any]) -> str:
        """Generate prompt for vulnerability analysis section."""
        return f"""You are a vulnerability assessment specialist. Analyze the following penetration testing results and generate a comprehensive Vulnerability Analysis report.

**Vulnerability Data:**
```json
{vulnerabilities_data}
```

**Instructions:**
1. Categorize vulnerabilities by severity (CRITICAL/HIGH/MEDIUM/LOW)
2. Identify exploitation chains (vulnerabilities that can be chained together)
3. Assess real-world exploitability and business impact
4. Prioritize remediation based on risk (likelihood × impact)
5. Map vulnerabilities to MITRE ATT&CK techniques where applicable
6. Provide specific remediation steps (not generic advice)
7. Use professional security terminology
8. Format in markdown with clear sections

**Format:**
### Vulnerability Analysis

#### Severity Distribution
[Summary of vulnerabilities by severity]

#### Critical Findings
[Detail each critical vulnerability]

#### Exploitation Risk Assessment
[Analysis of exploitation likelihood and impact]

#### Remediation Priority Matrix
[Prioritized remediation recommendations]

Generate the analysis now (400-600 words):"""

    @staticmethod
    def attack_pattern_analysis_prompt(
        timeline_data: list,
        attack_categories: Dict[str, int],
        protocols: Dict[str, int],
    ) -> str:
        """Generate prompt for attack pattern and TTPs analysis."""
        return f"""You are a cybersecurity analyst specializing in Tactics, Techniques, and Procedures (TTPs). Analyze the following attack patterns and generate a detailed TTP analysis.

**Attack Timeline (Recent Events):**
```json
{timeline_data}
```

**Attack Categories Distribution:**
```json
{attack_categories}
```

**Protocol Distribution:**
```json
{protocols}
```

**Instructions:**
1. Identify distinct attack patterns and techniques
2. Map observed techniques to MITRE ATT&CK framework
3. Detect automated vs. manual attack signatures
4. Identify reconnaissance, exploitation, and post-exploitation phases
5. Assess attacker sophistication level (script kiddie to APT)
6. Highlight unusual or novel techniques
7. Provide detection and prevention strategies
8. Use markdown with clear structure

**Format:**
### Attack Pattern Analysis

#### Observed Techniques (MITRE ATT&CK Mapping)
[List techniques with ATT&CK IDs]

#### Attack Lifecycle Phases
[Breakdown by reconnaissance, initial access, execution, etc.]

#### Attacker Sophistication Assessment
[Analysis of attacker skill level and resources]

#### Detection and Mitigation Strategies
[Specific defensive recommendations]

Generate the analysis now (400-600 words):"""

    @staticmethod
    def botnet_intelligence_prompt(botnet_data: list, cc_servers: int) -> str:
        """Generate prompt for botnet and C2 infrastructure analysis."""
        return f"""You are a threat intelligence analyst specializing in botnets and command & control infrastructure. Analyze the following botnet activity.

**Detected Botnet Clusters:**
```json
{botnet_data}
```

**Identified C&C Servers:** {cc_servers}

**Instructions:**
1. Profile each botnet cluster (size, coordination, sophistication)
2. Analyze C&C communication patterns and infrastructure
3. Identify botnet families if possible (Mirai, Emotet, etc.)
4. Assess botnet capabilities and objectives (DDoS, spam, crypto-mining, etc.)
5. Map C&C infrastructure (domains, IPs, hosting providers)
6. Provide attribution clues (infrastructure patterns, code signatures)
7. Recommend defensive actions (sinkholing, blocking, monitoring)
8. Use threat intelligence terminology

**Format:**
### Botnet Intelligence Analysis

#### Cluster Profiles
[Detail each botnet cluster]

#### C&C Infrastructure Assessment
[Analysis of command and control systems]

#### Botnet Capabilities and Objectives
[What the botnets are designed to do]

#### Attribution Indicators
[Clues about threat actor identity]

#### Disruption Recommendations
[Specific actions to disrupt botnet operations]

Generate the intelligence report now (400-600 words):"""

    @staticmethod
    def geographic_threat_analysis_prompt(
        geo_distribution: list, top_countries: Dict[str, int]
    ) -> str:
        """Generate prompt for geopolitical threat analysis."""
        return f"""You are a geopolitical threat analyst. Analyze the geographic distribution of cyber attacks and provide strategic intelligence.

**Geographic Distribution:**
```json
{geo_distribution}
```

**Top Attacking Countries:**
```json
{top_countries}
```

**Instructions:**
1. Analyze attack concentration by country/region
2. Correlate geography with known threat actors and APT groups
3. Identify geopolitical motivations (espionage, hacktivism, cybercrime)
4. Assess hosting infrastructure patterns (bulletproof hosting, VPS abuse)
5. Highlight unexpected geographic patterns or anomalies
6. Provide context on regional cyber threat landscape
7. Recommend geographic-based defensive strategies
8. Use geopolitical and threat intelligence terminology

**Format:**
### Geographic Threat Intelligence

#### Regional Distribution Analysis
[Breakdown of attacks by region]

#### Threat Actor Attribution by Geography
[Link regions to known threat groups]

#### Geopolitical Context
[Motivations and objectives by region]

#### Infrastructure Patterns
[Hosting providers, VPNs, proxies by country]

#### Geographic Defense Strategy
[Location-based security recommendations]

Generate the analysis now (350-500 words):"""

    @staticmethod
    def cve_exploitation_analysis_prompt(
        cve_matches: int, cve_data: list, attack_vectors: list
    ) -> str:
        """Generate prompt for CVE exploitation trends analysis."""
        return f"""You are a vulnerability intelligence analyst. Analyze CVE exploitation attempts detected in honeypot traffic.

**CVE Matches:** {cve_matches}

**Detected CVE Exploitation Attempts:**
```json
{cve_data}
```

**Attack Vectors:**
```json
{attack_vectors}
```

**Instructions:**
1. Identify which CVEs are being actively exploited
2. Assess severity and exploitability of each CVE
3. Determine if exploitation is automated (mass scanning) or targeted
4. Check for zero-day or recently disclosed vulnerabilities
5. Analyze exploitation trends (increasing, stable, decreasing)
6. Correlate CVEs with affected software/systems
7. Prioritize patching based on exploitation activity
8. Provide patch management recommendations

**Format:**
### CVE Exploitation Analysis

#### Active CVE Exploitation
[List CVEs being exploited with severity and frequency]

#### Exploitation Patterns
[Automated vs. targeted, trends over time]

#### Affected Systems and Software
[What systems are being targeted]

#### Patch Priority Recommendations
[Urgent, high, medium, low priority patches]

#### Detection Signatures
[IOCs and detection rules for these CVEs]

Generate the analysis now (350-500 words):"""

    @staticmethod
    def incident_timeline_narrative_prompt(
        timeline_events: list, critical_events: int, incident_type: str = "security"
    ) -> str:
        """Generate prompt for incident timeline narrative."""
        return f"""You are an incident response analyst. Generate a narrative timeline for this security incident.

**Incident Type:** {incident_type}
**Critical Events:** {critical_events}

**Timeline Events:**
```json
{timeline_events}
```

**Instructions:**
1. Create a chronological narrative of the incident
2. Identify initial access and attack progression
3. Highlight critical decision points and escalations
4. Connect related events to show attack chain
5. Assess incident containment and response effectiveness
6. Identify lessons learned and response gaps
7. Use incident response terminology (NIST, SANS frameworks)
8. Be factual and detailed

**Format:**
### Incident Timeline Narrative

#### Initial Detection
[How and when the incident was first detected]

#### Attack Progression
[Chronological description of attack phases]

#### Critical Events
[Detailed analysis of critical events]

#### Response Actions
[What was done to contain and remediate]

#### Lessons Learned
[Key takeaways and improvements]

Generate the timeline narrative now (400-600 words):"""

    @staticmethod
    def compliance_assessment_prompt(
        compliance_data: Dict[str, Any], framework: str = "NIST"
    ) -> str:
        """Generate prompt for compliance framework assessment."""
        return f"""You are a compliance and audit specialist. Assess security posture against {framework} framework.

**Compliance Data:**
```json
{compliance_data}
```

**Framework:** {framework} Cybersecurity Framework

**Instructions:**
1. Map security events to {framework} control categories
2. Assess control effectiveness based on observed threats
3. Identify gaps in detection and response capabilities
4. Evaluate logging and monitoring completeness
5. Check incident documentation and audit trail
6. Provide compliance score or rating if applicable
7. Recommend control improvements for compliance
8. Use formal compliance language

**Format:**
### {framework} Compliance Assessment

#### Control Category Assessment
[Evaluation of each control category]

#### Control Effectiveness Analysis
[How well controls performed against threats]

#### Compliance Gaps and Findings
[Areas not meeting framework requirements]

#### Audit Trail and Documentation
[Assessment of logging and record-keeping]

#### Compliance Recommendations
[Specific actions to improve compliance posture]

Generate the assessment now (400-600 words):"""

    @staticmethod
    def executive_risk_briefing_prompt(
        risk_data: Dict[str, Any], business_context: str = "enterprise"
    ) -> str:
        """Generate prompt for executive risk briefing (non-technical)."""
        return f"""You are a Chief Information Security Officer (CISO) briefing the board of directors. Create an executive risk briefing.

**Business Context:** {business_context}

**Risk Data:**
```json
{risk_data}
```

**Instructions:**
1. Translate technical threats to business risks
2. Quantify impact in business terms (downtime, data loss, reputation)
3. Compare risk posture to industry benchmarks
4. Highlight trends (improving, stable, deteriorating)
5. Provide strategic security recommendations
6. Avoid technical jargon - use business language
7. Be concise and action-oriented
8. Include executive summary at the top

**Format:**
### Executive Risk Briefing

#### Security Posture Summary
[One-paragraph status: CRITICAL/ELEVATED/STABLE/SECURE]

#### Business Risk Assessment
[Key risks in business impact terms]

#### Industry Benchmark Comparison
[How we compare to peers]

#### Strategic Recommendations
[High-level actions for board consideration]

#### Investment Priorities
[Where security budget should be allocated]

Generate the executive briefing now (300-400 words, non-technical):"""

    @staticmethod
    def threat_actor_attribution_prompt(
        attack_data: Dict[str, Any], threat_intel: Dict[str, Any]
    ) -> str:
        """Generate prompt for threat actor attribution analysis."""
        return f"""You are a threat attribution specialist. Analyze attack patterns to attribute activity to threat actors or groups.

**Attack Data:**
```json
{attack_data}
```

**Threat Intelligence Context:**
```json
{threat_intel}
```

**Instructions:**
1. Identify TTPs that match known threat actors (APT28, Lazarus, etc.)
2. Analyze infrastructure patterns (hosting, domains, IPs)
3. Assess campaign objectives (espionage, financial gain, disruption)
4. Evaluate attribution confidence level (low, medium, high)
5. Provide evidence supporting attribution
6. Discuss alternative hypotheses
7. Use threat actor naming conventions (APT, Fancy Bear, etc.)
8. Be cautious - acknowledge attribution uncertainty

**Format:**
### Threat Actor Attribution Analysis

#### Primary Attribution
[Most likely threat actor with confidence level]

#### Supporting Evidence
[TTPs, infrastructure, and other indicators]

#### Campaign Objectives
[What the threat actor is trying to achieve]

#### Alternative Hypotheses
[Other possible attributions and why]

#### Attribution Confidence Assessment
[Confidence level and caveats]

Generate the attribution analysis now (350-500 words):"""

    @staticmethod
    def get_custom_section_prompt(
        section_name: str,
        section_data: Dict[str, Any],
        context: str = "",
    ) -> str:
        """Generate a generic prompt for custom report sections."""
        return f"""You are a professional cybersecurity analyst. Generate a comprehensive report section on: {section_name}

**Section Context:** {context}

**Data:**
```json
{section_data}
```

**Instructions:**
1. Analyze the provided data thoroughly
2. Structure your analysis with clear headers and subheadings
3. Use professional cybersecurity terminology
4. Provide actionable insights and recommendations
5. Include relevant statistics and metrics
6. Use markdown formatting
7. Be concise but thorough (300-500 words)

**Format:**
### {section_name}

[Your analysis here with appropriate subheadings]

Generate the section now:"""
