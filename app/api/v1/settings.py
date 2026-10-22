"""Sanitized settings inspection endpoint."""

from fastapi import APIRouter, Depends

from app.api.dependencies import verify_api_key
from app.core.config import settings
from app.domain.schemas import APIResponse

router = APIRouter(
    prefix="/api/v1/settings",
    tags=["Settings"],
    dependencies=[Depends(verify_api_key)],
)


@router.get("", response_model=APIResponse)
async def get_sanitized_settings():
    """Inspect active system configuration with all secrets strictly redacted."""
    return APIResponse(
        data={
            "app_name": settings.APP_NAME,
            "app_version": settings.APP_VERSION,
            "environment": settings.APP_ENV,
            "debug": settings.DEBUG,
            "api_host": settings.API_HOST,
            "api_port": settings.API_PORT,
            "ollama_base_url": settings.OLLAMA_BASE_URL,
            "default_local_model": settings.DEFAULT_LOCAL_MODEL,
            "cloud_ai_enabled": settings.CLOUD_AI_ENABLED,
            "approved_roots": settings.APPROVED_ROOTS,
            "allowed_commands": settings.ALLOWED_COMMANDS,
            "max_orchestration_steps": settings.MAX_ORCHESTRATION_STEPS,
            "scheduler_enabled": settings.SCHEDULER_ENABLED,
        }
    )
