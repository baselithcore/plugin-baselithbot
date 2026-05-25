"""Advanced SVG Chart Generators for Honeypot Reports.

This module contains advanced chart visualization functions including
correlation matrix, botnet clustering, protocol donut, and threat gauge.

Split from charts.py for modularity (Phase 5 charts).
"""

import math
from typing import Dict, List, Optional

from .models import SecurityReport, BotnetSummary


def generate_correlation_matrix_svg(
    report: SecurityReport,
    correlation_data: Optional[Dict[str, Dict[str, float]]] = None,
) -> str:
    """Generate attack category correlation matrix with REAL data.

    Computes actual co-occurrence correlations between attack categories
    based on shared source IPs or timing patterns.

    Args:
        report: SecurityReport
        correlation_data: Optional pre-computed correlation data

    Returns:
        SVG correlation matrix
    """
    categories = list(report.threat_summary.top_attack_categories.keys())[:5]
    if len(categories) < 2:
        return ""

    # Compute real correlations from timeline data if not provided
    if correlation_data is None:
        correlation_data = _compute_category_correlations(report, categories)

    size = 300
    cell_size = 45
    offset_x = 55
    offset_y = 50

    svg_parts = [
        f'<svg width="{size}" height="{size + 40}" viewBox="0 0 {size} {size + 40}" xmlns="http://www.w3.org/2000/svg">',
        # Title
        '<text x="150" y="20" text-anchor="middle" font-size="12" font-weight="bold" fill="#1a1a2e">Attack Type Correlation Matrix</text>',
        # Gradient definitions for professional look
        "<defs>",
        '  <linearGradient id="cellGrad" x1="0%" y1="0%" x2="100%" y2="100%">',
        '    <stop offset="0%" style="stop-color:#fff;stop-opacity:0.3"/>',
        '    <stop offset="100%" style="stop-color:#000;stop-opacity:0.1"/>',
        "  </linearGradient>",
        "</defs>",
    ]

    # Draw cells with real correlation values
    for i, cat1 in enumerate(categories):
        for j, cat2 in enumerate(categories):
            x = offset_x + j * cell_size
            y = offset_y + i * cell_size

            # Get correlation value
            if i == j:
                intensity = 1.0  # Self-correlation is always 1
            else:
                intensity = correlation_data.get(cat1, {}).get(cat2, 0.0)

            # Professional color gradient (blue-purple scale)
            if intensity > 0.7:
                color = "#9d4edd"  # Strong - purple
            elif intensity > 0.4:
                color = "#00b4d8"  # Medium - blue
            elif intensity > 0.2:
                color = "#48cae4"  # Weak - light blue
            else:
                color = "#caf0f8"  # Very weak - very light blue

            # Cell with rounded corners
            svg_parts.append(
                f'<rect x="{x}" y="{y}" width="{cell_size - 3}" height="{cell_size - 3}" '
                f'fill="{color}" rx="4" stroke="#fff" stroke-width="1"/>'
            )

            # Value text (white on dark, dark on light)
            text_color = "#fff" if intensity > 0.5 else "#333"
            svg_parts.append(
                f'<text x="{x + cell_size / 2 - 1.5}" y="{y + cell_size / 2 + 2}" '
                f'text-anchor="middle" font-size="9" font-weight="500" fill="{text_color}">'
                f"{intensity:.2f}</text>"
            )

    # Row labels (left side)
    for i, cat in enumerate(categories):
        label = cat[:6] if len(cat) <= 6 else cat[:5] + "."
        svg_parts.append(
            f'<text x="{offset_x - 5}" y="{offset_y + i * cell_size + cell_size / 2 + 3}" '
            f'text-anchor="end" font-size="8" fill="#333">{label}</text>'
        )

    # Column labels (top)
    for i, cat in enumerate(categories):
        label = cat[:6] if len(cat) <= 6 else cat[:5] + "."
        svg_parts.append(
            f'<text x="{offset_x + i * cell_size + cell_size / 2 - 1}" y="{offset_y - 8}" '
            f'text-anchor="middle" font-size="8" fill="#333">{label}</text>'
        )

    # Color legend
    legend_y = size + 10
    legend_items = [
        ("High", "#9d4edd"),
        ("Med", "#00b4d8"),
        ("Low", "#48cae4"),
        ("None", "#caf0f8"),
    ]
    legend_x = 50
    for label, color in legend_items:
        svg_parts.append(
            f'<rect x="{legend_x}" y="{legend_y}" width="12" height="12" fill="{color}" rx="2"/>'
        )
        svg_parts.append(
            f'<text x="{legend_x + 16}" y="{legend_y + 9}" font-size="8" fill="#666">{label}</text>'
        )
        legend_x += 55

    svg_parts.append("</svg>")
    return "\n".join(svg_parts)


