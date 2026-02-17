"""Internal API endpoints for agent container communication.

These endpoints are cluster-internal only -- called by agent containers
during boot (to fetch configuration) and runtime (to report status).
Not intended for external API consumers.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from botcrew.api.deps import get_db, get_pod_manager
from botcrew.models.agent import Agent
from botcrew.schemas.internal import (
    BootConfigResponse,
    StatusReportRequest,
    StatusReportResponse,
)
from botcrew.services.agent_service import AgentService
from botcrew.services.pod_manager import PodManager

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/agents/{agent_id}/boot-config")
async def get_boot_config(
    agent_id: str,
    db: AsyncSession = Depends(get_db),
    pod_manager: PodManager = Depends(get_pod_manager),
) -> BootConfigResponse:
    """Return full boot configuration for an agent container.

    Called once at agent startup. Returns identity, personality, model
    settings, heartbeat config, current memory, and all system API keys
    needed for the model provider.
    """
    service = AgentService(db, pod_manager)
    agent = await service.get_agent(agent_id)
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")

    secrets = await service.get_system_secrets()

    return BootConfigResponse(
        agent_id=str(agent.id),
        name=agent.name,
        identity=agent.identity,
        personality=agent.personality,
        model_provider=agent.model_provider,
        model_name=agent.model_name,
        heartbeat_prompt=agent.heartbeat_prompt,
        heartbeat_interval_seconds=agent.heartbeat_interval_seconds,
        memory=agent.memory,
        secrets=secrets,
    )


@router.post("/agents/{agent_id}/status")
async def report_status(
    agent_id: str,
    body: StatusReportRequest,
    db: AsyncSession = Depends(get_db),
) -> StatusReportResponse:
    """Accept a status report from an agent container.

    Maps reported status to the agent's database status:
    - 'ready'     -> 'running'  (agent fully booted and operational)
    - 'error'     -> 'error'    (critical failure during boot or runtime)
    - 'unhealthy' -> 'error'    (degraded operation treated as error)

    Commits the status change and returns acknowledgement.
    """
    agent = await db.get(Agent, agent_id)
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Map reported status to DB status
    status_map = {
        "ready": "running",
        "error": "error",
        "unhealthy": "error",
    }
    agent.status = status_map[body.status]

    await db.commit()

    logger.info(
        "Agent '%s' (%s) reported status=%s checks=%s error=%s",
        agent.name,
        agent_id,
        body.status,
        body.checks,
        body.error,
    )

    return StatusReportResponse(acknowledged=True)
