"""Security analysis and vulnerability scanning endpoints."""

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db, verify_api_key
from app.domain.schemas import (
    APIResponse,
    SecurityFindingRead,
    SecurityReportRead,
    SecurityScanRequest,
)
from app.services.security_service import SecurityService

router = APIRouter(
    prefix="/api/v1/security",
    tags=["Security Analysis & Reports"],
    dependencies=[Depends(verify_api_key)],
)


@router.post("/scan", response_model=APIResponse, status_code=status.HTTP_201_CREATED)
async def run_security_scan(
    payload: SecurityScanRequest,
    db: AsyncSession = Depends(get_db),
):
    """Run source-code security analysis and secret-pattern scanning."""
    report = await SecurityService.run_scan(db, payload.target_path)
    return APIResponse(
        data=SecurityReportRead(
            id=report.id,
            created_at=report.created_at,
            summary=report.summary_counts,
            findings=[
                SecurityFindingRead(
                    id=f.id,
                    title=f.title,
                    severity=f.severity,
                    category=f.category,
                    file_path=f.file_path,
                    line_number=f.line_number,
                    evidence=f.evidence,
                    explanation=f.explanation,
                    remediation=f.remediation,
                )
                for f in report.findings
            ],
            markdown_content=report.markdown_content,
        )
    )


@router.get("/reports", response_model=APIResponse)
async def list_reports(
    limit: int = Query(20, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    reports = await SecurityService.list_reports(db, limit=limit)
    return APIResponse(
        data=[
            {
                "id": r.id,
                "target_path": r.target_path,
                "summary": r.summary_counts,
                "created_at": r.created_at,
            }
            for r in reports
        ]
    )


@router.get("/reports/{report_id}", response_model=APIResponse)
async def get_report(
    report_id: str,
    db: AsyncSession = Depends(get_db),
):
    report = await SecurityService.get_report(db, report_id)
    return APIResponse(
        data=SecurityReportRead(
            id=report.id,
            created_at=report.created_at,
            summary=report.summary_counts,
            findings=[
                SecurityFindingRead(
                    id=f.id,
                    title=f.title,
                    severity=f.severity,
                    category=f.category,
                    file_path=f.file_path,
                    line_number=f.line_number,
                    evidence=f.evidence,
                    explanation=f.explanation,
                    remediation=f.remediation,
                )
                for f in report.findings
            ],
            markdown_content=report.markdown_content,
        )
    )
