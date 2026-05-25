"""PDF Helper Functions for Honeypot Reports.

This module contains functions to generate HTML components for PDF reports.
These are extracted from routes/reports.py for better maintainability.

CSS styles are in pdf_css.py for modularity.
"""

from typing import List, Dict, Optional
from html import escape

from .models import SecurityReport, PayloadExcerpt, AttackerCorrelation


def generate_cover_page(report: SecurityReport) -> str:
    """Generate professional cover page HTML for PDF.

    Args:
        report: SecurityReport instance

    Returns:
        Cover page HTML string
    """
    ts = report.threat_summary
    meta = report.metadata

    # Calculate threat level indicator
    critical_ratio = (
        (ts.critical_events + ts.high_events) / max(ts.total_events, 1) * 100
    )
    if critical_ratio > 30:
        threat_level = "CRITICAL"
        threat_color = "#ff4757"
    elif critical_ratio > 15:
        threat_level = "HIGH"
        threat_color = "#ff7f50"
    elif critical_ratio > 5:
        threat_level = "MODERATE"
        threat_color = "#ffa502"
    else:
        threat_level = "LOW"
        threat_color = "#2ed573"

    return f"""
<div class="cover-page">
    <div class="cover-header">
        <div class="cover-brand">
            <div class="cover-logo">🛡️</div>
            <div class="cover-institution">HONEYPOT THREAT INTELLIGENCE</div>
            <div class="cover-tagline">Advanced Cybersecurity Research Platform</div>
        </div>
    </div>

    <div class="cover-main">
        <div class="cover-threat-badge" style="border-color: {threat_color}; color: {threat_color};">
            THREAT LEVEL: {threat_level}
        </div>
        
        <h1 class="cover-title">Security Intelligence<br/>Research Report</h1>
        <div class="cover-subtitle">{meta.report_type.value.replace("_", " ").title()} Analysis</div>
        
        <div class="cover-divider"></div>

        <div class="cover-stats">
            <div class="cover-stat">
                <div class="cover-stat-icon">📊</div>
                <div class="cover-stat-value">{ts.total_events:,}</div>
                <div class="cover-stat-label">Security Events</div>
            </div>
            <div class="cover-stat">
                <div class="cover-stat-icon">🎯</div>
                <div class="cover-stat-value">{ts.unique_attackers:,}</div>
                <div class="cover-stat-label">Threat Actors</div>
            </div>
            <div class="cover-stat">
                <div class="cover-stat-icon">🔴</div>
                <div class="cover-stat-value">{ts.critical_events + ts.high_events:,}</div>
                <div class="cover-stat-label">Critical Alerts</div>
            </div>
            <div class="cover-stat">
                <div class="cover-stat-icon">🌐</div>
                <div class="cover-stat-value">{ts.detected_botnets}</div>
                <div class="cover-stat-label">Botnets Detected</div>
            </div>
        </div>
    </div>

    <div class="cover-footer">
        <div class="cover-meta-grid">
            <div class="cover-meta-item">
                <span class="cover-meta-label">Report ID</span>
                <span class="cover-meta-value">{meta.report_id}</span>
            </div>
            <div class="cover-meta-item">
                <span class="cover-meta-label">Classification</span>
                <span class="cover-meta-value">{meta.classification}</span>
            </div>
            <div class="cover-meta-item">
                <span class="cover-meta-label">Generated</span>
                <span class="cover-meta-value">{meta.generated_at.strftime("%Y-%m-%d %H:%M UTC")}</span>
            </div>
            <div class="cover-meta-item">
                <span class="cover-meta-label">Analysis Period</span>
                <span class="cover-meta-value">{meta.time_range_start.strftime("%Y-%m-%d")} → {meta.time_range_end.strftime("%Y-%m-%d")}</span>
            </div>
        </div>
        <div class="cover-org">{meta.organization or "Honeypot Security Research Infrastructure"}</div>
        <div class="cover-confidential">CONFIDENTIAL - FOR AUTHORIZED PERSONNEL ONLY</div>
    </div>
</div>
<div style="page-break-after: always;"></div>
"""


