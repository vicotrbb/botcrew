"""Wake endpoint -- heartbeat trigger for agent containers.

POST /wake processes the agent's heartbeat prompt through the same
Agno agent pipeline as /message. Called by the orchestrator's heartbeat
system to keep agents active and self-directed.
"""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

router = APIRouter()


class WakeResponse(BaseModel):
    """Response from the /wake endpoint."""

    content: str
    agent_id: str


@router.post("/wake", response_model=WakeResponse)
async def wake(request: Request) -> WakeResponse | JSONResponse:
    """Process the heartbeat prompt through the Agno agent.

    Reads the heartbeat_prompt dynamically from the HeartbeatTimer
    (SelfTools may have changed it at runtime).  Falls back to boot
    config if heartbeat timer is not available.

    Returns:
        WakeResponse with the agent's response and its ID.
        503 if the runtime is not initialized.
    """
    runtime = getattr(request.app.state, "runtime", None)
    if runtime is None or not runtime.is_ready:
        return JSONResponse(
            status_code=503,
            content={"detail": "Agent runtime is not ready"},
        )

    # Read heartbeat prompt dynamically (SelfTools may have changed it)
    heartbeat = getattr(request.app.state, "heartbeat", None)
    if heartbeat is not None:
        heartbeat_prompt = heartbeat.prompt
    else:
        config: dict = request.app.state.config
        heartbeat_prompt = config.get(
            "heartbeat_prompt",
            "You are waking up. Check your memory and decide what to do next.",
        )

    response = await runtime.process_message(heartbeat_prompt)

    config = request.app.state.config
    return WakeResponse(
        content=response,
        agent_id=config.get("agent_id", getattr(request.app.state, "agent_id", "unknown")),
    )
