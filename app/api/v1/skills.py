"""Skill discovery, GitHub acquisition, validation, installation, and lifecycle API endpoints."""


from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db, verify_api_key
from app.domain.schemas import APIResponse
from app.skills.acquisition import SkillAcquisitionService
from app.skills.registry import skill_registry

router = APIRouter(
    prefix="/api/v1/skills",
    tags=["Skill Ecosystem & GitHub Acquisition"],
    dependencies=[Depends(verify_api_key)],
)


class SkillSearchRequest(BaseModel):
    query: str = Field(description="Search terms for finding open-source skills on GitHub")
    capability: str | None = Field(default=None, description="Optional capability filter")
    language: str | None = Field(default=None, description="Preferred programming language")
    max_results: int = Field(default=10, ge=1, le=30)


class SkillAcquisitionRequest(BaseModel):
    repository_url: str = Field(description="Valid GitHub repository URL (https://github.com/owner/repo)")
    skill_id: str | None = Field(default=None, description="Optional custom skill identifier")
    requested_commit: str = Field(default="", description="Specific commit hash or branch to acquire")


class SkillInstallRequest(BaseModel):
    acquisition_id: str = Field(description="ID of the quarantined acquisition to install")
    approval_id: str | None = Field(default=None, description="Human approval ID if skill requires approval")


class SkillRollbackRequest(BaseModel):
    target_version: str | None = Field(default=None, description="Optional target version to roll back to")


@router.post("/search", response_model=APIResponse)
async def search_github_skills(req: SkillSearchRequest):
    """Search public GitHub repositories for potential agent skills."""
    candidates = await SkillAcquisitionService.search_github_skills(
        query=req.query,
        capability=req.capability,
        language=req.language,
        max_results=req.max_results,
    )
    return APIResponse(data=[c.model_dump() for c in candidates])


@router.post("/acquisitions", response_model=APIResponse)
async def acquire_skill_repository(
    req: SkillAcquisitionRequest,
    db: AsyncSession = Depends(get_db),
):
    """Clone a GitHub repository into quarantine, pin its commit, and execute a security scan."""
    record = await SkillAcquisitionService.acquire_repository(
        session=db,
        repository_url=req.repository_url,
        skill_id=req.skill_id,
        requested_commit=req.requested_commit,
    )
    return APIResponse(data={
        "acquisition_id": record.id,
        "skill_id": record.skill_id,
        "source_url": record.source_url,
        "pinned_commit": record.pinned_commit,
        "status": record.status,
        "quarantine_path": record.quarantine_path,
        "validation_report": record.validation_report,
        "error_message": record.error_message,
    })


