"""Pydantic v2 schemas for secrets CRUD API.

Defines request schemas for creating and updating secrets. Response data
uses the generic JSONAPIResource type with secret attributes mapped inline
(same pattern as skills).
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class CreateSecretRequest(BaseModel):
    """Request body for creating a new secret.

    The ``key`` field uniquely identifies the secret and the ``value``
    holds the sensitive data.
    """

    key: str = Field(..., max_length=255)
    value: str
    description: str | None = None


class UpdateSecretRequest(BaseModel):
    """Partial update request for an existing secret.

    All fields are optional -- only provided (non-None) fields are applied.
    """

    key: str | None = Field(default=None, max_length=255)
    value: str | None = None
    description: str | None = None
