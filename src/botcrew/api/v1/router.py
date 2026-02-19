"""V1 API router aggregating all sub-routers."""

from fastapi import APIRouter

from botcrew.api.v1.agents.router import router as agents_router
from botcrew.api.v1.channels.router import router as channels_router
from botcrew.api.v1.integrations.router import router as integrations_router
from botcrew.api.v1.internal.router import router as internal_router
from botcrew.api.v1.projects.router import router as projects_router
from botcrew.api.v1.secrets.router import router as secrets_router
from botcrew.api.v1.tasks.router import router as tasks_router
from botcrew.api.v1.skills.router import router as skills_router
from botcrew.api.v1.system.router import router as system_router

v1_router = APIRouter()
v1_router.include_router(system_router, prefix="/system", tags=["system"])
v1_router.include_router(agents_router, prefix="/agents", tags=["agents"])
v1_router.include_router(channels_router, prefix="/channels", tags=["channels"])
v1_router.include_router(projects_router, prefix="/projects", tags=["projects"])
v1_router.include_router(tasks_router, prefix="/tasks", tags=["tasks"])
v1_router.include_router(skills_router, prefix="/skills", tags=["skills"])
v1_router.include_router(secrets_router, prefix="/secrets", tags=["secrets"])
v1_router.include_router(integrations_router, prefix="/integrations", tags=["integrations"])
v1_router.include_router(internal_router, prefix="/internal", tags=["internal"])
