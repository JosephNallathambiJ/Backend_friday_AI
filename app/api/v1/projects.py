"""Project and directory grant management endpoints."""

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db, verify_api_key
from app.domain.schemas import APIResponse, ProjectCreate, ProjectRead
from app.services.project_service import ProjectService
from app.services.retrieval_service import RetrievalService

router = APIRouter(
    prefix="/api/v1/projects",
    tags=["Projects & Directory Grants"],
    dependencies=[Depends(verify_api_key)],
)


@router.post("", response_model=APIResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    payload: ProjectCreate,
    db: AsyncSession = Depends(get_db),
):
    project = await ProjectService.create_project(
        session=db,
        name=payload.name,
        root_path=payload.root_path,
        description=payload.description,
    )
    return APIResponse(
        data=ProjectRead(
            id=project.id,
            name=project.name,
            description=project.description,
            root_path=project.root_path,
            created_at=project.created_at,
            updated_at=project.updated_at,
            approved_paths=[g.approved_path for g in project.directory_grants],
        )
    )


@router.get("", response_model=APIResponse)
async def list_projects(db: AsyncSession = Depends(get_db)):
    projects = await ProjectService.list_projects(db)
    return APIResponse(
        data=[
            ProjectRead(
                id=p.id,
                name=p.name,
                description=p.description,
                root_path=p.root_path,
                created_at=p.created_at,
                updated_at=p.updated_at,
                approved_paths=[g.approved_path for g in p.directory_grants]
                if p.directory_grants
                else [],
            )
            for p in projects
        ]
    )


@router.get("/{project_id}", response_model=APIResponse)
async def get_project(
    project_id: str,
    db: AsyncSession = Depends(get_db),
):
    project = await ProjectService.get_project(db, project_id)
    return APIResponse(
        data=ProjectRead(
            id=project.id,
            name=project.name,
            description=project.description,
            root_path=project.root_path,
            created_at=project.created_at,
            updated_at=project.updated_at,
            approved_paths=[g.approved_path for g in project.directory_grants]
            if project.directory_grants
            else [],
        )
    )


@router.post("/{project_id}/index", response_model=APIResponse)
async def index_project(
    project_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Trigger FTS5 full-text indexing of eligible files under approved project root."""
    stats = await RetrievalService.index_project_files(db, project_id)
    return APIResponse(data=stats)


@router.get("/{project_id}/search", response_model=APIResponse)
async def search_project(
    project_id: str,
    q: str = Query(..., min_length=1),
    limit: int = Query(5, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    """Search indexed files using FTS5 keyword matching."""
    results = await RetrievalService.search(db, query=q, project_id=project_id, limit=limit)
    return APIResponse(data={"query": q, "results": results, "count": len(results)})
