"""Render helper mixins for ReportRenderer.

Contains the 7 private _render_* methods as a mixin.
"""

from typing import List

from ..models import (
    AttackerCorrelation,
    CredentialAnalysis,
    DiscoveryEnrichment,
    MISPStatus,
    PayloadExcerpt,
    ThreatIntelSummary,
)


class RenderHelpersMixin:
    """Private _render_* helpers for ReportRenderer."""

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
