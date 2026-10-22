"""System Status, Diagnostics, Capabilities and Information endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db
from app.domain.schemas import APIResponse
from app.services.system_service import SystemService

router = APIRouter(prefix="/system", tags=["System & Diagnostics"])


@router.get("/status", response_model=APIResponse)
async def get_system_status(db: AsyncSession = Depends(get_db)):
    """Return comprehensive system and component status."""
    status_data = await SystemService.get_system_status(db)
    return APIResponse(success=True, data=status_data)


@router.get("/diagnostics", response_model=APIResponse)
async def get_system_diagnostics(db: AsyncSession = Depends(get_db)):
    """Return component diagnostics, latencies, and actionable recommendations."""
    diagnostics = await SystemService.get_diagnostics(db)
    return APIResponse(success=True, data=diagnostics)


@router.get("/capabilities", response_model=APIResponse)
async def get_system_capabilities(db: AsyncSession = Depends(get_db)):
    """Return all registered system tools, capabilities, and permission profiles."""
    capabilities = await SystemService.get_capabilities(db)
    return APIResponse(success=True, data={"total": len(capabilities), "capabilities": capabilities})


@router.get("/info", response_model=APIResponse)
async def get_system_info():
    """Return static system identity, branding, and features metadata."""
    info = SystemService.get_system_info()
    return APIResponse(success=True, data=info)
