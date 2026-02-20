"""Agent container FastAPI application.

Factory function creates the app, wires health/wake/message/spawn/config-update
routers, and runs the boot sequence + AgentRuntime initialization + HeartbeatTimer
start/stop in the lifespan context manager.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI

from agent.agent_runtime import AgentRuntime
from agent.api.health import router as health_router
from agent.api.message import router as message_router
from agent.api.wake import router as wake_router
from agent.boot import boot_agent
from agent.config import get_settings
from agent.heartbeat import HeartbeatTimer

logger = logging.getLogger(__name__)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Run the agent boot sequence and initialize the AgentRuntime.

    Sets app.state fields that the health endpoint reads:
    - boot_status: 'starting' -> 'healthy' | 'unhealthy'
    - agent_id: UUID of this agent
    - browser_connected: result of browser sidecar health check
    - model_provider: model provider string
    - config: full config dict from orchestrator
    - runtime: AgentRuntime instance (available after successful boot)
    - heartbeat: HeartbeatTimer instance (available after successful boot)
    """
    settings = get_settings()

    # Set initial state
    app.state.boot_status = "starting"
    app.state.agent_id = settings.agent_id
    app.state.browser_connected = False
    app.state.model_provider = settings.model_provider
    app.state.config = None
    app.state.runtime = None
    app.state.heartbeat = None

    try:
        # Step 1: Boot sequence (fetch config, self-checks, report status)
        config = await boot_agent(settings)
        app.state.config = config

        # Step 2: Initialize AgentRuntime with Agno Agent + tools
        runtime = AgentRuntime(config, settings)
        await runtime.initialize()
        app.state.runtime = runtime

        # Step 3: Create activity logging callback (fire-and-forget via httpx)
        async def log_activity(event_type: str, details: dict) -> None:
            try:
                async with httpx.AsyncClient(timeout=5) as client:
                    await client.post(
                        f"{settings.orchestrator_url}/api/v1/internal/agents/{settings.agent_id}/activities",
                        json={
                            "event_type": event_type,
                            "summary": f"Heartbeat: {event_type}",
                            "details": details,
                        },
                    )
            except Exception:
                pass  # Activity logging must never block

        # Step 4: Create and start heartbeat timer
        heartbeat = HeartbeatTimer(
            runtime=runtime,
            interval=config.get("heartbeat_interval_seconds", 300),
            prompt=config.get(
                "heartbeat_prompt",
                "Check your assigned tasks and projects for work that needs attention.\n\n"
                "Use list_my_tasks and list_my_projects to see current assignments. "
                "Read your memory to recall what you did previously and avoid re-doing completed work.\n\n"
                "For each assigned project, check for a coordination doc at "
                "/workspace/projects/{project_id}/.botcrew/coordination.md using read_file. "
                "If none exists and you have project goals, create one and draft an initial plan. "
                "If one exists, check your assigned work items and execute them via self_invoke.\n\n"
                "For each task that needs work, use self_invoke with a focused instruction "
                "describing exactly what to do. Each sub-call runs independently with full tool access.\n\n"
                "When nothing needs attention, consider improving yourself -- reflect on recent work, "
                "update your identity or personality, or refine this heartbeat prompt.\n\n"
                "Only send messages to channels when you have something meaningful to share.",
            ),
            on_activity=log_activity,
        )
        runtime.set_heartbeat(heartbeat)  # Wire heartbeat ref into runtime + SelfTools

        if config.get("heartbeat_enabled", True):
            await heartbeat.start()

        app.state.heartbeat = heartbeat

        app.state.boot_status = "healthy"
        app.state.browser_connected = True
        logger.info("Agent '%s' boot complete -- status: healthy", settings.agent_name)
    except Exception as exc:
        app.state.boot_status = "unhealthy"
        logger.error("Agent '%s' boot failed: %s", settings.agent_name, exc)

    yield

    # Shutdown: stop heartbeat timer cleanly
    if app.state.heartbeat is not None:
        await app.state.heartbeat.stop()

    logger.info("Agent '%s' shutting down", settings.agent_name)


def create_app() -> FastAPI:
    """Create and configure the agent FastAPI application."""
    from agent.api.config_update import router as config_update_router
    from agent.api.evaluate import router as evaluate_router
    from agent.api.spawn import router as spawn_router

    app = FastAPI(
        title="Botcrew Agent",
        description="AI agent container runtime",
        version="1.0.0",
        lifespan=lifespan,
        docs_url=None,
        redoc_url=None,
    )

    app.include_router(health_router)
    app.include_router(wake_router)
    app.include_router(message_router)
    app.include_router(spawn_router)
    app.include_router(evaluate_router)
    app.include_router(config_update_router)

    return app
