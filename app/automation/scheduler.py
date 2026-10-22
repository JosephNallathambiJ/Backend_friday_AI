"""Persistent background task scheduler supporting cron expressions and fixed intervals."""

import asyncio
from datetime import datetime, timedelta

from croniter import croniter
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import logger
from app.core.time import utc_now
from app.db.models.schedule import JobExecutionHistory, ScheduledJob
from app.db.session import async_session_factory
from app.domain.enums import JobStatus


class TaskScheduler:
    """Persistent scheduler executing jobs in the background."""

    def __init__(self):
        self._running = False
        self._worker_task: asyncio.Task | None = None

    async def start(self):
        """Start the background scheduler worker."""
        if not settings.SCHEDULER_ENABLED:
            logger.info("Scheduler is disabled in configuration.")
            return

        if self._running:
            return

        self._running = True
        self._worker_task = asyncio.create_task(self._scheduler_loop())
        logger.info("Scheduler worker started.")

    async def stop(self):
        """Stop the background scheduler worker gracefully."""
        self._running = False
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
        logger.info("Scheduler worker stopped.")

    async def _scheduler_loop(self):
        """Periodically check database for pending scheduled jobs."""
        while self._running:
            try:
                async with async_session_factory() as session:
                    await self._evaluate_jobs(session)
            except Exception as e:
                logger.error(f"Error in scheduler tick: {e}", exc_info=True)

            await asyncio.sleep(10)  # Check every 10 seconds

    async def _evaluate_jobs(self, session: AsyncSession):
        now = utc_now()
        stmt = select(ScheduledJob).where(ScheduledJob.status == JobStatus.ACTIVE)
        jobs = (await session.execute(stmt)).scalars().all()

        for job in jobs:
            should_run = False
            if job.next_run_at is None:
                # Compute next run time
                job.next_run_at = self._calculate_next_run(job, now)
                await session.commit()
                continue

            if now >= job.next_run_at:
                should_run = True

            if should_run:
                # Execute job safely with duplicate run prevention
                await self._execute_job(session, job, now)

    def _calculate_next_run(self, job: ScheduledJob, base_time: datetime) -> datetime:
        if job.cron_expression:
            itr = croniter(job.cron_expression, base_time)
            return itr.get_next(datetime)
        elif job.interval_seconds:
            return base_time + timedelta(seconds=job.interval_seconds)
        return base_time + timedelta(hours=24)

    async def _execute_job(self, session: AsyncSession, job: ScheduledJob, run_time: datetime):
        logger.info(f"[SCHEDULER] Executing job '{job.name}' (type: {job.task_type})")
        start_ms = int(utc_now().timestamp() * 1000)

        # Update next_run_at to prevent duplicate executions
        job.last_run_at = run_time
        job.next_run_at = self._calculate_next_run(job, run_time)

        execution = JobExecutionHistory(
            job_id=job.id,
            status="running",
            duration_ms=0,
        )
        session.add(execution)
        await session.commit()

        status = "succeeded"
        error_msg = None

        try:
            # Dispatch predefined tasks (e.g. index refresh, security audit)
            if job.task_type == "security_scan":
                from app.services.security_service import SecurityService

                await SecurityService.run_scan(session)
            # Predefined task types can be extended cleanly
        except Exception as e:
            status = "failed"
            error_msg = str(e)
            logger.error(f"Scheduled job '{job.name}' failed: {e}")

        duration = int(utc_now().timestamp() * 1000) - start_ms
        execution.status = status
        execution.duration_ms = duration
        execution.error_message = error_msg
        await session.commit()


scheduler = TaskScheduler()
