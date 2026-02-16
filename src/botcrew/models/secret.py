from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from botcrew.models.base import AuditMixin, Base, UUIDPrimaryKeyMixin


class Secret(Base, UUIDPrimaryKeyMixin, AuditMixin):
    """Key-value secret storage for sensitive configuration."""

    __tablename__ = "secrets"

    key: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
