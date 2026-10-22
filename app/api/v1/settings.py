"""Sanitized and persistent settings API endpoints."""

from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db, verify_api_key
from app.domain.schemas import APIResponse
from app.services.user_settings_service import UserSettingsService

router = APIRouter(
    prefix="/api/v1/settings",
    tags=["Settings"],
    dependencies=[Depends(verify_api_key)],
)


class SettingsPatchRequest(BaseModel):
    language: str | None = Field(default=None, description="Preferred language code")
    locale: str | None = Field(default=None, description="Preferred locale tag")
    theme: str | None = Field(default=None, description="HUD theme identifier")
    selected_model: str | None = Field(default=None, description="Selected AI model name")
    voice_provider: str | None = Field(default=None, description="Selected voice provider")
    selected_voice: str | None = Field(default=None, description="Selected voice name")
    speech_speed: float | None = Field(default=None, ge=0.5, le=2.0, description="Speech rate")
    voice_input_enabled: bool | None = None
    voice_output_enabled: bool | None = None
    realtime_events_enabled: bool | None = None
    terminal_profile: str | None = None
    custom_preferences: dict[str, Any] | None = None


@router.get("", response_model=APIResponse)
async def get_settings(
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(verify_api_key),
):
    """Inspect active user preferences and sanitized system execution settings."""
    settings_dict = await UserSettingsService.get_settings_dict(db, user_id=user_id)
    return APIResponse(success=True, data=settings_dict)


@router.patch("", response_model=APIResponse)
async def update_settings(
    payload: SettingsPatchRequest,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(verify_api_key),
):
    """Partially update user HUD preferences with server validation."""
    updates = payload.model_dump(exclude_unset=True)
    updated = await UserSettingsService.update_settings(db, updates=updates, user_id=user_id)
    return APIResponse(success=True, data=updated)


@router.get("/options", response_model=APIResponse)
async def get_settings_options():
    """Return permitted options and dynamic models/voices for the settings modal."""
    options = await UserSettingsService.get_settings_options()
    return APIResponse(success=True, data=options)
