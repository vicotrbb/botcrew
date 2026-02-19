"""TaskTools -- Agno toolkit for agent task management.

Enables agents to discover assigned tasks, read full task context
(including secrets, skills, and collaborating agents), update task
status, and append progress notes.

All tools return plain ``str`` results. Failures are returned as
graceful error strings -- never raised.
"""

from __future__ import annotations

import logging

import httpx
from agno.tools import Toolkit

logger = logging.getLogger(__name__)


class TaskTools(Toolkit):
    """Agno toolkit wrapping the orchestrator internal tasks API.

    The orchestrator exposes task endpoints at::

        GET   /api/v1/internal/agents/{id}/tasks              (list tasks)
        GET   /api/v1/internal/agents/{id}/tasks/{task_id}    (task detail)
        PATCH /api/v1/internal/agents/{id}/tasks/{task_id}    (update task)

    All responses are plain dicts (not JSON:API envelope).
    """

    def __init__(
        self,
        orchestrator_url: str,
        agent_id: str,
        **kwargs,
    ):
        self.orchestrator_url = orchestrator_url.rstrip("/")
        self.agent_id = agent_id

        super().__init__(
            name="task_tools",
            tools=[
                self.list_my_tasks,
                self.get_task_details,
                self.update_task_status,
                self.add_task_note,
            ],
            **kwargs,
        )

    # ------------------------------------------------------------------
    # Internal helper
    # ------------------------------------------------------------------

    def _request(
        self,
        method: str,
        url: str,
        json_data: dict | None = None,
    ) -> dict | None:
        """Make a synchronous HTTP request to the orchestrator API.

        Returns parsed JSON on success, ``None`` on any error.
        Task API failures must never crash the agent.
        """
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
                "Task API request failed: %s %s -> %s",
                method,
                url,
                exc,
            )
            return None

    # ------------------------------------------------------------------
    # Tools
    # ------------------------------------------------------------------

    def list_my_tasks(self) -> str:
        """List all tasks assigned to you with their status and descriptions."""
        url = (
            f"{self.orchestrator_url}/api/v1/internal/agents/"
            f"{self.agent_id}/tasks"
        )
        result = self._request("GET", url)
        if result is None:
            return "Task information is temporarily unavailable."

        tasks = result.get("data", [])
        if not tasks:
            return "No tasks assigned."

        lines: list[str] = [f"Your tasks ({len(tasks)}):"]
        for t in tasks:
            status = t.get("status", "unknown")
            lines.append(
                f"- {t.get('task_name', 'Unnamed')} [{status}] "
                f"(ID: {t.get('task_id', 'unknown')})"
            )
            desc = t.get("description") or "No description"
            lines.append(f"  Description: {desc}")
            lines.append(f"  Channel: {t.get('channel_id') or 'No channel'}")
        return "\n".join(lines)

    def get_task_details(self, task_id: str) -> str:
        """Get full details for a specific task including directive, secrets, skills, and collaborators."""
        url = (
            f"{self.orchestrator_url}/api/v1/internal/agents/"
            f"{self.agent_id}/tasks/{task_id}"
        )
        result = self._request("GET", url)
        if result is None:
            return "Task not found or not assigned to you."

        data = result.get("data", {})
        lines: list[str] = [
            f"# Task: {data.get('task_name', 'Unnamed')}",
            "",
            f"**ID:** {data.get('task_id', task_id)}",
            f"**Status:** {data.get('status', 'unknown')}",
            f"**Channel:** {data.get('channel_id') or 'No channel'}",
            "",
        ]

        description = data.get("description")
        if description:
            lines.append(f"## Description\n{description}")
            lines.append("")

        directive = data.get("directive")
        if directive:
            lines.append(f"## Directive\n{directive}")
            lines.append("")

        notes = data.get("notes")
        if notes:
            lines.append(f"## Notes\n{notes}")
            lines.append("")

        # Show secret key names only (not values) for security in logs
        secrets = data.get("secrets", [])
        if secrets:
            lines.append("## Secrets")
            for s in secrets:
                lines.append(f"- {s.get('key', 'unknown')}")
            lines.append("")

        skills = data.get("skills", [])
        if skills:
            lines.append("## Skills")
            for s in skills:
                lines.append(
                    f"- **{s.get('name', 'unknown')}**: "
                    f"{s.get('description', 'No description')}"
                )
            lines.append("")

        agents = data.get("agents", [])
        if agents:
            lines.append("## Other Agents")
            for a in agents:
                lines.append(f"- {a.get('name', 'unknown')} (ID: {a.get('agent_id', 'unknown')})")
            lines.append("")

        return "\n".join(lines)

    def update_task_status(self, task_id: str, status: str) -> str:
        """Update the status of a task. Use 'done' to mark as complete, 'open' to reopen."""
        url = (
            f"{self.orchestrator_url}/api/v1/internal/agents/"
            f"{self.agent_id}/tasks/{task_id}"
        )
        result = self._request("PATCH", url, json_data={"status": status})
        if result is None:
            return "Failed to update task status."
        return f"Task status updated to {status}."

    def add_task_note(self, task_id: str, note: str) -> str:
        """Append a progress note to a task. Notes are timestamped and attributed to you."""
        url = (
            f"{self.orchestrator_url}/api/v1/internal/agents/"
            f"{self.agent_id}/tasks/{task_id}"
        )
        result = self._request(
            "PATCH",
            url,
            json_data={"note": note, "agent_name": self.agent_id},
        )
        if result is None:
            return "Failed to add note to task."
        return "Note added to task."
