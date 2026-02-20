"""AgentRuntime -- Agno Agent wrapper for the agent container.

Wraps an Agno ``Agent`` instance with all twelve toolkits (ShellTools,
SleepTools, FileTools, BrowserTools, MemoryTools, SelfTools,
CommunicationTools, CodingTools, DuckDuckGoTools, SkillTools,
ProjectTools, TaskTools), providing a ``process_message()`` interface
used by /message, /wake, and heartbeat.

Sub-instances are spawned via ``spawn_sub_instance()`` which creates a
fresh isolated Agent with the same model and tools but an independent
session.  Sub-instances cannot spawn further sub-instances (depth=1
enforcement via ``is_sub_call`` flag on SelfTools).

The runtime is initialised during the FastAPI lifespan startup, after
the boot sequence has fetched configuration from the orchestrator.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any

from agno.agent import Agent
from agno.db.sqlite import SqliteDb
from agno.tools.sleep import SleepTools
from agno.tools.file import FileTools
from agno.tools.shell import ShellTools
from agno.tools.coding import CodingTools
from agno.tools.duckduckgo import DuckDuckGoTools

from agent.config import AgentSettings
from agent.model_factory import create_model
from agent.tools.browser_tools import BrowserTools
from agent.tools.communication_tools import CommunicationTools
from agent.tools.memory_tools import MemoryTools
from agent.tools.self_tools import SelfTools
from agent.tools.project_tools import ProjectTools
from agent.tools.skill_tools import SkillTools
from agent.tools.task_tools import TaskTools

logger = logging.getLogger(__name__)

COLLABORATION_INSTRUCTIONS = """

## Multi-Agent Collaboration

When you are assigned to a project with other agents, you work as a team.
The coordination doc at `/workspace/projects/{project_id}/.botcrew/coordination.md`
is the single source of truth for project collaboration state.

### Discovery
- During heartbeat, check each assigned project for a coordination doc:
  `/workspace/projects/{project_id}/.botcrew/coordination.md`
- If NO coordination doc exists, you are the first agent. Create it using the template below,
  draft an initial plan based on the project goals, and announce yourself in the project channel.
- If a coordination doc exists, read it to understand current state. If you are not listed in the
  Team section, add yourself and announce in the project channel. Then claim available work.

### Working Together
- Claim available work items by editing the coordination doc (assign your name to unclaimed items).
- Before claiming work, re-read the coordination doc to check if another agent took it.
- Use self_invoke to spawn focused sub-calls for actual implementation work.
  Include the FULL absolute path in the instruction:
  `/workspace/projects/{project_id}/.botcrew/coordination.md`
- Update the coordination doc immediately when you complete a work item (mark checkbox, add note).
- Share significant progress, questions, and decisions in the project channel.

### Communication Discipline
- Only send a message when it adds NEW information or moves the project forward.
- Do NOT reply just to acknowledge. "Got it" or "Sounds good" wastes attention.
- Do NOT repeat information another agent has already shared.
- Before replying, ask: "Does this response contain new information?" If not, do not send it.
- After processing messages from a channel, mark them as read so you do not re-process them.

### Completion
- When all work items in the coordination doc are complete, announce a completion summary
  in the project channel.
- Use update_project_status to mark the project as 'complete' and add a summary note.

### Coordination Doc Template
When creating a new coordination doc, use this format:

