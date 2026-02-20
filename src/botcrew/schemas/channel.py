"""Pydantic v2 schemas for channel CRUD operations.

Defines request/response models for channel creation, updates,
membership management, and channel attribute serialization.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class CreateChannelRequest(BaseModel):
    """Request body for creating a new channel."""

    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = None
    channel_type: str = Field(default="shared", pattern="^(shared|dm|custom|project|task)$")
    agent_ids: list[str] = Field(default_factory=list)
    creator_user_identifier: str | None = None


class UpdateChannelRequest(BaseModel):
    """Request body for updating an existing channel. All fields optional."""

    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = None


class AddMemberRequest(BaseModel):
    """Request body for adding a member to a channel.

    At least one of agent_id or user_identifier must be provided.
    Validation is performed in the service layer, not the schema.
    """

    agent_id: str | None = None
    user_identifier: str | None = None


class ChannelAttributes(BaseModel):
    """Attributes returned in channel responses."""

    name: str
    description: str | None
    channel_type: str
    creator_user_identifier: str | None
    created_at: datetime
    updated_at: datetime


class ChannelMemberAttributes(BaseModel):
    """Attributes returned in channel member responses."""

    channel_id: str
    agent_id: str | None
    user_identifier: str | None
    created_at: datetime
