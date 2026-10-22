"""Tactical Commands submission API routes."""

from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db, verify_api_key
from app.domain.schemas import APIResponse
from app.services.command_service import CommandService

router = APIRouter(prefix="/commands", tags=["Commands"])


class CommandSubmissionRequest(BaseModel):
    command: str = Field(..., min_length=1, description="User command text")
    conversation_id: str | None = Field(default=None, description="Optional conversation context")
    context: dict[str, Any] | None = Field(default_factory=dict, description="Task context data")
    response_mode: str = Field(default="sync", description="'sync' or 'async'")
    locale: str = Field(default="en-US", description="Locale tag")
    request_id: str | None = Field(default=None, description="Client-generated idempotency key")


@router.post("", response_model=APIResponse)
async def submit_command(
    payload: CommandSubmissionRequest,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(verify_api_key),
):
    """Submit a tactical command for agent planning, tool execution, and HUD updates."""
    result = await CommandService.process_command(
        session=db,
        command_text=payload.command,
        conversation_id=payload.conversation_id,
        context=payload.context,
        response_mode=payload.response_mode,
        locale=payload.locale,
        request_id=payload.request_id,
    )
    return APIResponse(success=True, data=result)
