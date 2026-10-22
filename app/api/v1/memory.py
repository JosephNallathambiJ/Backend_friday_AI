"""Memory records API endpoints."""

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db, verify_api_key
from app.domain.enums import MemoryCategory
from app.domain.schemas import APIResponse, MemoryCreate, MemoryRead
from app.services.memory_service import MemoryService

router = APIRouter(
    prefix="/api/v1/memory",
    tags=["Memory Management"],
    dependencies=[Depends(verify_api_key)],
)


@router.post("", response_model=APIResponse, status_code=status.HTTP_201_CREATED)
async def create_memory(
    payload: MemoryCreate,
    db: AsyncSession = Depends(get_db),
):
    mem = await MemoryService.create_or_update_memory(
        session=db,
        category=payload.category,
        key=payload.key,
        content=payload.content,
        project_id=payload.project_id,
        metadata_json=payload.metadata_json,
    )
    return APIResponse(
        data=MemoryRead(
            id=mem.id,
            category=mem.category,
            key=mem.key,
            content=mem.content,
            project_id=mem.project_id,
            created_at=mem.created_at,
            updated_at=mem.updated_at,
        )
    )


@router.get("", response_model=APIResponse)
async def list_memories(
    category: MemoryCategory | None = Query(None),
    project_id: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    memories = await MemoryService.list_memories(
        session=db,
        category=category,
        project_id=project_id,
    )
    return APIResponse(
        data=[
            MemoryRead(
                id=m.id,
                category=m.category,
                key=m.key,
                content=m.content,
                project_id=m.project_id,
                created_at=m.created_at,
                updated_at=m.updated_at,
            )
            for m in memories
        ]
    )


@router.get("/{memory_id}", response_model=APIResponse)
async def get_memory(
    memory_id: str,
    db: AsyncSession = Depends(get_db),
):
    m = await MemoryService.get_memory(db, memory_id)
    return APIResponse(
        data=MemoryRead(
            id=m.id,
            category=m.category,
            key=m.key,
            content=m.content,
            project_id=m.project_id,
            created_at=m.created_at,
            updated_at=m.updated_at,
        )
    )


@router.delete("/{memory_id}", response_model=APIResponse)
async def delete_memory(
    memory_id: str,
    db: AsyncSession = Depends(get_db),
):
    await MemoryService.delete_memory(db, memory_id)
    return APIResponse(data={"deleted": True, "memory_id": memory_id})


@router.delete("/project/{project_id}", response_model=APIResponse)
async def clear_project_memory(
    project_id: str,
    db: AsyncSession = Depends(get_db),
):
    count = await MemoryService.clear_project_memory(db, project_id)
    return APIResponse(data={"cleared_count": count, "project_id": project_id})
