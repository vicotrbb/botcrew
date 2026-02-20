"""Channel REST endpoints for CRUD, membership, messaging, and unread retrieval.

Provides the full REST API surface for the communication system:
- Channel CRUD (create, list, get, update, delete)
- Membership management (add, remove, list members)
- Message history with cursor-based pagination
- REST message sending (used by agents posting to channels)
- Unread message retrieval (COMM-04 infrastructure for heartbeat)
- Read cursor updates
- Direct message sending to agents

All endpoints follow JSON:API envelope format and existing DI patterns.
WebSocket endpoints are handled separately in Plan 08.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from botcrew.api.deps import get_communication_service, get_db
from botcrew.models.channel import Channel, ChannelMember
from botcrew.models.message import Message
from botcrew.models.read_cursor import ReadCursor
from botcrew.schemas.channel import (
    AddMemberRequest,
    CreateChannelRequest,
    UpdateChannelRequest,
)
from botcrew.schemas.jsonapi import (
    JSONAPIListResponse,
    JSONAPIRequest,
    JSONAPIResource,
    JSONAPISingleResponse,
)
from botcrew.schemas.message import SendMessageRequest
from botcrew.schemas.pagination import PaginationLinks, PaginationMeta, encode_cursor
from botcrew.services.channel_service import ChannelService
from botcrew.services.communication import CommunicationService
from botcrew.services.message_service import MessageService

router = APIRouter()


# ---------------------------------------------------------------------------
# Attribute mapping helpers
# ---------------------------------------------------------------------------


def _channel_to_attrs(channel: Channel) -> dict:
    """Map a Channel model to JSON:API attributes."""
    return {
        "name": channel.name,
        "description": channel.description,
        "channel_type": channel.channel_type,
        "creator_user_identifier": channel.creator_user_identifier,
        "created_at": channel.created_at.isoformat(),
        "updated_at": channel.updated_at.isoformat(),
    }


def _channel_resource(channel: Channel) -> JSONAPIResource:
    """Build a JSON:API resource from a Channel."""
    return JSONAPIResource(
        type="channels",
        id=str(channel.id),
        attributes=_channel_to_attrs(channel),
    )


def _member_to_attrs(member: ChannelMember) -> dict:
    """Map a ChannelMember model to JSON:API attributes."""
    return {
        "channel_id": str(member.channel_id),
        "agent_id": str(member.agent_id) if member.agent_id else None,
        "user_identifier": member.user_identifier,
        "created_at": member.created_at.isoformat(),
    }


def _member_resource(member: ChannelMember) -> JSONAPIResource:
    """Build a JSON:API resource from a ChannelMember."""
    return JSONAPIResource(
        type="channel-members",
        id=str(member.id),
        attributes=_member_to_attrs(member),
    )


def _message_to_attrs(message: Message) -> dict:
    """Map a Message model to JSON:API attributes."""
    return {
        "content": message.content,
        "message_type": message.message_type,
        "sender_agent_id": str(message.sender_agent_id) if message.sender_agent_id else None,
        "sender_user_identifier": message.sender_user_identifier,
        "channel_id": str(message.channel_id),
        "metadata": message.metadata_,
        "created_at": message.created_at.isoformat(),
        "updated_at": message.updated_at.isoformat(),
    }


def _message_resource(message: Message) -> JSONAPIResource:
    """Build a JSON:API resource from a Message."""
    return JSONAPIResource(
        type="messages",
        id=str(message.id),
        attributes=_message_to_attrs(message),
    )


def _read_cursor_to_attrs(cursor: ReadCursor) -> dict:
    """Map a ReadCursor model to JSON:API attributes."""
    return {
        "channel_id": str(cursor.channel_id),
        "agent_id": str(cursor.agent_id) if cursor.agent_id else None,
        "user_identifier": cursor.user_identifier,
        "last_read_message_id": str(cursor.last_read_message_id) if cursor.last_read_message_id else None,
        "last_read_at": cursor.last_read_at.isoformat() if cursor.last_read_at else None,
    }


def _read_cursor_resource(cursor: ReadCursor) -> JSONAPIResource:
    """Build a JSON:API resource from a ReadCursor."""
    return JSONAPIResource(
        type="read-cursors",
        id=str(cursor.id),
        attributes=_read_cursor_to_attrs(cursor),
    )


# ---------------------------------------------------------------------------
# Channel CRUD
# ---------------------------------------------------------------------------


@router.post("", status_code=201)
async def create_channel(
    body: JSONAPIRequest[CreateChannelRequest],
    db: AsyncSession = Depends(get_db),
) -> JSONAPISingleResponse:
    """Create a new channel with optional initial members."""
    attrs = body.data.attributes
    service = ChannelService(db)
    channel = await service.create_channel(
        name=attrs.name,
        description=attrs.description,
        channel_type=attrs.channel_type,
        creator_user_identifier=attrs.creator_user_identifier,
        agent_ids=attrs.agent_ids,
    )
    return JSONAPISingleResponse(data=_channel_resource(channel))


@router.get("")
async def list_channels(
    user_identifier: str | None = Query(default=None),
    agent_id: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> JSONAPIListResponse:
    """List channels, optionally filtered by membership."""
    service = ChannelService(db)
    channels = await service.list_channels(
        user_identifier=user_identifier,
        agent_id=agent_id,
    )
    return JSONAPIListResponse(
        data=[_channel_resource(c) for c in channels],
    )


@router.get("/{channel_id}")
async def get_channel(
    channel_id: str,
    db: AsyncSession = Depends(get_db),
) -> JSONAPISingleResponse:
    """Get a single channel by ID."""
    service = ChannelService(db)
    channel = await service.get_channel(channel_id)
    if channel is None:
        raise HTTPException(status_code=404, detail="Channel not found")
    return JSONAPISingleResponse(data=_channel_resource(channel))


@router.patch("/{channel_id}")
async def update_channel(
    channel_id: str,
    body: JSONAPIRequest[UpdateChannelRequest],
    db: AsyncSession = Depends(get_db),
) -> JSONAPISingleResponse:
    """Update a channel's name or description."""
    attrs = body.data.attributes
    service = ChannelService(db)
    channel = await service.get_channel(channel_id)
    if channel is None:
        raise HTTPException(status_code=404, detail="Channel not found")

    update_data = attrs.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(channel, field, value)

    await db.commit()
    await db.refresh(channel)
    return JSONAPISingleResponse(data=_channel_resource(channel))


