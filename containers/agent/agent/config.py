"""Agent container configuration.

Pydantic BaseSettings for the agent container. Environment variables are set
directly in the pod spec (AGENT_ID, AGENT_NAME, MODEL_PROVIDER, etc.) without
a prefix -- unlike the orchestrator which uses BOTCREW_ prefix.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings


class AgentSettings(BaseSettings):
    """Agent container settings loaded from environment variables.

    All env vars are injected by the K8s pod spec (see pod_spec.py).
    No env_prefix is used because the orchestrator already sets the
    exact variable names (AGENT_ID, MODEL_PROVIDER, etc.).
    """

    # Agent identity (set by pod spec)
    agent_id: str
    agent_name: str
    model_provider: str
    model_name: str

    # Orchestrator connection
    orchestrator_url: str = "http://botcrew-orchestrator:8000"

    # Agent HTTP server
    port: int = 8080

    # Browser sidecar (shares pod network via localhost)
    browser_sidecar_url: str = "http://localhost:8001"


@lru_cache
def get_settings() -> AgentSettings:
    """Return cached agent settings instance."""
    return AgentSettings()
