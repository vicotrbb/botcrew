"""Pydantic schemas for API request/response models."""

from botcrew.schemas.jsonapi import (
    JSONAPIError,
    JSONAPIErrorResponse,
    JSONAPIListResponse,
    JSONAPIResource,
    JSONAPISingleResponse,
)

__all__ = [
    "JSONAPIError",
    "JSONAPIErrorResponse",
    "JSONAPIListResponse",
    "JSONAPIResource",
    "JSONAPISingleResponse",
]
