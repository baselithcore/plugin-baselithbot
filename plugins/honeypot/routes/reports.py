"""Reports API Router.

Endpoints for generating and managing attack pattern research reports.
"""

from core.observability.logging import get_logger
import traceback
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response

from core.auth import AuthRole
from plugins.auth.dependencies import require_roles

from ..reports import (
    ReportConfig,
    ReportFormat,
    ReportSection,
    ReportType,
    SecurityReport,
)
from ..reports.models import ReportGenerationRequest

from .reports_helpers import (
    get_service,
    get_type_description,
    get_section_description,
    get_default_sections,
)
from .reports_pdf import generate_pdf_from_report

router = APIRouter(
    prefix="/reports",
    tags=["reports"],
    dependencies=[Depends(require_roles(AuthRole.ADMIN, AuthRole.USER))],
)
logger = get_logger(__name__)


@router.post("/generate", response_model=SecurityReport)
async def generate_report(request: ReportGenerationRequest) -> SecurityReport:
    """Generate an attack pattern research report.

    Generates a comprehensive research report based on the provided configuration.
    Returns the report data which can be rendered in the frontend or downloaded.
    """
    try:
        service = get_service()
        report = await service.generate_report(
            config=request.config,
            title=request.title,
        )
        return report
    except Exception as e:
        logger.error(f"Failed to generate report: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate report: {str(e)}",
        )


@router.post("/generate/markdown")
async def generate_markdown_report(request: ReportGenerationRequest) -> Response:
    """Generate and download a Markdown research report.

    Returns the report as a downloadable Markdown file.
    """
    try:
        service = get_service()
        report = await service.generate_report(
            config=request.config,
            title=request.title,
        )

        markdown_content = service.render_markdown(report)

        # Create filename
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        filename = f"research_report_{report.metadata.report_type.value}_{timestamp}.md"

        return Response(
            content=markdown_content,
            media_type="text/markdown",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
            },
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate markdown report: {str(e)}",
        )


@router.post("/generate/pdf")
async def generate_pdf_report(request: ReportGenerationRequest):
    """Generate and download a PDF research report.

    Requires weasyprint or similar PDF library. Falls back to HTML if PDF
    generation is unavailable. Includes SVG charts for visual data representation.
    """
    try:
        service = get_service()
        report = await service.generate_report(
            config=request.config,
            title=request.title,
        )

        # Generate markdown first
        markdown_content = service.render_markdown(report)

        # Generate PDF using the dedicated module
        return await generate_pdf_from_report(report, markdown_content)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Critical error generating PDF report: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate PDF report: {str(e)}",
        )


@router.get("/types")
async def get_report_types() -> dict:
    """Get available report types and sections."""
    return {
        "types": [
            {
                "id": rt.value,
                "name": rt.value.replace("_", " ").title(),
                "description": get_type_description(rt),
            }
            for rt in ReportType
        ],
        "sections": [
            {
                "id": rs.value,
                "name": rs.value.replace("_", " ").title(),
                "description": get_section_description(rs),
            }
            for rs in ReportSection
        ],
        "formats": [{"id": rf.value, "name": rf.value.upper()} for rf in ReportFormat],
    }


@router.get("/preview")
async def preview_report(
    report_type: ReportType = Query(ReportType.TECHNICAL),
    time_range_hours: int = Query(168, ge=1, le=8760),
    honeypot_id: Optional[str] = Query(None),
    sections: Optional[List[ReportSection]] = Query(None),
) -> SecurityReport:
    """Generate a preview of a research report without downloading.

    Useful for showing report data in the frontend before export.
    """
    try:
        service = get_service()

        # Use default sections based on report type if not provided
        if not sections:
            sections = get_default_sections(report_type)

        config = ReportConfig(
            report_type=report_type,
            sections=sections,
            time_range_hours=time_range_hours,
            honeypot_id=honeypot_id,
        )

        report = await service.generate_report(config=config)
        return report
    except Exception as e:
        logger.error(f"Failed to generate preview: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate preview: {str(e)}",
        )
