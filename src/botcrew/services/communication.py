"""Unified message routing with transport abstraction.

CommunicationService orchestrates persist-then-route for every message.
TransportAdapter ABC enables future transport implementations.
NativeTransport publishes directly to Redis pub/sub for channel broadcast
(fast path, no Celery) and uses Celery only for DM delivery to agent
containers (reliable path with retries).
"""

from __future__ import annotations

import json
import logging
import re
from abc import ABC, abstractmethod

import redis.asyncio

from botcrew.models.agent import Agent
from botcrew.models.message import Message
from botcrew.services.channel_service import ChannelService
from botcrew.services.message_service import MessageService

logger = logging.getLogger(__name__)

# @mention regex -- matches word characters and hyphens (e.g. @test-agent)
_MENTION_PATTERN = re.compile(r"@([\w-]+)")


class TransportAdapter(ABC):
    """Base interface for message delivery transports.

    Each transport implements channel broadcast and agent DM delivery
    using its own underlying infrastructure.
    """

    @abstractmethod
    async def deliver_to_channel(self, channel_id: str, message: dict) -> None:
        """Deliver a message to all subscribers of a channel.

        Args:
            channel_id: UUID string of the target channel.
            message: Serialized message dict for WebSocket broadcast.
        """
        ...

    @abstractmethod
    async def deliver_to_agent(self, agent_id: str, message: dict) -> None:
        """Deliver a direct message to an agent container.

        Args:
            agent_id: UUID string of the target agent.
            message: Serialized message dict with content and sender info.
        """
        ...


class NativeTransport(TransportAdapter):
    """Native transport using Redis pub/sub (channel broadcast) and Celery (DM delivery).

    Channel broadcast goes DIRECTLY to Redis pub/sub -- no Celery worker in
    the path. This is the fast path: FastAPI -> Redis pub/sub -> PubSubManager
    listener -> ConnectionManager -> WebSocket clients.  Meets the <500ms
    latency requirement.

    DM delivery to agent containers uses Celery because agents may be booting,
    restarting, or temporarily unreachable.  Celery provides reliable retries
    with exponential backoff (max 3 retries, up to 60s backoff).

    Args:
        redis: The app's async Redis connection (same as app.state.redis).
            Publishing is a regular command, not a blocking operation, so
            sharing the connection is safe (unlike PubSubManager which needs
            a dedicated connection for subscribing).
    """

    def __init__(self, redis: redis.asyncio.Redis) -> None:
        self._redis = redis

    async def deliver_to_channel(self, channel_id: str, message: dict) -> None:
        """Publish directly to Redis pub/sub for WebSocket fan-out.

        Uses the ws:channel:{channel_id} topic that PubSubManager subscribes to.
        No Celery hop -- direct publish for minimum latency.
        """
        await self._redis.publish(
            f"ws:channel:{channel_id}", json.dumps(message)
        )

    async def deliver_to_agent(self, agent_id: str, message: dict) -> None:
        """Dispatch DM delivery to agent via Celery task with retries.

        Lazy import avoids circular dependency between Celery and FastAPI modules.
        """
        from botcrew.tasks.messaging import deliver_dm_to_agent

        deliver_dm_to_agent.delay(str(agent_id), message)