def _compute_category_correlations(
    report: SecurityReport,
    categories: List[str],
) -> Dict[str, Dict[str, float]]:
    """Compute real correlations between attack categories.

    Uses Jaccard similarity based on shared source IPs.

    Args:
        report: SecurityReport with timeline data
        categories: List of category names

    Returns:
        Nested dict of correlation values
    """
    # Group source IPs by category
    category_ips: Dict[str, set] = {cat: set() for cat in categories}

    for event in report.attack_timeline:
        cat = event.category
        if cat in category_ips:
            category_ips[cat].add(event.source_ip)

    # Compute Jaccard similarity
    correlations: Dict[str, Dict[str, float]] = {}
    for cat1 in categories:
        correlations[cat1] = {}
        for cat2 in categories:
            if cat1 == cat2:
                correlations[cat1][cat2] = 1.0
            else:
                set1 = category_ips[cat1]
                set2 = category_ips[cat2]
                intersection = len(set1 & set2)
                union = len(set1 | set2)
                correlations[cat1][cat2] = intersection / union if union > 0 else 0.0

    return correlations


def generate_botnet_cluster_chart(
    botnets: List[BotnetSummary],
    max_clusters: int = 6,
) -> str:
    """Generate botnet cluster visualization.

    Shows cluster sizes with severity color coding and coordination scores.

    Args:
        botnets: List of BotnetSummary objects
        max_clusters: Maximum clusters to display

    Returns:
        SVG string for botnet cluster chart
    """
    if not botnets:
        return ""

    display_botnets = botnets[:max_clusters]
    max_members = max(b.member_count for b in display_botnets) if display_botnets else 1

    width = 450
    height = 50 + len(display_botnets) * 55
    svg_parts = [
        f'<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg">',
        '<text x="225" y="20" text-anchor="middle" font-size="13" font-weight="bold" fill="#1a1a2e">Botnet Cluster Analysis</text>',
    ]

    y = 45
    for i, botnet in enumerate(display_botnets):
        # Severity color
        severity_colors = {
            "critical": "#ff4757",
            "high": "#ff7f50",
            "medium": "#ffa502",
            "low": "#2ed573",
        }
        color = severity_colors.get(botnet.severity, "#00b4d8")

        # Cluster ID badge
        svg_parts.append(
            f'<rect x="10" y="{y}" width="70" height="35" fill="#1a1a2e" rx="4"/>'
        )
        svg_parts.append(
            f'<text x="45" y="{y + 22}" text-anchor="middle" font-size="9" fill="#00b4d8">{botnet.cluster_id[:8]}</text>'
        )

        # Member count bar
        bar_width = (botnet.member_count / max_members) * 200
        svg_parts.append(
            f'<rect x="90" y="{y + 5}" width="{bar_width}" height="25" fill="{color}" rx="4"/>'
        )
        svg_parts.append(
            f'<text x="95" y="{y + 22}" font-size="10" font-weight="bold" fill="#fff">{botnet.member_count} members</text>'
        )

        # Coordination score
        score_pct = botnet.attack_coordination_score * 100
        svg_parts.append(
            f'<text x="310" y="{y + 22}" font-size="9" fill="#666">Coord: {score_pct:.0f}%</text>'
        )

        # Severity badge
        svg_parts.append(
            f'<rect x="380" y="{y + 7}" width="60" height="20" fill="{color}" rx="10"/>'
        )
        svg_parts.append(
            f'<text x="410" y="{y + 21}" text-anchor="middle" font-size="8" font-weight="bold" fill="#fff">{botnet.severity.upper()}</text>'
        )

        y += 55

    svg_parts.append("</svg>")
    return "\n".join(svg_parts)


