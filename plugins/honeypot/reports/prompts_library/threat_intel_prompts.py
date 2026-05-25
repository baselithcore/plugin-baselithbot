"""Threat Intelligence Analysis Prompts.

Prompts for attack patterns, botnets, geographic threats, and attribution.
"""

from typing import Dict, Any, List


def attack_pattern_analysis_prompt(
    patterns: List[Dict[str, Any]], total_events: int
) -> str:
    """Generate prompt for attack pattern analysis.

    Args:
        patterns: List of detected attack patterns
        total_events: Total number of events

    Returns:
        Formatted prompt string
    """
    return f"""You are a cybersecurity threat analyst. Analyze the following attack patterns detected in honeypot telemetry.

**Attack Pattern Data:**
- Total security events: {total_events:,}
- Unique attack patterns: {len(patterns)}
- Pattern samples: {patterns[:15]}

**Instructions:**
1. Identify dominant attack vectors and methodologies
2. Classify patterns by sophistication (automated scanners vs targeted attacks)
3. Detect emerging or unusual attack patterns
4. Map patterns to MITRE ATT&CK framework
5. Assess coordination and campaign indicators
6. Evaluate defender detection and response opportunities
7. Use markdown with headers and bullet points
8. Be technical and specific (350-500 words)

**Format:**
### Attack Pattern Analysis

#### Pattern Distribution
[Overview of attack types and frequencies]

#### Sophisticated Threat Activity
[Analysis of targeted or advanced attacks]

#### MITRE ATT&CK Mapping
[Techniques and tactics observed]

#### Detection Opportunities
[Recommendations for improving detection]

Generate analysis now:"""


def botnet_intelligence_prompt(botnet_data: list, cc_servers: int) -> str:
    """Generate prompt for botnet intelligence analysis.

    Args:
        botnet_data: Botnet cluster information
        cc_servers: Number of suspected C&C servers

    Returns:
        Formatted prompt string
    """
    return f"""You are a botnet intelligence specialist. Analyze the following botnet infrastructure detected through honeypot correlation analysis.

**Botnet Intelligence:**
- Detected botnet clusters: {len(botnet_data)}
- Suspected C&C servers: {cc_servers}
- Cluster details: {botnet_data}

**Instructions:**
1. Assess botnet sophistication and capabilities
2. Identify botnet families or campaigns (Mirai, QBot, etc.)
3. Analyze command & control infrastructure
4. Evaluate coordination patterns and attack orchestration
5. Determine threat level and potential impact
6. Provide IOCs for threat intelligence feeds
7. Recommend blocking and mitigation strategies
8. Use professional markdown formatting (300-450 words)

**Format:**
### Botnet Intelligence Assessment

#### Botnet Infrastructure Overview
[Summary of detected botnets and C&C servers]

#### Botnet Attribution & Classification
[Identification of known botnet families]

#### Coordination Analysis
[Assessment of attack orchestration sophistication]

#### Mitigation Recommendations
[Actionable steps to block and disrupt botnet activity]

Generate analysis now:"""


def geographic_threat_analysis_prompt(
    geo_data: List[Dict[str, Any]], top_countries: List[str]
) -> str:
    """Generate prompt for geographic threat analysis.

    Args:
        geo_data: Geographic distribution data
        top_countries: List of top attacking countries

    Returns:
        Formatted prompt string
    """
    return f"""You are a geopolitical threat analyst. Analyze the geographic distribution of cyber threats observed in honeypot data.

**Geographic Intelligence:**
- Countries represented: {len(geo_data)}
- Top attacking nations: {", ".join(top_countries[:7])}
- Detailed geo data: {geo_data[:10]}

**Instructions:**
1. Analyze geographic patterns and concentration
2. Identify state-sponsored or APT indicators
3. Correlate geography with attack types and sophistication
4. Assess geopolitical motivations and attribution confidence
5. Evaluate hosting infrastructure and bulletproof hosting
6. Discuss jurisdictional challenges for takedown/attribution
7. Professional intelligence community terminology
8. Markdown format (350-500 words)

**Format:**
### Geographic Threat Distribution

#### Regional Analysis
[Breakdown of threats by geographic region]

#### Attribution Indicators
[State-sponsored activity and APT correlations]

#### Infrastructure Assessment
[Hosting patterns and bulletproof infrastructure]

#### Geopolitical Context
[Motivations and jurisdictional considerations]

Generate analysis now:"""


def threat_actor_attribution_prompt(
    patterns: List[str], geo_data: Dict[str, Any], sophistication: str
) -> str:
    """Generate prompt for threat actor attribution analysis.

    Args:
        patterns: Observed attack patterns
        geo_data: Geographic attribution data
        sophistication: Assessed sophistication level

    Returns:
        Formatted prompt string
    """
    return f"""You are a threat attribution specialist. Analyze the following indicators to assess potential threat actor attribution.

**Attribution Indicators:**
- Attack patterns: {patterns}
- Geographic indicators: {geo_data}
- Assessed sophistication: {sophistication}

**Instructions:**
1. Evaluate confidence levels for attribution (LOW/MEDIUM/HIGH)
2. Identify TTPs matching known APT groups or threat actors
3. Analyze infrastructure overlap with known campaigns
4. Assess motivations (financial, espionage, disruption, hacktivism)
5. Compare patterns to threat intelligence databases
6. Provide caveats on attribution confidence
7. Use intelligence community attribution standards
8. Professional markdown (300-450 words)

**Format:**
### Threat Actor Attribution Assessment

#### Attribution Confidence: [LOW/MEDIUM/HIGH]

#### Observed TTPs
[Techniques matching known threat actors]

#### Infrastructure Analysis
[Overlap with known campaigns or groups]

#### Motivation Assessment
[Likely threat actor objectives]

#### Confidence Caveats
[Limitations and alternative explanations]

Generate assessment now:"""
