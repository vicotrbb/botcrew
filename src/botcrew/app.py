"""FastAPI application factory with async lifespan for DB, Redis, K8s, WebSocket, and reconciliation."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from botcrew.api.v1.router import v1_router
from botcrew.config import get_settings
from botcrew.database import close_db, get_session_factory, init_db
from botcrew.redis import close_redis, init_redis
from botcrew.services.pod_manager import PodManager
from botcrew.services.reconciliation import ReconciliationLoop
from botcrew.ws.connection_manager import ConnectionManager
from botcrew.ws.pubsub import PubSubManager


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage application startup and shutdown lifecycle.

    On startup: initialize database engine, session factory, Redis client,
    WebSocket connection manager, Redis pub/sub manager, K8s pod manager,
    and reconciliation loop.
    On shutdown: stop reconciliation, pub/sub manager, pod manager, Redis,
    and database (in that order to avoid using closed connections).
    """
    settings = get_settings()

    # Startup -- Database & Redis
    engine = await init_db(settings.database_url)
    app.state.db_engine = engine
    app.state.session_factory = get_session_factory(engine)
    app.state.redis = await init_redis(settings.redis_url)

    # Startup -- WebSocket connection manager (in-process, per-channel tracking)
    connection_manager = ConnectionManager()
    app.state.connection_manager = connection_manager

    # Startup -- Redis pub/sub for WebSocket fan-out (SEPARATE connection from app.state.redis)
    pubsub_manager = PubSubManager(settings.redis_url)

    async def handle_pubsub_message(channel_id: str, data: dict) -> None:
        """Forward Redis pub/sub messages to local WebSocket connections."""
        await connection_manager.send_to_channel(channel_id, data)

    await pubsub_manager.start(handler=handle_pubsub_message)
    app.state.pubsub_manager = pubsub_manager

    # Startup -- K8s Pod Manager
    pod_manager = PodManager(namespace=settings.k8s_namespace)
    await pod_manager.initialize()
    app.state.pod_manager = pod_manager

    # Startup -- Reconciliation Loop
    reconciliation = ReconciliationLoop(
        session_factory=app.state.session_factory,
        pod_manager=pod_manager,
        interval=60,
    )
    await reconciliation.start()
    app.state.reconciliation = reconciliation

    yield

    # Shutdown (reverse order: reconciliation -> pubsub -> pod_manager -> redis -> db)
    await app.state.reconciliation.stop()
    await app.state.pubsub_manager.stop()
    await app.state.pod_manager.close()
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

    # WebSocket router mounted at root (not under /api/v1) because the
    # HTTPRoute in Helm routes /ws/* separately from /api/* traffic.
    from botcrew.api.v1.channels.ws import router as ws_router

    app.include_router(ws_router)

    return app
