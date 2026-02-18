"""Public integrations CRUD endpoints returning JSON:API responses.

Provides create, list, get, update, and hard-delete operations for
integrations. The list endpoint supports optional filtering by
integration_type.

All endpoints follow JSON:API envelope format with cursor-based pagination
on the list endpoint.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from botcrew.api.deps import get_db
from botcrew.models.integration import Integration
from botcrew.schemas.integration import (
    CreateIntegrationRequest,
    UpdateIntegrationRequest,
)
from botcrew.schemas.jsonapi import (
    JSONAPIListResponse,
    JSONAPIRequest,
    JSONAPIResource,
    JSONAPISingleResponse,
)
from botcrew.schemas.pagination import PaginationLinks, encode_cursor
from botcrew.services.integration_service import IntegrationService

router = APIRouter()


# ---------------------------------------------------------------------------
# Attribute mapping helpers
# ---------------------------------------------------------------------------


def _integration_to_attrs(integration: Integration) -> dict:
    """Map an Integration model to JSON:API attributes."""
    return {
        "name": integration.name,
        "integration_type": integration.integration_type,
        "config": integration.config,
        "agent_id": integration.agent_id,
        "channel_id": integration.channel_id,
        "is_active": integration.is_active,
        "created_at": integration.created_at.isoformat(),
        "updated_at": integration.updated_at.isoformat(),
    }


def _integration_resource(integration: Integration) -> JSONAPIResource:
    """Build a JSON:API resource object from an Integration."""
    return JSONAPIResource(
        type="integrations",
        id=str(integration.id),
        attributes=_integration_to_attrs(integration),
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("", status_code=201)
async def create_integration(
    body: JSONAPIRequest[CreateIntegrationRequest],
    db: AsyncSession = Depends(get_db),
) -> JSONAPISingleResponse:
    """Create a new integration."""
    attrs = body.data.attributes
    service = IntegrationService(db)
    integration = await service.create_integration(
        name=attrs.name,
        integration_type=attrs.integration_type,
        config=attrs.config,
        agent_id=attrs.agent_id,
        channel_id=attrs.channel_id,
    )

    return JSONAPISingleResponse(data=_integration_resource(integration))


@router.get("")
async def list_integrations(
    request: Request,
    page_after: str | None = Query(default=None, alias="page[after]"),
    page_size: int = Query(default=20, ge=1, le=100, alias="page[size]"),
    integration_type: str | None = Query(default=None, alias="type"),
    db: AsyncSession = Depends(get_db),
) -> JSONAPIListResponse:
    """List integrations with cursor-based pagination.

    Optionally filter by ``type`` query parameter to show only integrations
    of a specific type.
    """
    service = IntegrationService(db)
    integrations, pagination_meta = await service.list_integrations(
        page_size=page_size,
        after=page_after,
        integration_type=integration_type,
    )

    base_url = str(request.url).split("?")[0]
    first_link = f"{base_url}?page[size]={page_size}"
    if integration_type:
        first_link += f"&type={integration_type}"
    links = PaginationLinks(first=first_link)

    if pagination_meta.has_next and integrations:
        last_integration = integrations[-1]
        next_cursor = encode_cursor(
            last_integration.created_at, str(last_integration.id)
        )
        next_link = (
            f"{base_url}?page[after]={next_cursor}&page[size]={page_size}"
        )
        if integration_type:
            next_link += f"&type={integration_type}"
        links.next = next_link

    return JSONAPIListResponse(
        data=[_integration_resource(i) for i in integrations],
        meta=pagination_meta.model_dump(),
        links=links.model_dump(exclude_none=True),
    )


@router.get("/{integration_id}")
async def get_integration(
    integration_id: str,
    db: AsyncSession = Depends(get_db),
) -> JSONAPISingleResponse:
    """Get a single integration by UUID."""
    service = IntegrationService(db)
    integration = await service.get_integration(integration_id)
    if integration is None:
        raise HTTPException(status_code=404, detail="Integration not found")

    return JSONAPISingleResponse(data=_integration_resource(integration))


@router.patch("/{integration_id}")
async def update_integration(
    integration_id: str,
    body: JSONAPIRequest[UpdateIntegrationRequest],
    db: AsyncSession = Depends(get_db),
) -> JSONAPISingleResponse:
    """Update specified fields of an existing integration."""
    attrs = body.data.attributes
    service = IntegrationService(db)
    update_data = attrs.model_dump(exclude_unset=True)

    try:
        integration = await service.update_integration(
            integration_id, **update_data
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return JSONAPISingleResponse(data=_integration_resource(integration))


@router.delete("/{integration_id}", status_code=204)
async def delete_integration(
    integration_id: str,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Hard-delete an integration."""
    service = IntegrationService(db)
    try:
        await service.delete_integration(integration_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
