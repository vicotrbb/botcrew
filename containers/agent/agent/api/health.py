"""Agent health endpoint.

Returns agent status for K8s liveness/readiness probes and debugging.
Reads state from request.app.state, which is populated during boot.
"""

from __future__ import annotations

from fastapi import APIRouter, Request
from pydantic import BaseModel

router = APIRouter()


class HealthResponse(BaseModel):
    """Health check response for the agent container."""

    status: str
    agent_id: str
    browser_connected: bool
    model_provider: str


@router.get("/health", response_model=HealthResponse)
async def health(request: Request) -> HealthResponse:
    """Health check endpoint.

    Returns the agent's current status, identity, and connectivity info.
    Used by K8s probes and the orchestrator for agent health monitoring.

    Status values:
    - 'starting': Boot sequence has not completed yet
    - 'healthy': Boot completed successfully and all checks passed
    - 'unhealthy': Boot failed or a critical check failed
    """
    app_state = request.app.state

    # Determine status from boot state
    boot_status: str = getattr(app_state, "boot_status", "starting")
    agent_id: str = getattr(app_state, "agent_id", "unknown")
    browser_connected: bool = getattr(app_state, "browser_connected", False)
    model_provider: str = getattr(app_state, "model_provider", "unknown")

    return HealthResponse(
        status=boot_status,
        agent_id=agent_id,
        browser_connected=browser_connected,
        model_provider=model_provider,
    )
