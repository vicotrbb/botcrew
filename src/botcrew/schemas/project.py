"""Pydantic v2 schemas for projects CRUD API.

Defines request schemas for creating, updating, and assigning agents to
projects. The ``ProjectAssignment`` model is used by the internal
boot-config endpoint to convey project context to agent containers.
Response data uses the generic JSONAPIResource type with project attributes
mapped inline (same pattern as agents and skills).
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class CreateProjectRequest(BaseModel):
    """Request body for creating a new project.

    ``name`` is the only required field.  All others are optional and can
    be set later via PATCH.
    """

    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = None
    goals: str | None = None
    github_repo_url: str | None = None


class UpdateProjectRequest(BaseModel):
    """Partial update request for an existing project.

    All fields are optional -- only provided (non-None) fields are applied.
    """

    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = None
    goals: str | None = None
    specs: str | None = None
    github_repo_url: str | None = None


class AssignAgentRequest(BaseModel):
    """Request body for assigning an agent to a project."""

    agent_id: str
    role_prompt: str | None = None


class AssignSecretRequest(BaseModel):
    """Request body for assigning a secret to a project."""

    secret_id: str


class ProjectAssignment(BaseModel):
    """Project assignment info included in agent boot-config.

    Returned by the internal ``/agents/{id}/projects`` endpoint so the
    agent container knows which projects it belongs to, their goals/specs,
    its per-project role prompt, and the workspace path for file access.
    """

    project_id: str
    project_name: str
    goals: str | None = None
    specs: str | None = None
    role_prompt: str | None = None
    workspace_path: str
    channel_id: str | None = None
