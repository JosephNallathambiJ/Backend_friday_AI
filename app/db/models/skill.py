"""Database models for FRIDAY AI Skill Ecosystem and GitHub Acquisition."""

from typing import Any

from sqlalchemy import JSON, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin
from app.domain.enums import AcquisitionStatus, SkillExecutionMode, SkillStatus, ToolRiskLevel


class SkillRecord(Base, UUIDMixin, TimestampMixin):
    """Registered installed skill in FRIDAY's managed library."""

    __tablename__ = "skills"

    skill_id: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    version: Mapped[str] = mapped_column(String(32), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    author: Mapped[str] = mapped_column(String(128), default="Community", nullable=False)
    license: Mapped[str] = mapped_column(String(64), default="Unknown", nullable=False)
    source: Mapped[str] = mapped_column(String(256), default="", nullable=False)
    source_commit: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    execution_mode: Mapped[SkillExecutionMode] = mapped_column(String(32), default=SkillExecutionMode.INSTRUCTION_ONLY, nullable=False)
    risk_level: Mapped[ToolRiskLevel] = mapped_column(String(32), default=ToolRiskLevel.READ_ONLY, nullable=False)
    status: Mapped[SkillStatus] = mapped_column(String(32), default=SkillStatus.INSTALLED, nullable=False, index=True)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    install_path: Mapped[str] = mapped_column(String(512), default="", nullable=False)
    integrity_hash: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    manifest_data: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)

    versions: Mapped[list["SkillVersionRecord"]] = relationship(
        "SkillVersionRecord",
        back_populates="skill",
        cascade="all, delete-orphan",
        order_by="SkillVersionRecord.created_at.desc()",
        lazy="selectin",
    )


class SkillVersionRecord(Base, UUIDMixin, TimestampMixin):
    """Historical version record for rolling back updated skills."""

    __tablename__ = "skill_versions"

    skill_pk: Mapped[str] = mapped_column(String(36), ForeignKey("skills.id", ondelete="CASCADE"), nullable=False, index=True)
    skill_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    version: Mapped[str] = mapped_column(String(32), nullable=False)
    source_commit: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    install_path: Mapped[str] = mapped_column(String(512), default="", nullable=False)
    checksum: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    manifest_data: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)

    skill: Mapped["SkillRecord"] = relationship("SkillRecord", back_populates="versions")


class SkillAcquisitionRecord(Base, UUIDMixin, TimestampMixin):
    """Stateful record of a GitHub discovery and skill acquisition lifecycle."""

    __tablename__ = "skill_acquisitions"

    skill_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    source_url: Mapped[str] = mapped_column(String(256), nullable=False)
    requested_commit: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    pinned_commit: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    status: Mapped[AcquisitionStatus] = mapped_column(String(32), default=AcquisitionStatus.QUEUED, nullable=False, index=True)
    quarantine_path: Mapped[str] = mapped_column(String(512), default="", nullable=False)
    validation_report: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    approval_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
