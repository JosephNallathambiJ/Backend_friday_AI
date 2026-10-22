"""Scheduled automation endpoints."""

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db, verify_api_key
from app.core.exceptions import NotFoundError, ValidationError
from app.db.models.schedule import ScheduledJob
from app.domain.enums import JobStatus
from app.domain.schemas import APIResponse, ScheduleCreate, ScheduleRead

router = APIRouter(
    prefix="/api/v1/schedules",
    tags=["Scheduled Automation"],
    dependencies=[Depends(verify_api_key)],
)


@router.post("", response_model=APIResponse, status_code=status.HTTP_201_CREATED)
async def create_schedule(
    payload: ScheduleCreate,
    db: AsyncSession = Depends(get_db),
):
    if not payload.cron_expression and not payload.interval_seconds:
        raise ValidationError("Either cron_expression or interval_seconds must be provided.")

    job = ScheduledJob(
        name=payload.name,
        cron_expression=payload.cron_expression,
        interval_seconds=payload.interval_seconds,
        task_type=payload.task_type,
        task_parameters=payload.task_parameters,
        status=JobStatus.ACTIVE,
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    return APIResponse(
        data=ScheduleRead(
            id=job.id,
            name=job.name,
            cron_expression=job.cron_expression,
            interval_seconds=job.interval_seconds,
            task_type=job.task_type,
            status=job.status,
            last_run_at=job.last_run_at,
            next_run_at=job.next_run_at,
            created_at=job.created_at,
        )
    )


@router.get("", response_model=APIResponse)
async def list_schedules(db: AsyncSession = Depends(get_db)):
    stmt = select(ScheduledJob).order_by(ScheduledJob.created_at.desc())
    jobs = (await db.execute(stmt)).scalars().all()
    return APIResponse(
        data=[
            ScheduleRead(
                id=j.id,
                name=j.name,
                cron_expression=j.cron_expression,
                interval_seconds=j.interval_seconds,
                task_type=j.task_type,
                status=j.status,
                last_run_at=j.last_run_at,
                next_run_at=j.next_run_at,
                created_at=j.created_at,
            )
            for j in jobs
        ]
    )


@router.post("/{job_id}/pause", response_model=APIResponse)
async def pause_schedule(job_id: str, db: AsyncSession = Depends(get_db)):
    job = (
        (await db.execute(select(ScheduledJob).where(ScheduledJob.id == job_id))).scalars().first()
    )
    if not job:
        raise NotFoundError(f"Job '{job_id}' not found.")
    job.status = JobStatus.PAUSED
    await db.commit()
    return APIResponse(data={"job_id": job.id, "status": job.status})


@router.post("/{job_id}/resume", response_model=APIResponse)
async def resume_schedule(job_id: str, db: AsyncSession = Depends(get_db)):
    job = (
        (await db.execute(select(ScheduledJob).where(ScheduledJob.id == job_id))).scalars().first()
    )
    if not job:
        raise NotFoundError(f"Job '{job_id}' not found.")
    job.status = JobStatus.ACTIVE
    await db.commit()
    return APIResponse(data={"job_id": job.id, "status": job.status})


@router.delete("/{job_id}", response_model=APIResponse)
async def delete_schedule(job_id: str, db: AsyncSession = Depends(get_db)):
    job = (
        (await db.execute(select(ScheduledJob).where(ScheduledJob.id == job_id))).scalars().first()
    )
    if not job:
        raise NotFoundError(f"Job '{job_id}' not found.")
    await db.delete(job)
    await db.commit()
    return APIResponse(data={"deleted": True, "job_id": job_id})
