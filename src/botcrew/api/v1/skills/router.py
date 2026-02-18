"""Public skills CRUD endpoints returning JSON:API responses.

Provides create, list, get, update, and soft-delete operations for the
global skills library. All endpoints follow JSON:API envelope format
with cursor-based pagination on the list endpoint.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from botcrew.api.deps import get_db
from botcrew.models.skill import Skill
from botcrew.schemas.jsonapi import (
    JSONAPIListResponse,
    JSONAPIRequest,
    JSONAPIResource,
    JSONAPISingleResponse,
)
from botcrew.schemas.pagination import PaginationLinks, encode_cursor
from botcrew.schemas.skill import CreateSkillRequest, UpdateSkillRequest
from botcrew.services.skill_service import SkillService

router = APIRouter()


# ---------------------------------------------------------------------------
# Attribute mapping helpers
# ---------------------------------------------------------------------------


def _skill_to_attrs(skill: Skill) -> dict:
    """Map a Skill model to JSON:API attributes."""
    return {
        "name": skill.name,
        "description": skill.description,
        "body": skill.body,
        "is_active": skill.is_active,
        "created_at": skill.created_at.isoformat(),
        "updated_at": skill.updated_at.isoformat(),
    }


def _skill_resource(skill: Skill) -> JSONAPIResource:
    """Build a JSON:API resource object from a Skill."""
    return JSONAPIResource(
        type="skills", id=str(skill.id), attributes=_skill_to_attrs(skill)
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("", status_code=201)
async def create_skill(
    body: JSONAPIRequest[CreateSkillRequest],
    db: AsyncSession = Depends(get_db),
) -> JSONAPISingleResponse:
    """Create a new skill in the global skills library."""
    attrs = body.data.attributes
    service = SkillService(db)
    try:
        skill = await service.create_skill(
            name=attrs.name,
            description=attrs.description,
            body=attrs.body,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    return JSONAPISingleResponse(data=_skill_resource(skill))


@router.get("")
async def list_skills(
    request: Request,
    page_after: str | None = Query(default=None, alias="page[after]"),
    page_size: int = Query(default=20, ge=1, le=100, alias="page[size]"),
    db: AsyncSession = Depends(get_db),
) -> JSONAPIListResponse:
    """List active skills with cursor-based pagination."""
    service = SkillService(db)
    skills, pagination_meta = await service.list_skills(
        page_size=page_size,
        after=page_after,
    )

    base_url = str(request.url).split("?")[0]
    first_link = f"{base_url}?page[size]={page_size}"
    links = PaginationLinks(first=first_link)

    if pagination_meta.has_next and skills:
        last_skill = skills[-1]
        next_cursor = encode_cursor(last_skill.created_at, str(last_skill.id))
        links.next = (
            f"{base_url}?page[after]={next_cursor}&page[size]={page_size}"
        )

    return JSONAPIListResponse(
        data=[_skill_resource(s) for s in skills],
        meta=pagination_meta.model_dump(),
        links=links.model_dump(exclude_none=True),
    )


@router.get("/{skill_id}")
async def get_skill(
    skill_id: str,
    db: AsyncSession = Depends(get_db),
) -> JSONAPISingleResponse:
    """Get a single skill by UUID."""
    service = SkillService(db)
    skill = await service.get_skill(skill_id)
    if skill is None:
        raise HTTPException(status_code=404, detail="Skill not found")

    return JSONAPISingleResponse(data=_skill_resource(skill))


@router.patch("/{skill_id}")
async def update_skill(
    skill_id: str,
    body: JSONAPIRequest[UpdateSkillRequest],
    db: AsyncSession = Depends(get_db),
) -> JSONAPISingleResponse:
    """Update specified fields of an existing skill."""
    attrs = body.data.attributes
    service = SkillService(db)
    update_data = attrs.model_dump(exclude_unset=True)

    try:
        skill = await service.update_skill(skill_id, **update_data)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return JSONAPISingleResponse(data=_skill_resource(skill))


@router.delete("/{skill_id}", status_code=204)
async def delete_skill(
    skill_id: str,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Soft-delete a skill (sets is_active=False)."""
    service = SkillService(db)
    try:
        await service.delete_skill(skill_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
