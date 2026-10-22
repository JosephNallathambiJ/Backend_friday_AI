"""Approval request database model."""

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDMixin
from app.domain.enums import ApprovalStatus, ToolRiskLevel


class ApprovalRequest(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "approval_requests"

    task_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tool_name: Mapped[str] = mapped_column(String(128), nullable=False)
    action_description: Mapped[str] = mapped_column(Text, nullable=False)
    risk_level: Mapped[ToolRiskLevel] = mapped_column(String(32), nullable=False)
    arguments_redacted: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    raw_arguments: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    status: Mapped[ApprovalStatus] = mapped_column(
        String(32),
        default=ApprovalStatus.PENDING,
        nullable=False,
        index=True,
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    decision_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    decision_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
