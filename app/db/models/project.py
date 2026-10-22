"""Project and Directory Grant database models."""

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin


class Project(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "projects"

    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    root_path: Mapped[str] = mapped_column(String(1024), nullable=False)

    directory_grants: Mapped[list["ProjectDirectoryGrant"]] = relationship(
        "ProjectDirectoryGrant",
        back_populates="project",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class ProjectDirectoryGrant(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "project_directory_grants"

    project_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    approved_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    read_only: Mapped[bool] = mapped_column(default=True, nullable=False)

    project: Mapped["Project"] = relationship("Project", back_populates="directory_grants")