def generate_table_of_contents() -> str:
    """Generate table of contents HTML for PDF.

    Returns:
        ToC HTML string
    """
    return """
<div class="toc">
    <h2>📋 Table of Contents</h2>
    <div class="toc-grid">
        <div class="toc-section">
            <div class="toc-section-title">Executive Overview</div>
            <ol class="toc-list">
                <li><a href="#abstract">Abstract &amp; Keywords</a></li>
                <li><a href="#key-findings">Key Findings</a></li>
                <li><a href="#visual-analysis">Visual Analysis</a></li>
            </ol>
        </div>
        <div class="toc-section">
            <div class="toc-section-title">Technical Analysis</div>
            <ol class="toc-list" start="4">
                <li><a href="#dataset-statistics">Dataset Statistics</a></li>
                <li><a href="#attack-pattern-analysis">Attack Pattern Analysis</a></li>
                <li><a href="#mitre-mapping">MITRE ATT&amp;CK Mapping</a></li>
            </ol>
        </div>
        <div class="toc-section">
            <div class="toc-section-title">Intelligence</div>
            <ol class="toc-list" start="7">
                <li><a href="#geographic-analysis">Geographic Analysis</a></li>
                <li><a href="#botnet-analysis">Botnet Clusters</a></li>
                <li><a href="#methodology">Research Methodology</a></li>
            </ol>
        </div>
        <div class="toc-section">
            <div class="toc-section-title">Appendices</div>
            <ol class="toc-list" start="10">
                <li><a href="#research-insights">Research Insights</a></li>
                <li><a href="#references">References</a></li>
                <li><a href="#appendix">Raw Data Summary</a></li>
            </ol>
        </div>
    </div>
</div>
<div style="page-break-after: always;"></div>
"""


# =============================================================================
# HTML Component Generators (Phase 4)
# =============================================================================


def generate_callout_box(
    title: str,
    content: str,
    callout_type: str = "info",
    icon: Optional[str] = None,
) -> str:
    """Generate HTML for a callout box.

    Args:
        title: Callout title
        content: Callout content text
        callout_type: Type (critical, warning, info, success)
        icon: Optional custom icon

    Returns:
        HTML string for callout box
    """
    icons = {
        "critical": "🚨",
        "warning": "⚠️",
        "info": "ℹ️",
        "success": "✅",
    }
    icon = icon or icons.get(callout_type, "📌")
    safe_title = escape(title)
    safe_content = escape(content)

    return f"""
<div class="callout callout-{callout_type}">
    <div class="callout-title">
        <span class="callout-icon">{icon}</span>
        <span>{safe_title}</span>
    </div>
    <div class="callout-content">{safe_content}</div>
</div>
"""


def generate_key_findings_box(findings: List[str]) -> str:
    """Generate HTML for key findings highlight box.

    Args:
        findings: List of key finding strings

    Returns:
        HTML string for key findings box
    """
    if not findings:
        return ""

    items = ""
    for finding in findings[:6]:  # Limit to 6 findings
        safe_finding = escape(finding)
        items += f"""
        <li>
            <span class="finding-icon">▸</span>
            <span>{safe_finding}</span>
        </li>"""

    return f"""
<div class="key-findings-box">
    <h3>🔍 Key Findings</h3>
    <ul class="key-findings-list">
        {items}
    </ul>
</div>
"""


def generate_payload_section_html(excerpts: List[PayloadExcerpt]) -> str:
    """Generate HTML for payload excerpts section.

    Args:
        excerpts: List of PayloadExcerpt objects

    Returns:
        HTML string for payload section
    """
    if not excerpts:
        return ""

    samples_html = ""
    for i, excerpt in enumerate(excerpts[:5], 1):
        safe_excerpt = escape(excerpt.excerpt[:400])
        safe_category = escape(excerpt.category)
        safe_country = escape(excerpt.source_country)
        safe_protocol = escape(excerpt.protocol)

        samples_html += f"""
<div class="payload-sample">
    <div class="payload-header">
        <span class="payload-category">Sample {i}: {safe_category} Attack</span>
        <span class="severity-badge severity-{excerpt.severity}">{excerpt.severity.upper()}</span>
    </div>
    <div class="payload-box">{safe_excerpt}</div>
    <div class="payload-meta">
        <span>🌍 {safe_country}</span>
        <span>📡 {safe_protocol}</span>
    </div>
</div>
"""

    return f"""
<div class="payload-section" id="payload-analysis">
    <h3>🔬 Attack Payload Analysis</h3>
    <p style="color: #666; font-size: 9pt; margin-bottom: 16px;">
        Representative attack payloads observed (sanitized for safety).
        These excerpts provide insight into attack techniques and patterns.
    </p>
    {samples_html}
</div>
"""


def generate_correlation_section_html(correlations: List[AttackerCorrelation]) -> str:
    """Generate HTML for attacker correlation section.

    Args:
        correlations: List of AttackerCorrelation objects

    Returns:
        HTML string for correlation section
    """
    if not correlations:
        return ""

    type_labels = {
        "timing": "Timing Synchronized",
        "pattern": "Payload Similarity",
        "infrastructure": "Shared Infrastructure",
        "cross_honeypot": "Multi-Target Campaign",
    }

    cards_html = ""
    for corr in correlations[:8]:
        label = type_labels.get(corr.correlation_type, corr.correlation_type.title())
        safe_evidence = escape(corr.evidence)
        confidence_pct = f"{corr.confidence * 100:.0f}%"

        ips_html = ""
        for ip in corr.involved_ips[:5]:
            ips_html += f"<code>{escape(ip)}</code> "
        if len(corr.involved_ips) > 5:
            ips_html += f"<em>(+{len(corr.involved_ips) - 5} more)</em>"

        cards_html += f"""
<div class="correlation-card">
    <div class="correlation-type">{label}</div>
    <span class="correlation-confidence">{confidence_pct}</span>
    <div class="correlation-evidence">{safe_evidence}</div>
    <div class="correlation-ips">{ips_html}</div>
</div>
"""

    return f"""
<div class="correlation-section" id="attacker-correlations">
    <h2>🔗 Attacker Correlation Analysis</h2>
    <p style="color: #666; font-size: 9pt; margin-bottom: 16px;">
        Correlations indicating coordinated attack behavior from potentially related threat actors.
    </p>
    {cards_html}
</div>
"""