```
# Project Coordination: {project_name}

## Status
Current phase: planning
Last updated: {ISO_TIMESTAMP} by {your_name}

## Team
| Agent | Role | Status | Joined |
|-------|------|--------|--------|
| {your_name} | Lead (first to join) | available | {ISO_TIMESTAMP} |

## Plan
> Status: Draft -- awaiting team review

{Your initial plan based on project goals}

## Work Items
No work items yet -- pending plan approval.

## Decisions
No decisions yet.

## Progress Log
- {ISO_TIMESTAMP} [{your_name}]: Created coordination doc and drafted initial plan.
```
"""


class AgentRuntime:
    """Core runtime wrapping an Agno Agent with all twelve toolkits.

    Lifecycle:
    1. ``__init__`` stores config, settings, sub-instance tracking
    2. ``initialize()`` creates the Agno Agent with all toolkits
    3. ``set_heartbeat()`` links the HeartbeatTimer after both objects exist
    4. ``process_message()`` runs user/heartbeat input through the agent
    5. ``spawn_sub_instance()`` creates isolated sub-agents for parallel work
    """

    def __init__(self, config: dict[str, Any], settings: AgentSettings) -> None:
        """Store boot configuration and settings.

        Args:
            config: Boot config dict from the orchestrator (contains name,
                    identity, personality, model_provider, model_name,
                    secrets, heartbeat_prompt, agent_id, etc.).
            settings: Agent container settings (URLs, ports).
        """
        self.config = config
        self.settings = settings
        self._agent: Agent | None = None
        self._heartbeat: Any | None = None
        self._self_tools: SelfTools | None = None
        self._active_sub_instances = 0

    async def initialize(self) -> None:
        """Create the Agno Agent instance with model and tools.

        Creates the AI model via the local model factory, builds
        instructions from identity + personality + skill summaries +
        project assignments + task assignments, and registers all nine
        toolkits (Browser, Memory, Self, Communication, Coding,
        DuckDuckGo, Skills, Projects, Tasks).
        """
        logger.info("Initializing AgentRuntime for '%s'", self.config["name"])

        # Ensure agent personal workspace directory exists
        agent_workspace = Path(f"/workspace/agents/{self.settings.agent_id}")
        try:
            agent_workspace.mkdir(parents=True, exist_ok=True)
        except OSError:
            logger.warning(
                "Could not create agent workspace directory: %s", agent_workspace
            )

        # SQLite database for conversation history persistence
        agent_db = SqliteDb(
            db_file=str(agent_workspace / "history.db"),
        )

        # Create the AI model
        model = create_model(
            self.config["model_provider"],
            self.config["model_name"],
            self.config.get("secrets", {}),
        )

        # Build instructions from identity and personality
        identity = self.config.get("identity", "") or ""
        personality = self.config.get("personality", "") or ""

        parts = [p for p in (identity, personality) if p.strip()]
        instructions = "\n".join(parts) if parts else None

        # Inject skill summaries into system prompt
        skills = self.config.get("skills", [])
        if skills:
            skills_section = "\n\n## Available Skills\n"
            skills_section += (
                "Use load_skill(name) to get full instructions " "for any skill.\n\n"
            )
            for s in skills:
                skills_section += f"- **{s['name']}**: {s['description']}\n"
            if instructions:
                instructions += skills_section
            else:
                instructions = skills_section.strip()

        # Inject project assignments into system prompt
        projects = self.config.get("projects", [])
        if projects:
            projects_section = "\n\n## Assigned Projects\n"
            projects_section += (
                "You are assigned to the following projects. "
                "During heartbeat, check each project for work. "
                "Use project_tools to get details and backup files.\n\n"
            )
            for p in projects:
                projects_section += (
                    f"- **{p['project_name']}** (workspace: {p['workspace_path']})"
                )
                if p.get("role_prompt"):
                    projects_section += f"\n  Role: {p['role_prompt']}"
                if p.get("goals"):
                    # Truncate long goals to first 200 chars for prompt
                    goals_preview = p["goals"][:200]
                    if len(p["goals"]) > 200:
                        goals_preview += "..."
                    projects_section += f"\n  Goals: {goals_preview}"
                projects_section += "\n"
            if instructions:
                instructions += projects_section
            else:
                instructions = projects_section.strip()

        # Inject task assignments into system prompt
        tasks = self.config.get("tasks", [])
        if tasks:
            tasks_section = "\n\n## Assigned Tasks\n"
            tasks_section += (
                "You have tasks assigned. Use task_tools to get full details "
                "and update status when complete.\n\n"
            )
            for t in tasks:
                status = t.get("status", "unknown")
                tasks_section += f"- **{t['task_name']}** [{status}]"
                desc = t.get("description")
                if desc:
                    tasks_section += f" -- {desc}"
                tasks_section += "\n"
            if instructions:
                instructions += tasks_section
            else:
                instructions = tasks_section.strip()

        # Inject collaboration instructions (always present -- active when agent has multi-agent projects)
        if instructions:
            instructions += COLLABORATION_INSTRUCTIONS
        else:
            instructions = COLLABORATION_INSTRUCTIONS.strip()

        # Create toolkits
        self._self_tools = SelfTools(
            orchestrator_url=self.settings.orchestrator_url,
            agent_id=self.settings.agent_id,
            runtime=self,
            heartbeat=self._heartbeat,  # May be None at init, updated via set_heartbeat
        )

        tools = [
            ShellTools(),
            SleepTools(),
            FileTools(),
            BrowserTools(browser_url=self.settings.browser_sidecar_url),
            MemoryTools(
                orchestrator_url=self.settings.orchestrator_url,
                agent_id=self.settings.agent_id,
            ),
            self._self_tools,
            CommunicationTools(
                orchestrator_url=self.settings.orchestrator_url,
                agent_id=self.settings.agent_id,
            ),
            CodingTools(
                base_dir=Path(f"/workspace/agents/{self.settings.agent_id}"),
                restrict_to_base_dir=False,  # Agent can access project dirs too
                all=True,
                shell_timeout=120,
                max_lines=2000,
                max_bytes=50_000,
            ),
            DuckDuckGoTools(
                enable_search=True,
                enable_news=True,
                timeout=10,
                fixed_max_results=10,
            ),
            SkillTools(
                orchestrator_url=self.settings.orchestrator_url,
                agent_id=self.settings.agent_id,
            ),
            ProjectTools(
                orchestrator_url=self.settings.orchestrator_url,
                agent_id=self.settings.agent_id,
            ),
            TaskTools(
                orchestrator_url=self.settings.orchestrator_url,
                agent_id=self.settings.agent_id,
            ),
        ]

        # Create Agno Agent with tools
        self._agent = Agent(
            model=model,
            name=self.config["name"],
            description=self.config.get("identity", ""),
            instructions=instructions,
            tools=tools,
            db=agent_db,
            add_history_to_context=True,
            num_history_runs=3,
            add_datetime_to_context=True,
            markdown=True,
        )

        logger.info("AgentRuntime initialized successfully")

    def set_heartbeat(self, heartbeat: Any) -> None:
        """Wire the HeartbeatTimer reference into runtime and SelfTools.

        Called from the lifespan after both the runtime and heartbeat
        timer exist (circular dependency resolution: runtime is created
        before heartbeat, heartbeat needs runtime, so we link after both
        are constructed).
        """
        self._heartbeat = heartbeat
        if self._self_tools is not None:
            self._self_tools._heartbeat = heartbeat

    def update_instructions(self) -> None:
        """Rebuild and apply agent instructions from current config.

        Called after SelfTools updates identity/personality in config
        to ensure the Agno Agent uses the latest values on the next
        ``arun()`` call.  Skill summaries are re-injected to survive
        identity/personality changes.
        """
        if self._agent is None:
            return

        identity = self.config.get("identity", "") or ""
        personality = self.config.get("personality", "") or ""
        parts = [p for p in (identity, personality) if p.strip()]
        self._agent.instructions = "\n".join(parts) if parts else None

        # Re-inject skill summaries after identity/personality rebuild
        skills = self.config.get("skills", [])
        if skills:
            skills_section = "\n\n## Available Skills\n"
            skills_section += (
                "Use load_skill(name) to get full instructions " "for any skill.\n\n"
            )
            for s in skills:
                skills_section += f"- **{s['name']}**: {s['description']}\n"
            if self._agent.instructions:
                self._agent.instructions += skills_section
            else:
                self._agent.instructions = skills_section.strip()

        # Re-inject project assignments after identity/personality rebuild
        projects = self.config.get("projects", [])
        if projects:
            projects_section = "\n\n## Assigned Projects\n"
            projects_section += (
                "You are assigned to the following projects. "
                "During heartbeat, check each project for work. "
                "Use project_tools to get details and backup files.\n\n"
            )
            for p in projects:
                projects_section += (
                    f"- **{p['project_name']}** (workspace: {p['workspace_path']})"
                )
                if p.get("role_prompt"):
                    projects_section += f"\n  Role: {p['role_prompt']}"
                if p.get("goals"):
                    goals_preview = p["goals"][:200]
                    if len(p["goals"]) > 200:
                        goals_preview += "..."
                    projects_section += f"\n  Goals: {goals_preview}"
                projects_section += "\n"
            if self._agent.instructions:
                self._agent.instructions += projects_section
            else:
                self._agent.instructions = projects_section.strip()

        # Re-inject task assignments after identity/personality rebuild
        tasks = self.config.get("tasks", [])
        if tasks:
            tasks_section = "\n\n## Assigned Tasks\n"
            tasks_section += (
                "You have tasks assigned. Use task_tools to get full details "
                "and update status when complete.\n\n"
            )
            for t in tasks:
                status = t.get("status", "unknown")
                tasks_section += f"- **{t['task_name']}** [{status}]"
                desc = t.get("description")
                if desc:
                    tasks_section += f" -- {desc}"
                tasks_section += "\n"
            if self._agent.instructions:
                self._agent.instructions += tasks_section
            else:
                self._agent.instructions = tasks_section.strip()

        # Re-inject collaboration instructions after identity/personality rebuild
        if self._agent.instructions:
            self._agent.instructions += COLLABORATION_INSTRUCTIONS
        else:
            self._agent.instructions = COLLABORATION_INSTRUCTIONS.strip()

    async def process_message(
        self,
        message: str,
        user_id: str | None = None,
    ) -> str:
        """Process a message through the Agno agent.

        Used by both /message (user input) and /wake (heartbeat prompt)
        endpoints -- same processing pipeline per CONTEXT.md.

        Args:
            message: The input text to process.
            user_id: Optional user identifier for conversation tracking.

        Returns:
            The agent's response text.
        """
        if self._agent is None:
            return "Agent is not initialized. Please wait for boot to complete."

        try:
            response = await self._agent.arun(
                message,
                user_id=user_id,
                session_id=self.config.get("agent_id", self.settings.agent_id),
            )
            return response.content
        except Exception as exc:
            logger.error("Error processing message: %s", exc, exc_info=True)
            return (
                "I encountered an error processing your message. " "Please try again."
            )

    # ------------------------------------------------------------------
    # Sub-instance spawning
    # ------------------------------------------------------------------

    async def spawn_sub_instance(self, task_prompt: str) -> str:
        """Spawn a fire-and-forget sub-instance with isolated Agent context.

        Each sub-instance gets a fresh Agno Agent with the same model, tools,
        and instructions but an isolated session. Sub-instances cannot spawn
        further sub-instances (depth=1 enforcement via is_sub_call flag).

        Args:
            task_prompt: The scoped instruction for the sub-instance.

        Returns:
            Status message indicating the sub-instance was spawned.
        """
        self._active_sub_instances += 1
        task = asyncio.create_task(self._run_sub_instance(task_prompt))
        task.add_done_callback(lambda _: self._on_sub_instance_done())
        return "Sub-instance spawned successfully."

    async def _run_sub_instance(self, prompt: str) -> str:
        """Run a sub-instance with its own Agent and session.

        Creates a fresh Agno Agent with the same model and tools (but
        SelfTools has is_sub_call=True to prevent recursive spawning).
        Uses a unique session_id for complete isolation.
        """
        import uuid

        try:
            sub_agent = self._create_sub_agent()
            response = await sub_agent.arun(
                prompt,
                session_id=str(uuid.uuid4()),
            )
            return response.content
        except Exception:
            logger.exception("Sub-instance failed for prompt: %s", prompt[:100])
            return ""

    def _on_sub_instance_done(self) -> None:
        """Decrement active sub-instance counter when a task completes."""
        self._active_sub_instances = max(0, self._active_sub_instances - 1)

    def _create_sub_agent(self) -> Agent:
        """Create a fresh Agent for sub-call execution.

        Uses same model, instructions, and tools as parent, but:
        - Fresh session (no shared conversation history)
        - SelfTools has is_sub_call=True (no recursive spawning)
        - No SqliteDb (ephemeral -- sub-call history not persisted)
        """
        model = create_model(
            self.config["model_provider"],
            self.config["model_name"],
            self.config.get("secrets", {}),
        )

        sub_self_tools = SelfTools(
            orchestrator_url=self.settings.orchestrator_url,
            agent_id=self.settings.agent_id,
            runtime=None,
            heartbeat=None,
            is_sub_call=True,
        )

        tools = [
            ShellTools(),
            SleepTools(),
            FileTools(),
            BrowserTools(browser_url=self.settings.browser_sidecar_url),
            MemoryTools(
                orchestrator_url=self.settings.orchestrator_url,
                agent_id=self.settings.agent_id,
            ),
            sub_self_tools,
            CommunicationTools(
                orchestrator_url=self.settings.orchestrator_url,
                agent_id=self.settings.agent_id,
            ),
            CodingTools(
                base_dir=Path(f"/workspace/agents/{self.settings.agent_id}"),
                restrict_to_base_dir=False,
                all=True,
                shell_timeout=120,
                max_lines=2000,
                max_bytes=50_000,
            ),
            DuckDuckGoTools(
                enable_search=True,
                enable_news=True,
                timeout=10,
                fixed_max_results=10,
            ),
            SkillTools(
                orchestrator_url=self.settings.orchestrator_url,
                agent_id=self.settings.agent_id,
            ),
            ProjectTools(
                orchestrator_url=self.settings.orchestrator_url,
                agent_id=self.settings.agent_id,
            ),
            TaskTools(
                orchestrator_url=self.settings.orchestrator_url,
                agent_id=self.settings.agent_id,
            ),
        ]

        return Agent(
            model=model,
            name=self.config["name"],
            description=self.config.get("identity", ""),
            instructions=self._agent.instructions if self._agent else None,
            tools=tools,
            add_datetime_to_context=True,
            markdown=True,
            # No db -- sub-call history is ephemeral
            # No add_history_to_context -- clean slate each sub-call
        )

    @property
    def is_ready(self) -> bool:
        """Return True if the Agno Agent has been initialized."""
        return self._agent is not None