class CommunicationService:
    """Central hub for all message routing in the communication system.

    Every message -- whether from a user via WebSocket, an agent via REST,
    or a DM -- flows through CommunicationService.  It persists to DB first
    (source of truth), then routes via the injected transport adapter.

    Follows the hub-and-spoke pattern: all message routing goes through the
    orchestrator; agents never talk to each other directly.

    Args:
        message_service: For message persistence (DB source of truth).
        channel_service: For channel/membership queries and DM channel creation.
        transport: Injected transport adapter (NativeTransport or test mock).
    """

    def __init__(
        self,
        message_service: MessageService,
        channel_service: ChannelService,
        transport: TransportAdapter,
    ) -> None:
        self._message_service = message_service
        self._channel_service = channel_service
        self._transport = transport

    async def send_channel_message(
        self,
        channel_id: str,
        content: str,
        sender_user_identifier: str | None = None,
        sender_agent_id: str | None = None,
        message_type: str = "chat",
        metadata_: dict | None = None,
    ) -> Message:
        """Send a message to a channel: persist, broadcast, handle @mentions.

        1. Persist to DB (source of truth -- always written first)
        2. Broadcast to channel via transport (WebSocket fan-out)
        3. Parse @mentions and deliver to mentioned agents via transport

        Args:
            channel_id: UUID of the target channel.
            content: Message text content.
            sender_user_identifier: Identifier of the sending user (if human).
            sender_agent_id: UUID of the sending agent (if agent).
            message_type: One of 'chat', 'system', 'dm'.
            metadata_: Optional JSON metadata.

        Returns:
            The persisted Message instance.
        """
        # 1. Persist -- DB is always written first
        msg = await self._message_service.create_message(
            channel_id=channel_id,
            content=content,
            message_type=message_type,
            sender_agent_id=sender_agent_id,
            sender_user_identifier=sender_user_identifier,
            metadata_=metadata_,
        )

        # 2. Build WebSocket message payload
        sender_type = "user" if sender_user_identifier else "agent"
        sender_id = sender_user_identifier or sender_agent_id
        ws_msg: dict = {
            "type": "message",
            "id": str(msg.id),
            "channel_id": channel_id,
            "sender_type": sender_type,
            "sender_id": sender_id,
            "content": content,
            "message_type": message_type,
            "created_at": msg.created_at.isoformat(),
        }

        # 3. Broadcast to channel (direct Redis pub/sub -- no Celery)
        await self._transport.deliver_to_channel(channel_id, ws_msg)

        # 4. Handle @mentions -- deliver to mentioned agents
        mentioned_agent_ids = await self._handle_mentions(
            channel_id=channel_id,
            content=content,
            sender_type=sender_type,
            sender_id=sender_id,
            message_id=str(msg.id),
        )

        # 5. Instant reply evaluation -- ONLY for user messages (bot-loop prevention)
        if sender_user_identifier and not sender_agent_id:
            await self._handle_instant_replies(
                channel_id=channel_id,
                content=content,
                message_id=str(msg.id),
                sender_user_identifier=sender_user_identifier,
                exclude_agent_ids=mentioned_agent_ids,
            )

        return msg

    async def send_direct_message(
        self,
        agent_id: str,
        content: str,
        sender_user_identifier: str | None = None,
        sender_agent_id: str | None = None,
    ) -> Message:
        """Send a direct message to an agent: persist, broadcast, deliver.

        1. Get or create DM channel between sender and agent
        2. Persist message in the DM channel
        3. Broadcast to DM channel (so WebSocket clients see it)
        4. Deliver to agent container (triggers agent processing)

        Args:
            agent_id: UUID of the target agent.
            content: Message text content.
            sender_user_identifier: Identifier of the sending user (if human).
            sender_agent_id: UUID of the sending agent (if agent-to-agent DM).

        Returns:
            The persisted Message instance.
        """
        # 1. Get or create DM channel
        if sender_user_identifier:
            dm_channel = await self._channel_service.get_or_create_dm_channel(
                agent_id=agent_id,
                user_identifier=sender_user_identifier,
            )
        else:
            # Agent-to-agent DM -- create a DM channel with both agents
            # For now, use the sender agent's ID as the user_identifier
            # since get_or_create_dm_channel expects a user_identifier.
            # This is a simplification; agent-to-agent DMs will be refined later.
            dm_channel = await self._channel_service.get_or_create_dm_channel(
                agent_id=agent_id,
                user_identifier=str(sender_agent_id) if sender_agent_id else "system",
            )

        # 2. Persist message in DM channel
        msg = await self._message_service.create_message(
            channel_id=str(dm_channel.id),
            content=content,
            message_type="dm",
            sender_agent_id=sender_agent_id,
            sender_user_identifier=sender_user_identifier,
        )

        # 3. Build WebSocket message payload and broadcast to DM channel
        sender_type = "user" if sender_user_identifier else "agent"
        sender_id = sender_user_identifier or sender_agent_id
        ws_msg: dict = {
            "type": "message",
            "id": str(msg.id),
            "channel_id": str(dm_channel.id),
            "sender_type": sender_type,
            "sender_id": sender_id,
            "content": content,
            "message_type": "dm",
            "created_at": msg.created_at.isoformat(),
        }
        await self._transport.deliver_to_channel(str(dm_channel.id), ws_msg)

        # 4. Deliver to agent container (triggers agent processing)
        dm_payload: dict = {
            "content": content,
            "sender_type": sender_type,
            "sender_id": sender_id,
            "message_id": str(msg.id),
        }
        await self._transport.deliver_to_agent(agent_id, dm_payload)

        return msg

    async def send_system_message(
        self,
        channel_id: str,
        content: str,
    ) -> Message:
        """Send a system message to a channel (no sender).

        Used for join/leave notifications, channel events, etc.
        Persists to DB and broadcasts to channel subscribers.

        Args:
            channel_id: UUID of the target channel.
            content: System message text.

        Returns:
            The persisted Message instance.
        """
        # Persist system message (no sender)
        msg = await self._message_service.create_message(
            channel_id=channel_id,
            content=content,
            message_type="system",
        )

        # Build WebSocket payload and broadcast
        ws_msg: dict = {
            "type": "message",
            "id": str(msg.id),
            "channel_id": channel_id,
            "sender_type": "system",
            "sender_id": None,
            "content": content,
            "message_type": "system",
            "created_at": msg.created_at.isoformat(),
        }
        await self._transport.deliver_to_channel(channel_id, ws_msg)

        return msg

    async def _handle_mentions(
        self,
        channel_id: str,
        content: str,
        sender_type: str,
        sender_id: str | None,
        message_id: str,
    ) -> set[str]:
        """Parse @mentions in message content and deliver to mentioned agents.

        Uses a simple regex to find @name patterns, then queries channel
        agent members to match by name. Intentionally simple -- can be
        enhanced later with fuzzy matching or agent display name indexing.

        Args:
            channel_id: UUID of the channel the message was sent in.
            content: Message text to parse for @mentions.
            sender_type: 'user' or 'agent'.
            sender_id: Identifier of the message sender.
            message_id: UUID of the persisted message.

        Returns:
            Set of agent ID strings that were dispatched via @mention delivery.
        """
        mentioned_agent_ids: set[str] = set()
        mentioned_names = _MENTION_PATTERN.findall(content)
        if not mentioned_names:
            return mentioned_agent_ids

        # Get all agent IDs in this channel
        agent_ids = await self._channel_service.get_channel_agent_ids(channel_id)
        if not agent_ids:
            return mentioned_agent_ids

        # Query agents by ID to match names against mentions
        from sqlalchemy import select
        from sqlalchemy.ext.asyncio import AsyncSession

        db: AsyncSession = self._channel_service.db
        result = await db.execute(
            select(Agent).where(Agent.id.in_(agent_ids))
        )
        channel_agents = result.scalars().all()

        # Match mentioned names to channel agents (case-insensitive)
        mentioned_names_lower = {name.lower() for name in mentioned_names}
        dm_payload: dict = {
            "content": content,
            "sender_type": sender_type,
            "sender_id": sender_id,
            "message_id": message_id,
            "reply_channel_id": channel_id,
        }

        for agent in channel_agents:
            # Match against agent name variations (hyphens, underscores, spaces)
            name_lower = agent.name.lower()
            name_underscored = name_lower.replace(" ", "_").replace("-", "_")
            name_hyphenated = name_lower.replace(" ", "-")
            if (
                name_lower in mentioned_names_lower
                or name_underscored in mentioned_names_lower
                or name_hyphenated in mentioned_names_lower
            ):
                logger.info(
                    "Delivering @mention to agent '%s' (%s) in channel %s",
                    agent.name,
                    agent.id,
                    channel_id,
                )
                await self._transport.deliver_to_agent(str(agent.id), dm_payload)
                mentioned_agent_ids.add(str(agent.id))

        return mentioned_agent_ids

    async def _handle_instant_replies(
        self,
        channel_id: str,
        content: str,
        message_id: str,
        sender_user_identifier: str,
        exclude_agent_ids: set[str] | None = None,
    ) -> None:
        """Dispatch instant reply evaluation to all agents in the channel.

        Each agent receives a Celery task to evaluate relevance and optionally
        respond. Agents already dispatched via @mentions are excluded to prevent
        duplicate responses.

        Args:
            channel_id: UUID of the channel.
            content: Message text content.
            message_id: UUID of the persisted message.
            sender_user_identifier: Identifier of the sending user.
            exclude_agent_ids: Agent IDs to skip (already dispatched via @mentions).
        """
        from botcrew.tasks.messaging import evaluate_instant_reply

        agent_ids = await self._channel_service.get_channel_agent_ids(channel_id)
        exclude = exclude_agent_ids or set()

        # Determine if this is a DM channel (agent always responds in DMs)
        channel = await self._channel_service.get_channel(channel_id)
        is_dm = channel is not None and channel.channel_type == "dm"

        for agent_id in agent_ids:
            if agent_id in exclude:
                continue
            evaluate_instant_reply.delay(
                agent_id=agent_id,
                channel_id=channel_id,
                message_content=content,
                message_id=message_id,
                sender_user_identifier=sender_user_identifier,
                is_dm=is_dm,
            )
