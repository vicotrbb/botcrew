"""Internal API endpoints for agent container communication.

These endpoints are cluster-internal only -- called by agent containers
during boot (to fetch configuration), runtime (to report status), and
for self-modification and activity logging.
Not intended for external API consumers.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from botcrew.api.deps import get_db, get_pod_manager
from botcrew.models.agent import Agent
from botcrew.models.project import Project, ProjectAgent, ProjectFile
from botcrew.models.skill import Skill
from botcrew.schemas.internal import (
    ActivityCreateRequest,
    ActivityCreateResponse,
    BootConfigResponse,
    SelfInfoResponse,
    SelfUpdateRequest,
    SelfUpdateResponse,
    SkillCreateFromAgentRequest,
    StatusReportRequest,
    StatusReportResponse,
)
from botcrew.services.activity_service import ActivityService
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

    # Fetch active skill summaries for boot-time awareness
    skills_result = await db.execute(
        select(Skill.name, Skill.description)
        .where(Skill.is_active.is_(True))
        .order_by(Skill.name)
    )
    skill_summaries = [
        {"name": row.name, "description": row.description}
        for row in skills_result.all()
    ]

    return BootConfigResponse(
        agent_id=str(agent.id),
        name=agent.name,
        identity=agent.identity,
        personality=agent.personality,
        model_provider=agent.model_provider,
        model_name=agent.model_name,
        heartbeat_prompt=agent.heartbeat_prompt,
        heartbeat_interval_seconds=agent.heartbeat_interval_seconds,
        heartbeat_enabled=agent.heartbeat_enabled,
        memory=agent.memory,
        secrets=secrets,
        skills=skill_summaries,
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


@router.get("/agents/{agent_id}/self")
async def get_self_info(
    agent_id: str,
    db: AsyncSession = Depends(get_db),
) -> SelfInfoResponse:
    """Return the agent's current self-modifiable configuration.

    Called by SelfTools.get_self_info() so the agent can read its own
    identity, personality, heartbeat config, and enabled state.
    """
    agent = await db.get(Agent, agent_id)
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")

    return SelfInfoResponse(
        agent_id=str(agent.id),
        name=agent.name,
        identity=agent.identity,
        personality=agent.personality,
        heartbeat_prompt=agent.heartbeat_prompt,
        heartbeat_interval_seconds=agent.heartbeat_interval_seconds,
        heartbeat_enabled=agent.heartbeat_enabled,
    )


@router.patch("/agents/{agent_id}/self")
async def self_update(
    agent_id: str,
    body: SelfUpdateRequest,
    db: AsyncSession = Depends(get_db),
) -> SelfUpdateResponse:
    """Update the agent's self-modifiable fields.

    Accepts a partial update -- only provided (non-None) fields are
    applied. The ``name`` field is deliberately excluded from the schema
    so agents can never rename themselves.

    Logs an activity record for each changed field via ActivityService.
    """
    agent = await db.get(Agent, agent_id)
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Identify which fields the agent is updating
    update_data = body.model_dump(exclude_none=True)
    fields_updated: list[str] = []

    for field, value in update_data.items():
        setattr(agent, field, value)
        fields_updated.append(field)

    if not fields_updated:
        return SelfUpdateResponse(status="no_change", fields_updated=[])

    await db.flush()

    # Log an activity for each field changed
    activity_service = ActivityService(db)
    for field in fields_updated:
        await activity_service.log_activity(
            agent_id=agent_id,
            event_type=f"self_{field}_update",
            summary=f"Agent modified its own {field}",
        )

    await db.commit()

    logger.info(
        "Agent '%s' (%s) self-updated fields: %s",
        agent.name,
        agent_id,
        fields_updated,
    )

    return SelfUpdateResponse(fields_updated=fields_updated)


@router.post("/agents/{agent_id}/activities")
async def create_activity(
    agent_id: str,
    body: ActivityCreateRequest,
    db: AsyncSession = Depends(get_db),
) -> ActivityCreateResponse:
    """Log an agent activity record.

    Fire-and-forget endpoint called by agent tools to record activities
    such as heartbeat wakes, messages sent, tool usage, etc.
    """
    agent = await db.get(Agent, agent_id)
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")

    activity_service = ActivityService(db)
    activity = await activity_service.log_activity(
        agent_id=agent_id,
        event_type=body.event_type,
        summary=body.summary,
        details=body.details,
    )

    if activity is None:
        raise HTTPException(
            status_code=500,
            detail="Failed to create activity record",
        )

    await db.commit()

    return ActivityCreateResponse(
        id=str(activity.id),
        event_type=activity.event_type,
        created_at=str(activity.created_at),
    )


# ---------------------------------------------------------------------------
# Internal skill endpoints (Phase 6)
# ---------------------------------------------------------------------------


@router.get("/agents/{agent_id}/skills")
async def list_agent_skills(
    agent_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """List all active skills (name + description) for agent toolkit access.

    Returns a lightweight summary list so agents know which skills are
    available without loading full bodies.
    """
    result = await db.execute(
        select(Skill).where(Skill.is_active.is_(True)).order_by(Skill.name)
    )
    skills = result.scalars().all()
    return {"data": [{"name": s.name, "description": s.description} for s in skills]}


@router.get("/agents/{agent_id}/skills/{skill_name}")
async def get_agent_skill(
    agent_id: str,
    skill_name: str,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Load a single skill by name with full body content.

    Used by SkillTools.load_skill() to fetch the complete markdown body
    of a skill for the agent to execute.
    """
    result = await db.execute(
        select(Skill).where(
            Skill.name == skill_name.lower(), Skill.is_active.is_(True)
        )
    )
    skill = result.scalar_one_or_none()
    if skill is None:
        raise HTTPException(
            status_code=404, detail=f"Skill not found: {skill_name}"
        )
    return {
        "data": {
            "name": skill.name,
            "description": skill.description,
            "body": skill.body,
        }
    }


