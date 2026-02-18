"""Secret CRUD service layer.

Provides create, list, get, update, and hard-delete operations for
secrets with cursor-based pagination.
"""

from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from botcrew.models.secret import Secret
from botcrew.schemas.pagination import PaginationMeta, decode_cursor

logger = logging.getLogger(__name__)


class SecretService:
    """Service for secret CRUD operations with pagination.

    Args:
        db: Async SQLAlchemy session for database operations.
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_secret(
        self,
        key: str,
        value: str,
        description: str | None = None,
    ) -> Secret:
        """Create a new secret.

        Args:
            key: Unique secret key.
            value: Secret value (sensitive data).
            description: Optional description of the secret.

        Returns:
            The created Secret record.

        Raises:
            ValueError: If a secret with the same key already exists.
        """
        secret = Secret(
            key=key,
            value=value,
            description=description,
        )
        self.db.add(secret)
        try:
            await self.db.commit()
        except IntegrityError as exc:
            await self.db.rollback()
            raise ValueError(
                f"Secret with key '{key}' already exists"
            ) from exc
        await self.db.refresh(secret)
        return secret

    async def list_secrets(
        self,
        page_size: int = 20,
        after: str | None = None,
    ) -> tuple[list[Secret], PaginationMeta]:
        """List secrets with cursor-based pagination.

        Args:
            page_size: Maximum number of secrets to return.
            after: Opaque cursor for pagination.

        Returns:
            Tuple of (secrets list, pagination metadata).
        """
        query = select(Secret)

        if after:
            cursor_created_at, cursor_id = decode_cursor(after)
            query = query.where(
                (Secret.created_at > cursor_created_at)
                | (
                    (Secret.created_at == cursor_created_at)
                    & (Secret.id > cursor_id)
                )
            )

        query = query.order_by(Secret.created_at.asc(), Secret.id.asc())
        query = query.limit(page_size + 1)

        result = await self.db.execute(query)
        secrets = list(result.scalars().all())

        has_next = len(secrets) > page_size
        if has_next:
            secrets = secrets[:page_size]

        has_prev = after is not None

        return secrets, PaginationMeta(has_next=has_next, has_prev=has_prev)

    async def get_secret(self, secret_id: str) -> Secret | None:
        """Get a secret by UUID.

        Args:
            secret_id: UUID of the secret.

        Returns:
            The Secret record, or None if not found.
        """
        result = await self.db.execute(
            select(Secret).where(Secret.id == secret_id)
        )
        return result.scalar_one_or_none()

    async def update_secret(self, secret_id: str, **kwargs: object) -> Secret:
        """Partial update of a secret's fields.

        Args:
            secret_id: UUID of the secret to update.
            **kwargs: Fields to update (key, value, description).

        Returns:
            The updated Secret record.

        Raises:
            ValueError: If the secret is not found.
        """
        secret = await self.get_secret(secret_id)
        if secret is None:
            raise ValueError(f"Secret not found: {secret_id}")

        for field, value in kwargs.items():
            if value is not None:
                setattr(secret, field, value)

        await self.db.commit()
        await self.db.refresh(secret)
        return secret

    async def delete_secret(self, secret_id: str) -> None:
        """Hard-delete a secret.

        Args:
            secret_id: UUID of the secret to delete.

        Raises:
            ValueError: If the secret is not found.
        """
        secret = await self.get_secret(secret_id)
        if secret is None:
            raise ValueError(f"Secret not found: {secret_id}")

        await self.db.delete(secret)
        await self.db.commit()