@router.get("/acquisitions/{acquisition_id}", response_model=APIResponse)
async def get_skill_acquisition(
    acquisition_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Fetch status and details of an ongoing or completed skill acquisition."""
    record = await SkillAcquisitionService.get_acquisition(db, acquisition_id)
    return APIResponse(data={
        "acquisition_id": record.id,
        "skill_id": record.skill_id,
        "source_url": record.source_url,
        "pinned_commit": record.pinned_commit,
        "status": record.status,
        "quarantine_path": record.quarantine_path,
        "validation_report": record.validation_report,
        "error_message": record.error_message,
    })


@router.post("/acquisitions/{acquisition_id}/cancel", response_model=APIResponse)
async def cancel_skill_acquisition(
    acquisition_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Cancel acquisition and clean up quarantine directory."""
    record = await SkillAcquisitionService.cancel_acquisition(db, acquisition_id)
    return APIResponse(data={"acquisition_id": record.id, "status": record.status})


@router.get("/acquisitions/{acquisition_id}/report", response_model=APIResponse)
async def get_acquisition_validation_report(
    acquisition_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Retrieve detailed static analysis and prompt injection scan report."""
    record = await SkillAcquisitionService.get_acquisition(db, acquisition_id)
    return APIResponse(data=record.validation_report or {"error": "Report not yet generated."})


@router.get("", response_model=APIResponse)
async def list_installed_skills(
    agent_type: str | None = Query(None, description="Filter skills by compatible agent"),
    active_only: bool = Query(True, description="Only return active enabled skills"),
    db: AsyncSession = Depends(get_db),
):
    """List all installed skills in the managed library."""
    skills = await skill_registry.list_installed_skills(db, agent_type=agent_type, active_only=active_only)
    return APIResponse(data=skills)


@router.get("/{skill_id}", response_model=APIResponse)
async def get_skill_details(
    skill_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get metadata for an installed skill."""
    record = await skill_registry.get_skill(db, skill_id)
    return APIResponse(data={
        "skill_id": record.skill_id,
        "name": record.name,
        "version": record.version,
        "description": record.description,
        "author": record.author,
        "license": record.license,
        "source": record.source,
        "source_commit": record.source_commit,
        "execution_mode": record.execution_mode,
        "risk_level": record.risk_level,
        "status": record.status,
        "is_active": record.is_active,
        "manifest_data": record.manifest_data,
        "install_path": record.install_path,
    })


@router.get("/{skill_id}/health", response_model=APIResponse)
async def check_skill_health(
    skill_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Perform on-disk health check and manifest verification."""
    health = await skill_registry.check_health(db, skill_id)
    return APIResponse(data=health)


@router.post("/install", response_model=APIResponse)
async def install_skill(
    req: SkillInstallRequest,
    db: AsyncSession = Depends(get_db),
):
    """Promote a validated quarantined acquisition into the managed skill library."""
    record = await skill_registry.install_skill(
        session=db,
        acquisition_id=req.acquisition_id,
        approval_id=req.approval_id,
    )
    return APIResponse(data={
        "skill_id": record.skill_id,
        "name": record.name,
        "version": record.version,
        "status": record.status,
        "install_path": record.install_path,
        "is_active": record.is_active,
    })


@router.post("/{skill_id}/install", response_model=APIResponse)
async def install_skill_by_id(
    skill_id: str,
    req: SkillInstallRequest,
    db: AsyncSession = Depends(get_db),
):
    """Convenience alias to install a specific skill acquisition."""
    record = await skill_registry.install_skill(
        session=db,
        acquisition_id=req.acquisition_id,
        approval_id=req.approval_id,
    )
    return APIResponse(data={
        "skill_id": record.skill_id,
        "name": record.name,
        "version": record.version,
        "status": record.status,
        "install_path": record.install_path,
        "is_active": record.is_active,
    })


@router.post("/{skill_id}/enable", response_model=APIResponse)
async def enable_skill(
    skill_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Enable an installed skill."""
    record = await skill_registry.enable_skill(db, skill_id)
    return APIResponse(data={"skill_id": record.skill_id, "is_active": record.is_active, "status": record.status})


@router.post("/{skill_id}/disable", response_model=APIResponse)
async def disable_skill(
    skill_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Disable an active skill."""
    record = await skill_registry.disable_skill(db, skill_id)
    return APIResponse(data={"skill_id": record.skill_id, "is_active": record.is_active, "status": record.status})


@router.post("/{skill_id}/rollback", response_model=APIResponse)
async def rollback_skill(
    skill_id: str,
    req: SkillRollbackRequest | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Roll back an updated skill to its previous version."""
    target_ver = req.target_version if req else None
    record = await skill_registry.rollback_skill(db, skill_id, target_version=target_ver)
    return APIResponse(data={
        "skill_id": record.skill_id,
        "version": record.version,
        "status": record.status,
        "source_commit": record.source_commit,
    })


@router.delete("/{skill_id}", response_model=APIResponse)
async def remove_skill(
    skill_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Remove and purge a skill from disk and library."""
    await skill_registry.remove_skill(db, skill_id)
    return APIResponse(data={"skill_id": skill_id, "removed": True})
