from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from botcrew.models.base import AuditMixin, Base, UUIDPrimaryKeyMixin


class Project(Base, UUIDPrimaryKeyMixin, AuditMixin):
    """A project that agents collaborate on."""

    __tablename__ = "projects"

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    goals: Mapped[str | None] = mapped_column(Text, nullable=True)
    specs: Mapped[str | None] = mapped_column(Text, nullable=True)
    github_repo_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    channel_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False), ForeignKey("channels.id"), nullable=True
    )
    status: Mapped[str] = mapped_column(
        String(20), server_default="active", nullable=False
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class ProjectAgent(Base, UUIDPrimaryKeyMixin, AuditMixin):
    """Association between a project and an assigned agent."""

    __tablename__ = "project_agents"
    __table_args__ = (
        UniqueConstraint("project_id", "agent_id", name="uq_project_agent_project_agent"),
    )

    project_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("projects.id"), nullable=False
    )
    agent_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("agents.id"), nullable=False
    )
    role_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)


class ProjectFile(Base, UUIDPrimaryKeyMixin, AuditMixin):
    """Backed-up spec/planning file from a project workspace."""

    __tablename__ = "project_files"
    __table_args__ = (
        UniqueConstraint("project_id", "path", name="uq_project_file_project_path"),
    )

    project_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("projects.id"), nullable=False
    )
    path: Mapped[str] = mapped_column(String(500), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    size: Mapped[int] = mapped_column(Integer, nullable=False)
    last_modified: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )


class ProjectSecret(Base, UUIDPrimaryKeyMixin, AuditMixin):
    """Association between a project and an assigned secret."""

    __tablename__ = "project_secrets"
    __table_args__ = (
        UniqueConstraint("project_id", "secret_id", name="uq_project_secret"),
    )

    project_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("projects.id"), nullable=False
    )
    secret_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("secrets.id"), nullable=False
    )
