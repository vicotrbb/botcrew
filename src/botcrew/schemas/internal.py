"""Pydantic v2 schemas for internal agent API endpoints.

These schemas define the request/response models for cluster-internal endpoints
that agent containers call during boot (to fetch configuration) and runtime
(to report status, read/update self config, and log activities).
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
    heartbeat_enabled: bool
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


# --- Self-modification schemas (Phase 5) ---


class SelfInfoResponse(BaseModel):
    """Current self-modifiable agent configuration.

    Returned by GET /agents/{agent_id}/self for SelfTools.get_self_info().
    """

    agent_id: str
    name: str
    identity: str
    personality: str
    heartbeat_prompt: str
    heartbeat_interval_seconds: int
    heartbeat_enabled: bool


class SelfUpdateRequest(BaseModel):
    """Partial update to agent self-modifiable fields.

    All fields are optional -- only provided fields are updated.
    Note: ``name`` is deliberately EXCLUDED. An agent can never modify
    its own name (per CONTEXT.md design decision).
    """

    identity: str | None = None
    personality: str | None = None
    heartbeat_prompt: str | None = None
    heartbeat_interval_seconds: int | None = Field(
        default=None,
        ge=300,
        le=86400,
        description="Heartbeat interval in seconds (300s min, 86400s max)",
    )


class SelfUpdateResponse(BaseModel):
    """Acknowledgement of a self-update with list of changed fields."""

    status: str = "updated"
    fields_updated: list[str]


class ActivityCreateRequest(BaseModel):
    """Request body for logging an agent activity."""

    event_type: str = Field(..., max_length=50)
    summary: str = ""
    details: dict | None = None


class ActivityCreateResponse(BaseModel):
    """Response after creating an activity record."""

    id: str
    event_type: str
    created_at: str
