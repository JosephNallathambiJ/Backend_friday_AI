"""Diagnostics API endpoints for running, inspecting, and cancelling backend audits."""

from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import verify_api_key
from app.domain.schemas import APIResponse
from app.services.diagnostics import (
    DiagnosticJobReport,
    DiagnosticRunRequest,
    diagnostic_job_runner,
)

router = APIRouter(
    tags=["Diagnostics & System Integrity"],
    dependencies=[Depends(verify_api_key)],
)


@router.post("/api/v1/diagnostics/run", response_model=APIResponse)
@router.post("/api/diagnostics/run", response_model=APIResponse)
async def run_diagnostics(request: DiagnosticRunRequest):
    """Trigger a comprehensive backend diagnostic run."""
    report: DiagnosticJobReport = await diagnostic_job_runner.run_diagnostics(request)
    return APIResponse(
        success=report.failed_checks == 0,
        data=report.model_dump(),
        message=report.summary,
    )


@router.get("/api/v1/diagnostics", response_model=APIResponse)
@router.get("/api/diagnostics", response_model=APIResponse)
async def list_diagnostic_jobs():
    """List all previous diagnostic audit jobs."""
    jobs = diagnostic_job_runner.list_jobs()
    return APIResponse(
        success=True,
        data={"total": len(jobs), "jobs": [j.model_dump() for j in jobs]},
    )


@router.get("/api/v1/diagnostics/{job_id}", response_model=APIResponse)
@router.get("/api/diagnostics/{job_id}", response_model=APIResponse)
async def get_diagnostic_job(job_id: str):
    """Retrieve full results and report for a specific diagnostic job ID."""
    job = diagnostic_job_runner.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Diagnostic job '{job_id}' not found.")
    return APIResponse(success=True, data=job.model_dump())


@router.post("/api/v1/diagnostics/{job_id}/cancel", response_model=APIResponse)
@router.post("/api/diagnostics/{job_id}/cancel", response_model=APIResponse)
async def cancel_diagnostic_job(job_id: str):
    """Cancel an active diagnostic job."""
    success = await diagnostic_job_runner.cancel_job(job_id)
    if not success:
        raise HTTPException(
            status_code=400,
            detail=f"Diagnostic job '{job_id}' could not be cancelled or does not exist.",
        )
    return APIResponse(success=True, message=f"Job '{job_id}' cancelled successfully.")
