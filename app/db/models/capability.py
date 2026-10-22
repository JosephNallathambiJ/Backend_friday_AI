"""Capability Grant database models for permission management."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDMixin
from app.domain.enums import CapabilityType, ScopeType


class CapabilityGrant(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "capability_grants"

    capability: Mapped[CapabilityType] = mapped_column(
        String(64),
        nullable=False,
        index=True,
    )
    scope_type: Mapped[ScopeType] = mapped_column(
        String(32),
        default=ScopeType.GLOBAL,
        nullable=False,
        index=True,
    )
    scope_value: Mapped[str] = mapped_column(
        String(512),
        default="*",
        nullable=False,
    )
    is_granted: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    granted_by: Mapped[str] = mapped_column(
        String(64),
        default="user",
        nullable=False,
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
