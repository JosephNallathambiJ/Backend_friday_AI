"""Memory record database model."""

from typing import Any

from sqlalchemy import JSON, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDMixin
from app.domain.enums import MemoryCategory


class MemoryRecord(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "memory_records"
    __table_args__ = (
        UniqueConstraint("category", "key", "project_id", name="uq_memory_category_key_project"),
    )

    category: Mapped[MemoryCategory] = mapped_column(String(32), nullable=False, index=True)
    key: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    project_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
