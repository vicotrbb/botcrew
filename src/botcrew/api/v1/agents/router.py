"""Agent CRUD endpoints returning JSON:API responses.

Provides create, list, get, update, delete, and duplicate operations
for agents. List and detail endpoints enrich status from live Kubernetes
pod state before responding.

The PATCH endpoint pushes heartbeat config changes to the running agent
container via fire-and-forget POST to the agent's /config-update endpoint.
"""

from __future__ import annotations

import logging

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from botcrew.api.deps import get_db, get_pod_manager
from botcrew.models.agent import Agent
from botcrew.schemas.agent import CreateAgentRequest, UpdateAgentRequest
from botcrew.schemas.jsonapi import (
    JSONAPIListResponse,
    JSONAPIResource,
    JSONAPISingleResponse,
)
from botcrew.schemas.pagination import PaginationLinks, encode_cursor
from botcrew.services.agent_service import AgentService
from botcrew.services.pod_manager import PodManager

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Attribute mapping helpers
# ---------------------------------------------------------------------------


def _agent_to_summary(agent: Agent) -> dict:
    """Map an Agent model to summary attributes for list responses."""
    return {
        "name": agent.name,
        "status": agent.status,
        "model_provider": agent.model_provider,
        "model_name": agent.model_name,
        "heartbeat_interval_seconds": agent.heartbeat_interval_seconds,
        "created_at": agent.created_at.isoformat(),
        "updated_at": agent.updated_at.isoformat(),
    }


def _agent_to_detail(agent: Agent) -> dict:
    """Map an Agent model to full detail attributes."""
    return {
        **_agent_to_summary(agent),
        "identity": agent.identity,
        "personality": agent.personality,
        "memory": agent.memory,
        "heartbeat_prompt": agent.heartbeat_prompt,
        "heartbeat_enabled": agent.heartbeat_enabled,
        "avatar_url": agent.avatar_url,
        "pod_name": agent.pod_name,
    }


def _agent_resource(agent: Agent, *, detail: bool = False) -> JSONAPIResource:
    """Build a JSON:API resource object from an Agent."""
    attrs = _agent_to_detail(agent) if detail else _agent_to_summary(agent)
    return JSONAPIResource(type="agents", id=str(agent.id), attributes=attrs)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("", status_code=201)
async def create_agent(
    body: CreateAgentRequest,
    db: AsyncSession = Depends(get_db),
    pod_manager: PodManager = Depends(get_pod_manager),
) -> JSONAPISingleResponse:
    """Create a new agent with Kubernetes pod orchestration."""
    service = AgentService(db, pod_manager)
    try:
        agent = await service.create_agent(
            name=body.name,
            model_provider=body.model_provider,
            model_name=body.model_name,
            identity=body.identity,
            personality=body.personality,
            heartbeat_interval_seconds=body.heartbeat_interval_seconds,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return JSONAPISingleResponse(data=_agent_resource(agent, detail=True))


@router.get("")
async def list_agents(
    request: Request,
    page_after: str | None = Query(default=None, alias="page[after]"),
    page_size: int = Query(default=20, ge=1, le=100, alias="page[size]"),
    filter_status: str | None = Query(default=None, alias="filter[status]"),
    sort: str = Query(default="created_at"),
    db: AsyncSession = Depends(get_db),
    pod_manager: PodManager = Depends(get_pod_manager),
) -> JSONAPIListResponse:
    """List agents with cursor-based pagination and live pod status."""
    # Parse and validate sort parameter
    sort_desc = sort.startswith("-")
    sort_field = sort.lstrip("-")
    valid_sort_fields = ("name", "created_at")
    if sort_field not in valid_sort_fields:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid sort field '{sort_field}'. Must be one of: {', '.join(valid_sort_fields)}",
        )

    # Cursor pagination only works with created_at sort.
    # If sorting by name with a cursor, ignore the cursor.
    effective_cursor = page_after
    if sort_field != "created_at" and page_after is not None:
        effective_cursor = None

    service = AgentService(db, pod_manager)
    agents, pagination_meta = await service.list_agents(
        page_size=page_size,
        after=effective_cursor,
        status_filter=filter_status,
        sort_by=sort_field,
        sort_desc=sort_desc,
    )

    # Enrich with live K8s pod status before building response
    agents = await service.enrich_agents_with_pod_status(agents)

    # Build pagination links preserving current filter/sort params
    base_url = str(request.url).split("?")[0]
    extra_params = ""
    if filter_status:
        extra_params += f"&filter[status]={filter_status}"
    if sort != "created_at":
        extra_params += f"&sort={sort}"

    first_link = f"{base_url}?page[size]={page_size}{extra_params}"
    links = PaginationLinks(first=first_link)

    if pagination_meta.has_next and agents:
        last_agent = agents[-1]
        next_cursor = encode_cursor(last_agent.created_at, str(last_agent.id))
        links.next = (
            f"{base_url}?page[after]={next_cursor}"
            f"&page[size]={page_size}{extra_params}"
        )

    return JSONAPIListResponse(
        data=[_agent_resource(a) for a in agents],
        meta=pagination_meta.model_dump(),
        links=links.model_dump(exclude_none=True),
    )


