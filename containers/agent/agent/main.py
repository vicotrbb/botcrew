"""Agent container FastAPI application.

Factory function creates the app, wires the health router, and runs
the boot sequence in the lifespan context manager. The AgentRuntime
(built in Plan 05) will also be initialised during lifespan startup.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI

from agent.api.health import router as health_router
from agent.boot import boot_agent
from agent.config import get_settings

logger = logging.getLogger(__name__)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Run the agent boot sequence on startup.

    Sets app.state fields that the health endpoint reads:
    - boot_status: 'starting' -> 'healthy' | 'unhealthy'
    - agent_id: UUID of this agent
    - browser_connected: result of browser sidecar health check
    - model_provider: model provider string
    - boot_config: full config dict from orchestrator
    """
    settings = get_settings()

    # Set initial state
    app.state.boot_status = "starting"
    app.state.agent_id = settings.agent_id
    app.state.browser_connected = False
    app.state.model_provider = settings.model_provider

    try:
        config = await boot_agent(settings)
        app.state.boot_config = config
        app.state.boot_status = "healthy"
        app.state.browser_connected = True  # boot_agent only returns ready if browser check passed
        logger.info("Agent '%s' boot complete -- status: healthy", settings.agent_name)
    except Exception as exc:
        app.state.boot_status = "unhealthy"
        app.state.boot_config = None
        logger.error("Agent '%s' boot failed: %s", settings.agent_name, exc)

    yield

    logger.info("Agent '%s' shutting down", settings.agent_name)


def create_app() -> FastAPI:
    """Create and configure the agent FastAPI application."""
    app = FastAPI(
        title="Botcrew Agent",
        description="AI agent container runtime",
        version="1.0.0",
        lifespan=lifespan,
        docs_url=None,
        redoc_url=None,
    )

    app.include_router(health_router)

    return app
