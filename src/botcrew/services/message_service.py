"""Message business logic service.

Encapsulates all database interactions for message persistence,
history retrieval with cursor-based pagination, and read cursor
management. Follows the established DI pattern (async session injection).
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from botcrew.models.message import Message
from botcrew.models.read_cursor import ReadCursor
from botcrew.schemas.pagination import PaginationMeta, decode_cursor

logger = logging.getLogger(__name__)


class MessageService:
    """Message persistence, history retrieval, and read cursor management.

    Provides message creation, cursor-paginated history (newest first),
    read cursor upsert, and unread count/messages retrieval.

    Args:
        db: Async SQLAlchemy session for database operations.
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_message(
        self,
        channel_id: str,
        content: str,
        message_type: str = "chat",
        sender_agent_id: str | None = None,
        sender_user_identifier: str | None = None,
        metadata_: dict | None = None,
    ) -> Message:
        """Create and persist a new message.

        Args:
            channel_id: UUID of the channel to post in.
            content: Message text content.
            message_type: One of 'chat', 'system', 'dm'.
            sender_agent_id: UUID of the sending agent (if agent).
            sender_user_identifier: Identifier of the sending user (if human).
            metadata_: Optional JSON metadata for the message.

        Returns:
            The created Message instance with populated timestamps.
        """
        message = Message(
            channel_id=channel_id,
            content=content,
            message_type=message_type,
            sender_agent_id=sender_agent_id,
            sender_user_identifier=sender_user_identifier,
            metadata_=metadata_,
        )
        self.db.add(message)
        await self.db.flush()
        await self.db.commit()
        await self.db.refresh(message)
        return message

    async def get_message_history(
        self,
        channel_id: str,
        page_size: int = 50,
        before: str | None = None,
    ) -> tuple[list[Message], PaginationMeta]:
        """Get paginated message history for a channel.

        Returns messages ordered by created_at DESC (newest first).
        Uses cursor-based pagination where ``before`` is an opaque cursor
        pointing to the oldest message in the current view. Queries for
        messages older than the cursor.

        Args:
            channel_id: UUID of the channel.
            page_size: Maximum number of messages to return.
            before: Opaque pagination cursor for fetching older messages.

        Returns:
            Tuple of (messages list, pagination metadata).
        """
        query = select(Message).where(Message.channel_id == channel_id)

        if before:
            cursor_created_at, cursor_id = decode_cursor(before)
            query = query.where(
                (Message.created_at < cursor_created_at)
                | (
                    (Message.created_at == cursor_created_at)
                    & (Message.id < cursor_id)
                )
            )

        query = query.order_by(
            Message.created_at.desc(),
            Message.id.desc(),
        )
        query = query.limit(page_size + 1)

        result = await self.db.execute(query)
        messages = list(result.scalars().all())

        has_next = len(messages) > page_size
        if has_next:
            messages = messages[:page_size]

        return messages, PaginationMeta(
            has_next=has_next,
            has_prev=before is not None,
        )

    async def update_read_cursor(
        self,
        channel_id: str,
        last_read_message_id: str,
        agent_id: str | None = None,
        user_identifier: str | None = None,
    ) -> ReadCursor:
        """Create or update a read cursor for a user or agent in a channel.

        Upserts: if a ReadCursor exists for the given (channel_id + agent_id)
        or (channel_id + user_identifier), updates it. Otherwise creates new.

        Args:
            channel_id: UUID of the channel.
            last_read_message_id: UUID of the last read message.
            agent_id: UUID of the agent (if tracking agent read position).
            user_identifier: Identifier of the user (if tracking user read position).

        Returns:
            The created or updated ReadCursor instance.
        """
        conditions = [ReadCursor.channel_id == channel_id]
        if agent_id:
            conditions.append(ReadCursor.agent_id == agent_id)
        else:
            conditions.append(ReadCursor.user_identifier == user_identifier)

        result = await self.db.execute(
            select(ReadCursor).where(and_(*conditions))
        )
        cursor = result.scalars().first()

        now = datetime.now(timezone.utc)

        if cursor is not None:
            cursor.last_read_message_id = last_read_message_id
            cursor.last_read_at = now
        else:
            cursor = ReadCursor(
                channel_id=channel_id,
                agent_id=agent_id,
                user_identifier=user_identifier,
                last_read_message_id=last_read_message_id,
                last_read_at=now,
            )
            self.db.add(cursor)

        await self.db.commit()
        await self.db.refresh(cursor)
        return cursor

    async def get_unread_count(
        self,
        channel_id: str,
        agent_id: str | None = None,
        user_identifier: str | None = None,
    ) -> int:
        """Get the number of unread messages for a user or agent in a channel.

        If no read cursor exists, all messages in the channel are unread.
        If a cursor exists, counts messages created after the cursor's
        last_read_at timestamp.

        Args:
            channel_id: UUID of the channel.
            agent_id: UUID of the agent.
            user_identifier: Identifier of the user.

        Returns:
            Number of unread messages.
        """
        read_cursor = await self._get_read_cursor(channel_id, agent_id, user_identifier)

        query = select(func.count()).select_from(Message).where(
            Message.channel_id == channel_id
        )

        if read_cursor is not None and read_cursor.last_read_at is not None:
            query = query.where(Message.created_at > read_cursor.last_read_at)

        result = await self.db.execute(query)
        return result.scalar_one()

    async def get_unread_messages(
        self,
        channel_id: str,
        agent_id: str | None = None,
        user_identifier: str | None = None,
    ) -> list[Message]:
        """Get unread messages for a user or agent in a channel.

        Same logic as get_unread_count but returns the actual Message objects.
        Used by heartbeat cycle (Phase 5) to fetch messages an agent hasn't
        seen yet.

        Args:
            channel_id: UUID of the channel.
            agent_id: UUID of the agent.
            user_identifier: Identifier of the user.

        Returns:
            List of unread Message instances ordered by created_at ASC.
        """
        read_cursor = await self._get_read_cursor(channel_id, agent_id, user_identifier)

        query = select(Message).where(Message.channel_id == channel_id)

        if read_cursor is not None and read_cursor.last_read_at is not None:
            query = query.where(Message.created_at > read_cursor.last_read_at)

        query = query.order_by(Message.created_at.asc())

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def _get_read_cursor(
        self,
        channel_id: str,
        agent_id: str | None = None,
        user_identifier: str | None = None,
    ) -> ReadCursor | None:
        """Internal helper to fetch the read cursor for a user or agent.

        Args:
            channel_id: UUID of the channel.
            agent_id: UUID of the agent.
            user_identifier: Identifier of the user.

        Returns:
            The ReadCursor instance, or None if not found.
        """
        conditions = [ReadCursor.channel_id == channel_id]
        if agent_id:
            conditions.append(ReadCursor.agent_id == agent_id)
        else:
            conditions.append(ReadCursor.user_identifier == user_identifier)

        result = await self.db.execute(
            select(ReadCursor).where(and_(*conditions))
        )
        return result.scalars().first()
