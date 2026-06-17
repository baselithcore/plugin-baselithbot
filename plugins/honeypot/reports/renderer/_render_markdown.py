"""render_markdown mixin for ReportRenderer."""

from ..models import SecurityReport


class RenderMarkdownMixin:
    """Provides the render_markdown public method."""

    def render_markdown(self, report: SecurityReport) -> str:
        """Render report as Markdown document with research focus.

        Args:
            report: SecurityReport instance

        Returns:
            Markdown formatted string
        """
        lines = []

        # Header with research focus
        lines.append(
            f"# Attack Pattern Research Report: {report.metadata.report_type.value.title()}"
        )
        lines.append("")
        lines.append(f"**Report ID:** {report.metadata.report_id}")
        lines.append(
            f"**Generated:** {report.metadata.generated_at.strftime('%Y-%m-%d %H:%M UTC')}"
        )
        lines.append(f"**Classification:** {report.metadata.classification}")
        if report.metadata.organization:
            lines.append(f"**Research Environment:** {report.metadata.organization}")
        lines.append(
            f"**Observation Period:** {report.metadata.time_range_start.strftime('%Y-%m-%d %H:%M')} to "
            f"{report.metadata.time_range_end.strftime('%Y-%m-%d %H:%M UTC')}"
        )
        lines.append("")
        lines.append("---")
        lines.append("")

        # Executive Summary
        if report.executive_summary:
            lines.append(report.executive_summary)
            lines.append("")
            lines.append("---")
            lines.append("")

        # Dataset Statistics with visual bars
        ts = report.threat_summary
        lines.append("## Dataset Statistics")
        lines.append("")
        lines.append("### Collection Overview")
        lines.append("")
        lines.append("| Metric | Value |")
        lines.append("|--------|-------|")
        lines.append(f"| Total Events Collected | {ts.total_events:,} |")
        lines.append(f"| Unique Source Addresses | {ts.unique_attackers:,} |")
        lines.append(f"| Critical Severity Events | {ts.critical_events:,} |")
        lines.append(f"| High Severity Events | {ts.high_events:,} |")
        lines.append(f"| Medium Severity Events | {ts.medium_events:,} |")
        lines.append(f"| Low Severity Events | {ts.low_events:,} |")
        lines.append(f"| Identified Botnet Clusters | {ts.detected_botnets} |")
        lines.append(f"| C&C Infrastructure Endpoints | {ts.potential_cc_servers} |")
        lines.append(f"| CVE Exploitation Attempts | {ts.cve_matches} |")
        lines.append(f"| Automated Traffic Ratio | {ts.bot_traffic_percentage:.1f}% |")
        lines.append("")

        # Severity distribution with ASCII visualization
        total_severity = (
            ts.critical_events + ts.high_events + ts.medium_events + ts.low_events
        )
        if total_severity > 0:
            lines.append("### Severity Distribution")
            lines.append("")
            lines.append("```")
            for label, count in [
                ("Critical", ts.critical_events),
                ("High", ts.high_events),
                ("Medium", ts.medium_events),
                ("Low", ts.low_events),
            ]:
                pct = (count / total_severity * 100) if total_severity > 0 else 0
                bar = "█" * int(pct / 5) + "░" * (20 - int(pct / 5))
                lines.append(f"{label:8} {bar} {count:>6} ({pct:5.1f}%)")
            lines.append("```")
            lines.append("")

        # Attack Category Distribution
        if ts.top_attack_categories:
            lines.append("### Attack Category Distribution")
            lines.append("")
            lines.append("| Category | Events | Percentage |")
            lines.append("|----------|--------|------------|")
            total_cat = sum(ts.top_attack_categories.values())
            for cat, count in sorted(
                ts.top_attack_categories.items(), key=lambda x: -x[1]
            )[:10]:
                pct = (count / total_cat * 100) if total_cat > 0 else 0
                lines.append(f"| {cat} | {count:,} | {pct:.1f}% |")
            lines.append("")

        # Protocol Distribution
        if ts.top_protocols:
            lines.append("### Protocol Distribution")
            lines.append("")
            lines.append("| Protocol | Events |")
            lines.append("|----------|--------|")
            for proto, count in sorted(ts.top_protocols.items(), key=lambda x: -x[1])[
                :8
            ]:
                lines.append(f"| {proto} | {count:,} |")
            lines.append("")

        # Geographic Analysis
        if report.geo_distribution:
            lines.append("## Geographic Source Analysis")
            lines.append("")
            lines.append("| Country | Events | Unique IPs | Primary Attack Types |")
            lines.append("|---------|--------|------------|----------------------|")
            for geo in report.geo_distribution[:15]:
                types = (
                    ", ".join(geo.primary_attack_types[:2])
                    if geo.primary_attack_types
                    else "-"
                )
                lines.append(
                    f"| {geo.country_name} ({geo.country_code}) | {geo.attack_count:,} | {geo.unique_ips} | {types} |"
                )
            lines.append("")

        # Botnet Cluster Analysis
        if report.botnet_activity:
            lines.append("## Botnet Cluster Analysis")
            lines.append("")
            lines.append(
                "> The following clusters exhibit coordinated attack behavior patterns."
            )
            lines.append("")
            for botnet in report.botnet_activity:
                lines.append(f"### Cluster: {botnet.cluster_id}")
                lines.append(f"- **Member Count:** {botnet.member_count}")
                lines.append(f"- **Severity Classification:** {botnet.severity}")
                lines.append(
                    f"- **Coordination Score:** {botnet.attack_coordination_score:.2f}"
                )
                if botnet.suspected_cc_servers:
                    lines.append(
                        f"- **Suspected C&C Infrastructure:** {', '.join(botnet.suspected_cc_servers[:5])}"
                    )
                if botnet.common_protocols:
                    lines.append(
                        f"- **Common Protocols:** {', '.join(botnet.common_protocols)}"
                    )
                lines.append(
                    f"- **First Detected:** {botnet.first_detected.strftime('%Y-%m-%d %H:%M')}"
                )
                lines.append(
                    f"- **Last Activity:** {botnet.last_activity.strftime('%Y-%m-%d %H:%M')}"
                )
                lines.append("")

        # Pentest Results
        if report.pentest_results:
            lines.append("## Penetration Test Analysis")
            lines.append("")
            lines.append(
                "| Playbook | Security Score | Tests Passed | Critical | High |"
            )
            lines.append(
                "|----------|----------------|--------------|----------|------|"
            )
            for pt in report.pentest_results:
                lines.append(
                    f"| {pt.playbook_name} | {pt.security_score:.0f} | "
                    f"{pt.passed_tests}/{pt.total_tests} | {pt.critical_findings} | {pt.high_findings} |"
                )
            lines.append("")

        # Vulnerability Patterns
        if report.vulnerabilities:
            lines.append("## Vulnerability Exploitation Patterns")
            lines.append("")
            lines.append(
                "> Vulnerabilities actively targeted by observed attack traffic."
            )
            lines.append("")
            for vuln in report.vulnerabilities[:10]:
                lines.append(f"### [{vuln.severity.upper()}] {vuln.name}")
                lines.append(f"- **Category:** {vuln.category}")
                lines.append(f"- **Description:** {vuln.description}")
                lines.append(f"- **Observed Exploitation Pattern:** {vuln.remediation}")
                if vuln.cve_references:
                    lines.append(
                        f"- **CVE References:** {', '.join(vuln.cve_references)}"
                    )
                lines.append(f"- **Confidence Score:** {vuln.confidence:.0%}")
                lines.append("")

        # IOC Patterns
        if report.iocs:
            lines.append("## Indicators of Compromise (IOC) Patterns")
            lines.append("")
            lines.append("| Type | Value | Threat Level | Confidence |")
            lines.append("|------|-------|--------------|------------|")
            for ioc in report.iocs[:25]:
                lines.append(
                    f"| {ioc.ioc_type} | `{ioc.value}` | {ioc.threat_level} | {ioc.confidence:.0%} |"
                )
            lines.append("")

        # Discovery Enrichment Insights (Phase 7)
        if report.discovery_enrichment:
            lines.append(self._render_discovery_insights(report.discovery_enrichment))
            lines.append("")

        # Attacker Correlations
        if report.correlations:
            lines.append(self._render_correlations(report.correlations))
            lines.append("")

        # Payload Excerpts
        if report.payload_excerpts:
            lines.append(self._render_payload_excerpts(report.payload_excerpts))
            lines.append("")

        # Threat Intelligence Summary
        if report.threat_intel_summary:
            lines.append(self._render_threat_intel(report.threat_intel_summary))
            lines.append("")

        # Credential Analysis
        if report.credential_analysis:
            lines.append(self._render_credential_analysis(report.credential_analysis))
            lines.append("")

        # MISP Status
        if report.misp_status and report.misp_status.enabled:
            lines.append(self._render_misp_status(report.misp_status))
            lines.append("")

        # Sequential Attack Analysis (Kill Chain)
        if report.sequential_analysis:
            lines.append(self._render_sequential_analysis(report.sequential_analysis))
            lines.append("")

        # Research Insights (formerly Recommendations)
        if report.recommendations:
            lines.append("## Research Insights & Future Directions")
            lines.append("")
            for i, rec in enumerate(report.recommendations, 1):
                lines.append(f"{i}. {rec}")
            lines.append("")

        # Footer
        lines.append("---")
        lines.append("")
        lines.append(
            f"*Report generated by Honeypot Research System v{report.metadata.version}*"
        )

        return "\n".join(lines)
