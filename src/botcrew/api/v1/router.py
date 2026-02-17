"""V1 API router aggregating all sub-routers."""

from fastapi import APIRouter

from botcrew.api.v1.agents.router import router as agents_router
from botcrew.api.v1.system.router import router as system_router

v1_router = APIRouter()
v1_router.include_router(system_router, prefix="/system", tags=["system"])
v1_router.include_router(agents_router, prefix="/agents", tags=["agents"])