@router.post("/agents/{agent_id}/skills", status_code=201)
async def create_agent_skill(
    agent_id: str,
    body: SkillCreateFromAgentRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Create a new skill from an agent.

    Allows agents to contribute skills to the global library.
    Logs an activity record for audit trail.
    """
    skill = Skill(
        name=body.name.strip().lower(),
        description=body.description,
        body=body.body,
    )
    db.add(skill)
    try:
        await db.commit()
    except Exception:
        await db.rollback()
        raise HTTPException(
            status_code=409, detail=f"Skill '{body.name}' already exists"
        )

    activity_service = ActivityService(db)
    await activity_service.log_activity(
        agent_id=agent_id,
        event_type="skill_created",
        summary=f"Created skill: {body.name}",
    )
    await db.commit()

    return {"data": {"name": skill.name, "id": str(skill.id)}}


# ---------------------------------------------------------------------------
# Internal project endpoints (Phase 7)
# ---------------------------------------------------------------------------


@router.get("/agents/{agent_id}/projects")
async def list_agent_projects(
    agent_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """List active project assignments for an agent.

    Returns project details including goals, specs, role_prompt, and
    the workspace path where the project is mounted inside the agent pod.
    """
    result = await db.execute(
        select(ProjectAgent, Project)
        .join(Project, ProjectAgent.project_id == Project.id)
        .where(ProjectAgent.agent_id == agent_id)
        .where(Project.status == "active")
    )
    data = [
        {
            "project_id": str(pa.project_id),
            "project_name": proj.name,
            "goals": proj.goals,
            "specs": proj.specs,
            "role_prompt": pa.role_prompt,
            "workspace_path": f"/workspace/projects/{pa.project_id}",
            "channel_id": str(proj.channel_id) if proj.channel_id else None,
        }
        for pa, proj in result.all()
    ]
    return {"data": data}


@router.get("/agents/{agent_id}/projects/{project_id}")
async def get_agent_project(
    agent_id: str,
    project_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get details for a specific project assigned to an agent.

    Returns 404 if the project does not exist or the agent is not assigned.
    """
    result = await db.execute(
        select(ProjectAgent, Project)
        .join(Project, ProjectAgent.project_id == Project.id)
        .where(ProjectAgent.agent_id == agent_id)
        .where(ProjectAgent.project_id == project_id)
        .where(Project.status == "active")
    )
    row = result.first()
    if row is None:
        raise HTTPException(status_code=404, detail="Project assignment not found")
    pa, proj = row
    return {
        "data": {
            "project_id": str(pa.project_id),
            "project_name": proj.name,
            "goals": proj.goals,
            "specs": proj.specs,
            "role_prompt": pa.role_prompt,
            "workspace_path": f"/workspace/projects/{pa.project_id}",
            "channel_id": str(proj.channel_id) if proj.channel_id else None,
        }
    }


@router.post("/agents/{agent_id}/projects/{project_id}/backup")
async def backup_project_files(
    agent_id: str,
    project_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Backup spec files from agent workspace to the database.

    Reads all ``.md`` files from the project's ``.botcrew/`` directory
    and upserts them into the ``project_files`` table.  Returns the count
    of files backed up.  Gracefully handles missing directories.
    """
    # Verify agent is assigned to this project
    assignment = await db.execute(
        select(ProjectAgent).where(
            ProjectAgent.agent_id == agent_id,
            ProjectAgent.project_id == project_id,
        )
    )
    if assignment.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=403, detail="Agent is not assigned to this project"
        )

    workspace_dir = Path(f"/workspace/projects/{project_id}/.botcrew")
    count = 0

    try:
        if not workspace_dir.is_dir():
            return {"data": {"files_backed_up": 0, "project_id": project_id}}

        for filepath in workspace_dir.glob("*.md"):
            if not filepath.is_file():
                continue
            content = filepath.read_text()
            size = os.path.getsize(filepath)
            last_modified = datetime.fromtimestamp(
                os.path.getmtime(filepath), tz=timezone.utc
            )
            # Relative path from project workspace root
            rel_path = str(filepath.relative_to(f"/workspace/projects/{project_id}"))

            # Upsert: check for existing file record
            existing_result = await db.execute(
                select(ProjectFile).where(
                    ProjectFile.project_id == project_id,
                    ProjectFile.path == rel_path,
                )
            )
            existing = existing_result.scalar_one_or_none()
            if existing:
                existing.content = content
                existing.size = size
                existing.last_modified = last_modified
            else:
                db.add(
                    ProjectFile(
                        project_id=project_id,
                        path=rel_path,
                        content=content,
                        size=size,
                        last_modified=last_modified,
                    )
                )
            count += 1

        await db.commit()
    except (OSError, FileNotFoundError):
        return {"data": {"files_backed_up": 0, "project_id": project_id}}

    return {"data": {"files_backed_up": count, "project_id": project_id}}
