"""Task execution lifecycle and state machine management."""

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, TaskCancelledError
from app.db.models.task import Task, TaskEvent
from app.domain.enums import TaskStatus


class TaskService:
    @staticmethod
    async def create_task(
        session: AsyncSession,
        task_type: str,
        summary: str,
        project_id: str | None = None,
        parameters: dict[str, Any] | None = None,
    ) -> Task:
        task = Task(
            task_type=task_type,
            summary=summary,
            project_id=project_id,
            parameters=parameters or {},
            status=TaskStatus.QUEUED,
        )
        session.add(task)
        await session.flush()

        event = TaskEvent(
            task_id=task.id,
            event_type="TASK_CREATED",
            message=f"Task '{task_type}' queued.",
            payload=parameters,
        )
        session.add(event)
        await session.commit()
        await session.refresh(task)
        return task

    @staticmethod
    async def get_task(session: AsyncSession, task_id: str) -> Task:
        result = await session.execute(select(Task).where(Task.id == task_id))
        task = result.scalars().first()
        if not task:
            raise NotFoundError(f"Task '{task_id}' not found.")
        return task

    @staticmethod
    async def update_status(
        session: AsyncSession,
        task_id: str,
        status: TaskStatus,
        current_step: str | None = None,
        result_data: dict[str, Any] | None = None,
        error_message: str | None = None,
    ) -> Task:
        task = await TaskService.get_task(session, task_id)
        if task.status == TaskStatus.CANCELLED and status != TaskStatus.CANCELLED:
            raise TaskCancelledError(f"Task '{task_id}' was cancelled.")

        task.status = status
        if current_step:
            task.current_step = current_step
        if result_data:
            task.result_data = result_data
        if error_message:
            task.error_message = error_message

        event = TaskEvent(
            task_id=task.id,
            event_type=f"STATUS_{status.value.upper()}",
            message=current_step or f"Status changed to {status.value}",
            payload={"error": error_message} if error_message else result_data,
        )
        session.add(event)
        await session.commit()
        await session.refresh(task)
        return task

    @staticmethod
    async def cancel_task(session: AsyncSession, task_id: str) -> Task:
        return await TaskService.update_status(
            session=session,
            task_id=task_id,
            status=TaskStatus.CANCELLED,
            current_step="Cancelled by user request.",
        )

    @staticmethod
    async def list_tasks(
        session: AsyncSession,
        project_id: str | None = None,
        status: TaskStatus | None = None,
        limit: int = 50,
    ) -> list[Task]:
        query = select(Task).order_by(Task.created_at.desc()).limit(limit)
        if project_id:
            query = query.where(Task.project_id == project_id)
        if status:
            query = query.where(Task.status == status)
        result = await session.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def get_task_events(session: AsyncSession, task_id: str) -> list[TaskEvent]:
        await TaskService.get_task(session, task_id)
        stmt = (
            select(TaskEvent)
            .where(TaskEvent.task_id == task_id)
            .order_by(TaskEvent.created_at.asc())
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())
