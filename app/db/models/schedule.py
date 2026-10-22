"""Scheduled jobs and execution history database models."""

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin
from app.domain.enums import JobStatus


class ScheduledJob(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "scheduled_jobs"

    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    cron_expression: Mapped[str | None] = mapped_column(String(128), nullable=True)
    interval_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    task_type: Mapped[str] = mapped_column(String(128), nullable=False)
    task_parameters: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    status: Mapped[JobStatus] = mapped_column(
        String(32),
        default=JobStatus.ACTIVE,
        nullable=False,
        index=True,
    )
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    next_run_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    executions: Mapped[list["JobExecutionHistory"]] = relationship(
        "JobExecutionHistory",
        back_populates="job",
        cascade="all, delete-orphan",
        order_by="JobExecutionHistory.created_at.desc()",
    )


class JobExecutionHistory(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "job_execution_history"

    job_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("scheduled_jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    task_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    duration_ms: Mapped[int] = mapped_column(default=0, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    job: Mapped["ScheduledJob"] = relationship("ScheduledJob", back_populates="executions")
