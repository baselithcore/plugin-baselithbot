"""SVG Chart Generators for Honeypot Reports.

This module contains functions to generate SVG visualizations for security reports.
These are extracted from routes/reports.py for better maintainability.
Enhanced with professional styling and improved data visualization (Phase 5).

Advanced charts (correlation matrix, botnet cluster, protocol donut, threat gauge)
are in charts_advanced.py for modularity.
"""

import math
from collections import defaultdict

from .models import SecurityReport

# Re-export advanced charts for backwards compatibility
from .charts_advanced import (  # noqa: F401
    generate_botnet_cluster_chart,
    generate_correlation_matrix_svg,
    generate_protocol_donut_svg,
    generate_threat_level_gauge_svg,
)


def generate_severity_pie_svg(report: SecurityReport) -> str:
    """Generate SVG pie chart for severity distribution.

    Args:
        report: SecurityReport with threat_summary

    Returns:
        SVG string for the pie chart
    """
    ts = report.threat_summary
    data = [
        ("Critical", ts.critical_events, "#ff4757"),
        ("High", ts.high_events, "#ff7f50"),
        ("Medium", ts.medium_events, "#ffa502"),
        ("Low", ts.low_events, "#2ed573"),
    ]

    total = sum(d[1] for d in data)
    if total == 0:
        return ""

    svg_parts = [
        '<svg width="300" height="200" viewBox="0 0 300 200" xmlns="http://www.w3.org/2000/svg">',
        '<text x="150" y="20" text-anchor="middle" font-size="14" font-weight="bold" fill="#333">Severity Distribution</text>',
    ]

    # Pie chart centered at (100, 110) with radius 70
    cx, cy, r = 100, 110, 70
    start_angle = 0

    for label, count, color in data:
        if count == 0:
            continue
        pct = count / total
        angle = pct * 360

        # Calculate arc
        end_angle = start_angle + angle
        start_rad = math.radians(start_angle - 90)
        end_rad = math.radians(end_angle - 90)

        x1 = cx + r * math.cos(start_rad)
        y1 = cy + r * math.sin(start_rad)
        x2 = cx + r * math.cos(end_rad)
        y2 = cy + r * math.sin(end_rad)

        large_arc = 1 if angle > 180 else 0

        path = f"M {cx} {cy} L {x1} {y1} A {r} {r} 0 {large_arc} 1 {x2} {y2} Z"
        svg_parts.append(
            f'<path d="{path}" fill="{color}" stroke="#fff" stroke-width="1"/>'
        )

        start_angle = end_angle

    # Legend
    legend_y = 60
    for label, count, color in data:
        if count > 0:
            pct = count / total * 100
            svg_parts.append(
                f'<rect x="200" y="{legend_y}" width="12" height="12" fill="{color}"/>'
            )
            svg_parts.append(
                f'<text x="218" y="{legend_y + 10}" font-size="10" fill="#333">{label}: {count} ({pct:.1f}%)</text>'
            )
            legend_y += 20

    svg_parts.append("</svg>")
    return "\n".join(svg_parts)


def generate_category_bar_svg(report: SecurityReport) -> str:
    """Generate SVG bar chart for attack categories.

    Args:
        report: SecurityReport with threat_summary

    Returns:
        SVG string for the bar chart
    """
    categories = report.threat_summary.top_attack_categories
    if not categories:
        return ""

    # Take top 6 categories
    sorted_cats = sorted(categories.items(), key=lambda x: -x[1])[:6]
    max_val = max(c[1] for c in sorted_cats) if sorted_cats else 1

    colors = ["#00b4d8", "#9d4edd", "#ff4757", "#2ed573", "#ffa502", "#ff7f50"]

    height = 40 + len(sorted_cats) * 35
    svg_parts = [
        f'<svg width="500" height="{height}" viewBox="0 0 500 {height}" xmlns="http://www.w3.org/2000/svg">',
        '<text x="250" y="20" text-anchor="middle" font-size="14" font-weight="bold" fill="#333">Attack Category Distribution</text>',
    ]

    y = 45
    bar_height = 22
    max_bar_width = 280

    for i, (cat, count) in enumerate(sorted_cats):
        bar_width = (count / max_val) * max_bar_width
        color = colors[i % len(colors)]

        # Label
        label = cat[:20] + "..." if len(cat) > 20 else cat
        svg_parts.append(
            f'<text x="110" y="{y + 15}" text-anchor="end" font-size="10" fill="#333">{label}</text>'
        )

        # Bar
        svg_parts.append(
            f'<rect x="120" y="{y}" width="{bar_width}" height="{bar_height}" fill="{color}" rx="3"/>'
        )

        # Count
        svg_parts.append(
            f'<text x="{125 + bar_width + 5}" y="{y + 15}" font-size="10" fill="#333">{count:,}</text>'
        )

        y += 35

    svg_parts.append("</svg>")
    return "\n".join(svg_parts)


