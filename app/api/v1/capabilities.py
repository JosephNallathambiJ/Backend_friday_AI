"""Capability and Permission management API routes."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db
from app.domain.schemas import (
    APIResponse,
    CapabilityGrantRead,
    CapabilityGrantRequest,
    CapabilityInspectionRead,
    CapabilityRevokeRequest,
)
from app.security.permissions import CapabilityManager

router = APIRouter(prefix="/capabilities", tags=["Capabilities & Permissions"])


@router.get("", response_model=APIResponse)
async def list_capabilities(
    db: AsyncSession = Depends(get_db),
):
    """List all system capabilities and their active grant status and scopes."""
    status_list = await CapabilityManager.list_capabilities_status(db)
    return APIResponse(
        success=True,
        data=[
            CapabilityInspectionRead(
                capability=item["capability"],
                description=item["description"],
                is_granted=item["is_granted"],
                scopes=item["scopes"],
            )
            for item in status_list
        ],
    )


@router.post("/grant", response_model=APIResponse)
async def grant_capability(
    req: CapabilityGrantRequest,
    db: AsyncSession = Depends(get_db),
):
    """Explicitly grant a capability for a specified scope."""
    grant = await CapabilityManager.grant_capability(
        db,
        capability=req.capability,
        scope_type=req.scope_type,
        scope_value=req.scope_value,
    )
    return APIResponse(
        success=True,
        data=CapabilityGrantRead(
            id=grant.id,
            capability=grant.capability.value
            if hasattr(grant.capability, "value")
            else str(grant.capability),
            scope_type=grant.scope_type.value
            if hasattr(grant.scope_type, "value")
            else str(grant.scope_type),
            scope_value=grant.scope_value,
            is_granted=grant.is_granted,
            granted_by=grant.granted_by,
            created_at=grant.created_at,
            revoked_at=grant.revoked_at,
        ),
    )


@router.post("/revoke", response_model=APIResponse)
async def revoke_capability(
    req: CapabilityRevokeRequest,
    db: AsyncSession = Depends(get_db),
):
    """Explicitly revoke a capability for a specified scope."""
    revoked = await CapabilityManager.revoke_capability(
        db,
        capability=req.capability,
        scope_type=req.scope_type,
        scope_value=req.scope_value,
    )
    return APIResponse(success=True, data={"revoked": revoked, "capability": req.capability})
