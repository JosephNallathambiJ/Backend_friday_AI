"""API endpoints for Dual-Brain Architecture and Specialist Routing."""

from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.services.dual_brain_service import (
    BrainRoutingDecision,
    FridayBrainOrchestrator,
    ModelRouter,
)

router = APIRouter(prefix="/api/v1/brain", tags=["dual_brain"])


class BrainRouteRequest(BaseModel):
    prompt: str = Field(..., description="User prompt or task goal.")
    task_type: str = Field(default="general", description="Task classification category.")


class BrainExecutionRequest(BaseModel):
    prompt: str = Field(..., description="Prompt to execute via dual-brain orchestrator.")
    task_type: str = Field(default="general")
    task_id: str | None = None
    user_id: str = "local_user"


class CollaborativeReviewRequest(BaseModel):
    prompt: str = Field(..., description="Code generation or technical task needing defensive security review.")
    task_id: str | None = None


@router.get("/models")
async def get_dual_brain_models() -> dict[str, Any]:
    """Inspect and report detection status of both Left Brain and Right Brain in Ollama."""
    return await FridayBrainOrchestrator.get_model_diagnostics()


@router.post("/decide_route", response_model=BrainRoutingDecision)
async def decide_routing(req: BrainRouteRequest) -> BrainRoutingDecision:
    """Deterministically determine optimal brain (Left, Right, Deterministic Math, or Dual)."""
    return ModelRouter.route_request(prompt=req.prompt, task_type=req.task_type)


@router.post("/route")
async def execute_via_brain_routing(
    req: BrainExecutionRequest,
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Execute task through full dual-brain router and specialist orchestrator."""
    return await FridayBrainOrchestrator.execute_request(
        session=session,
        user_prompt=req.prompt,
        task_id=req.task_id,
        task_type=req.task_type,
        user_id=req.user_id,
    )


@router.post("/collaborate")
async def execute_collaborative_workflow(
    req: CollaborativeReviewRequest,
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Execute dual-brain collaboration (Left Brain implements, Right Brain conducts defensive security review)."""
    return await FridayBrainOrchestrator.execute_collaborative_workflow(
        session=session,
        user_prompt=req.prompt,
        task_id=req.task_id,
    )
