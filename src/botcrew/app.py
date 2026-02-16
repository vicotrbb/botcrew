"""FastAPI application factory with async lifespan for DB and Redis initialization."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from botcrew.api.v1.router import v1_router
from botcrew.config import get_settings
from botcrew.database import close_db, get_session_factory, init_db
from botcrew.redis import close_redis, init_redis


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage application startup and shutdown lifecycle.

    On startup: initialize database engine, session factory, and Redis client.
    On shutdown: close database engine and Redis client.
    """
    settings = get_settings()

    # Startup
    engine = await init_db(settings.database_url)
    app.state.db_engine = engine
    app.state.session_factory = get_session_factory(engine)
    app.state.redis = await init_redis(settings.redis_url)

    yield

    # Shutdown
    await close_redis(app.state.redis)
    await close_db(engine)


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

    This is the app factory. Uvicorn calls it with the --factory flag:
        uvicorn botcrew.app:create_app --factory
    """
    settings = get_settings()

    app = FastAPI(
        title="Botcrew Orchestrator",
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/api/docs" if settings.debug else None,
        redoc_url="/api/redoc" if settings.debug else None,
    )

    app.include_router(v1_router, prefix="/api/v1")

    return app
