"""Cybersecurity and Omni OSINT Power API endpoints."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.cyber_agent import cyber_agent
from app.api.dependencies import get_db, verify_api_key
from app.domain.enums import TargetType, TechniqueType
from app.domain.schemas import APIResponse
from app.integrations.omni_osint import (
    OSINTQueryRequest,
    omni_osint_adapter,
)
from app.security.target_authorization import (
    TargetAuthorization,
    target_auth_manager,
)

router = APIRouter(
    prefix="/api/v1/cyber",
    tags=["Cyber Agent & OSINT"],
    dependencies=[Depends(verify_api_key)],
)


class CreateAuthorizationRequest(BaseModel):
    target: str = Field(..., description="Target hostname, IP, or asset identifier")
    target_type: TargetType = Field(default=TargetType.DOMAIN)
    scope_reference: str = Field(..., description="Approval reference or scope document reference")
    allowed_techniques: list[TechniqueType] = Field(
        default_factory=lambda: [
            TechniqueType.PASSIVE_DNS,
            TechniqueType.PASSIVE_WHOIS,
            TechniqueType.CERTIFICATE_TRANSPARENCY,
            TechniqueType.HTTP_SECURITY_HEADERS,
            TechniqueType.DEPENDENCY_AUDIT,
            TechniqueType.SECRET_SCAN,
        ]
    )
    excluded_targets: list[str] = Field(default_factory=list)
    rate_limit_rps: float = Field(default=2.0, ge=0.1, le=50.0)
    concurrency_limit: int = Field(default=2, ge=1, le=10)
    operator: str = Field(default="admin")
    active_recon_permitted: bool = Field(default=False)


class CyberScanRequest(BaseModel):
    target: str
    target_type: str = "domain"
    action: str = "full_scan"
    authorization_id: str | None = None
    parameters: dict[str, Any] = Field(default_factory=dict)


@router.post("/authorizations", response_model=APIResponse)
async def create_target_authorization(payload: CreateAuthorizationRequest):
    """Register an explicit TargetAuthorization record for security testing."""
    auth = TargetAuthorization(
        target=payload.target,
        target_type=payload.target_type,
        scope_reference=payload.scope_reference,
        allowed_techniques=payload.allowed_techniques,
        excluded_targets=payload.excluded_targets,
        rate_limit_rps=payload.rate_limit_rps,
        concurrency_limit=payload.concurrency_limit,
        operator=payload.operator,
        active_recon_permitted=payload.active_recon_permitted,
    )
    target_auth_manager.register(auth)
    return APIResponse(
        success=True,
        data=auth.model_dump(),
        message=f"TargetAuthorization '{auth.id}' created for target '{auth.target}'.",
    )


@router.get("/authorizations", response_model=APIResponse)
async def list_target_authorizations():
    """List all registered target authorization records."""
    records = target_auth_manager.list_all()
    return APIResponse(
        success=True,
        data={"total": len(records), "authorizations": [r.model_dump() for r in records]},
    )


@router.get("/authorizations/{auth_id}", response_model=APIResponse)
async def get_target_authorization(auth_id: str):
    """Retrieve details of a target authorization by ID."""
    auth = target_auth_manager.get(auth_id)
    if not auth:
        raise HTTPException(status_code=404, detail=f"TargetAuthorization '{auth_id}' not found.")
    return APIResponse(success=True, data=auth.model_dump())


@router.post("/scan", response_model=APIResponse)
async def execute_cyber_scan(
    payload: CyberScanRequest,
    db: AsyncSession = Depends(get_db),
):
    """Execute cyber security analysis and reconnaissance mission."""
    params = dict(payload.parameters)
    params["target"] = payload.target
    params["target_type"] = payload.target_type
    params["action"] = payload.action
    params["authorization_id"] = payload.authorization_id

    result = await cyber_agent.execute(
        task_id=f"scan-{payload.target[:10]}",
        goal=f"Cyber scan for {payload.target}",
        parameters=params,
        session=db,
    )
    return APIResponse(
        success=result.success,
        data=result.data,
        message=result.summary,
    )


@router.get("/osint/capabilities", response_model=APIResponse)
async def get_omni_osint_capabilities():
    """Discover capabilities of the Omni OSINT Power integration."""
    caps = omni_osint_adapter.get_capabilities()
    return APIResponse(success=True, data=caps.model_dump())


@router.get("/osint/health", response_model=APIResponse)
async def get_omni_osint_health():
    """Check connectivity and operational status of Omni OSINT Power."""
    health = await omni_osint_adapter.check_health()
    return APIResponse(success=health.get("connected", False) or health.get("mock_mode", False), data=health)


@router.post("/osint/query", response_model=APIResponse)
async def query_omni_osint(payload: OSINTQueryRequest):
    """Query Omni OSINT Power for domain, certificate, or threat intelligence."""
    try:
        res = await omni_osint_adapter.query(payload)
        return APIResponse(success=True, data=res.model_dump(), message=res.summary)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except RuntimeError as re_err:
        raise HTTPException(status_code=429, detail=str(re_err))
