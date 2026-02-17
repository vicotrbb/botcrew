"""Config update endpoint -- receives config pushes from orchestrator.

POST /config-update is called by the orchestrator after a user updates
agent heartbeat settings (interval, prompt, enabled) via the public API.
This ensures changes take effect within one heartbeat cycle without
waiting for the agent to poll.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter()


class ConfigUpdateRequest(BaseModel):
    """Request body for heartbeat config push from orchestrator."""

    heartbeat_interval_seconds: int | None = Field(
        default=None, ge=300, le=86400,
    )
    heartbeat_prompt: str | None = None
    heartbeat_enabled: bool | None = None


class ConfigUpdateResponse(BaseModel):
    """Response confirming which config changes were applied."""

    status: str
    changes_applied: list[str]


@router.post("/config-update", response_model=ConfigUpdateResponse)
async def config_update(
    request: Request,
    body: ConfigUpdateRequest,
) -> ConfigUpdateResponse | JSONResponse:
    """Apply orchestrator-pushed heartbeat config changes.

    Updates in-memory config and restarts/starts/stops the heartbeat
    timer as needed.  Called by the orchestrator when a user updates
    heartbeat settings via PATCH /api/v1/agents/{id}.

    Returns:
        ConfigUpdateResponse listing changes applied.
        503 if the agent is not fully booted.
    """
    heartbeat = getattr(request.app.state, "heartbeat", None)
    config = getattr(request.app.state, "config", None)
    changes: list[str] = []

    if heartbeat is None:
        return JSONResponse(
            status_code=503,
            content={"detail": "Agent not fully booted"},
        )

    # Update heartbeat interval and/or prompt (restart timer with new values)
    restart_kwargs: dict = {}
    if body.heartbeat_interval_seconds is not None:
        restart_kwargs["interval"] = body.heartbeat_interval_seconds
        if config:
            config["heartbeat_interval_seconds"] = body.heartbeat_interval_seconds
        changes.append("heartbeat_interval_seconds")

    if body.heartbeat_prompt is not None:
        restart_kwargs["prompt"] = body.heartbeat_prompt
        if config:
            config["heartbeat_prompt"] = body.heartbeat_prompt
        changes.append("heartbeat_prompt")

    if restart_kwargs:
        await heartbeat.restart(**restart_kwargs)
        logger.info("Heartbeat restarted with updated config: %s", changes)

    # Handle heartbeat_enabled toggle
    if body.heartbeat_enabled is not None:
        if config:
            config["heartbeat_enabled"] = body.heartbeat_enabled
        if body.heartbeat_enabled:
            if not heartbeat._running:
                await heartbeat.start()
                changes.append("heartbeat_enabled=true (started)")
        else:
            if heartbeat._running:
                await heartbeat.stop()
                changes.append("heartbeat_enabled=false (stopped)")

    logger.info("Config update applied: %s", changes)
    return ConfigUpdateResponse(status="ok", changes_applied=changes)