def generate_watermark_html(classification: str = "CONFIDENTIAL") -> str:
    """Generate watermark HTML element.

    Args:
        classification: Classification text for watermark

    Returns:
        HTML string for watermark
    """
    safe_classification = escape(classification)
    return f'<div class="watermark">{safe_classification}</div>'


def generate_metric_cards_html(report: SecurityReport) -> str:
    """Generate metric cards summary section.

    Args:
        report: SecurityReport instance

    Returns:
        HTML string for metric cards
    """
    ts = report.threat_summary

    return f"""
<div class="metric-cards">
    <div class="metric-card">
        <div class="metric-card-icon">📊</div>
        <div class="metric-card-value">{ts.total_events:,}</div>
        <div class="metric-card-label">Total Events</div>
    </div>
    <div class="metric-card">
        <div class="metric-card-icon">🎯</div>
        <div class="metric-card-value">{ts.unique_attackers:,}</div>
        <div class="metric-card-label">Threat Actors</div>
    </div>
    <div class="metric-card">
        <div class="metric-card-icon">🔴</div>
        <div class="metric-card-value">{ts.critical_events + ts.high_events:,}</div>
        <div class="metric-card-label">Critical/High</div>
    </div>
    <div class="metric-card">
        <div class="metric-card-icon">🌐</div>
        <div class="metric-card-value">{ts.detected_botnets}</div>
        <div class="metric-card-label">Botnets</div>
    </div>
</div>
"""


def generate_misp_status_html(
    enabled: bool,
    status: str,
    sync_percentage: int,
) -> str:
    """Generate MISP status box HTML.

    Args:
        enabled: Whether MISP is enabled
        status: Connection status string
        sync_percentage: Sync percentage (0-100)

    Returns:
        HTML string for MISP status box
    """
    if not enabled:
        return ""

    icon = "✅" if status == "connected" else "⚠️"
    safe_status = escape(status.title())

    return f"""
<div class="misp-status-box">
    <div class="misp-icon">{icon}</div>
    <div class="misp-info">
        <div class="misp-title">MISP Integration</div>
        <div class="misp-detail">Status: {safe_status}</div>
    </div>
    <div>
        <div class="misp-sync-bar">
            <div class="misp-sync-fill" style="width: {sync_percentage}%;"></div>
        </div>
        <div style="font-size: 8pt; color: #666; text-align: center; margin-top: 4px;">
            {sync_percentage}% synced
        </div>
    </div>
</div>
"""


def generate_discovery_insights_html(enrichment: Dict) -> str:
    """Generate discovery insights section HTML.

    Args:
        enrichment: Discovery enrichment dictionary

    Returns:
        HTML string for discovery insights
    """
    if not enrichment:
        return ""

    behavioral = enrichment.get("behavioral_meta", {})
    ml = enrichment.get("ml_meta", {})
    cc = enrichment.get("cc_meta", {})

    timing_clusters = behavioral.get("timing_clusters_count", 0)
    anomaly_count = ml.get("anomaly_count", 0)
    cluster_count = ml.get("cluster_count", 0)
    beaconing = cc.get("beaconing_patterns", 0)

    return f"""
<div class="discovery-insights" id="discovery-analysis">
    <h3>🔍 Discovery Analysis Insights</h3>
    <div class="insight-grid">
        <div class="insight-card">
            <div class="insight-card-title">Timing Clusters</div>
            <div class="insight-card-value">{timing_clusters}</div>
            <div class="insight-card-label">Synchronized attack groups</div>
        </div>
        <div class="insight-card">
            <div class="insight-card-title">ML Clusters</div>
            <div class="insight-card-value">{cluster_count}</div>
            <div class="insight-card-label">Behavioral patterns</div>
        </div>
        <div class="insight-card">
            <div class="insight-card-title">Anomalies</div>
            <div class="insight-card-value">{anomaly_count}</div>
            <div class="insight-card-label">Unusual behaviors</div>
        </div>
        <div class="insight-card">
            <div class="insight-card-title">C&C Patterns</div>
            <div class="insight-card-value">{beaconing}</div>
            <div class="insight-card-label">Beaconing detected</div>
        </div>
    </div>
</div>
"""
