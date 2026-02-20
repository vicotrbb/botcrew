"""Channel business logic service.

Encapsulates all database interactions for channel CRUD and membership
management. Follows the established DI pattern (async session injection).
"""

from __future__ import annotations

import logging

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from botcrew.models.channel import Channel, ChannelMember

logger = logging.getLogger(__name__)


class ChannelService:
    """Channel CRUD and membership management.

    Provides channel creation, retrieval, listing, and member
    add/remove operations. Supports special-case channels like
    #general (shared) and DM channels between agent and user.

    Args:
        db: Async SQLAlchemy session for database operations.
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_channel(
        self,
        name: str,
        description: str | None = None,
        channel_type: str = "shared",
        creator_user_identifier: str | None = None,
        agent_ids: list[str] | None = None,
    ) -> Channel:
        """Create a new channel with optional initial members.

        Creates the Channel record and adds ChannelMember entries for
        each agent_id and the creator_user_identifier (if provided).

        Args:
            name: Channel display name.
            description: Optional channel description.
            channel_type: One of 'shared', 'dm', 'custom'.
            creator_user_identifier: User who created the channel.
            agent_ids: List of agent UUIDs to add as initial members.

        Returns:
            The created Channel instance with populated timestamps.
        """
        channel = Channel(
            name=name,
            description=description,
            channel_type=channel_type,
            creator_user_identifier=creator_user_identifier,
        )
        self.db.add(channel)
        await self.db.flush()

        # Add agents as members
        for agent_id in agent_ids or []:
            member = ChannelMember(
                channel_id=channel.id,
                agent_id=agent_id,
            )
            self.db.add(member)

        # Add creator as member
        if creator_user_identifier:
            member = ChannelMember(
                channel_id=channel.id,
                user_identifier=creator_user_identifier,
            )
            self.db.add(member)

        await self.db.commit()
        await self.db.refresh(channel)
        return channel

    async def get_or_create_general_channel(self) -> Channel:
        """Get or create the default #general shared channel.

        Queries for an existing channel named '#general' with type 'shared'.
        If not found, creates one.

        Returns:
            The #general Channel instance.
        """
        result = await self.db.execute(
            select(Channel).where(
                and_(
                    Channel.name == "#general",
                    Channel.channel_type == "shared",
                )
            )
        )
        channel = result.scalars().first()
        if channel is not None:
            return channel

        logger.info("Creating default #general channel")
        return await self.create_channel(
            name="#general",
            description="Default shared channel",
            channel_type="shared",
        )

    async def get_or_create_dm_channel(
        self,
        agent_id: str,
        user_identifier: str,
    ) -> Channel:
        """Get or create a DM channel between an agent and a user.

        Queries for an existing DM channel where both the agent and user
        are members. If not found, creates one with both as members.

        Args:
            agent_id: UUID of the agent.
            user_identifier: Identifier of the human user.

        Returns:
            The DM Channel instance.
        """
        # Find DM channels where the agent is a member
        agent_channels = (
            select(ChannelMember.channel_id)
            .where(ChannelMember.agent_id == agent_id)
            .subquery()
        )
        # Find DM channels where the user is a member
        user_channels = (
            select(ChannelMember.channel_id)
            .where(ChannelMember.user_identifier == user_identifier)
            .subquery()
        )
        # Find DM channel that has both
        result = await self.db.execute(
            select(Channel).where(
                and_(
                    Channel.channel_type == "dm",
                    Channel.id.in_(select(agent_channels.c.channel_id)),
                    Channel.id.in_(select(user_channels.c.channel_id)),
                )
            )
        )
        channel = result.scalars().first()
        if channel is not None:
            return channel

        logger.info(
            "Creating DM channel between agent '%s' and user '%s'",
            agent_id,
            user_identifier,
        )
        return await self.create_channel(
            name="DM",
            description=agent_id,  # Store agent_id for frontend DM channel mapping
            channel_type="dm",
            agent_ids=[agent_id],
            creator_user_identifier=user_identifier,
        )

    async def get_channel(self, channel_id: str) -> Channel | None:
        """Get a single channel by ID.

        Args:
            channel_id: UUID of the channel.

        Returns:
            The Channel instance, or None if not found.
        """
        return await self.db.get(Channel, channel_id)

    async def list_channels(
        self,
        user_identifier: str | None = None,
        agent_id: str | None = None,
    ) -> list[Channel]:
        """List channels, optionally filtered by membership.

        If user_identifier or agent_id is provided, returns only channels
        where they are a member. Otherwise returns all channels.

        Args:
            user_identifier: Filter to channels this user belongs to.
            agent_id: Filter to channels this agent belongs to.

        Returns:
            List of Channel instances ordered by created_at.
        """
        query = select(Channel)

        if user_identifier:
            member_channel_ids = (
                select(ChannelMember.channel_id)
                .where(ChannelMember.user_identifier == user_identifier)
                .subquery()
            )
            query = query.where(
                Channel.id.in_(select(member_channel_ids.c.channel_id))
            )
        elif agent_id:
            member_channel_ids = (
                select(ChannelMember.channel_id)
                .where(ChannelMember.agent_id == agent_id)
                .subquery()
            )
            query = query.where(
                Channel.id.in_(select(member_channel_ids.c.channel_id))
            )

        query = query.order_by(Channel.created_at.asc())

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def add_member(
        self,
        channel_id: str,
        agent_id: str | None = None,
        user_identifier: str | None = None,
    ) -> ChannelMember:
        """Add a member to a channel.

        At least one of agent_id or user_identifier must be provided.
        Checks for duplicate membership before creating.

        Args:
            channel_id: UUID of the channel.
            agent_id: UUID of the agent to add.
            user_identifier: Identifier of the user to add.

        Returns:
            The created ChannelMember instance.

        Raises:
            ValueError: If neither agent_id nor user_identifier provided,
                or if the member already exists.
        """
        if not agent_id and not user_identifier:
            raise ValueError(
                "At least one of agent_id or user_identifier must be provided"
            )

        # Check for existing membership
        conditions = [ChannelMember.channel_id == channel_id]
        if agent_id:
            conditions.append(ChannelMember.agent_id == agent_id)
        else:
            conditions.append(ChannelMember.user_identifier == user_identifier)

        result = await self.db.execute(
            select(ChannelMember).where(and_(*conditions))
        )
        existing = result.scalars().first()
        if existing is not None:
            raise ValueError("Member already exists in this channel")

        member = ChannelMember(
            channel_id=channel_id,
            agent_id=agent_id,
            user_identifier=user_identifier,
        )
        self.db.add(member)
        await self.db.commit()
        await self.db.refresh(member)
        return member

    async def remove_member(
        self,
        channel_id: str,
        agent_id: str | None = None,
        user_identifier: str | None = None,
    ) -> None:
        """Remove a member from a channel.

        Args:
            channel_id: UUID of the channel.
            agent_id: UUID of the agent to remove.
            user_identifier: Identifier of the user to remove.

        Raises:
            ValueError: If the member is not found.
        """
        conditions = [ChannelMember.channel_id == channel_id]
        if agent_id:
            conditions.append(ChannelMember.agent_id == agent_id)
        else:
            conditions.append(ChannelMember.user_identifier == user_identifier)

        result = await self.db.execute(
            select(ChannelMember).where(and_(*conditions))
        )
        member = result.scalars().first()
        if member is None:
            raise ValueError("Member not found in this channel")

        await self.db.delete(member)
        await self.db.commit()

    async def get_channel_members(self, channel_id: str) -> list[ChannelMember]:
        """Get all members of a channel.

        Args:
            channel_id: UUID of the channel.

        Returns:
            List of ChannelMember instances.
        """
        result = await self.db.execute(
            select(ChannelMember).where(ChannelMember.channel_id == channel_id)
        )
        return list(result.scalars().all())

    async def get_channel_agent_ids(self, channel_id: str) -> list[str]:
        """Get agent IDs for all agent members in a channel.

        Returns only non-None agent_ids, excluding human members.
        Used by CommunicationService for @mention routing.

        Args:
            channel_id: UUID of the channel.

        Returns:
            List of agent UUID strings.
        """
        result = await self.db.execute(
            select(ChannelMember.agent_id).where(
                and_(
                    ChannelMember.channel_id == channel_id,
                    ChannelMember.agent_id.is_not(None),
                )
            )
        )
        return list(result.scalars().all())
