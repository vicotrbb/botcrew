"""System router providing health check and operational endpoints."""

import logging

from fastapi import APIRouter, Request
from sqlalchemy import text

from botcrew.schemas.jsonapi import JSONAPIResource, JSONAPISingleResponse

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/health", response_model=JSONAPISingleResponse)
async def health_check(request: Request) -> JSONAPISingleResponse:
    """Return system health status including database and Redis connectivity.

    Returns a JSON:API formatted response with type ``system-health``,
    reporting the overall status as ``healthy`` (all services up) or
    ``degraded`` (one or more services down).
    """
    # Check database connectivity
    db_ok = False
    try:
        session_factory = request.app.state.session_factory
        async with session_factory() as session:
            await session.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        logger.warning("Database health check failed", exc_info=True)

    # Check Redis connectivity
    redis_ok = False
    try:
        await request.app.state.redis.ping()
        redis_ok = True
    except Exception:
        logger.warning("Redis health check failed", exc_info=True)

    status = "healthy" if (db_ok and redis_ok) else "degraded"

    return JSONAPISingleResponse(
        data=JSONAPIResource(
            type="system-health",
            id="current",
            attributes={
                "status": status,
                "database": "connected" if db_ok else "disconnected",
                "redis": "connected" if redis_ok else "disconnected",
            },
        )
    )
