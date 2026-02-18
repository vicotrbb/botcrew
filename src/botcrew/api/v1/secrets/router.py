"""Public secrets CRUD endpoints returning JSON:API responses.

Provides create, list, get, update, and hard-delete operations for
secrets. The list endpoint masks secret values for safety; the single-get
endpoint reveals the actual value.

All endpoints follow JSON:API envelope format with cursor-based pagination
on the list endpoint.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from botcrew.api.deps import get_db
from botcrew.models.secret import Secret
from botcrew.schemas.jsonapi import (
    JSONAPIListResponse,
    JSONAPIRequest,
    JSONAPIResource,
    JSONAPISingleResponse,
)
from botcrew.schemas.pagination import PaginationLinks, encode_cursor
from botcrew.schemas.secret import CreateSecretRequest, UpdateSecretRequest
from botcrew.services.secret_service import SecretService

router = APIRouter()


# ---------------------------------------------------------------------------
# Attribute mapping helpers
# ---------------------------------------------------------------------------


def _secret_to_attrs(secret: Secret, *, mask_value: bool = True) -> dict:
    """Map a Secret model to JSON:API attributes.

    Args:
        secret: The Secret model instance.
        mask_value: If True, replace the value with "********".
    """
    return {
        "key": secret.key,
        "value": "********" if mask_value else secret.value,
        "description": secret.description,
        "created_at": secret.created_at.isoformat(),
        "updated_at": secret.updated_at.isoformat(),
    }


def _secret_resource(
    secret: Secret, *, mask_value: bool = True
) -> JSONAPIResource:
    """Build a JSON:API resource object from a Secret."""
    return JSONAPIResource(
        type="secrets",
        id=str(secret.id),
        attributes=_secret_to_attrs(secret, mask_value=mask_value),
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("", status_code=201)
async def create_secret(
    body: JSONAPIRequest[CreateSecretRequest],
    db: AsyncSession = Depends(get_db),
) -> JSONAPISingleResponse:
    """Create a new secret."""
    attrs = body.data.attributes
    service = SecretService(db)
    try:
        secret = await service.create_secret(
            key=attrs.key,
            value=attrs.value,
            description=attrs.description,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    return JSONAPISingleResponse(data=_secret_resource(secret, mask_value=False))


@router.get("")
async def list_secrets(
    request: Request,
    page_after: str | None = Query(default=None, alias="page[after]"),
    page_size: int = Query(default=20, ge=1, le=100, alias="page[size]"),
    db: AsyncSession = Depends(get_db),
) -> JSONAPIListResponse:
    """List secrets with cursor-based pagination.

    Secret values are masked in list responses for safety.
    Use the single-get endpoint to reveal a specific secret's value.
    """
    service = SecretService(db)
    secrets, pagination_meta = await service.list_secrets(
        page_size=page_size,
        after=page_after,
    )

    base_url = str(request.url).split("?")[0]
    first_link = f"{base_url}?page[size]={page_size}"
    links = PaginationLinks(first=first_link)

    if pagination_meta.has_next and secrets:
        last_secret = secrets[-1]
        next_cursor = encode_cursor(last_secret.created_at, str(last_secret.id))
        links.next = (
            f"{base_url}?page[after]={next_cursor}&page[size]={page_size}"
        )

    return JSONAPIListResponse(
        data=[_secret_resource(s, mask_value=True) for s in secrets],
        meta=pagination_meta.model_dump(),
        links=links.model_dump(exclude_none=True),
    )


@router.get("/{secret_id}")
async def get_secret(
    secret_id: str,
    db: AsyncSession = Depends(get_db),
) -> JSONAPISingleResponse:
    """Get a single secret by UUID with the actual (unmasked) value."""
    service = SecretService(db)
    secret = await service.get_secret(secret_id)
    if secret is None:
        raise HTTPException(status_code=404, detail="Secret not found")

    return JSONAPISingleResponse(data=_secret_resource(secret, mask_value=False))


@router.patch("/{secret_id}")
async def update_secret(
    secret_id: str,
    body: JSONAPIRequest[UpdateSecretRequest],
    db: AsyncSession = Depends(get_db),
) -> JSONAPISingleResponse:
    """Update specified fields of an existing secret."""
    attrs = body.data.attributes
    service = SecretService(db)
    update_data = attrs.model_dump(exclude_unset=True)

    try:
        secret = await service.update_secret(secret_id, **update_data)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return JSONAPISingleResponse(data=_secret_resource(secret, mask_value=False))


@router.delete("/{secret_id}", status_code=204)
async def delete_secret(
    secret_id: str,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Hard-delete a secret."""
    service = SecretService(db)
    try:
        await service.delete_secret(secret_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
