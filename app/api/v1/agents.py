"""Agent Run lifecycle and execution event API routes."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.runtime import AgentRuntime
from app.api.dependencies import get_db
from app.domain.schemas import (
    AgentRunCreate,
    AgentRunEventRead,
    AgentRunRead,
    APIResponse,
)
from app.services.activity_service import activity_service

router = APIRouter(prefix="/agents", tags=["Agent Runtime"])


@router.get("/state", response_model=APIResponse)
async def get_agent_activity_state():
    """Retrieve current central visualizer state, task status, and step telemetry."""
    state = activity_service.get_state()
    return APIResponse(success=True, data=state.model_dump(mode="json"))


@router.post("/runs", response_model=APIResponse, status_code=201)
async def create_agent_run(
    run_in: AgentRunCreate,
    execute_now: bool = Query(default=True, description="Whether to execute steps immediately"),
    db: AsyncSession = Depends(get_db),
):
    """Create a new agent run with a structured plan, and optionally start execution."""
    run = await AgentRuntime.create_run(db, run_in)
    if execute_now:
        run = await AgentRuntime.execute_run_steps(db, run.id)

    return APIResponse(
        success=True,
        data=AgentRunRead(
            id=run.id,
            agent_type=run.agent_type.value
            if hasattr(run.agent_type, "value")
            else str(run.agent_type),
            status=run.status.value if hasattr(run.status, "value") else str(run.status),
            goal=run.goal,
            project_id=run.project_id,
            conversation_id=run.conversation_id,
            plan=run.plan_data,
            execution_budget=run.execution_budget,
            current_step_index=run.current_step_index,
            result_summary=run.result_summary,
            error_message=run.error_message,
            cancellation_requested=run.cancellation_requested,
            created_at=run.created_at,
            updated_at=run.updated_at,
        ),
    )


@router.get("/runs", response_model=APIResponse)
async def list_agent_runs(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """List agent runs with pagination."""
    runs = await AgentRuntime.list_runs(db, limit=limit, offset=offset)
    return APIResponse(
        success=True,
        data=[
            AgentRunRead(
                id=r.id,
                agent_type=r.agent_type.value
                if hasattr(r.agent_type, "value")
                else str(r.agent_type),
                status=r.status.value if hasattr(r.status, "value") else str(r.status),
                goal=r.goal,
                project_id=r.project_id,
                conversation_id=r.conversation_id,
                plan=r.plan_data,
                execution_budget=r.execution_budget,
                current_step_index=r.current_step_index,
                result_summary=r.result_summary,
                error_message=r.error_message,
                cancellation_requested=r.cancellation_requested,
                created_at=r.created_at,
                updated_at=r.updated_at,
            )
            for r in runs
        ],
    )


@router.get("/runs/{run_id}", response_model=APIResponse)
async def get_agent_run(
    run_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Retrieve detailed state of a specific agent run."""
    run = await AgentRuntime.get_run(db, run_id)
    return APIResponse(
        success=True,
        data=AgentRunRead(
            id=run.id,
            agent_type=run.agent_type.value
            if hasattr(run.agent_type, "value")
            else str(run.agent_type),
            status=run.status.value if hasattr(run.status, "value") else str(run.status),
            goal=run.goal,
            project_id=run.project_id,
            conversation_id=run.conversation_id,
            plan=run.plan_data,
            execution_budget=run.execution_budget,
            current_step_index=run.current_step_index,
            result_summary=run.result_summary,
            error_message=run.error_message,
            cancellation_requested=run.cancellation_requested,
            created_at=run.created_at,
            updated_at=run.updated_at,
        ),
    )


@router.post("/runs/{run_id}/cancel", response_model=APIResponse)
async def cancel_agent_run(
    run_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Request cancellation of an active agent run."""
    run = await AgentRuntime.cancel_run(db, run_id)
    return APIResponse(
        success=True,
        data={
            "run_id": run.id,
            "status": run.status.value if hasattr(run.status, "value") else str(run.status),
        },
    )


@router.get("/runs/{run_id}/events", response_model=APIResponse)
async def get_agent_run_events(
    run_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Retrieve execution events for an agent run."""
    events = await AgentRuntime.get_run_events(db, run_id)
    return APIResponse(
        success=True,
        data=[
            AgentRunEventRead(
                id=e.id,
                run_id=e.run_id,
                event_type=e.event_type,
                message=e.message,
                payload=e.payload,
                created_at=e.created_at,
            )
            for e in events
        ],
    )