def generate_protocol_donut_svg(report: SecurityReport) -> str:
    """Generate donut chart for protocol distribution.

    More visually appealing than simple pie chart with hollow center.

    Args:
        report: SecurityReport with threat_summary

    Returns:
        SVG string for donut chart
    """
    protocols = report.threat_summary.top_protocols
    if not protocols:
        return ""

    # Take top 6 protocols
    sorted_protocols = sorted(protocols.items(), key=lambda x: -x[1])[:6]
    total = sum(p[1] for p in sorted_protocols)
    if total == 0:
        return ""

    colors = ["#00b4d8", "#9d4edd", "#ff4757", "#2ed573", "#ffa502", "#ff7f50"]

    svg_parts = [
        '<svg width="320" height="220" viewBox="0 0 320 220" xmlns="http://www.w3.org/2000/svg">',
        '<text x="160" y="20" text-anchor="middle" font-size="13" font-weight="bold" fill="#1a1a2e">Protocol Distribution</text>',
    ]

    # Donut chart centered at (110, 120) with outer radius 70, inner radius 40
    cx, cy = 110, 120
    outer_r, inner_r = 70, 40
    start_angle = 0

    for i, (proto, count) in enumerate(sorted_protocols):
        pct = count / total
        angle = pct * 360

        end_angle = start_angle + angle
        start_rad = math.radians(start_angle - 90)
        end_rad = math.radians(end_angle - 90)

        # Outer arc points
        ox1 = cx + outer_r * math.cos(start_rad)
        oy1 = cy + outer_r * math.sin(start_rad)
        ox2 = cx + outer_r * math.cos(end_rad)
        oy2 = cy + outer_r * math.sin(end_rad)

        # Inner arc points
        ix1 = cx + inner_r * math.cos(start_rad)
        iy1 = cy + inner_r * math.sin(start_rad)
        ix2 = cx + inner_r * math.cos(end_rad)
        iy2 = cy + inner_r * math.sin(end_rad)

        large_arc = 1 if angle > 180 else 0
        color = colors[i % len(colors)]

        # Path: outer arc, line to inner, inner arc (reverse), line back
        path = (
            f"M {ox1} {oy1} "
            f"A {outer_r} {outer_r} 0 {large_arc} 1 {ox2} {oy2} "
            f"L {ix2} {iy2} "
            f"A {inner_r} {inner_r} 0 {large_arc} 0 {ix1} {iy1} Z"
        )
        svg_parts.append(
            f'<path d="{path}" fill="{color}" stroke="#fff" stroke-width="2"/>'
        )

        start_angle = end_angle

    # Center text
    svg_parts.append(
        f'<text x="{cx}" y="{cy - 5}" text-anchor="middle" font-size="18" font-weight="bold" fill="#1a1a2e">{total:,}</text>'
    )
    svg_parts.append(
        f'<text x="{cx}" y="{cy + 12}" text-anchor="middle" font-size="9" fill="#666">Events</text>'
    )

    # Legend
    legend_y = 50
    for i, (proto, count) in enumerate(sorted_protocols):
        pct = count / total * 100
        color = colors[i % len(colors)]
        svg_parts.append(
            f'<rect x="210" y="{legend_y}" width="12" height="12" fill="{color}" rx="2"/>'
        )
        svg_parts.append(
            f'<text x="228" y="{legend_y + 10}" font-size="9" fill="#333">'
            f"{proto}: {count:,} ({pct:.1f}%)</text>"
        )
        legend_y += 22

    svg_parts.append("</svg>")
    return "\n".join(svg_parts)


def generate_threat_level_gauge_svg(
    critical_ratio: float,
    threat_level: str,
) -> str:
    """Generate threat level gauge visualization.

    Args:
        critical_ratio: Ratio of critical+high events (0-100)
        threat_level: Text label (CRITICAL, HIGH, MODERATE, LOW)

    Returns:
        SVG string for gauge chart
    """
    width = 200
    height = 130

    # Determine color based on level
    level_colors = {
        "CRITICAL": "#ff4757",
        "HIGH": "#ff7f50",
        "MODERATE": "#ffa502",
        "LOW": "#2ed573",
    }
    color = level_colors.get(threat_level, "#00b4d8")

    svg_parts = [
        f'<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg">',
        '<text x="100" y="15" text-anchor="middle" font-size="10" font-weight="bold" fill="#333">Threat Level</text>',
    ]

    # Gauge arc (semicircle)
    cx, cy = 100, 90
    r = 60

    # Background arc (gray)
    svg_parts.append(
        f'<path d="M {cx - r} {cy} A {r} {r} 0 0 1 {cx + r} {cy}" '
        f'fill="none" stroke="#e9ecef" stroke-width="15" stroke-linecap="round"/>'
    )

    # Filled arc based on ratio
    fill_angle = (critical_ratio / 100) * 180
    end_rad = math.radians(fill_angle - 180)
    end_x = cx + r * math.cos(end_rad)
    end_y = cy + r * math.sin(end_rad)
    large_arc = 1 if fill_angle > 90 else 0

    if critical_ratio > 0:
        svg_parts.append(
            f'<path d="M {cx - r} {cy} A {r} {r} 0 {large_arc} 1 {end_x} {end_y}" '
            f'fill="none" stroke="{color}" stroke-width="15" stroke-linecap="round"/>'
        )

    # Center text
    svg_parts.append(
        f'<text x="{cx}" y="{cy - 5}" text-anchor="middle" font-size="22" font-weight="bold" fill="{color}">'
        f"{critical_ratio:.0f}%</text>"
    )
    svg_parts.append(
        f'<text x="{cx}" y="{cy + 15}" text-anchor="middle" font-size="11" font-weight="600" fill="{color}">'
        f"{threat_level}</text>"
    )

    svg_parts.append("</svg>")
    return "\n".join(svg_parts)
