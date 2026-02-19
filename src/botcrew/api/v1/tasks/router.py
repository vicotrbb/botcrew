"""Public task CRUD and sub-resource assignment endpoints.

Provides 15 REST endpoints for task management following JSON:API
envelope format with cursor-based pagination on the list endpoint.
Same patterns as the projects router.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from botcrew.api.deps import get_db
from botcrew.models.task import Task, TaskAgent, TaskSecret, TaskSkill
from botcrew.schemas.jsonapi import (
    JSONAPIListResponse,
    JSONAPIRequest,
    JSONAPIResource,
    JSONAPISingleResponse,
)
from botcrew.schemas.pagination import PaginationLinks, encode_cursor
from botcrew.schemas.task import (
    AssignAgentRequest,
    AssignSecretRequest,
    AssignSkillRequest,
    CreateTaskRequest,
    UpdateTaskRequest,
)
from botcrew.services.task_service import TaskService

router = APIRouter()


# ---------------------------------------------------------------------------
# Attribute mapping helpers
# ---------------------------------------------------------------------------


def _task_to_attrs(task: Task) -> dict:
    """Map a Task model to JSON:API attributes."""
    return {
        "name": task.name,
        "description": task.description,
        "directive": task.directive,
        "notes": task.notes,
        "status": task.status,
        "channel_id": str(task.channel_id) if task.channel_id else None,
        "created_at": task.created_at.isoformat(),
        "updated_at": task.updated_at.isoformat(),
    }


def _task_resource(task: Task) -> JSONAPIResource:
    """Build a JSON:API resource object from a Task."""
    return JSONAPIResource(
        type="tasks",
        id=str(task.id),
        attributes=_task_to_attrs(task),
    )


def _task_agent_to_attrs(ta: TaskAgent) -> dict:
    """Map a TaskAgent model to JSON:API attributes."""
    return {
        "task_id": str(ta.task_id),
        "agent_id": str(ta.agent_id),
        "created_at": ta.created_at.isoformat(),
    }


def _task_agent_resource(ta: TaskAgent) -> JSONAPIResource:
    """Build a JSON:API resource object from a TaskAgent."""
    return JSONAPIResource(
        type="task_agents",
        id=str(ta.id),
        attributes=_task_agent_to_attrs(ta),
    )


def _task_secret_to_attrs(ts: TaskSecret) -> dict:
    """Map a TaskSecret model to JSON:API attributes."""
    return {
        "task_id": str(ts.task_id),
        "secret_id": str(ts.secret_id),
        "created_at": ts.created_at.isoformat(),
    }


def _task_secret_resource(ts: TaskSecret) -> JSONAPIResource:
    """Build a JSON:API resource object from a TaskSecret."""
    return JSONAPIResource(
        type="task_secrets",
        id=str(ts.id),
        attributes=_task_secret_to_attrs(ts),
    )


def _task_skill_to_attrs(tsk: TaskSkill) -> dict:
    """Map a TaskSkill model to JSON:API attributes."""
    return {
        "task_id": str(tsk.task_id),
        "skill_id": str(tsk.skill_id),
        "created_at": tsk.created_at.isoformat(),
    }


def _task_skill_resource(tsk: TaskSkill) -> JSONAPIResource:
    """Build a JSON:API resource object from a TaskSkill."""
    return JSONAPIResource(
        type="task_skills",
        id=str(tsk.id),
        attributes=_task_skill_to_attrs(tsk),
    )


# ---------------------------------------------------------------------------
# Task CRUD endpoints
# ---------------------------------------------------------------------------


@router.post("", status_code=201)
async def create_task(
    body: JSONAPIRequest[CreateTaskRequest],
    db: AsyncSession = Depends(get_db),
) -> JSONAPISingleResponse:
    """Create a new task with an auto-created channel."""
    attrs = body.data.attributes
    service = TaskService(db)
    task = await service.create_task(
        name=attrs.name,
        description=attrs.description,
        directive=attrs.directive,
    )
    return JSONAPISingleResponse(data=_task_resource(task))


@router.get("")
async def list_tasks(
    request: Request,
    page_after: str | None = Query(default=None, alias="page[after]"),
    page_size: int = Query(default=20, ge=1, le=100, alias="page[size]"),
    db: AsyncSession = Depends(get_db),
) -> JSONAPIListResponse:
    """List all tasks with cursor-based pagination."""
    service = TaskService(db)
    tasks, pagination_meta = await service.list_tasks(
        page_size=page_size,
        after=page_after,
    )

    base_url = str(request.url).split("?")[0]
    first_link = f"{base_url}?page[size]={page_size}"
    links = PaginationLinks(first=first_link)

    if pagination_meta.has_next and tasks:
        last_task = tasks[-1]
        next_cursor = encode_cursor(
            last_task.created_at, str(last_task.id)
        )
        links.next = (
            f"{base_url}?page[after]={next_cursor}&page[size]={page_size}"
        )

    return JSONAPIListResponse(
        data=[_task_resource(t) for t in tasks],
        meta=pagination_meta.model_dump(),
        links=links.model_dump(exclude_none=True),
    )


@router.get("/{task_id}")
async def get_task(
    task_id: str,
    db: AsyncSession = Depends(get_db),
) -> JSONAPISingleResponse:
    """Get a single task by UUID."""
    service = TaskService(db)
    task = await service.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return JSONAPISingleResponse(data=_task_resource(task))


@router.patch("/{task_id}")
async def update_task(
    task_id: str,
    body: JSONAPIRequest[UpdateTaskRequest],
    db: AsyncSession = Depends(get_db),
) -> JSONAPISingleResponse:
    """Update specified fields of an existing task."""
    attrs = body.data.attributes
    service = TaskService(db)
    update_data = attrs.model_dump(exclude_unset=True)
    try:
        task = await service.update_task(task_id, **update_data)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return JSONAPISingleResponse(data=_task_resource(task))


@router.delete("/{task_id}", status_code=204)
async def delete_task(
    task_id: str,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Hard-delete a task with full cascade cleanup."""
    service = TaskService(db)
    try:
        await service.delete_task(task_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# Agent assignment sub-resource
# ---------------------------------------------------------------------------


@router.post("/{task_id}/agents", status_code=201)
async def assign_agent(
    task_id: str,
    body: JSONAPIRequest[AssignAgentRequest],
    db: AsyncSession = Depends(get_db),
) -> JSONAPISingleResponse:
    """Assign an agent to a task."""
    attrs = body.data.attributes
    service = TaskService(db)
    try:
        assignment = await service.assign_agent(
            task_id=task_id,
            agent_id=attrs.agent_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return JSONAPISingleResponse(data=_task_agent_resource(assignment))


@router.get("/{task_id}/agents")
async def list_task_agents(
    task_id: str,
    db: AsyncSession = Depends(get_db),
) -> JSONAPIListResponse:
    """List all agent assignments for a task."""
    service = TaskService(db)
    assignments = await service.list_task_agents(task_id)
    return JSONAPIListResponse(
        data=[_task_agent_resource(a) for a in assignments],
    )


@router.delete("/{task_id}/agents/{agent_id}", status_code=204)
async def remove_agent(
    task_id: str,
    agent_id: str,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Remove an agent from a task."""
    service = TaskService(db)
    try:
        await service.remove_agent(task_id, agent_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# Secret assignment sub-resource
# ---------------------------------------------------------------------------


@router.post("/{task_id}/secrets", status_code=201)
async def assign_secret(
    task_id: str,
    body: JSONAPIRequest[AssignSecretRequest],
    db: AsyncSession = Depends(get_db),
) -> JSONAPISingleResponse:
    """Assign a secret to a task."""
    attrs = body.data.attributes
    service = TaskService(db)
    try:
        assignment = await service.assign_secret(
            task_id=task_id,
            secret_id=attrs.secret_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return JSONAPISingleResponse(data=_task_secret_resource(assignment))


@router.get("/{task_id}/secrets")
async def list_task_secrets(
    task_id: str,
    db: AsyncSession = Depends(get_db),
) -> JSONAPIListResponse:
    """List all secret assignments for a task."""
    service = TaskService(db)
    secrets = await service.list_task_secrets(task_id)
    return JSONAPIListResponse(
        data=[_task_secret_resource(s) for s in secrets],
    )


@router.delete("/{task_id}/secrets/{secret_id}", status_code=204)
async def remove_secret(
    task_id: str,
    secret_id: str,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Remove a secret from a task."""
    service = TaskService(db)
    try:
        await service.remove_secret(task_id, secret_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# Skill assignment sub-resource
# ---------------------------------------------------------------------------


@router.post("/{task_id}/skills", status_code=201)
async def assign_skill(
    task_id: str,
    body: JSONAPIRequest[AssignSkillRequest],
    db: AsyncSession = Depends(get_db),
) -> JSONAPISingleResponse:
    """Assign a skill to a task."""
    attrs = body.data.attributes
    service = TaskService(db)
    try:
        assignment = await service.assign_skill(
            task_id=task_id,
            skill_id=attrs.skill_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return JSONAPISingleResponse(data=_task_skill_resource(assignment))


@router.get("/{task_id}/skills")
async def list_task_skills(
    task_id: str,
    db: AsyncSession = Depends(get_db),
) -> JSONAPIListResponse:
    """List all skill assignments for a task."""
    service = TaskService(db)
    skills = await service.list_task_skills(task_id)
    return JSONAPIListResponse(
        data=[_task_skill_resource(s) for s in skills],
    )


@router.delete("/{task_id}/skills/{skill_id}", status_code=204)
async def remove_skill(
    task_id: str,
    skill_id: str,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Remove a skill from a task."""
    service = TaskService(db)
    try:
        await service.remove_skill(task_id, skill_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
