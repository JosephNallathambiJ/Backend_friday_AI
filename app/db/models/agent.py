"""Agent Run and Agent Event database models."""

from typing import Any

from sqlalchemy import JSON, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin
from app.domain.enums import AgentRunStatus, AgentType


class AgentRun(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "agent_runs"

    agent_type: Mapped[AgentType] = mapped_column(
        String(32),
        default=AgentType.ORCHESTRATOR,
        nullable=False,
        index=True,
    )
    status: Mapped[AgentRunStatus] = mapped_column(
        String(32),
        default=AgentRunStatus.PENDING,
        nullable=False,
        index=True,
    )
    goal: Mapped[str] = mapped_column(Text, nullable=False)
    project_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("projects.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    conversation_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("conversations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    plan_data: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    execution_budget: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        default=lambda: {
            "max_steps": 25,
            "current_step": 0,
            "max_duration_seconds": 300,
            "max_tool_calls": 50,
            "tool_call_count": 0,
        },
        nullable=False,
    )
    current_step_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    result_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    cancellation_requested: Mapped[bool] = mapped_column(default=False, nullable=False)

    events: Mapped[list["AgentRunEvent"]] = relationship(
        "AgentRunEvent",
        back_populates="run",
        cascade="all, delete-orphan",
        order_by="AgentRunEvent.created_at",
        lazy="selectin",
    )


class AgentRunEvent(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "agent_run_events"

    run_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("agent_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    event_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    payload: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    run: Mapped["AgentRun"] = relationship("AgentRun", back_populates="events")
