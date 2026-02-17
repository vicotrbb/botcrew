"""Pydantic v2 schemas for skills CRUD API.

Defines request schemas for creating and updating skills. Response data
uses the generic JSONAPIResource type with skill attributes mapped inline
(same pattern as agents).
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class CreateSkillRequest(BaseModel):
    """Request body for creating a new skill.

    The ``name`` field is stripped and lowercased by the service layer
    before persistence.
    """

    name: str = Field(..., max_length=100)
    description: str = Field(..., max_length=250)
    body: str


class UpdateSkillRequest(BaseModel):
    """Partial update request for an existing skill.

    All fields are optional -- only provided (non-None) fields are applied.
    The ``name`` field is lowercased by the service layer if provided.
    """

    name: str | None = Field(default=None, max_length=100)
    description: str | None = Field(default=None, max_length=250)
    body: str | None = None
