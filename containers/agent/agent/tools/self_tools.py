"""SelfTools -- Agno toolkit for agent self-modification via orchestrator API.

Enables botcrew agents to introspect and modify their own configuration
(identity, personality, heartbeat prompt, heartbeat interval) through the
orchestrator's internal self endpoints.  Self-modifications persist to the
DB, update the in-memory config, and restart the heartbeat timer when
heartbeat settings change.

Agents can NEVER modify their own name -- name is user-only per CONTEXT.md.

All tools return plain ``str`` results (Agno convention).  Failures are
returned as graceful error strings -- never raised -- so the agent keeps
functioning even when the orchestrator is temporarily unavailable.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx
from agno.tools import Toolkit

logger = logging.getLogger(__name__)


class SelfTools(Toolkit):
    """Agno toolkit wrapping the orchestrator self-modification API.

    The orchestrator exposes self endpoints at::

        GET   /api/v1/internal/agents/{id}/self
        PATCH /api/v1/internal/agents/{id}/self

    And activity logging at::

        POST  /api/v1/internal/agents/{id}/activities
    """

    def __init__(
        self,
        orchestrator_url: str,
        agent_id: str,
        runtime: Any | None = None,
        heartbeat: Any | None = None,
        **kwargs: Any,
    ) -> None:
        self.orchestrator_url = orchestrator_url.rstrip("/")
        self.agent_id = agent_id
        self._runtime = runtime
        self._heartbeat = heartbeat

        super().__init__(
            name="self_tools",
            tools=[
                self.get_self_info,
                self.update_identity,
                self.update_personality,
                self.update_heartbeat_prompt,
                self.update_heartbeat_interval,
            ],
            **kwargs,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _request(
        self,
        method: str,
        path: str,
        json_data: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        """Make a synchronous HTTP request to the orchestrator self API.

        Returns the parsed JSON response on success, or ``None`` on any
        error.  Failures must never crash the agent.
        """
        url = (
            f"{self.orchestrator_url}/api/v1/internal/agents/"
            f"{self.agent_id}{path}"
        )
        try:
            with httpx.Client(timeout=10) as client:
                response = client.request(
                    method=method,
                    url=url,
                    json=json_data,
                )
                response.raise_for_status()
                return response.json()
        except Exception as exc:
            logger.warning(
                "Self API request failed: %s %s -> %s",
                method,
                url,
                exc,
            )
            return None

    def _log_activity(self, event_type: str, summary: str) -> None:
        """Fire-and-forget activity logging via orchestrator API.

        POST /api/v1/internal/agents/{id}/activities with event_type and
        summary.  All exceptions silently caught -- activity logging must
        never block or crash the agent.
        """
        url = (
            f"{self.orchestrator_url}/api/v1/internal/agents/"
            f"{self.agent_id}/activities"
        )
        try:
            with httpx.Client(timeout=5) as client:
                client.post(
                    url,
                    json={"event_type": event_type, "summary": summary},
                )
        except Exception:
            pass  # Activity logging is fire-and-forget

    # ------------------------------------------------------------------
    # Tools
    # ------------------------------------------------------------------

    def get_self_info(self) -> str:
        """Read your current identity, personality, and heartbeat configuration.

        Use this to understand who you are and how you're configured.
        """
        result = self._request("GET", "/self")
        if result is None:
            return "Unable to read self info at this time."
        try:
            data = result.get("data", {}).get("attributes", {})
            parts = [
                f"Name: {data.get('name', 'Unknown')}",
                f"Identity: {data.get('identity', 'Not set')}",
                f"Personality: {data.get('personality', 'Not set')}",
                f"Heartbeat prompt: {data.get('heartbeat_prompt', 'Not set')}",
                f"Heartbeat interval: {data.get('heartbeat_interval_seconds', 'Unknown')} seconds",
            ]
            return "\n".join(parts)
        except Exception as exc:
            logger.error("get_self_info unexpected error: %s", exc)
            return "Unable to read self info at this time."

    def update_identity(self, identity: str) -> str:
        """Update your identity description. This defines who you are and your role. This change is permanent."""
        result = self._request("PATCH", "/self", {"identity": identity})
        if result is None:
            return "Failed to update identity. The orchestrator may be temporarily unavailable."

        # Update in-memory config
        if self._runtime is not None:
            try:
                self._runtime.config["identity"] = identity
            except Exception:
                pass

        self._log_activity(
            "self_identity_update",
            f"Updated identity to: {identity[:200]}",
        )
        return "Identity updated successfully."

    def update_personality(self, personality: str) -> str:
        """Update your personality. This defines how you communicate and behave. This change is permanent."""
        result = self._request(
            "PATCH", "/self", {"personality": personality}
        )
        if result is None:
            return "Failed to update personality. The orchestrator may be temporarily unavailable."

        # Update in-memory config
        if self._runtime is not None:
            try:
                self._runtime.config["personality"] = personality
            except Exception:
                pass

        self._log_activity(
            "self_personality_update",
            f"Updated personality to: {personality[:200]}",
        )
        return "Personality updated successfully."

    def update_heartbeat_prompt(self, prompt: str) -> str:
        """Update your heartbeat prompt -- the instruction you receive each time you wake up.

        This change is permanent.
        """
        result = self._request(
            "PATCH", "/self", {"heartbeat_prompt": prompt}
        )
        if result is None:
            return "Failed to update heartbeat prompt. The orchestrator may be temporarily unavailable."

        # Update in-memory config
        if self._runtime is not None:
            try:
                self._runtime.config["heartbeat_prompt"] = prompt
            except Exception:
                pass

        # Restart heartbeat timer with new prompt
        if self._heartbeat is not None:
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(self._heartbeat.restart(prompt=prompt))
            except RuntimeError:
                pass  # No running loop (shouldn't happen in agent container)

        self._log_activity(
            "self_heartbeat_prompt_update",
            f"Updated heartbeat prompt to: {prompt[:200]}",
        )
        return "Heartbeat prompt updated successfully."

    def update_heartbeat_interval(self, interval_seconds: int) -> str:
        """Update how often you wake up (300-86400 seconds).

        Min 300 seconds (5 min), max 86400 seconds (24 hours). This change is permanent.
        """
        # Client-side validation
        if interval_seconds < 300 or interval_seconds > 86400:
            return (
                "Invalid interval. Must be between 300 seconds (5 minutes) "
                "and 86400 seconds (24 hours)."
            )

        result = self._request(
            "PATCH",
            "/self",
            {"heartbeat_interval_seconds": interval_seconds},
        )
        if result is None:
            return "Failed to update heartbeat interval. The orchestrator may be temporarily unavailable."

        # Update in-memory config
        if self._runtime is not None:
            try:
                self._runtime.config[
                    "heartbeat_interval_seconds"
                ] = interval_seconds
            except Exception:
                pass

        # Restart heartbeat timer with new interval
        if self._heartbeat is not None:
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(
                    self._heartbeat.restart(interval=interval_seconds)
                )
            except RuntimeError:
                pass  # No running loop (shouldn't happen in agent container)

        self._log_activity(
            "self_heartbeat_interval_update",
            f"Updated heartbeat interval to {interval_seconds} seconds",
        )
        return f"Heartbeat interval updated to {interval_seconds} seconds."
