from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from botcrew.models.base import AuditMixin, Base, UUIDPrimaryKeyMixin


class TokenUsage(Base, UUIDPrimaryKeyMixin, AuditMixin):
    """Per-call LLM token usage record for an agent."""

    __tablename__ = "token_usage"

    agent_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("agents.id"), nullable=False
    )
    task_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False), ForeignKey("tasks.id"), nullable=True
    )
    project_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False), ForeignKey("projects.id"), nullable=True
    )
    model_provider: Mapped[str] = mapped_column(String(50), nullable=False)
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    input_tokens: Mapped[int] = mapped_column(Integer, nullable=False)
    output_tokens: Mapped[int] = mapped_column(Integer, nullable=False)
    call_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
