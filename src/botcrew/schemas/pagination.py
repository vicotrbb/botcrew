"""Cursor-based pagination utilities and models.

Provides encoding/decoding of opaque cursors for JSON:API-style
pagination, plus Pydantic models for pagination metadata and links.
"""

from __future__ import annotations

import base64
import json
from datetime import datetime

from pydantic import BaseModel


class PaginationMeta(BaseModel):
    """Pagination metadata for JSON:API list responses."""

    has_next: bool
    has_prev: bool
    total: int | None = None


class PaginationLinks(BaseModel):
    """Pagination links for JSON:API list responses."""

    first: str
    last: str | None = None
    next: str | None = None
    prev: str | None = None


def encode_cursor(created_at: datetime, id: str) -> str:
    """Encode a pagination cursor from a created_at timestamp and resource id.

    Args:
        created_at: The created_at timestamp of the boundary resource.
        id: The UUID of the boundary resource.

    Returns:
        A URL-safe base64-encoded cursor string.
    """
    payload = json.dumps({"c": created_at.isoformat(), "i": id})
    return base64.urlsafe_b64encode(payload.encode()).decode()


def decode_cursor(cursor: str) -> tuple[datetime, str]:
    """Decode a pagination cursor back into its components.

    Args:
        cursor: A URL-safe base64-encoded cursor string.

    Returns:
        A tuple of (created_at, id).

    Raises:
        ValueError: If the cursor is malformed or contains invalid data.
    """
    try:
        payload = json.loads(base64.urlsafe_b64decode(cursor.encode()).decode())
        return datetime.fromisoformat(payload["c"]), payload["i"]
    except (json.JSONDecodeError, KeyError, ValueError) as exc:
        msg = f"Invalid pagination cursor: {cursor}"
        raise ValueError(msg) from exc
