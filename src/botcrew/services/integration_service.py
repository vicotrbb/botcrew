"""Integration CRUD service layer.

Provides create, list, get, update, and hard-delete operations for
integrations with cursor-based pagination and optional type filtering.
"""

from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from botcrew.models.integration import Integration
from botcrew.schemas.pagination import PaginationMeta, decode_cursor

logger = logging.getLogger(__name__)


class IntegrationService:
    """Service for integration CRUD operations with pagination.

    Args:
        db: Async SQLAlchemy session for database operations.
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_integration(
        self,
        name: str,
        integration_type: str,
        config: str,
        agent_id: str | None = None,
        channel_id: str | None = None,
    ) -> Integration:
        """Create a new integration.

        Args:
            name: Integration display name.
            integration_type: Type identifier (e.g. "ai_provider", "github").
            config: JSON string with provider-specific configuration.
            agent_id: Optional associated agent UUID.
            channel_id: Optional associated channel UUID.

        Returns:
            The created Integration record.
        """
        integration = Integration(
            name=name,
            integration_type=integration_type,
            config=config,
            agent_id=agent_id,
            channel_id=channel_id,
        )
        self.db.add(integration)
        await self.db.commit()
        await self.db.refresh(integration)
        return integration

    async def list_integrations(
        self,
        page_size: int = 20,
        after: str | None = None,
        integration_type: str | None = None,
    ) -> tuple[list[Integration], PaginationMeta]:
        """List integrations with cursor-based pagination.

        Args:
            page_size: Maximum number of integrations to return.
            after: Opaque cursor for pagination.
            integration_type: Optional filter by integration type.

        Returns:
            Tuple of (integrations list, pagination metadata).
        """
        query = select(Integration)

        if integration_type:
            query = query.where(Integration.integration_type == integration_type)

        if after:
            cursor_created_at, cursor_id = decode_cursor(after)
            query = query.where(
                (Integration.created_at > cursor_created_at)
                | (
                    (Integration.created_at == cursor_created_at)
                    & (Integration.id > cursor_id)
                )
            )

        query = query.order_by(
            Integration.created_at.asc(), Integration.id.asc()
        )
        query = query.limit(page_size + 1)

        result = await self.db.execute(query)
        integrations = list(result.scalars().all())

        has_next = len(integrations) > page_size
        if has_next:
            integrations = integrations[:page_size]

        has_prev = after is not None

        return integrations, PaginationMeta(
            has_next=has_next, has_prev=has_prev
        )

    async def get_integration(
        self, integration_id: str
    ) -> Integration | None:
        """Get an integration by UUID.

        Args:
            integration_id: UUID of the integration.

        Returns:
            The Integration record, or None if not found.
        """
        result = await self.db.execute(
            select(Integration).where(Integration.id == integration_id)
        )
        return result.scalar_one_or_none()

    async def update_integration(
        self, integration_id: str, **kwargs: object
    ) -> Integration:
        """Partial update of an integration's fields.

        Args:
            integration_id: UUID of the integration to update.
            **kwargs: Fields to update.

        Returns:
            The updated Integration record.

        Raises:
            ValueError: If the integration is not found.
        """
        integration = await self.get_integration(integration_id)
        if integration is None:
            raise ValueError(f"Integration not found: {integration_id}")

        for field, value in kwargs.items():
            if value is not None:
                setattr(integration, field, value)

        await self.db.commit()
        await self.db.refresh(integration)
        return integration

    async def delete_integration(self, integration_id: str) -> None:
        """Hard-delete an integration.

        Args:
            integration_id: UUID of the integration to delete.

        Raises:
            ValueError: If the integration is not found.
        """
        integration = await self.get_integration(integration_id)
        if integration is None:
            raise ValueError(f"Integration not found: {integration_id}")

        await self.db.delete(integration)
        await self.db.commit()
