"""Public project CRUD, assignment, sync, and file endpoints.

Provides 12 REST endpoints for project management following JSON:API
envelope format with cursor-based pagination on the list endpoint.
Same patterns as the skills router.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from botcrew.api.deps import get_db
from botcrew.models.project import Project, ProjectAgent, ProjectFile, ProjectSecret
from botcrew.schemas.jsonapi import (
    JSONAPIListResponse,
    JSONAPIRequest,
    JSONAPIResource,
    JSONAPISingleResponse,
)
from botcrew.schemas.pagination import PaginationLinks, encode_cursor
from botcrew.schemas.project import (
    AssignAgentRequest,
    AssignSecretRequest,
    CreateProjectRequest,
    UpdateProjectRequest,
)
from botcrew.services.project_service import ProjectService

router = APIRouter()


# ---------------------------------------------------------------------------
# Attribute mapping helpers
# ---------------------------------------------------------------------------


def _project_to_attrs(project: Project) -> dict:
    """Map a Project model to JSON:API attributes."""
    return {
        "name": project.name,
        "description": project.description,
        "goals": project.goals,
        "specs": project.specs,
        "github_repo_url": project.github_repo_url,
        "channel_id": str(project.channel_id) if project.channel_id else None,
        "status": project.status,
        "created_at": project.created_at.isoformat(),
        "updated_at": project.updated_at.isoformat(),
    }


def _project_resource(project: Project) -> JSONAPIResource:
    """Build a JSON:API resource object from a Project."""
    return JSONAPIResource(
        type="projects",
        id=str(project.id),
        attributes=_project_to_attrs(project),
    )


def _assignment_to_attrs(pa: ProjectAgent) -> dict:
    """Map a ProjectAgent model to JSON:API attributes."""
    return {
        "project_id": str(pa.project_id),
        "agent_id": str(pa.agent_id),
        "role_prompt": pa.role_prompt,
        "created_at": pa.created_at.isoformat(),
    }


def _assignment_resource(pa: ProjectAgent) -> JSONAPIResource:
    """Build a JSON:API resource object from a ProjectAgent."""
    return JSONAPIResource(
        type="project_agents",
        id=str(pa.id),
        attributes=_assignment_to_attrs(pa),
    )


def _file_to_attrs(pf: ProjectFile, include_content: bool = False) -> dict:
    """Map a ProjectFile model to JSON:API attributes."""
    attrs: dict = {
        "project_id": str(pf.project_id),
        "path": pf.path,
        "size": pf.size,
        "last_modified": pf.last_modified.isoformat(),
        "created_at": pf.created_at.isoformat(),
    }
    if include_content:
        attrs["content"] = pf.content
    return attrs


def _file_resource(
    pf: ProjectFile, include_content: bool = False
) -> JSONAPIResource:
    """Build a JSON:API resource object from a ProjectFile."""
    return JSONAPIResource(
        type="project_files",
        id=str(pf.id),
        attributes=_file_to_attrs(pf, include_content=include_content),
    )


# ---------------------------------------------------------------------------
# Project CRUD endpoints
# ---------------------------------------------------------------------------


@router.post("", status_code=201)
async def create_project(
    body: JSONAPIRequest[CreateProjectRequest],
    db: AsyncSession = Depends(get_db),
) -> JSONAPISingleResponse:
    """Create a new project with an auto-created channel."""
    attrs = body.data.attributes
    service = ProjectService(db)
    project = await service.create_project(
        name=attrs.name,
        description=attrs.description,
        goals=attrs.goals,
        github_repo_url=attrs.github_repo_url,
    )
    return JSONAPISingleResponse(data=_project_resource(project))


@router.get("")
async def list_projects(
    request: Request,
    page_after: str | None = Query(default=None, alias="page[after]"),
    page_size: int = Query(default=20, ge=1, le=100, alias="page[size]"),
    db: AsyncSession = Depends(get_db),
) -> JSONAPIListResponse:
    """List active projects with cursor-based pagination."""
    service = ProjectService(db)
    projects, pagination_meta = await service.list_projects(
        page_size=page_size,
        after=page_after,
    )

    base_url = str(request.url).split("?")[0]
    first_link = f"{base_url}?page[size]={page_size}"
    links = PaginationLinks(first=first_link)

    if pagination_meta.has_next and projects:
        last_project = projects[-1]
        next_cursor = encode_cursor(
            last_project.created_at, str(last_project.id)
        )
        links.next = (
            f"{base_url}?page[after]={next_cursor}&page[size]={page_size}"
        )

    return JSONAPIListResponse(
        data=[_project_resource(p) for p in projects],
        meta=pagination_meta.model_dump(),
        links=links.model_dump(exclude_none=True),
    )


@router.get("/{project_id}")
async def get_project(
    project_id: str,
    db: AsyncSession = Depends(get_db),
) -> JSONAPISingleResponse:
    """Get a single project by UUID."""
    service = ProjectService(db)
    project = await service.get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return JSONAPISingleResponse(data=_project_resource(project))


@router.patch("/{project_id}")
async def update_project(
    project_id: str,
    body: JSONAPIRequest[UpdateProjectRequest],
    db: AsyncSession = Depends(get_db),
) -> JSONAPISingleResponse:
    """Update specified fields of an existing project."""
    attrs = body.data.attributes
    service = ProjectService(db)
    update_data = attrs.model_dump(exclude_unset=True)
    try:
        project = await service.update_project(project_id, **update_data)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return JSONAPISingleResponse(data=_project_resource(project))


@router.delete("/{project_id}", status_code=204)
async def delete_project(
    project_id: str,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Hard-delete a project with full cascade cleanup."""
    service = ProjectService(db)
    try:
        await service.delete_project(project_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# Agent assignment sub-resource
# ---------------------------------------------------------------------------


@router.post("/{project_id}/agents", status_code=201)
async def assign_agent(
    project_id: str,
    body: JSONAPIRequest[AssignAgentRequest],
    db: AsyncSession = Depends(get_db),
) -> JSONAPISingleResponse:
    """Assign an agent to a project with optional role_prompt."""
    attrs = body.data.attributes
    service = ProjectService(db)
    try:
        assignment = await service.assign_agent(
            project_id=project_id,
            agent_id=attrs.agent_id,
            role_prompt=attrs.role_prompt,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return JSONAPISingleResponse(data=_assignment_resource(assignment))


@router.get("/{project_id}/agents")
async def list_project_agents(
    project_id: str,
    db: AsyncSession = Depends(get_db),
) -> JSONAPIListResponse:
    """List all agent assignments for a project."""
    service = ProjectService(db)
    assignments = await service.list_project_agents(project_id)
    return JSONAPIListResponse(
        data=[_assignment_resource(a) for a in assignments],
    )


@router.delete("/{project_id}/agents/{agent_id}", status_code=204)
async def remove_agent(
    project_id: str,
    agent_id: str,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Remove an agent from a project.

    Returns 204 No Content on successful removal.
    """
    service = ProjectService(db)
    try:
        await service.remove_agent(project_id, agent_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# GitHub sync
# ---------------------------------------------------------------------------


@router.post("/{project_id}/sync", status_code=202)
async def trigger_sync(
    project_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Queue a GitHub pull sync for a project."""
    service = ProjectService(db)
    try:
        result = await service.trigger_sync(project_id)
    except ValueError as exc:
        detail = str(exc)
        if "no github_repo_url" in detail:
            raise HTTPException(status_code=400, detail=detail) from exc
        raise HTTPException(status_code=404, detail=detail) from exc
    return {"data": result}


# ---------------------------------------------------------------------------
# Project files
# ---------------------------------------------------------------------------


@router.get("/{project_id}/files")
async def list_project_files(
    project_id: str,
    db: AsyncSession = Depends(get_db),
) -> JSONAPIListResponse:
    """List backed-up spec files for a project (without content)."""
    service = ProjectService(db)
    files = await service.list_project_files(project_id)
    return JSONAPIListResponse(
        data=[_file_resource(f, include_content=False) for f in files],
    )


@router.get("/{project_id}/files/{file_id}")
async def get_project_file(
    project_id: str,
    file_id: str,
    db: AsyncSession = Depends(get_db),
) -> JSONAPISingleResponse:
    """Get a single project file with content."""
    service = ProjectService(db)
    pf = await service.get_project_file(project_id, file_id)
    if pf is None:
        raise HTTPException(status_code=404, detail="Project file not found")
    return JSONAPISingleResponse(
        data=_file_resource(pf, include_content=True)
    )


# ---------------------------------------------------------------------------
# Secret assignment sub-resource
# ---------------------------------------------------------------------------


def _secret_assignment_to_attrs(ps: ProjectSecret) -> dict:
    """Map a ProjectSecret model to JSON:API attributes."""
    return {
        "project_id": str(ps.project_id),
        "secret_id": str(ps.secret_id),
        "created_at": ps.created_at.isoformat(),
    }


def _secret_assignment_resource(ps: ProjectSecret) -> JSONAPIResource:
    """Build a JSON:API resource object from a ProjectSecret."""
    return JSONAPIResource(
        type="project-secrets",
        id=str(ps.id),
        attributes=_secret_assignment_to_attrs(ps),
    )


@router.post("/{project_id}/secrets", status_code=201)
async def assign_secret(
    project_id: str,
    body: JSONAPIRequest[AssignSecretRequest],
    db: AsyncSession = Depends(get_db),
) -> JSONAPISingleResponse:
    """Assign a secret to a project."""
    attrs = body.data.attributes
    service = ProjectService(db)
    try:
        assignment = await service.assign_secret(
            project_id=project_id,
            secret_id=attrs.secret_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return JSONAPISingleResponse(data=_secret_assignment_resource(assignment))


@router.get("/{project_id}/secrets")
async def list_project_secrets(
    project_id: str,
    db: AsyncSession = Depends(get_db),
) -> JSONAPIListResponse:
    """List all secret assignments for a project."""
    service = ProjectService(db)
    assignments = await service.list_project_secrets(project_id)
    return JSONAPIListResponse(
        data=[_secret_assignment_resource(a) for a in assignments],
    )


@router.delete("/{project_id}/secrets/{secret_id}", status_code=204)
async def remove_secret(
    project_id: str,
    secret_id: str,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Remove a secret from a project."""
    service = ProjectService(db)
    try:
        await service.remove_secret(project_id, secret_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
