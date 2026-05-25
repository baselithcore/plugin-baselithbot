"""PDF Report Generation Logic.

Handles PDF generation from SecurityReport objects.
Extracted from reports.py for modularity.
"""

import io
from core.observability.logging import get_logger
from datetime import datetime, timezone

from fastapi import HTTPException
from fastapi.responses import StreamingResponse

from ..reports import SecurityReport
from ..reports.charts import (
    generate_category_bar_svg,
    generate_correlation_matrix_svg,
    generate_geo_bar_svg,
    generate_severity_pie_svg,
    generate_timeline_svg,
)
from ..reports.pdf_helpers import (
    generate_cover_page,
    generate_table_of_contents,
)
from ..reports.pdf_css import REPORT_CSS

logger = get_logger(__name__)


def build_charts_html(report: SecurityReport) -> tuple[str, str]:
    """Build charts HTML sections from report data.

    Args:
        report: SecurityReport instance

    Returns:
        Tuple of (charts_html, timeline_html)
    """
    # Generate SVG charts
    severity_svg = generate_severity_pie_svg(report)
    category_svg = generate_category_bar_svg(report)
    geo_svg = generate_geo_bar_svg(report)
    timeline_svg = generate_timeline_svg(report)
    correlation_svg = generate_correlation_matrix_svg(report)

    # Charts section
    charts_html = ""
    if severity_svg or category_svg or geo_svg:
        charts_html = """
<div class="charts-section" id="visual-analysis">
    <h2>Visual Analysis</h2>
    <div class="chart-grid">
"""
        if severity_svg:
            charts_html += f'<div class="chart">{severity_svg}</div>'
        if category_svg:
            charts_html += f'<div class="chart">{category_svg}</div>'
        if geo_svg:
            charts_html += f'<div class="chart">{geo_svg}</div>'
        if correlation_svg:
            charts_html += f'<div class="chart">{correlation_svg}</div>'
        charts_html += """
    </div>
</div>
<hr/>
"""

    # Timeline section
    timeline_html = ""
    if timeline_svg:
        timeline_html = f"""
<div class="charts-section">
    <h2>Temporal Analysis</h2>
    <div class="chart-grid">
        <div class="chart">{timeline_svg}</div>
    </div>
</div>
<hr/>
"""

    return charts_html, timeline_html


