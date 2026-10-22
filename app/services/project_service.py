"""Project and directory grant management service."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, ValidationError
from app.db.models.project import Project, ProjectDirectoryGrant
from app.security.path_validation import validate_path_in_roots


class ProjectService:
    @staticmethod
    async def create_project(
        session: AsyncSession,
        name: str,
        root_path: str,
        description: str | None = None,
    ) -> Project:
        resolved_root = validate_path_in_roots(root_path)
        if not resolved_root.exists() or not resolved_root.is_dir():
            raise ValidationError(f"Root path '{root_path}' does not exist or is not a directory.")

        # Check unique name
        existing = await session.execute(select(Project).where(Project.name == name))
        if existing.scalars().first():
            raise ValidationError(f"Project with name '{name}' already exists.")

        project = Project(
            name=name,
            description=description,
            root_path=str(resolved_root),
        )
        session.add(project)
        await session.flush()

        # Add default grant for root_path
        grant = ProjectDirectoryGrant(
            project_id=project.id,
            approved_path=str(resolved_root),
            read_only=False,
        )
        session.add(grant)
        await session.commit()
        await session.refresh(project)
        return project

    @staticmethod
    async def list_projects(session: AsyncSession) -> list[Project]:
        result = await session.execute(select(Project).order_by(Project.created_at.desc()))
        return list(result.scalars().all())

    @staticmethod
    async def get_project(session: AsyncSession, project_id: str) -> Project:
        result = await session.execute(select(Project).where(Project.id == project_id))
        project = result.scalars().first()
        if not project:
            raise NotFoundError(f"Project '{project_id}' not found.")
        return project

    @staticmethod
    async def add_directory_grant(
        session: AsyncSession,
        project_id: str,
        path: str,
        read_only: bool = True,
    ) -> ProjectDirectoryGrant:
        project = await ProjectService.get_project(session, project_id)
        resolved_path = validate_path_in_roots(path)

        grant = ProjectDirectoryGrant(
            project_id=project.id,
            approved_path=str(resolved_path),
            read_only=read_only,
        )
        session.add(grant)
        await session.commit()
        await session.refresh(grant)
        return grant
