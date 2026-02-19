from sqlalchemy import ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from botcrew.models.base import AuditMixin, Base, UUIDPrimaryKeyMixin


class Task(Base, UUIDPrimaryKeyMixin, AuditMixin):
    """A structured work directive assigned to agents."""

    __tablename__ = "tasks"

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    directive: Mapped[str] = mapped_column(Text, nullable=False)
    notes: Mapped[str] = mapped_column(Text, server_default="", nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), server_default="open", nullable=False
    )
    channel_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False), ForeignKey("channels.id"), nullable=True
    )


class TaskAgent(Base, UUIDPrimaryKeyMixin, AuditMixin):
    """Association between a task and an assigned agent."""

    __tablename__ = "task_agents"
    __table_args__ = (
        UniqueConstraint("task_id", "agent_id", name="uq_task_agent_task_agent"),
    )

    task_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("tasks.id"), nullable=False
    )
    agent_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("agents.id"), nullable=False
    )


class TaskSecret(Base, UUIDPrimaryKeyMixin, AuditMixin):
    """Association between a task and an assigned secret."""

    __tablename__ = "task_secrets"
    __table_args__ = (
        UniqueConstraint("task_id", "secret_id", name="uq_task_secret_task_secret"),
    )

    task_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("tasks.id"), nullable=False
    )
    secret_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("secrets.id"), nullable=False
    )


class TaskSkill(Base, UUIDPrimaryKeyMixin, AuditMixin):
    """Association between a task and an assigned skill."""

    __tablename__ = "task_skills"
    __table_args__ = (
        UniqueConstraint("task_id", "skill_id", name="uq_task_skill_task_skill"),
    )

    task_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("tasks.id"), nullable=False
    )
    skill_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("skills.id"), nullable=False
    )