def build_pdf_html(
    report: SecurityReport,
    html_content: str,
    charts_html: str,
    timeline_html: str,
) -> str:
    """Build complete HTML document for PDF generation.

    Args:
        report: SecurityReport instance
        html_content: Rendered markdown as HTML
        charts_html: Charts section HTML
        timeline_html: Timeline section HTML

    Returns:
        Complete HTML document string
    """
    # Generate cover page and ToC
    cover_page_html = generate_cover_page(report)
    toc_html = generate_table_of_contents()

    return f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Attack Pattern Research Report</title>
    <style>
        {REPORT_CSS}
        @page {{
            size: A4;
            margin: 2cm;
            @bottom-center {{
                content: "Page " counter(page) " of " counter(pages);
                font-size: 9pt;
                color: #666;
            }}
        }}
        body {{
            font-family: 'Georgia', 'Times New Roman', serif;
            font-size: 11pt;
            line-height: 1.7;
            color: #222;
            background: #fff;
        }}
        h1 {{
            color: #1a1a2e;
            border-bottom: 3px solid #00b4d8;
            padding-bottom: 0.5em;
            font-size: 22pt;
            font-family: 'Helvetica Neue', Arial, sans-serif;
        }}
        h2 {{
            color: #16213e;
            border-bottom: 2px solid #9d4edd;
            padding-bottom: 0.3em;
            margin-top: 1.5em;
            font-size: 15pt;
            font-family: 'Helvetica Neue', Arial, sans-serif;
        }}
        h3 {{
            color: #0f3460;
            font-size: 12pt;
            font-family: 'Helvetica Neue', Arial, sans-serif;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 1em 0;
            font-size: 9.5pt;
        }}
        th, td {{
            border: 1px solid #ccc;
            padding: 8px 10px;
            text-align: left;
        }}
        th {{
            background: linear-gradient(135deg, #1a1a2e, #16213e);
            color: white;
            font-weight: 600;
        }}
        tr:nth-child(even) {{
            background: #f8f9fa;
        }}
        code {{
            background: #f4f4f4;
            padding: 2px 6px;
            border-radius: 3px;
            font-family: 'Consolas', 'Monaco', monospace;
            font-size: 9pt;
            color: #c7254e;
        }}
        pre {{
            background: #f8f9fa;
            border: 1px solid #e9ecef;
            border-radius: 4px;
            padding: 12px;
            font-size: 9pt;
            overflow-x: auto;
        }}
        blockquote {{
            border-left: 4px solid #9d4edd;
            margin: 1em 0;
            padding: 0.5em 1em;
            background: #f8f9fa;
            font-style: italic;
        }}
        hr {{
            border: none;
            border-top: 1px solid #dee2e6;
            margin: 2em 0;
        }}
        ul, ol {{
            margin-left: 1.5em;
        }}
        li {{
            margin-bottom: 0.4em;
        }}
        .charts-section {{
            page-break-inside: avoid;
            margin: 2em 0;
        }}
        .chart-grid {{
            display: flex;
            flex-wrap: wrap;
            gap: 20px;
            justify-content: center;
        }}
        .chart {{
            background: #fafafa;
            border: 1px solid #eee;
            border-radius: 8px;
            padding: 15px;
            page-break-inside: avoid;
        }}
        .report-footer {{
            margin-top: 3em;
            padding-top: 1em;
            border-top: 2px solid #dee2e6;
            font-size: 9pt;
            color: #666;
            text-align: center;
        }}
    </style>
</head>
<body>
{cover_page_html}
{toc_html}
{charts_html}
{timeline_html}
{html_content}
<div class="report-footer">
    <p>Generated by Honeypot Research System | Classification: {report.metadata.classification}</p>
    <p>This report is intended for cybersecurity research purposes only.</p>
</div>
</body>
</html>
"""


async def generate_pdf_from_report(
    report: SecurityReport,
    markdown_content: str,
) -> StreamingResponse:
    """Generate PDF from report and markdown content.

    Args:
        report: SecurityReport instance
        markdown_content: Pre-rendered markdown content

    Returns:
        StreamingResponse with PDF content

    Raises:
        HTTPException: If PDF generation fails
    """
    try:
        from markdown_it import MarkdownIt
        from weasyprint import HTML

        # Convert markdown to HTML
        md = MarkdownIt("gfm-like", {"linkify": False})
        html_content = md.render(markdown_content)

        # Build chart sections
        charts_html, timeline_html = build_charts_html(report)

        # Build complete HTML document
        styled_html = build_pdf_html(
            report,
            html_content,
            charts_html,
            timeline_html,
        )

        # Generate PDF
        pdf_buffer = io.BytesIO()
        HTML(string=styled_html).write_pdf(pdf_buffer)
        pdf_buffer.seek(0)

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        filename = (
            f"research_report_{report.metadata.report_type.value}_{timestamp}.pdf"
        )

        return StreamingResponse(
            pdf_buffer,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
            },
        )

    except ImportError as e:
        logger.warning(f"PDF generation dependencies not available: {e}")
        raise HTTPException(
            status_code=500,
            detail="PDF generation dependencies not available (weasyprint/markdown-it)",
        )
    except Exception as e:
        logger.warning(f"PDF generation failed, attempting HTML fallback: {e}")
        return await generate_html_fallback(report, markdown_content)


async def generate_html_fallback(
    report: SecurityReport,
    markdown_content: str,
) -> StreamingResponse:
    """Generate HTML fallback when PDF generation fails.

    Args:
        report: SecurityReport instance
        markdown_content: Pre-rendered markdown content

    Returns:
        StreamingResponse with HTML content
    """
    try:
        from markdown_it import MarkdownIt

        md = MarkdownIt("gfm-like", {"linkify": False})
        html_content = md.render(markdown_content)

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        filename = (
            f"research_report_{report.metadata.report_type.value}_{timestamp}.html"
        )

        return StreamingResponse(
            iter([html_content.encode()]),
            media_type="text/html",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "X-PDF-Fallback": "true",
            },
        )
    except Exception as e:
        logger.error(f"HTML fallback also failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate report: {str(e)}",
        )
