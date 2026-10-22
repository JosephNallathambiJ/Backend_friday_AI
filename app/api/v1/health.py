"""Health and status endpoints."""

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db
from app.core.config import settings
from app.domain.schemas import HealthResponse, SystemStatusResponse
from app.providers.registry import provider_registry

router = APIRouter(tags=["Health & Status"])


@router.get("/health", response_model=HealthResponse)
@router.get("/api/v1/health", response_model=HealthResponse)
@router.get("/health/live", response_model=HealthResponse)
async def liveness_check():
    """Liveness probe indicating process is responsive."""
    return HealthResponse(status="alive")


@router.get("/health/ready", response_model=HealthResponse)
async def readiness_check(db: AsyncSession = Depends(get_db)):
    """Readiness probe checking database connectivity."""
    try:
        await db.execute(text("SELECT 1"))
        return HealthResponse(status="ready")
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "unhealthy", "error": str(e)},
        )


@router.get("/api/v1/status", response_model=SystemStatusResponse)
async def system_status(db: AsyncSession = Depends(get_db)):
    """System status including database, local Ollama connectivity, pulled models, and settings."""
    db_ok = False
    try:
        await db.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        pass

    ollama_provider = provider_registry.get("ollama")
    ollama_ok = await ollama_provider.check_health()
    models = await ollama_provider.list_models() if ollama_ok else []

    return SystemStatusResponse(
        app_name=settings.APP_NAME,
        version=settings.APP_VERSION,
        environment=settings.APP_ENV,
        database_connected=db_ok,
        ollama_connected=ollama_ok,
        ollama_models=models,
        default_model=settings.DEFAULT_LOCAL_MODEL,
        cloud_enabled=settings.CLOUD_AI_ENABLED,
        scheduler_running=settings.SCHEDULER_ENABLED,
    )
