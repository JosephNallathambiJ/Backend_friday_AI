"""Tool definition and execution record database models."""

from typing import Any

from sqlalchemy import JSON, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDMixin
from app.domain.enums import ToolRiskLevel


class ToolDefinition(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "tool_definitions"

    name: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    risk_level: Mapped[ToolRiskLevel] = mapped_column(String(32), nullable=False)
    requires_approval: Mapped[bool] = mapped_column(default=False, nullable=False)
    parameters_schema: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    enabled: Mapped[bool] = mapped_column(default=True, nullable=False)


class ToolExecutionRecord(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "tool_execution_records"

    task_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("tasks.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    tool_name: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    parameters_redacted: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    result_data: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    execution_time_ms: Mapped[int] = mapped_column(default=0, nullable=False)
    dry_run: Mapped[bool] = mapped_column(default=False, nullable=False)
    approval_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
