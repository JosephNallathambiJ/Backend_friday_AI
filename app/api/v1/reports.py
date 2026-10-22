"""Report formatting endpoints."""

from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db, verify_api_key
from app.services.security_service import SecurityService

router = APIRouter(
    prefix="/api/v1/reports",
    tags=["Reports"],
    dependencies=[Depends(verify_api_key)],
)


@router.get("/{report_id}/markdown")
async def get_report_markdown(
    report_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Retrieve raw markdown text of a security analysis report."""
    report = await SecurityService.get_report(db, report_id)
    return Response(content=report.markdown_content, media_type="text/markdown")
