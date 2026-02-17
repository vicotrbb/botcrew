"""SkillTools -- Agno toolkit for accessing the global skills library.

Enables agents to discover, load, and create skills via the orchestrator's
internal API. Skills are markdown instructions that any agent can follow.

All tools return plain ``str`` results (Agno convention). Failures are
returned as graceful error strings -- never raised.
"""

from __future__ import annotations

import logging

import httpx
from agno.tools import Toolkit

logger = logging.getLogger(__name__)


class SkillTools(Toolkit):
    """Agno toolkit wrapping the orchestrator internal skills API.

    The orchestrator exposes skill endpoints at::

        GET  /api/v1/internal/agents/{id}/skills          (list skills)
        GET  /api/v1/internal/agents/{id}/skills/{name}    (load skill)
        POST /api/v1/internal/agents/{id}/skills           (create skill)

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
            name="skill_tools",
            tools=[self.list_skills, self.load_skill, self.create_skill],
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
        Skill API failures must never crash the agent.
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
                "Skill API request failed: %s %s -> %s",
                method,
                url,
                exc,
            )
            return None

    # ------------------------------------------------------------------
    # Tools
    # ------------------------------------------------------------------

    def list_skills(self) -> str:
        """List all available skills with names and descriptions.

        Use this to discover what skills exist before loading one.
        """
        url = (
            f"{self.orchestrator_url}/api/v1/internal/agents/"
            f"{self.agent_id}/skills"
        )
        result = self._request("GET", url)
        if result is None:
            return "Skills are temporarily unavailable."

        skills = result.get("data", [])
        if not skills:
            return "No skills available."

        lines: list[str] = [f"Available skills ({len(skills)}):"]
        for s in skills:
            lines.append(f"- {s['name']}: {s['description']}")
        return "\n".join(lines)

    def load_skill(self, skill_name: str) -> str:
        """Load full instructions for a skill by name.

        Call this to get detailed instructions before performing a task.
        """
        if not skill_name or not skill_name.strip():
            return "Skill name is required."

        name = skill_name.strip().lower()
        url = (
            f"{self.orchestrator_url}/api/v1/internal/agents/"
            f"{self.agent_id}/skills/{name}"
        )
        result = self._request("GET", url)
        if result is None:
            return (
                f"Failed to load skill '{name}'. "
                "It may not exist or the service is unavailable."
            )

        data = result.get("data", {})
        return (
            f"# Skill: {data.get('name', name)}\n\n"
            f"{data.get('body', 'No instructions available.')}"
        )

    def create_skill(self, name: str, description: str, body: str) -> str:
        """Create a new skill available to all agents.

        Description max 250 chars. Body is markdown instructions.
        """
        if len(description) > 250:
            return "Description must be 250 characters or fewer."

        url = (
            f"{self.orchestrator_url}/api/v1/internal/agents/"
            f"{self.agent_id}/skills"
        )
        result = self._request(
            "POST",
            url,
            json_data={
                "name": name.strip().lower(),
                "description": description,
                "body": body,
            },
        )
        if result is None:
            return f"Failed to create skill '{name}'. The name may already exist."

        return f"Skill '{name}' created successfully."
