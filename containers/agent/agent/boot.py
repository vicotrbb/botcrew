"""Agent boot sequence.

Implements the startup flow for an agent container:
1. Fetch configuration from the orchestrator (with exponential backoff)
2. Run self-checks (browser sidecar health, model provider validity)
3. Report status back to the orchestrator
4. Return config for the AgentRuntime (built in Plan 05)
"""

from __future__ import annotations

import asyncio
import logging

import httpx

from agent.config import AgentSettings

logger = logging.getLogger(__name__)

# Supported model providers (mirrors orchestrator's PROVIDER_REGISTRY keys)
SUPPORTED_PROVIDERS = ("openai", "anthropic", "ollama", "glm")


async def fetch_config_with_retry(
    orchestrator_url: str,
    agent_id: str,
    max_retries: int = 10,
) -> dict:
    """Fetch boot configuration from the orchestrator with exponential backoff.

    Calls GET /api/v1/internal/agents/{agent_id}/boot-config and retries
    with exponential backoff (1s, 2s, 4s, ... capped at 60s) if the
    orchestrator is unavailable.

    Args:
        orchestrator_url: Base URL of the orchestrator (e.g. http://botcrew-orchestrator:8000).
        agent_id: UUID of this agent.
        max_retries: Maximum number of retry attempts before giving up.

    Returns:
        Boot configuration dict (BootConfigResponse fields).

    Raises:
        RuntimeError: If all retries are exhausted.
    """
    url = f"{orchestrator_url}/api/v1/internal/agents/{agent_id}/boot-config"
    delay = 1.0
    max_delay = 60.0

    for attempt in range(1, max_retries + 1):
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url)
                response.raise_for_status()
                logger.info(
                    "Fetched boot config from orchestrator (attempt %d/%d)",
                    attempt,
                    max_retries,
                )
                return response.json()
        except (httpx.HTTPError, httpx.TimeoutException) as exc:
            if attempt == max_retries:
                raise RuntimeError(
                    f"Failed to fetch boot config after {max_retries} attempts: {exc}"
                ) from exc
            logger.warning(
                "Boot config fetch failed (attempt %d/%d), retrying in %.1fs: %s",
                attempt,
                max_retries,
                delay,
                exc,
            )
            await asyncio.sleep(delay)
            delay = min(delay * 2, max_delay)

    # Unreachable, but satisfies type checker
    raise RuntimeError("Failed to fetch boot config")  # pragma: no cover


async def run_self_checks(
    browser_url: str,
    model_provider: str,
) -> dict[str, bool]:
    """Run post-boot self-checks.

    Checks:
    - Browser sidecar: GET {browser_url}/api/v1/health returns 200
    - Model provider: provider string is in the supported list

    Each check is independent -- failure returns False for that check
    without raising. The caller decides whether to treat failures as
    critical.

    Args:
        browser_url: Base URL of the browser sidecar (e.g. http://localhost:8001).
        model_provider: Provider string to validate.

    Returns:
        Dict of check results, e.g. {"browser": True, "model": True}.
    """
    checks: dict[str, bool] = {}

    # Check browser sidecar health
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{browser_url}/api/v1/health")
            checks["browser"] = response.status_code == 200
            if checks["browser"]:
                logger.info("Browser sidecar health check passed")
            else:
                logger.warning(
                    "Browser sidecar returned status %d", response.status_code
                )
    except Exception as exc:
        logger.warning("Browser sidecar health check failed: %s", exc)
        checks["browser"] = False

    # Check model provider validity
    try:
        checks["model"] = model_provider in SUPPORTED_PROVIDERS
        if checks["model"]:
            logger.info("Model provider '%s' is supported", model_provider)
        else:
            logger.warning(
                "Model provider '%s' not in supported list: %s",
                model_provider,
                SUPPORTED_PROVIDERS,
            )
    except Exception as exc:
        logger.warning("Model provider check failed: %s", exc)
        checks["model"] = False

    return checks


async def report_status(
    orchestrator_url: str,
    agent_id: str,
    status: str,
    checks: dict[str, bool],
) -> None:
    """Report agent status back to the orchestrator.

    Calls POST /api/v1/internal/agents/{agent_id}/status with the
    boot result. If the call fails, logs a warning but does NOT crash --
    the agent can still function without the orchestrator acknowledging
    its status.

    Args:
        orchestrator_url: Base URL of the orchestrator.
        agent_id: UUID of this agent.
        status: One of 'ready', 'error', 'unhealthy'.
        checks: Self-check results dict.
    """
    url = f"{orchestrator_url}/api/v1/internal/agents/{agent_id}/status"
    body = {"status": status, "checks": checks}

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, json=body)
            response.raise_for_status()
            logger.info(
                "Reported status '%s' to orchestrator (checks=%s)", status, checks
            )
    except Exception as exc:
        logger.warning(
            "Failed to report status to orchestrator (non-fatal): %s", exc
        )


async def boot_agent(settings: AgentSettings) -> dict:
    """Execute the full agent boot sequence.

    Steps:
    1. Fetch configuration from the orchestrator (with retry)
    2. Run self-checks (browser sidecar, model provider)
    3. Determine overall status (ready if browser check passes)
    4. Report status to the orchestrator
    5. Return the config dict for AgentRuntime initialization

    Args:
        settings: Agent container settings.

    Returns:
        Boot configuration dict from the orchestrator.
    """
    logger.info("Starting boot sequence for agent '%s' (%s)", settings.agent_name, settings.agent_id)

    # Step 1: Fetch config from orchestrator
    logger.info("Step 1: Fetching boot config from orchestrator")
    config = await fetch_config_with_retry(
        settings.orchestrator_url, settings.agent_id
    )

    # Step 2: Run self-checks
    logger.info("Step 2: Running self-checks")
    checks = await run_self_checks(
        settings.browser_sidecar_url, config["model_provider"]
    )

    # Step 3: Determine status -- browser is critical for agent operation
    if checks.get("browser", False):
        status = "ready"
    else:
        status = "error"
    logger.info("Step 3: Boot status determined as '%s'", status)

    # Step 4: Report status to orchestrator
    logger.info("Step 4: Reporting status to orchestrator")
    await report_status(
        settings.orchestrator_url, settings.agent_id, status, checks
    )

    # Step 5: Return config for AgentRuntime (Plan 05)
    logger.info("Boot sequence complete for agent '%s'", settings.agent_name)
    return config
