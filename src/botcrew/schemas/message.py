"""Pydantic v2 schemas for message operations.

Defines request/response models for sending messages, message attributes,
WebSocket message format, and WebSocket send payload validation.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class SendMessageRequest(BaseModel):
    """Request body for sending a message to a channel."""

    content: str = Field(..., min_length=1)
    message_type: str = Field(default="chat", pattern="^(chat|system|dm)$")


class MessageAttributes(BaseModel):
    """Attributes returned in message responses.

    The metadata field uses an alias because the SQLAlchemy model maps
    the Python attribute ``metadata_`` to the SQL column ``metadata``
    to avoid shadowing SQLAlchemy's internal ``.metadata`` attribute.
    """

    model_config = ConfigDict(populate_by_name=True)

    content: str
    message_type: str
    sender_agent_id: str | None
    sender_user_identifier: str | None
    channel_id: str
    metadata_: dict | None = Field(default=None, alias="metadata")
    created_at: datetime
    updated_at: datetime


class WebSocketMessage(BaseModel):
    """Message format for WebSocket broadcast to connected clients."""

    type: str  # "message", "join", "leave"
    id: str | None = None  # message ID if type=message
    channel_id: str
    sender_type: str | None = None  # "user" or "agent"
    sender_id: str | None = None
    content: str | None = None
    message_type: str | None = None  # "chat", "system", "dm"
    created_at: datetime | None = None


class WebSocketSendPayload(BaseModel):
    """Validated payload received from WebSocket clients for sending messages."""

    type: str = Field(default="message", pattern="^(message)$")
    content: str = Field(..., min_length=1)
    message_type: str = Field(default="chat", pattern="^(chat|system)$")
