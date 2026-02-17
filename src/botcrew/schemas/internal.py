"""Pydantic v2 schemas for internal agent API endpoints.

These schemas define the request/response models for cluster-internal endpoints
that agent containers call during boot (to fetch configuration) and runtime
(to report status back to the orchestrator).
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class BootConfigResponse(BaseModel):
    """Full boot configuration returned to an agent container at startup.

    Includes agent identity, model settings, heartbeat config, current memory,
    and all system secrets (API keys). The agent container uses these to
    initialise its model provider and begin operation.
    """

    agent_id: str
    name: str
    identity: str
    personality: str
    model_provider: str
    model_name: str
    heartbeat_prompt: str
    heartbeat_interval_seconds: int
    memory: str
    secrets: dict[str, str] = Field(
        default_factory=dict,
        description="System-wide API keys, e.g. {'ANTHROPIC_API_KEY': 'sk-...'}",
    )


class StatusReportRequest(BaseModel):
    """Status report sent by an agent container after self-checks.

    The agent reports 'ready' when boot completes successfully, 'error'
    if a critical check fails, or 'unhealthy' for degraded operation.
    """

    status: str = Field(
        ...,
        pattern="^(ready|error|unhealthy)$",
        description="One of: ready, error, unhealthy",
    )
    checks: dict[str, bool] | None = Field(
        default=None,
        description="Self-check results, e.g. {'browser': true, 'model': true}",
    )
    error: str | None = Field(
        default=None,
        description="Error message when status is 'error'",
    )


class StatusReportResponse(BaseModel):
    """Acknowledgement returned after processing an agent status report."""

    acknowledged: bool = True
