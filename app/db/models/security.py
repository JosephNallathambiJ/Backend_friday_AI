"""Security findings and reports database models."""

from sqlalchemy import JSON, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin
from app.domain.enums import FindingSeverity


class SecurityReport(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "security_reports"

    target_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    summary_counts: Mapped[dict[str, int]] = mapped_column(JSON, default=dict, nullable=False)
    markdown_content: Mapped[str] = mapped_column(Text, nullable=False)

    findings: Mapped[list["SecurityFinding"]] = relationship(
        "SecurityFinding",
        back_populates="report",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class SecurityFinding(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "security_findings"

    report_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("security_reports.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    severity: Mapped[FindingSeverity] = mapped_column(String(32), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    file_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    line_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    evidence: Mapped[str] = mapped_column(Text, nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    remediation: Mapped[str] = mapped_column(Text, nullable=False)

    report: Mapped["SecurityReport"] = relationship("SecurityReport", back_populates="findings")
