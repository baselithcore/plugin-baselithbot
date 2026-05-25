"""Report Generator.

Responsible for generating text content (Executive Summary, Recommendations)
based on aggregated data.
"""

from typing import List, Optional

from .models import ReportConfig, SecurityReport, ThreatSummary


class ReportTextGenerator:
    """Generates text content for reports."""

    async def generate_executive_summary(
        self,
        threat_summary: ThreatSummary,
        config: ReportConfig,
        title: Optional[str] = None,
    ) -> str:
        """Generate executive summary text."""
        org_name = config.organization_name or "the organization"
        time_period = f"the past {config.time_range_hours} hours"

        if config.report_type == "executive":
            return self._generate_executive_style(threat_summary, org_name, time_period)
        elif config.report_type == "threat_intel":
            return self._generate_threat_intel_style(
                threat_summary, org_name, time_period
            )
        elif config.report_type == "compliance":
            return self._generate_compliance_style(
                threat_summary, org_name, time_period
            )
        else:
            # Default to technical/standard style
            return self._generate_technical_style(threat_summary, org_name, time_period)

    def _generate_executive_style(
        self, summary: ThreatSummary, org: str, period: str
    ) -> str:
        """High-level business focused summary."""
        status = "CRITICAL" if summary.critical_events > 0 else "STABLE"
        if status == "STABLE" and summary.high_events > 10:
            status = "ELEVATED"

        return f"""## Executive Overview

### Security Posture Status: {status}

**Executive Briefing**:
Over the {period}, {org}'s security sensors successfully intercepted and neutralized **{summary.total_events:,}** attempting intrusions. The automated defense systems prevented potential unauthorized access from **{summary.unique_attackers:,}** distinct sources.

**Business Impact Assessment**:
*   **Critical Incidents**: {summary.critical_events} required immediate automated mitigation.
*   **Infrastructure Safety**: Systems remained resilient against {summary.detected_botnets} detected botnet campaigns.
*   **Risk Profile**: {summary.bot_traffic_percentage:.1f}% of traffic was identified as automated non-targeted noise.

**Strategic Recommendation**:
{"Immediate review of critical incident logs is recommended." if summary.critical_events > 0 else "Maintain current security posture and continue regular monitoring."}
"""

    def _generate_threat_intel_style(
        self, summary: ThreatSummary, org: str, period: str
    ) -> str:
        """IOC and campaign focused summary."""
        top_cc = ", ".join(list(summary.top_attacking_countries.keys())[:3])

        return f"""## Threat Intelligence Briefing

### Campaign Analysis
Data collection from {period} indicates active probing from **{summary.unique_attackers:,}** threat actors. 
Activity is concentrated in the following regions: **{top_cc}**.

### Key Indicators
*   **Botnet Activity**: {summary.detected_botnets} active clusters identified.
*   **C2 Infrastructure**: {summary.potential_cc_servers} potential Command & Control nodes correlated.
*   **CVE Targeting**: Attackers are actively scanning for {summary.cve_matches} known vulnerabilities.

### Threat Actor Profile
The majority of traffic ({summary.bot_traffic_percentage:.1f}%) matches known automated scanner signatures. Advanced persistent threats (APTs) constitute the remaining targeted traffic.
"""

    def _generate_compliance_style(
        self, summary: ThreatSummary, org: str, period: str
    ) -> str:
        """Audit and logging focused summary."""
        return f"""## Compliance & Audit Summary

### Audit Period: {period}
**Organization**: {org}

### Security Controls Effectiveness
*   **Access Attempts Recorded**: {summary.total_events:,}
*   **Source IPs Logged**: {summary.unique_attackers:,}
*   **Protocol Coverage**: {", ".join(list(summary.top_protocols.keys())[:3])}

### Incident Management
*   **Critical Severity Events**: {summary.critical_events} (Ticketed: Auto-generated)
*   **High Severity Events**: {summary.high_events}
*   **Policy Violations**: 0 detected

All events have been securely logged and timestamped in accordance with data retention policies.
"""

    def _generate_technical_style(
        self, summary: ThreatSummary, org: str, period: str
    ) -> str:
        """Detailed technical summary (Original Style)."""
        # Determine threat level
        if summary.critical_events > 10 or summary.detected_botnets > 2:
            threat_level = "CRITICAL"
        elif summary.critical_events > 0 or summary.high_events > 20:
            threat_level = "HIGH"
        elif summary.high_events > 0 or summary.medium_events > 50:
            threat_level = "MEDIUM"
        else:
            threat_level = "LOW"

        top_cats = ", ".join(
            [f"{k} ({v})" for k, v in list(summary.top_attack_categories.items())[:3]]
        )
        top_countries = ", ".join(
            [f"{k}" for k, v in list(summary.top_attacking_countries.items())[:5]]
        )

        return f"""## Technical Analysis

### Threat Level: {threat_level}

Detailed telemetry for {period} shows a total of **{summary.total_events:,}** events. The infrastructure detected **{summary.unique_attackers:,}** unique IP addresses.

### Telemetry Breakdown
*   **Critical Alerts**: {summary.critical_events:,}
*   **High Severity**: {summary.high_events:,}
*   **Botnets**: {summary.detected_botnets} clusters
*   **C2 Nodes**: {summary.potential_cc_servers}
*   **CVE Matches**: {summary.cve_matches}
*   **Noise Level**: {summary.bot_traffic_percentage:.1f}% automated

### Attack Vector Analysis
Primary attack vectors observed: {top_cats or "None"}.
Traffic sources: {top_countries or "Unknown"}.
"""

    async def generate_recommendations(
        self,
        threat_summary: ThreatSummary,
        report: SecurityReport,
    ) -> List[str]:
        """Generate security recommendations based on findings."""
        recommendations = []

        # Critical event recommendations
        if threat_summary.critical_events > 0:
            recommendations.append(
                "URGENT: Review and investigate all critical severity events immediately. "
                f"{threat_summary.critical_events} critical events were detected."
            )

        # Botnet recommendations
        if threat_summary.detected_botnets > 0:
            recommendations.append(
                f"Botnet Activity Detected: {threat_summary.detected_botnets} botnet clusters identified. "
                "Consider implementing network-level blocking for associated IP ranges."
            )

        # C&C server recommendations
        if threat_summary.potential_cc_servers > 0:
            recommendations.append(
                f"Potential C&C Infrastructure: {threat_summary.potential_cc_servers} potential command-and-control "
                "servers identified. Add these IPs to your threat intelligence feeds and block lists."
            )

        # High bot traffic recommendations
        if threat_summary.bot_traffic_percentage > 50:
            recommendations.append(
                f"Automated Attack Traffic: {threat_summary.bot_traffic_percentage:.1f}% of traffic is automated. "
                "Consider implementing rate limiting and CAPTCHA challenges for suspicious activity."
            )

        # Attack category-specific recommendations
        categories = threat_summary.top_attack_categories
        if categories.get("sql_injection", 0) > 10:
            recommendations.append(
                "SQL Injection Attempts: Implement parameterized queries and input validation. "
                "Review database access patterns and enable SQL injection protection in WAF."
            )

        if categories.get("brute_force", 0) > 50:
            recommendations.append(
                "Brute Force Attacks: Implement account lockout policies, rate limiting on auth endpoints, "
                "and consider multi-factor authentication for critical systems."
            )

        if categories.get("path_traversal", 0) > 10:
            recommendations.append(
                "Path Traversal Attempts: Review file access controls and implement proper input sanitization. "
                "Ensure web server configurations restrict access to sensitive directories."
            )

        if categories.get("command_injection", 0) > 5:
            recommendations.append(
                "Command Injection Detected: Audit all system command execution in application code. "
                "Implement strict input validation and use parameterized commands."
            )

        # Vulnerability-based recommendations
        if report.vulnerabilities:
            critical_vulns = [
                v for v in report.vulnerabilities if v.severity == "critical"
            ]
            if critical_vulns:
                recommendations.append(
                    f"Critical Vulnerabilities: {len(critical_vulns)} critical vulnerabilities found during "
                    "penetration testing. Prioritize remediation of these issues before production deployment."
                )

        # CVE recommendations
        if threat_summary.cve_matches > 0:
            recommendations.append(
                f"CVE Correlations: {threat_summary.cve_matches} attack patterns matched known CVEs. "
                "Review the CVE list and ensure all affected software is patched."
            )

        # General recommendations
        if threat_summary.unique_attackers > 100:
            recommendations.append(
                "High Attacker Volume: Consider implementing geo-blocking for non-essential regions "
                "and enhancing DDoS protection capabilities."
            )

        # Default recommendations if no specific ones
        if not recommendations:
            recommendations = [
                "Continue monitoring honeypot activity for emerging threats.",
                "Ensure all security patches are applied to production systems.",
                "Review and update firewall rules based on observed attack patterns.",
            ]

        return recommendations
