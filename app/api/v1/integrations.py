"""Device Integrations and Telemetry API routes."""

from fastapi import APIRouter

from app.domain.schemas import (
    APIResponse,
    AppLaunchRequest,
    DeviceCapabilityRead,
    NotificationRequest,
)
from app.services.device_context_service import DeviceContextService

router = APIRouter(prefix="/integrations", tags=["Device Integrations"])


@router.get("", response_model=APIResponse)
async def get_device_integrations():
    """Discover device capabilities and supported system adapters."""
    info = DeviceContextService.get_system_info()
    return APIResponse(
        success=True,
        data=DeviceCapabilityRead(
            os_name=info["os_name"],
            os_version=info["os_version"],
            platform=info["platform"],
            architecture=info["architecture"],
            cpu_count=info["cpu_count"],
            memory_total_gb=16.0,  # Telemetry baseline
            supported_adapters=info["supported_adapters"],
        ),
    )


@router.post("/launch", response_model=APIResponse)
async def launch_application(req: AppLaunchRequest):
    """Launch an explicitly permitted local desktop application."""
    res = await DeviceContextService.launch_application(
        app_name=req.app_name,
        arguments=req.arguments,
    )
    return APIResponse(success=True, data=res)


@router.post("/notifications", response_model=APIResponse)
async def send_desktop_notification(req: NotificationRequest):
    """Send a local operating-system notification to the user."""
    res = await DeviceContextService.send_notification(
        title=req.title,
        message=req.message,
        subtitle=req.subtitle,
    )
    return APIResponse(success=True, data=res)
