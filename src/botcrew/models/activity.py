from sqlalchemy import JSON, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from botcrew.models.base import AuditMixin, Base, UUIDPrimaryKeyMixin


class Activity(Base, UUIDPrimaryKeyMixin, AuditMixin):
    """Agent activity log entry for tracking all agent actions.

    Records heartbeat wakes, self-modifications, messages sent, tool usage,
    and any other agent-initiated events. Provides a comprehensive audit
    trail per agent, queryable by event type and chronological order.
    """

    __tablename__ = "activities"

    agent_id: Mapped[str] = mapped_column(
        ForeignKey("agents.id"),
        nullable=False,
        index=True,
    )
    event_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )
    summary: Mapped[str] = mapped_column(
        Text,
        server_default="",
        nullable=False,
    )
    details: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
    )
