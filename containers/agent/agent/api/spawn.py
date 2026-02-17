"""Spawn endpoint -- fire-and-forget sub-instance for parallel work.

POST /spawn creates an asyncio task that processes a given prompt
through the same AgentRuntime pipeline, enabling the agent to
handle multiple tasks in parallel during heartbeat.
"""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

router = APIRouter()


class SpawnRequest(BaseModel):
    """Request body for spawning a sub-instance."""

    prompt: str


class SpawnResponse(BaseModel):
    """Response indicating spawn result and active sub-instance count."""

    status: str
    active_sub_instances: int


@router.post("/spawn", response_model=SpawnResponse)
async def spawn(request: Request, body: SpawnRequest) -> SpawnResponse | JSONResponse:
    """Spawn a sub-instance for parallel work.

    Creates an asyncio task running the prompt through the same
    AgentRuntime.process_message() pipeline.  The sub-instance is
    fire-and-forget -- the caller gets an immediate response.

    Returns:
        SpawnResponse with status and current active sub-instance count.
        503 if the runtime is not initialized.
    """
    runtime = getattr(request.app.state, "runtime", None)
    if runtime is None or not runtime.is_ready:
        return JSONResponse(
            status_code=503,
            content={"detail": "Agent runtime is not ready"},
        )

    result = await runtime.spawn_sub_instance(body.prompt)
    return SpawnResponse(
        status=result,
        active_sub_instances=runtime._active_sub_instances,
    )