@router.get("/{agent_id}")
async def get_agent(
    agent_id: str,
    db: AsyncSession = Depends(get_db),
    pod_manager: PodManager = Depends(get_pod_manager),
) -> JSONAPISingleResponse:
    """Get a single agent with live Kubernetes pod status."""
    service = AgentService(db, pod_manager)
    agent = await service.get_agent_with_live_status(agent_id)
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")

    return JSONAPISingleResponse(data=_agent_resource(agent, detail=True))


@router.patch("/{agent_id}")
async def update_agent(
    agent_id: str,
    body: UpdateAgentRequest,
    db: AsyncSession = Depends(get_db),
    pod_manager: PodManager = Depends(get_pod_manager),
) -> JSONAPISingleResponse:
    """Update specified fields of an existing agent."""
    service = AgentService(db, pod_manager)
    update_data = body.model_dump(exclude_unset=True)

    try:
        agent = await service.update_agent(agent_id, **update_data)
    except ValueError as exc:
        msg = str(exc)
        if "not found" in msg.lower():
            raise HTTPException(status_code=404, detail=msg) from exc
        raise HTTPException(status_code=422, detail=msg) from exc

    # Push heartbeat config changes to running agent (fire-and-forget)
    heartbeat_fields = {
        "heartbeat_interval_seconds",
        "heartbeat_prompt",
        "heartbeat_enabled",
    }
    config_changes = {k: v for k, v in update_data.items() if k in heartbeat_fields}
    if config_changes:
        pod_url = (
            f"http://agent-{agent_id}.botcrew-agents"
            f".botcrew.svc.cluster.local:8080"
        )
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                await client.post(
                    f"{pod_url}/config-update", json=config_changes,
                )
        except Exception:
            logger.warning(
                "Failed to push config update to agent %s "
                "(agent may be offline)",
                agent_id,
            )

    return JSONAPISingleResponse(data=_agent_resource(agent, detail=True))


@router.delete("/{agent_id}", status_code=204)
async def delete_agent(
    agent_id: str,
    db: AsyncSession = Depends(get_db),
    pod_manager: PodManager = Depends(get_pod_manager),
) -> None:
    """Delete an agent and its Kubernetes pod."""
    service = AgentService(db, pod_manager)
    try:
        await service.delete_agent(agent_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{agent_id}/duplicate", status_code=201)
async def duplicate_agent(
    agent_id: str,
    db: AsyncSession = Depends(get_db),
    pod_manager: PodManager = Depends(get_pod_manager),
) -> JSONAPISingleResponse:
    """Clone an agent's configuration with empty memory and a new pod."""
    service = AgentService(db, pod_manager)
    try:
        agent = await service.duplicate_agent(agent_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return JSONAPISingleResponse(data=_agent_resource(agent, detail=True))


# ---------------------------------------------------------------------------
# Sub-resource routers
# ---------------------------------------------------------------------------

from botcrew.api.v1.agents.memory_router import router as memory_router  # noqa: E402

router.include_router(memory_router, tags=["agent-memory"])
