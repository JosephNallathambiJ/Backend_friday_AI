"""Terminal Session and Command History database models."""


from sqlalchemy import JSON, Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin


class TerminalSession(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "terminal_sessions"

    user_id: Mapped[str] = mapped_column(String(64), default="local_user", nullable=False, index=True)
    working_directory: Mapped[str] = mapped_column(String(512), nullable=False)
    profile_name: Mapped[str] = mapped_column(String(64), default="system_check", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    history: Mapped[list["TerminalCommandHistory"]] = relationship(
        "TerminalCommandHistory",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="TerminalCommandHistory.created_at",
        lazy="selectin",
    )


class TerminalCommandHistory(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "terminal_command_history"

    session_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("terminal_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    command_line: Mapped[str] = mapped_column(String(1024), nullable=False)
    executable: Mapped[str] = mapped_column(String(128), nullable=False)
    args: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    exit_code: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    stdout: Mapped[str] = mapped_column(Text, default="", nullable=False)
    stderr: Mapped[str] = mapped_column(Text, default="", nullable=False)
    execution_time_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    timed_out: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    cancelled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    session: Mapped["TerminalSession"] = relationship("TerminalSession", back_populates="history")
