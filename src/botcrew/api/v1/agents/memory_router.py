"""Memory sub-resource endpoints for agents.

Provides GET/PUT/PATCH operations on an agent's memory field
as a JSON:API sub-resource. Uses direct DB session operations
(not AgentService) since memory CRUD is simple read/write
with no business logic.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from botcrew.api.deps import get_db
from botcrew.models.agent import Agent
from botcrew.schemas.agent import MemoryPatchRequest, MemoryUpdateRequest
from botcrew.schemas.jsonapi import JSONAPIResource, JSONAPISingleResponse

router = APIRouter()


def _memory_response(agent: Agent) -> JSONAPISingleResponse:
    """Build a JSON:API response for the agent memory sub-resource."""
    return JSONAPISingleResponse(
        data=JSONAPIResource(
            type="agent-memory",
            id=str(agent.id),
            attributes={"content": agent.memory},
        )
    )


@router.get("/{agent_id}/memory")
async def get_memory(
    agent_id: str,
    db: AsyncSession = Depends(get_db),
) -> JSONAPISingleResponse:
    """Return the current memory content for an agent."""
    agent = await db.get(Agent, agent_id)
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")

    return _memory_response(agent)


@router.put("/{agent_id}/memory")
async def replace_memory(
    agent_id: str,
    body: MemoryUpdateRequest,
    db: AsyncSession = Depends(get_db),
) -> JSONAPISingleResponse:
    """Replace the entire memory content for an agent."""
    agent = await db.get(Agent, agent_id)
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")

    agent.memory = body.content
    await db.commit()
    await db.refresh(agent)

    return _memory_response(agent)


@router.patch("/{agent_id}/memory")
async def patch_memory(
    agent_id: str,
    body: MemoryPatchRequest,
    db: AsyncSession = Depends(get_db),
) -> JSONAPISingleResponse:
    """Append to or replace agent memory.

    If ``content`` is provided, replaces memory entirely (same as PUT).
    If ``append`` is provided, appends to existing memory with a newline separator.
    At least one of ``content`` or ``append`` must be provided.
    """
    agent = await db.get(Agent, agent_id)
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")

    if body.content is not None:
        agent.memory = body.content
    elif body.append is not None:
        agent.memory = (
            agent.memory + "\n" + body.append if agent.memory else body.append
        )
    else:
        raise HTTPException(
            status_code=422, detail="Either 'content' or 'append' must be provided"
        )

    await db.commit()
    await db.refresh(agent)

    return _memory_response(agent)
