"""Central AI visualizer activity state endpoints."""

from fastapi import APIRouter

from app.domain.schemas import APIResponse
from app.services.activity_service import activity_service

router = APIRouter(prefix="/agent", tags=["Agent Visualizer State"])


@router.get("/state", response_model=APIResponse)
async def get_agent_activity_state():
    """Retrieve current central visualizer state, task status, and step telemetry."""
    state = activity_service.get_state()
    return APIResponse(success=True, data=state.model_dump(mode="json"))
