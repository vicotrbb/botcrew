"""MemoryTools -- Agno toolkit for persistent agent memory via orchestrator API.

Enables botcrew agents to read and write their freeform memory stored in
Postgres via the orchestrator's memory sub-resource endpoints. Memory
survives across conversations and restarts.

All tools return plain ``str`` results (Agno convention). Failures are
returned as graceful error strings -- never raised -- so the agent keeps
functioning even when memory is temporarily unavailable.
"""

from __future__ import annotations

import logging

import httpx
from agno.tools import Toolkit

logger = logging.getLogger(__name__)


class MemoryTools(Toolkit):
    """Agno toolkit wrapping the orchestrator memory API.

    The orchestrator exposes memory endpoints at::

        GET    /api/v1/agents/{id}/memory
        PUT    /api/v1/agents/{id}/memory
        PATCH  /api/v1/agents/{id}/memory

    All responses use JSON:API format with
    ``data.attributes.content`` carrying the memory text.
    """

    def __init__(
        self,
        orchestrator_url: str,
        agent_id: str,
        **kwargs,
    ):
        self.orchestrator_url = orchestrator_url.rstrip("/")
        self.agent_id = agent_id
        self.default_timeout = 10  # seconds

        super().__init__(
            name="memory_tools",
            tools=[
                self.read_memory,
                self.write_memory,
                self.append_memory,
            ],
            **kwargs,
        )

    # ------------------------------------------------------------------
    # Internal helper
    # ------------------------------------------------------------------

    def _request(
        self,
        method: str,
        path: str,
        json_data: dict | None = None,
    ) -> dict | None:
        """Make a synchronous HTTP request to the orchestrator memory API.

        Returns the parsed JSON response on success, or ``None`` on any
        error.  Memory failures must never crash the agent (Research
        pitfall #4).
        """
        url = (
            f"{self.orchestrator_url}/api/v1/agents/"
            f"{self.agent_id}{path}"
        )
        try:
            with httpx.Client(timeout=self.default_timeout) as client:
                response = client.request(
                    method=method,
                    url=url,
                    json=json_data,
                )
                response.raise_for_status()
                return response.json()
        except Exception as exc:
            logger.warning(
                "Memory API request failed: %s %s -> %s",
                method,
                url,
                exc,
            )
            return None

    # ------------------------------------------------------------------
    # Tools
    # ------------------------------------------------------------------

    def read_memory(self) -> str:
        """Read your freeform memory. This is your persistent memory that survives across conversations and restarts. Use it to remember important information, decisions, and context."""
        try:
            result = self._request("GET", "/memory")
            if result is None:
                return "Memory is temporarily unavailable."
            content = (
                result.get("data", {})
                .get("attributes", {})
                .get("content", "")
            )
            if not content:
                return "Memory is currently empty."
            return content
        except Exception as exc:
            logger.error("read_memory unexpected error: %s", exc)
            return (
                "Memory is temporarily unavailable. "
                "You can still function normally."
            )

    def write_memory(self, content: str) -> str:
        """Replace your entire memory with new content. WARNING: This overwrites everything. Use append_memory to add to existing memory without losing previous content."""
        try:
            result = self._request("PUT", "/memory", {"content": content})
            if result is None:
                return (
                    "Memory is temporarily unavailable. "
                    "You can still function normally."
                )
            return "Memory updated successfully."
        except Exception as exc:
            logger.error("write_memory unexpected error: %s", exc)
            return (
                "Memory is temporarily unavailable. "
                "You can still function normally."
            )

    def append_memory(self, content: str) -> str:
        """Append new content to your existing memory. The new content is added to the end of your current memory with a newline separator. Use this to add new information without losing previous memory."""
        try:
            result = self._request("PATCH", "/memory", {"append": content})
            if result is None:
                return (
                    "Memory is temporarily unavailable. "
                    "You can still function normally."
                )
            return "Memory updated successfully."
        except Exception as exc:
            logger.error("append_memory unexpected error: %s", exc)
            return (
                "Memory is temporarily unavailable. "
                "You can still function normally."
            )
