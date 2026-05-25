"""Report Renderer.

Responsible for rendering reports into various formats (Markdown, etc.)
with research-focused language and enhanced statistical visualizations.
"""

from typing import List

from .models import (
    AttackerCorrelation,
    CredentialAnalysis,
    DiscoveryEnrichment,
    MISPStatus,
    PayloadExcerpt,
    SecurityReport,
    ThreatIntelSummary,
)


class ReportRenderer:
    """Renders reports into final formats with research focus."""

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

    # =========================================================================
    # Enrichment Section Renderers (Phase 7)
    # =========================================================================

    def _render_discovery_insights(self, enrichment: DiscoveryEnrichment) -> str:
        """Render discovery analysis insights section."""
        lines = []
        lines.append("## Discovery Analysis Insights")
        lines.append("")

        if enrichment.analyzed_at:
            lines.append(
                f"*Analysis performed: {enrichment.analyzed_at.strftime('%Y-%m-%d %H:%M UTC')}*"
            )
            lines.append("")

        # Behavioral Analysis
        behavioral = enrichment.behavioral_meta
        if behavioral:
            lines.append("### Behavioral Analysis")
            lines.append("")
            timing_count = behavioral.get("timing_clusters_count", 0)
            payload_groups = behavioral.get("payload_similarity_groups_count", 0)
            scan_patterns = behavioral.get("scan_patterns_count", 0)

            if any([timing_count, payload_groups, scan_patterns]):
                lines.append("| Pattern Type | Count |")
                lines.append("|--------------|-------|")
                if timing_count:
                    lines.append(f"| Timing Synchronized Clusters | {timing_count} |")
                if payload_groups:
                    lines.append(f"| Similar Payload Groups | {payload_groups} |")
                if scan_patterns:
                    lines.append(f"| Coordinated Scan Patterns | {scan_patterns} |")
                lines.append("")

        # ML Analysis
        ml = enrichment.ml_meta
        if ml:
            clusters = ml.get("cluster_count", 0)
            anomalies = ml.get("anomaly_count", 0)
            if clusters or anomalies:
                lines.append("### ML-Based Pattern Detection")
                lines.append("")
                lines.append(f"- **Identified Clusters:** {clusters}")
                lines.append(f"- **Anomalous Behaviors:** {anomalies}")
                lines.append("")

        # C&C Detection
        cc = enrichment.cc_meta
        if cc:
            beaconing = cc.get("beaconing_patterns", 0)
            dga = cc.get("dga_detected", 0)
            fast_flux = cc.get("fast_flux_detected", 0)

            if any([beaconing, dga, fast_flux]):
                lines.append("### Command & Control Indicators")
                lines.append("")
                if beaconing:
                    lines.append(f"- **Beaconing Patterns:** {beaconing} detected")
                if dga:
                    lines.append(
                        f"- **DGA (Domain Generation Algorithm):** {dga} suspected"
                    )
                if fast_flux:
                    lines.append(f"- **Fast-Flux Networks:** {fast_flux} indicators")
                lines.append("")

        # Zero-Day Indicators
        zeroday = enrichment.zeroday_meta
        if zeroday and zeroday.get("candidates_count", 0) > 0:
            lines.append("### Potential Zero-Day Indicators")
            lines.append("")
            lines.append(
                f"> **{zeroday.get('candidates_count', 0)}** novel attack patterns detected "
                f"that may indicate previously unknown exploitation techniques."
            )
            lines.append("")

        # Malware Families
        if enrichment.identified_malware_families:
            lines.append("### Identified Malware Families")
            lines.append("")
            for family in enrichment.identified_malware_families[:5]:
                lines.append(f"- {family}")
            lines.append("")

        return "\n".join(lines)

    def _render_correlations(self, correlations: List[AttackerCorrelation]) -> str:
        """Render attacker correlation analysis section."""
        lines = []
        lines.append("## Attacker Correlation Analysis")
        lines.append("")
        lines.append(
            "> The following correlations indicate coordinated attack behavior "
            "from potentially related threat actors."
        )
        lines.append("")

        # Group by type
        by_type = {}
        for corr in correlations:
            if corr.correlation_type not in by_type:
                by_type[corr.correlation_type] = []
            by_type[corr.correlation_type].append(corr)

        type_labels = {
            "timing": "Timing-Synchronized Attacks",
            "pattern": "Payload Similarity",
            "infrastructure": "Shared Infrastructure",
            "cross_honeypot": "Multi-Target Campaigns",
        }

        for corr_type, items in by_type.items():
            label = type_labels.get(corr_type, corr_type.title())
            lines.append(f"### {label}")
            lines.append("")

            for i, corr in enumerate(items[:3], 1):
                lines.append(f"**Correlation {i}** (Confidence: {corr.confidence:.0%})")
                lines.append(f"- Evidence: {corr.evidence}")
                if corr.involved_ips:
                    ips_display = ", ".join(f"`{ip}`" for ip in corr.involved_ips[:5])
                    if len(corr.involved_ips) > 5:
                        ips_display += f" (+{len(corr.involved_ips) - 5} more)"
                    lines.append(f"- IPs: {ips_display}")
                lines.append("")

        return "\n".join(lines)

    def _render_payload_excerpts(self, excerpts: List[PayloadExcerpt]) -> str:
        """Render payload excerpts section for research context."""
        lines = []
        lines.append("## Attack Payload Analysis")
        lines.append("")
        lines.append(
            "> Representative attack payloads observed (sanitized for safety). "
            "These excerpts provide insight into attack techniques and patterns."
        )
        lines.append("")

        for i, excerpt in enumerate(excerpts[:8], 1):
            severity_badge = f"[{excerpt.severity.upper()}]"
            lines.append(f"### Sample {i}: {excerpt.category} {severity_badge}")
            lines.append("")
            lines.append(f"- **Protocol:** {excerpt.protocol}")
            lines.append(f"- **Source:** {excerpt.source_country}")
            if excerpt.ai_classification:
                lines.append(f"- **AI Classification:** {excerpt.ai_classification}")
            lines.append("")
            lines.append("```")
            lines.append(excerpt.excerpt[:400])  # Limit display
            lines.append("```")
            lines.append("")

        return "\n".join(lines)

    def _render_threat_intel(self, summary: ThreatIntelSummary) -> str:
        """Render threat intelligence summary section."""
        lines = []
        lines.append("## Threat Intelligence Summary")
        lines.append("")

        # IOC Counts
        if summary.ioc_counts:
            lines.append("### Extracted Indicators of Compromise")
            lines.append("")
            lines.append("| IOC Type | Count |")
            lines.append("|----------|-------|")
            for ioc_type, count in summary.ioc_counts.items():
                if count > 0:
                    lines.append(f"| {ioc_type.title()} | {count:,} |")
            lines.append("")

        # Command Patterns
        if summary.command_patterns:
            lines.append("### Common Command Patterns")
            lines.append("")
            lines.append("```")
            for pattern in summary.command_patterns[:5]:
                lines.append(pattern[:100])  # Truncate long patterns
            lines.append("```")
            lines.append("")

        # User Agents
        if summary.user_agents:
            lines.append("### Observed User Agents")
            lines.append("")
            for ua in summary.user_agents[:5]:
                lines.append(f"- `{ua[:80]}`")  # Truncate
            lines.append("")

        # YARA Rules
        if summary.yara_rules:
            lines.append("### Auto-Generated YARA Rules")
            lines.append("")
            lines.append(f"*{summary.yara_rules_count} detection rules generated*")
            lines.append("")
            for rule in summary.yara_rules[:2]:
                lines.append("```yara")
                lines.append(rule[:500])  # Truncate
                lines.append("```")
                lines.append("")

        return "\n".join(lines)

    def _render_credential_analysis(self, analysis: CredentialAnalysis) -> str:
        """Render credential attack analysis section."""
        lines = []
        lines.append("## Credential Attack Analysis")
        lines.append("")

        if analysis.total_attempts == 0:
            lines.append("*No credential-based attacks detected in this period.*")
            return "\n".join(lines)

        lines.append("### Statistics")
        lines.append("")
        lines.append("| Metric | Value |")
        lines.append("|--------|-------|")
        lines.append(f"| Total Attempts | {analysis.total_attempts:,} |")
        lines.append(f"| Unique Usernames | {analysis.unique_usernames:,} |")
        lines.append(f"| Unique Password Patterns | {analysis.unique_passwords:,} |")
        lines.append("")

        # Top Usernames
        if analysis.top_usernames:
            lines.append("### Most Targeted Usernames")
            lines.append("")
            lines.append("| Username | Attempts |")
            lines.append("|----------|----------|")
            for entry in analysis.top_usernames[:10]:
                username = entry.get("username", "?")
                count = entry.get("count", 0)
                lines.append(f"| `{username}` | {count:,} |")
            lines.append("")

        # Password Patterns (masked)
        if analysis.top_passwords:
            lines.append("### Password Pattern Distribution")
            lines.append("")
            lines.append("| Pattern | Attempts |")
            lines.append("|---------|----------|")
            for entry in analysis.top_passwords[:8]:
                pattern = entry.get("pattern", "?")
                count = entry.get("count", 0)
                lines.append(f"| {pattern} | {count:,} |")
            lines.append("")

        return "\n".join(lines)

    def _render_misp_status(self, status: MISPStatus) -> str:
        """Render MISP integration status section."""
        lines = []
        lines.append("## MISP Integration Status")
        lines.append("")

        status_icon = "✅" if status.status == "connected" else "⚠️"
        lines.append(f"**Status:** {status_icon} {status.status.title()}")
        lines.append(f"**Sync Percentage:** {status.sync_percentage}%")
        if status.exported_iocs_count:
            lines.append(f"**IOCs Exported:** {status.exported_iocs_count:,}")
        lines.append("")

        return "\n".join(lines)

    def _render_sequential_analysis(self, sessions: List) -> str:
        """Render sequential attack analysis (Kill Chain) section.

        Args:
            sessions: List of AttackSessionAnalysis objects

        Returns:
            Markdown formatted sequential analysis
        """
        lines = []
        lines.append("## Sequential Attack Analysis (Kill Chain)")
        lines.append("")
        lines.append(
            "> This section reconstructs the step-by-step progression of coordinated "
            "attack sessions, revealing the attacker's methodology and intent."
        )
        lines.append("")

        for i, session in enumerate(
            sessions[:5], 1
        ):  # Limit to 5 sessions for readability
            lines.append(f"### Session {i}: {session.attacker_ip}")
            lines.append("")
            lines.append(f"**Session ID:** `{session.session_id}`")
            lines.append(f"**Attacker:** `{session.attacker_ip}`")
            lines.append(f"**Total Steps:** {len(session.steps)}")
            lines.append("")

            # Attack Timeline
            if session.steps:
                lines.append("#### Attack Timeline")
                lines.append("")
                lines.append("| Time | Phase | Action | Severity |")
                lines.append("|------|-------|--------|----------|")

                for step in session.steps[:20]:  # Limit to 20 steps per session
                    time_str = (
                        step.timestamp.strftime("%H:%M:%S")
                        if hasattr(step.timestamp, "strftime")
                        else str(step.timestamp)
                    )
                    # Truncate description to fit table
                    description = (
                        step.description[:80] + "..."
                        if len(step.description) > 80
                        else step.description
                    )
                    lines.append(
                        f"| {time_str} | {step.phase} | {description} | {step.severity} |"
                    )

                lines.append("")

            # LLM-Generated Narrative
            if session.narrative:
                lines.append("#### Forensic Analysis")
                lines.append("")
                lines.append(session.narrative)
                lines.append("")

            # Payload Samples (if available)
            payload_steps = [s for s in session.steps if s.payload_snippet]
            if payload_steps:
                lines.append("#### Notable Payloads")
                lines.append("")
                for j, step in enumerate(payload_steps[:3], 1):  # Show up to 3 payloads
                    lines.append(f"**Payload {j}** ({step.phase}):")
                    lines.append("```")
                    lines.append(step.payload_snippet[:200])  # Truncate for readability
                    lines.append("```")
                    lines.append("")

            lines.append("---")
            lines.append("")

        return "\n".join(lines)