def generate_geo_bar_svg(report: SecurityReport) -> str:
    """Generate SVG bar chart for geographic distribution.

    Args:
        report: SecurityReport with geo_distribution

    Returns:
        SVG string for the bar chart
    """
    geo_data = report.geo_distribution
    if not geo_data:
        return ""

    # Take top 8 countries
    top_countries = geo_data[:8]
    max_val = max(g.attack_count for g in top_countries) if top_countries else 1

    colors = [
        "#00b4d8",
        "#9d4edd",
        "#ff4757",
        "#2ed573",
        "#ffa502",
        "#ff7f50",
        "#778ca3",
        "#a55eea",
    ]

    height = 40 + len(top_countries) * 30
    svg_parts = [
        f'<svg width="500" height="{height}" viewBox="0 0 500 {height}" xmlns="http://www.w3.org/2000/svg">',
        '<text x="250" y="20" text-anchor="middle" font-size="14" font-weight="bold" fill="#333">Geographic Source Distribution</text>',
    ]

    y = 45
    bar_height = 18
    max_bar_width = 280

    for i, geo in enumerate(top_countries):
        bar_width = (geo.attack_count / max_val) * max_bar_width
        color = colors[i % len(colors)]

        # Country label
        label = f"{geo.country_code}"
        svg_parts.append(
            f'<text x="50" y="{y + 13}" text-anchor="end" font-size="10" fill="#333">{label}</text>'
        )

        # Bar
        svg_parts.append(
            f'<rect x="60" y="{y}" width="{bar_width}" height="{bar_height}" fill="{color}" rx="2"/>'
        )

        # Count
        svg_parts.append(
            f'<text x="{65 + bar_width + 5}" y="{y + 13}" font-size="9" fill="#333">{geo.attack_count:,} ({geo.unique_ips} IPs)</text>'
        )

        y += 30

    svg_parts.append("</svg>")
    return "\n".join(svg_parts)


def generate_timeline_svg(report: SecurityReport) -> str:
    """Generate SVG timeline visualization showing attack intensity over time.

    Args:
        report: SecurityReport with timeline data

    Returns:
        SVG string for timeline chart
    """
    # Create a simplified timeline visualization
    if not report.attack_timeline:
        return ""

    hourly_counts: dict = defaultdict(int)
    for event in report.attack_timeline:
        hour_key = event.timestamp.strftime("%Y-%m-%d %H:00")
        hourly_counts[hour_key] += 1

    if not hourly_counts:
        return ""

    # Take last 24 data points
    sorted_hours = sorted(hourly_counts.items())[-24:]
    max_count = max(c for _, c in sorted_hours) if sorted_hours else 1

    width = 600
    height = 200
    bar_width = (width - 80) / len(sorted_hours) - 2
    max_bar_height = 120

    svg_parts = [
        f'<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg">',
        '<text x="300" y="20" text-anchor="middle" font-size="14" font-weight="bold" fill="#333">Attack Activity Timeline</text>',
        # Y-axis
        '<line x1="50" y1="40" x2="50" y2="170" stroke="#ccc" stroke-width="1"/>',
        # X-axis
        '<line x1="50" y1="170" x2="580" y2="170" stroke="#ccc" stroke-width="1"/>',
    ]

    x = 55
    for i, (hour, count) in enumerate(sorted_hours):
        bar_height = (count / max_count) * max_bar_height
        y = 170 - bar_height

        # Gradient color based on intensity
        intensity = count / max_count
        if intensity > 0.7:
            color = "#ff4757"
        elif intensity > 0.4:
            color = "#ffa502"
        else:
            color = "#00b4d8"

        svg_parts.append(
            f'<rect x="{x}" y="{y}" width="{bar_width}" height="{bar_height}" fill="{color}" rx="2"/>'
        )
        x += bar_width + 2

    # Labels
    svg_parts.append(
        '<text x="25" y="110" font-size="9" fill="#666" transform="rotate(-90, 25, 110)">Events</text>'
    )
    svg_parts.append(
        '<text x="300" y="190" text-anchor="middle" font-size="9" fill="#666">Time Period</text>'
    )

    svg_parts.append("</svg>")
    return "\n".join(svg_parts)
