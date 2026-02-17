from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from botcrew.models.base import AuditMixin, Base, UUIDPrimaryKeyMixin


class ReadCursor(Base, UUIDPrimaryKeyMixin, AuditMixin):
    """Tracks per-user/per-agent read position within a channel."""

    __tablename__ = "read_cursors"
    __table_args__ = (
        UniqueConstraint("channel_id", "agent_id", name="uq_read_cursor_channel_agent"),
        UniqueConstraint("channel_id", "user_identifier", name="uq_read_cursor_channel_user"),
    )

    channel_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("channels.id"), nullable=False
    )
    agent_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False), ForeignKey("agents.id"), nullable=True
    )
    user_identifier: Mapped[str | None] = mapped_column(String(255), nullable=True)
    last_read_message_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False), ForeignKey("messages.id"), nullable=True
    )
    last_read_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
