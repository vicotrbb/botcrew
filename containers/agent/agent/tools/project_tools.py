"""ProjectTools -- Agno toolkit for project awareness during heartbeat.

Enables agents to discover assigned projects, read goals/specs, and
trigger backup of spec files from workspace to database.

All tools return plain ``str`` results. Failures are returned as
graceful error strings -- never raised.
"""

from __future__ import annotations

import logging

import httpx
from agno.tools import Toolkit

logger = logging.getLogger(__name__)


class ProjectTools(Toolkit):
    """Agno toolkit wrapping the orchestrator internal projects API.

    The orchestrator exposes project endpoints at::

        GET  /api/v1/internal/agents/{id}/projects              (list projects)
        GET  /api/v1/internal/agents/{id}/projects/{project_id}  (project detail)
        POST /api/v1/internal/agents/{id}/projects/{project_id}/backup (backup)

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
            name="project_tools",
            tools=[
                self.list_my_projects,
                self.get_project_details,
                self.backup_spec_files,
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
        Project API failures must never crash the agent.
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
                "Project API request failed: %s %s -> %s",
                method,
                url,
                exc,
            )
            return None

    # ------------------------------------------------------------------
    # Tools
    # ------------------------------------------------------------------

    def list_my_projects(self) -> str:
        """List all projects you are assigned to with their goals and workspace paths."""
        url = (
            f"{self.orchestrator_url}/api/v1/internal/agents/"
            f"{self.agent_id}/projects"
        )
        result = self._request("GET", url)
        if result is None:
            return "Project information is temporarily unavailable."

        projects = result.get("data", [])
        if not projects:
            return "No projects assigned."

        lines: list[str] = [f"Your projects ({len(projects)}):"]
        for p in projects:
            lines.append(
                f"- {p.get('project_name', 'Unnamed')} "
                f"(ID: {p.get('project_id', 'unknown')})"
            )
            goals = p.get("goals") or "No goals set"
            lines.append(f"  Goals: {goals}")
            lines.append(f"  Workspace: {p.get('workspace_path', 'unknown')}")
            channel = p.get("channel_id") or "No channel"
            lines.append(f"  Channel: {channel}")
        return "\n".join(lines)

    def get_project_details(self, project_id: str) -> str:
        """Get full details for a specific project including goals, specs, and role."""
        url = (
            f"{self.orchestrator_url}/api/v1/internal/agents/"
            f"{self.agent_id}/projects/{project_id}"
        )
        result = self._request("GET", url)
        if result is None:
            return "Project not found or not assigned to you."

        data = result.get("data", {})
        lines: list[str] = [
            f"# Project: {data.get('project_name', 'Unnamed')}",
            "",
            f"**ID:** {data.get('project_id', project_id)}",
            f"**Workspace:** {data.get('workspace_path', 'unknown')}",
            f"**Channel:** {data.get('channel_id') or 'No channel'}",
            "",
        ]

        goals = data.get("goals")
        if goals:
            lines.append(f"## Goals\n{goals}")
            lines.append("")

        specs = data.get("specs")
        if specs:
            lines.append(f"## Specs\n{specs}")
            lines.append("")

        role_prompt = data.get("role_prompt")
        if role_prompt:
            lines.append(f"## Your Role\n{role_prompt}")
            lines.append("")

        return "\n".join(lines)

    def backup_spec_files(self, project_id: str) -> str:
        """Trigger backup of spec/planning files from project workspace to database."""
        url = (
            f"{self.orchestrator_url}/api/v1/internal/agents/"
            f"{self.agent_id}/projects/{project_id}/backup"
        )
        result = self._request("POST", url)
        if result is None:
            return "Failed to backup spec files."

        count = result.get("backed_up", 0)
        return f"Backed up {count} files for project {project_id}."
