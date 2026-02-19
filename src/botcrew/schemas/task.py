"""Pydantic v2 schemas for tasks CRUD API.

Defines request schemas for creating, updating, and assigning agents,
secrets, and skills to tasks. Response data uses the generic
JSONAPIResource type with task attributes mapped inline (same pattern
as projects).
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class CreateTaskRequest(BaseModel):
    """Request body for creating a new task.

    ``name`` and ``directive`` are required. ``description`` is optional
    and can be set later via PATCH.
    """

    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = None
    directive: str = Field(..., min_length=1)


class UpdateTaskRequest(BaseModel):
    """Partial update request for an existing task.

    All fields are optional -- only provided (non-None) fields are applied.
    """

    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = None
    directive: str | None = None
    status: str | None = Field(default=None, pattern="^(open|done)$")
    notes: str | None = None


class AssignAgentRequest(BaseModel):
    """Request body for assigning an agent to a task."""

    agent_id: str


class AssignSecretRequest(BaseModel):
    """Request body for assigning a secret to a task."""

    secret_id: str


class AssignSkillRequest(BaseModel):
    """Request body for assigning a skill to a task."""

    skill_id: str
