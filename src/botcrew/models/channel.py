from sqlalchemy import ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from botcrew.models.base import AuditMixin, Base, UUIDPrimaryKeyMixin


class Channel(Base, UUIDPrimaryKeyMixin, AuditMixin):
    """Communication channel where agents and humans interact."""

    __tablename__ = "channels"

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    channel_type: Mapped[str] = mapped_column(
        String(20), server_default="shared", nullable=False
    )


class ChannelMember(Base, UUIDPrimaryKeyMixin, AuditMixin):
    """Association between a channel and its members (agents or humans)."""

    __tablename__ = "channel_members"
    __table_args__ = (
        UniqueConstraint("channel_id", "agent_id", name="uq_channel_member_channel_agent"),
    )

    channel_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("channels.id"), nullable=False
    )
    agent_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False), ForeignKey("agents.id"), nullable=True
    )
    user_identifier: Mapped[str | None] = mapped_column(String(255), nullable=True)
