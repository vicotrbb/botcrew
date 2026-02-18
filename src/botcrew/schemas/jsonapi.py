"""JSON:API envelope models using Pydantic v2.

Enforces the JSON:API specification's data/type/id/attributes structure
for all API requests and responses. Every mutation endpoint accepts a
JSONAPIRequest wrapper; every endpoint returns one of the response
envelope types.

Reference: https://jsonapi.org/format/
"""

from typing import Any, Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


# ---------------------------------------------------------------------------
# Request wrappers
# ---------------------------------------------------------------------------


class JSONAPIRequestData(BaseModel, Generic[T]):
    """The ``data`` object inside a JSON:API request body."""

    type: str
    attributes: T


class JSONAPIRequest(BaseModel, Generic[T]):
    """JSON:API request envelope wrapping ``{ data: { type, attributes } }``."""

    data: JSONAPIRequestData[T]


class JSONAPIResource(BaseModel):
    """A single JSON:API resource object with type, id, and attributes."""

    type: str
    id: str
    attributes: dict[str, Any]
    relationships: dict[str, Any] | None = None


class JSONAPISingleResponse(BaseModel):
    """JSON:API response envelope containing a single resource."""

    data: JSONAPIResource


class JSONAPIListResponse(BaseModel):
    """JSON:API response envelope containing a list of resources."""

    data: list[JSONAPIResource]
    meta: dict[str, Any] | None = None
    links: dict[str, Any] | None = None


class JSONAPIError(BaseModel):
    """A single JSON:API error object."""

    status: str
    title: str
    detail: str | None = None
    source: dict[str, str] | None = None


class JSONAPIErrorResponse(BaseModel):
    """JSON:API response envelope containing a list of errors."""

    errors: list[JSONAPIError]
