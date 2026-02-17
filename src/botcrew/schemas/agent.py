"""Pydantic v2 schemas for agent CRUD operations.

Defines request/response models for agent creation, updates, listing,
detail views, and memory sub-resource operations.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

# CONTEXT decision: model_provider and model_name are required at creation time.
# AGENT-01's "just a name" is overridden by explicit user decision to require model selection.
# The DB retains server_defaults for safety, but the API schema enforces explicit choice.


class CreateAgentRequest(BaseModel):
    """Request body for creating a new agent."""

    name: str = Field(..., min_length=1, max_length=100)
    model_provider: Literal["openai", "anthropic", "ollama", "glm"] = Field(...)
    model_name: str = Field(..., min_length=1, max_length=100)
    identity: str | None = None
    personality: str | None = None
    heartbeat_interval_seconds: int = Field(default=300, ge=10, le=86400)


class UpdateAgentRequest(BaseModel):
    """Request body for updating an existing agent. All fields optional."""

    name: str | None = Field(default=None, min_length=1, max_length=100)
    identity: str | None = None
    personality: str | None = None
    heartbeat_prompt: str | None = None
    heartbeat_interval_seconds: int | None = Field(default=None, ge=10, le=86400)
    heartbeat_enabled: bool | None = None
    model_provider: Literal["openai", "anthropic", "ollama", "glm"] | None = None
    model_name: str | None = Field(default=None, min_length=1, max_length=100)


class AgentSummaryAttributes(BaseModel):
    """Attributes returned in agent list responses."""

    name: str
    status: str
    model_provider: str
    model_name: str
    heartbeat_interval_seconds: int
    created_at: datetime
    updated_at: datetime


class AgentDetailAttributes(AgentSummaryAttributes):
    """Full attributes returned in agent detail responses."""

    identity: str
    personality: str
    heartbeat_prompt: str
    heartbeat_enabled: bool
    avatar_url: str | None
    pod_name: str | None
    memory: str


class MemoryUpdateRequest(BaseModel):
    """Request body for full memory replacement (PUT)."""

    content: str


class MemoryPatchRequest(BaseModel):
    """Request body for partial memory update (PATCH)."""

    append: str | None = None
    content: str | None = None
