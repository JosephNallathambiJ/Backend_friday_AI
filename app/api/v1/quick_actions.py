"""Tactical Quick-Action Registry API routes."""

from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db, verify_api_key
from app.domain.schemas import APIResponse
from app.services.quick_action_service import QuickActionService

router = APIRouter(prefix="/quick-actions", tags=["Quick Actions"])


class ExecuteQuickActionRequest(BaseModel):
    parameters: dict[str, Any] | None = Field(default_factory=dict, description="Action input arguments")


@router.get("", response_model=APIResponse)
async def list_quick_actions(user_id: str = Depends(verify_api_key)):
    """List all registered tactical HUD quick actions."""
    actions = QuickActionService.list_actions()
    return APIResponse(
        success=True,
        data={
            "total": len(actions),
            "actions": [a.model_dump(mode="json") for a in actions],
        },
    )


@router.post("/{action_id}/execute", response_model=APIResponse)
async def execute_quick_action(
    action_id: str,
    payload: ExecuteQuickActionRequest | None = None,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(verify_api_key),
):
    """Execute a registered quick action and return structured results."""
    params = payload.parameters if payload else {}
    result = await QuickActionService.execute_action(
        session=db,
        action_id=action_id,
        parameters=params,
    )
    return APIResponse(success=True, data=result)
