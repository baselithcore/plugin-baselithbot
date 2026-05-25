"""Fallback Handlers for LLM Report Generation.

Provides template-based fallbacks with research-focused language.
"""

from typing import List

from ...models import ThreatSummary, ReportConfig


def fallback_executive_summary(
    threat_summary: ThreatSummary, config: ReportConfig
) -> str:
    """Generate fallback research summary using templates.

    Args:
        threat_summary: Threat statistics
        config: Report configuration

    Returns:
        Template-based research summary
    """
    org = config.organization_name or "the research environment"

    return f"""## Research Overview

### Data Collection Summary

During the observation period, the honeypot infrastructure in {org} captured **{threat_summary.total_events:,}** attack events from **{threat_summary.unique_attackers:,}** unique source addresses.

**Dataset Characteristics:**
- Critical Severity Events: {threat_summary.critical_events}
- High Severity Events: {threat_summary.high_events}
- Identified Botnet Clusters: {threat_summary.detected_botnets}
- Automated Traffic Ratio: {threat_summary.bot_traffic_percentage:.1f}%

**Research Value:** This dataset provides {_research_value_assessment(threat_summary)} for studying modern attack patterns and threat actor behaviors.
"""


def _research_value_assessment(threat_summary: ThreatSummary) -> str:
    """Assess the research value of the dataset."""
    if threat_summary.detected_botnets > 0 or threat_summary.critical_events > 5:
        return "significant research opportunities"
    elif threat_summary.total_events > 1000:
        return "substantial data for statistical analysis"
    elif threat_summary.unique_attackers > 100:
        return "diverse source distribution for geographic studies"
    else:
        return "baseline data for comparison studies"


def fallback_threat_analysis(threat_summary: ThreatSummary) -> str:
    """Generate fallback pattern analysis using templates.

    Args:
        threat_summary: Threat statistics

    Returns:
        Template-based pattern analysis
    """
    return f"""### Attack Pattern Research Analysis

**Dataset Overview:**
The collected data comprises {threat_summary.total_events:,} total security events, providing a comprehensive view of attack patterns and techniques.

**Key Observations:**
- {threat_summary.detected_botnets} distinct botnet clusters exhibiting coordinated behavior
- {threat_summary.potential_cc_servers} command & control infrastructure endpoints identified
- {threat_summary.cve_matches} CVE exploitation attempts observed
- {threat_summary.bot_traffic_percentage:.1f}% of traffic attributed to automated scanning tools

**Research Significance:**
The data reveals {"diverse attack patterns suitable for behavioral clustering studies" if threat_summary.critical_events > 0 else "baseline attack activity useful for establishing normal patterns"}.
"""


def fallback_research_insights(threat_summary: ThreatSummary) -> List[str]:
    """Generate fallback research insights using rule-based logic.

    Args:
        threat_summary: Threat statistics

    Returns:
        List of research insight strings
    """
    insights = []

    # Pattern observations based on data characteristics
    if threat_summary.critical_events > 0:
        insights.append(
            f"Pattern Analysis: {threat_summary.critical_events} critical severity events warrant deeper behavioral analysis to understand sophisticated attack techniques"
        )

    if threat_summary.detected_botnets > 0:
        insights.append(
            f"Coordination Study: {threat_summary.detected_botnets} botnet clusters show coordinated behavior patterns suitable for infrastructure mapping research"
        )

    if threat_summary.potential_cc_servers > 0:
        insights.append(
            "Infrastructure Analysis: Identified C&C endpoints provide opportunities for studying command and control communication patterns"
        )

    if threat_summary.cve_matches > 0:
        insights.append(
            f"Exploitation Trends: {threat_summary.cve_matches} CVE exploitation attempts reveal current vulnerability targeting patterns in the wild"
        )

    if threat_summary.bot_traffic_percentage > 50:
        insights.append(
            "Automation Analysis: High automated traffic ratio suggests prevalent use of scanning tools worthy of fingerprinting studies"
        )

    if threat_summary.high_events > 10:
        insights.append(
            "Severity Distribution: Event severity patterns could inform detection threshold research and classification improvements"
        )

    # General research insights
    insights.extend(
        [
            "Temporal Patterns: Time-series analysis of the collected data could reveal attack campaign rhythms and geographic correlations",
            "Behavioral Clustering: Machine learning techniques could identify distinct attacker profiles from the observed patterns",
            "Comparative Study: This dataset provides baseline measurements for longitudinal attack trend analysis",
        ]
    )

    return insights[:10]  # Limit to top 10


# Backward compatibility alias
def fallback_recommendations(threat_summary: ThreatSummary) -> List[str]:
    """Alias for fallback_research_insights for backward compatibility."""
    return fallback_research_insights(threat_summary)


def fallback_ioc_analysis(ioc_count: int, unique_sources: int) -> str:
    """Generate fallback IOC pattern analysis using templates.

    Args:
        ioc_count: Total IOC count
        unique_sources: Number of unique sources

    Returns:
        Template-based IOC pattern analysis
    """
    return f"""### IOC Pattern Analysis

**Dataset Summary:**
Collected {ioc_count} Indicators of Compromise (IOCs) from {unique_sources} unique sources during the observation period.

**Distribution Analysis:**
- IP addresses exhibiting coordinated behavioral patterns
- Command & Control infrastructure endpoints
- Known exploit delivery mechanisms

**Clustering Observations:**
- Geographic clustering suggests organized campaign infrastructure
- Temporal patterns indicate automated scanning operations
- Protocol analysis reveals reconnaissance and exploitation phases

**Research Applications:**
- Infrastructure fingerprinting for attribution studies
- Behavioral clustering for threat actor profiling
- Temporal correlation for campaign timeline reconstruction
"""
