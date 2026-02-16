from sqlalchemy import Boolean, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from botcrew.models.base import AuditMixin, Base, UUIDPrimaryKeyMixin


class Agent(Base, UUIDPrimaryKeyMixin, AuditMixin):
    """AI agent entity with identity, personality, and runtime configuration."""

    __tablename__ = "agents"

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    identity: Mapped[str] = mapped_column(Text, server_default="", nullable=False)
    personality: Mapped[str] = mapped_column(Text, server_default="", nullable=False)
    memory: Mapped[str] = mapped_column(Text, server_default="", nullable=False)
    heartbeat_prompt: Mapped[str] = mapped_column(Text, server_default="", nullable=False)
    heartbeat_interval_seconds: Mapped[int] = mapped_column(
        Integer, server_default="900", nullable=False
    )
    heartbeat_enabled: Mapped[bool] = mapped_column(
        Boolean, server_default="true", nullable=False
    )
    model_provider: Mapped[str] = mapped_column(
        String(50), server_default="anthropic", nullable=False
    )
    model_name: Mapped[str] = mapped_column(
        String(100), server_default="claude-sonnet-4-20250514", nullable=False
    )
    avatar_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), server_default="created", nullable=False
    )
    pod_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
