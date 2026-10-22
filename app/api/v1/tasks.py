"""Task execution and lifecycle endpoints."""

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db, verify_api_key
from app.domain.enums import TaskStatus
from app.domain.schemas import APIResponse, TaskCreate, TaskRead
from app.services.task_service import TaskService

router = APIRouter(
    prefix="/api/v1/tasks",
    tags=["Tasks & Background Workers"],
    dependencies=[Depends(verify_api_key)],
)


@router.post("", response_model=APIResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    payload: TaskCreate,
    db: AsyncSession = Depends(get_db),
):
    task = await TaskService.create_task(
        session=db,
        task_type=payload.task_type,
        summary=payload.summary,
        project_id=payload.project_id,
        parameters=payload.parameters,
    )
    return APIResponse(
        data=TaskRead(
            id=task.id,
            task_type=task.task_type,
            summary=task.summary,
            project_id=task.project_id,
            status=task.status,
            current_step=task.current_step,
            created_at=task.created_at,
            updated_at=task.updated_at,
        )
    )


@router.get("", response_model=APIResponse)
async def list_tasks(
    project_id: str | None = Query(None),
    status: TaskStatus | None = Query(None),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    tasks = await TaskService.list_tasks(
        session=db,
        project_id=project_id,
        status=status,
        limit=limit,
    )
    return APIResponse(
        data=[
            TaskRead(
                id=t.id,
                task_type=t.task_type,
                summary=t.summary,
                project_id=t.project_id,
                status=t.status,
                current_step=t.current_step,
                error_message=t.error_message,
                created_at=t.created_at,
                updated_at=t.updated_at,
                result_data=t.result_data,
            )
            for t in tasks
        ]
    )


@router.get("/{task_id}", response_model=APIResponse)
async def get_task(
    task_id: str,
    db: AsyncSession = Depends(get_db),
):
    task = await TaskService.get_task(db, task_id)
    return APIResponse(
        data=TaskRead(
            id=task.id,
            task_type=task.task_type,
            summary=task.summary,
            project_id=task.project_id,
            status=task.status,
            current_step=task.current_step,
            error_message=task.error_message,
            created_at=task.created_at,
            updated_at=task.updated_at,
            result_data=task.result_data,
        )
    )


@router.post("/{task_id}/cancel", response_model=APIResponse)
async def cancel_task(
    task_id: str,
    db: AsyncSession = Depends(get_db),
):
    task = await TaskService.cancel_task(db, task_id)
    return APIResponse(
        data=TaskRead(
            id=task.id,
            task_type=task.task_type,
            summary=task.summary,
            project_id=task.project_id,
            status=task.status,
            current_step=task.current_step,
            error_message=task.error_message,
            created_at=task.created_at,
            updated_at=task.updated_at,
            result_data=task.result_data,
        )
    )


@router.get("/{task_id}/events", response_model=APIResponse)
async def get_task_events(
    task_id: str,
    db: AsyncSession = Depends(get_db),
):
    events = await TaskService.get_task_events(db, task_id)
    return APIResponse(
        data=[
            {
                "id": e.id,
                "event_type": e.event_type,
                "message": e.message,
                "payload": e.payload,
                "created_at": e.created_at,
            }
            for e in events
        ]
    )