@router.delete("/{channel_id}", status_code=204)
async def delete_channel(
    channel_id: str,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a channel."""
    service = ChannelService(db)
    channel = await service.get_channel(channel_id)
    if channel is None:
        raise HTTPException(status_code=404, detail="Channel not found")

    await db.delete(channel)
    await db.commit()


# ---------------------------------------------------------------------------
# Membership management
# ---------------------------------------------------------------------------


@router.post("/{channel_id}/members", status_code=201)
async def add_member(
    channel_id: str,
    body: JSONAPIRequest[AddMemberRequest],
    db: AsyncSession = Depends(get_db),
) -> JSONAPISingleResponse:
    """Add a member (agent or user) to a channel."""
    attrs = body.data.attributes
    service = ChannelService(db)

    # Verify channel exists
    channel = await service.get_channel(channel_id)
    if channel is None:
        raise HTTPException(status_code=404, detail="Channel not found")

    try:
        member = await service.add_member(
            channel_id=channel_id,
            agent_id=attrs.agent_id,
            user_identifier=attrs.user_identifier,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return JSONAPISingleResponse(data=_member_resource(member))


@router.delete("/{channel_id}/members", status_code=204)
async def remove_member(
    channel_id: str,
    body: JSONAPIRequest[AddMemberRequest],
    db: AsyncSession = Depends(get_db),
) -> None:
    """Remove a member from a channel."""
    attrs = body.data.attributes
    service = ChannelService(db)
    try:
        await service.remove_member(
            channel_id=channel_id,
            agent_id=attrs.agent_id,
            user_identifier=attrs.user_identifier,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{channel_id}/members")
async def list_members(
    channel_id: str,
    db: AsyncSession = Depends(get_db),
) -> JSONAPIListResponse:
    """List all members of a channel."""
    service = ChannelService(db)
    members = await service.get_channel_members(channel_id)
    return JSONAPIListResponse(
        data=[_member_resource(m) for m in members],
    )


# ---------------------------------------------------------------------------
# Message history and sending
# ---------------------------------------------------------------------------


@router.get("/{channel_id}/messages")
async def get_message_history(
    channel_id: str,
    page_size: int = Query(default=50, ge=1, le=200),
    before: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> JSONAPIListResponse:
    """Get paginated message history for a channel (newest first)."""
    service = MessageService(db)
    messages, pagination_meta = await service.get_message_history(
        channel_id=channel_id,
        page_size=page_size,
        before=before,
    )

    # Build pagination links
    links = PaginationLinks(first=f"?page_size={page_size}")

    if pagination_meta.has_next and messages:
        oldest_msg = messages[-1]
        next_cursor = encode_cursor(oldest_msg.created_at, str(oldest_msg.id))
        links.next = f"?page_size={page_size}&before={next_cursor}"

    return JSONAPIListResponse(
        data=[_message_resource(m) for m in messages],
        meta=pagination_meta.model_dump(),
        links=links.model_dump(exclude_none=True),
    )


@router.post("/{channel_id}/messages", status_code=201)
async def send_channel_message(
    channel_id: str,
    body: JSONAPIRequest[SendMessageRequest],
    sender_agent_id: str | None = Query(default=None),
    sender_user_identifier: str | None = Query(default=None),
    comm_service: CommunicationService = Depends(get_communication_service),
) -> JSONAPISingleResponse:
    """Send a message to a channel via REST (used by agents posting to channels)."""
    attrs = body.data.attributes
    if not sender_agent_id and not sender_user_identifier:
        raise HTTPException(
            status_code=422,
            detail="One of sender_agent_id or sender_user_identifier query params is required",
        )

    msg = await comm_service.send_channel_message(
        channel_id=channel_id,
        content=attrs.content,
        sender_agent_id=sender_agent_id,
        sender_user_identifier=sender_user_identifier,
        message_type=attrs.message_type,
    )
    return JSONAPISingleResponse(data=_message_resource(msg))


# ---------------------------------------------------------------------------
# Unread messages (COMM-04 infrastructure)
# ---------------------------------------------------------------------------


@router.get("/{channel_id}/messages/unread")
async def get_unread_messages(
    channel_id: str,
    response: Response,
    agent_id: str | None = Query(default=None),
    user_identifier: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> JSONAPIListResponse:
    """Get unread messages for an agent or user in a channel.

    This is the endpoint agents use during heartbeat cycles to check
    shared rooms for new messages (COMM-04 infrastructure).

    Returns unread messages ordered by created_at ASC (oldest first)
    and includes X-Unread-Count header for convenience.
    """
    if not agent_id and not user_identifier:
        raise HTTPException(
            status_code=422,
            detail="One of agent_id or user_identifier query params is required",
        )

    service = MessageService(db)
    messages = await service.get_unread_messages(
        channel_id=channel_id,
        agent_id=agent_id,
        user_identifier=user_identifier,
    )

    unread_count = await service.get_unread_count(
        channel_id=channel_id,
        agent_id=agent_id,
        user_identifier=user_identifier,
    )

    response.headers["X-Unread-Count"] = str(unread_count)

    return JSONAPIListResponse(
        data=[_message_resource(m) for m in messages],
        meta={"unread_count": unread_count},
    )


@router.post("/{channel_id}/messages/read")
async def mark_messages_read(
    channel_id: str,
    last_read_message_id: str = Query(...),
    agent_id: str | None = Query(default=None),
    user_identifier: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> JSONAPISingleResponse:
    """Mark messages as read by updating the read cursor.

    Updates the read cursor position for a given agent or user in a
    channel. Subsequent unread queries will only return messages
    created after this cursor.
    """
    if not agent_id and not user_identifier:
        raise HTTPException(
            status_code=422,
            detail="One of agent_id or user_identifier query params is required",
        )

    service = MessageService(db)
    cursor = await service.update_read_cursor(
        channel_id=channel_id,
        last_read_message_id=last_read_message_id,
        agent_id=agent_id,
        user_identifier=user_identifier,
    )
    return JSONAPISingleResponse(data=_read_cursor_resource(cursor))


# ---------------------------------------------------------------------------
# Direct messages
# ---------------------------------------------------------------------------


@router.post("/dm-channel/{agent_id}")
async def get_or_create_dm_channel(
    agent_id: str,
    user_identifier: str = Query(default="user"),
    db: AsyncSession = Depends(get_db),
) -> JSONAPISingleResponse:
    """Get or create a DM channel between the current user and an agent.

    Returns an existing DM channel if one exists, or creates a new one.
    Used by the frontend DM section for lazy channel creation on first click.
    """
    service = ChannelService(db)
    channel = await service.get_or_create_dm_channel(
        agent_id=agent_id,
        user_identifier=user_identifier,
    )
    return JSONAPISingleResponse(data=_channel_resource(channel))


@router.post("/dm/{agent_id}", status_code=202)
async def send_direct_message(
    agent_id: str,
    body: JSONAPIRequest[SendMessageRequest],
    sender_user_identifier: str | None = Query(default=None),
    comm_service: CommunicationService = Depends(get_communication_service),
) -> JSONAPISingleResponse:
    """Send a direct message to an agent (async delivery, returns 202)."""
    attrs = body.data.attributes
    msg = await comm_service.send_direct_message(
        agent_id=agent_id,
        content=attrs.content,
        sender_user_identifier=sender_user_identifier,
    )
    return JSONAPISingleResponse(data=_message_resource(msg))
