"""Memory service for project and user preference records."""

from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.db.models.memory import MemoryRecord
from app.domain.enums import MemoryCategory


class MemoryService:
    @staticmethod
    async def create_or_update_memory(
        session: AsyncSession,
        category: MemoryCategory,
        key: str,
        content: str,
        project_id: str | None = None,
        metadata_json: dict[str, Any] | None = None,
    ) -> MemoryRecord:
        stmt = select(MemoryRecord).where(
            MemoryRecord.category == category,
            MemoryRecord.key == key,
            MemoryRecord.project_id == project_id,
        )
        existing = (await session.execute(stmt)).scalars().first()
        if existing:
            existing.content = content
            existing.metadata_json = metadata_json
            await session.commit()
            await session.refresh(existing)
            return existing

        record = MemoryRecord(
            category=category,
            key=key,
            content=content,
            project_id=project_id,
            metadata_json=metadata_json,
        )
        session.add(record)
        await session.commit()
        await session.refresh(record)
        return record

    @staticmethod
    async def list_memories(
        session: AsyncSession,
        category: MemoryCategory | None = None,
        project_id: str | None = None,
    ) -> list[MemoryRecord]:
        query = select(MemoryRecord).order_by(MemoryRecord.updated_at.desc())
        if category:
            query = query.where(MemoryRecord.category == category)
        if project_id:
            query = query.where(MemoryRecord.project_id == project_id)

        result = await session.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def get_memory(session: AsyncSession, memory_id: str) -> MemoryRecord:
        result = await session.execute(select(MemoryRecord).where(MemoryRecord.id == memory_id))
        record = result.scalars().first()
        if not record:
            raise NotFoundError(f"Memory record '{memory_id}' not found.")
        return record

    @staticmethod
    async def delete_memory(session: AsyncSession, memory_id: str) -> None:
        record = await MemoryService.get_memory(session, memory_id)
        await session.delete(record)
        await session.commit()

    @staticmethod
    async def clear_project_memory(session: AsyncSession, project_id: str) -> int:
        stmt = delete(MemoryRecord).where(MemoryRecord.project_id == project_id)
        result = await session.execute(stmt)
        await session.commit()
        return result.rowcount or 0
