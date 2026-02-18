"""Pydantic v2 schemas for integrations CRUD API.

Defines request schemas for creating and updating integrations. Response
data uses the generic JSONAPIResource type with integration attributes
mapped inline (same pattern as skills).
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class CreateIntegrationRequest(BaseModel):
    """Request body for creating a new integration.

    The ``config`` field stores a JSON string with provider-specific
    configuration for the integration.
    """

    name: str = Field(..., max_length=100)
    integration_type: str = Field(..., max_length=50)
    config: str
    agent_id: str | None = None
    channel_id: str | None = None


class UpdateIntegrationRequest(BaseModel):
    """Partial update request for an existing integration.

    All fields are optional -- only provided (non-None) fields are applied.
    """

    name: str | None = Field(default=None, max_length=100)
    integration_type: str | None = Field(default=None, max_length=50)
    config: str | None = None
    agent_id: str | None = None
    channel_id: str | None = None
    is_active: bool | None = None
