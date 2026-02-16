from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from botcrew.models.base import AuditMixin, Base, UUIDPrimaryKeyMixin


class Message(Base, UUIDPrimaryKeyMixin, AuditMixin):
    """A message sent within a channel by an agent or a human."""

    __tablename__ = "messages"

    channel_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("channels.id"), nullable=False
    )
    sender_agent_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False), ForeignKey("agents.id"), nullable=True
    )
    sender_user_identifier: Mapped[str | None] = mapped_column(String(255), nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    message_type: Mapped[str] = mapped_column(
        String(20), server_default="chat", nullable=False
    )
