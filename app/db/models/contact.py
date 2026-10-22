"""Contact record database model."""

from typing import Any

from sqlalchemy import JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDMixin


class ContactRecord(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "contacts"

    display_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    given_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    family_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    organization: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    emails: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    phones: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    labels: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    provider_id: Mapped[str] = mapped_column(String(64), default="local_database", nullable=False)
    raw_metadata: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
