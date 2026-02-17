"""AgentRuntime -- Agno Agent wrapper for the agent container.

Wraps an Agno ``Agent`` instance with BrowserTools, MemoryTools, SelfTools,
and CommunicationTools, providing a ``process_message()`` interface used by
/message, /wake, and heartbeat.

The runtime is initialised during the FastAPI lifespan startup, after
the boot sequence has fetched configuration from the orchestrator.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from agno.agent import Agent

from agent.config import AgentSettings
from agent.model_factory import create_model
from agent.tools.browser_tools import BrowserTools
from agent.tools.communication_tools import CommunicationTools
from agent.tools.memory_tools import MemoryTools
from agent.tools.self_tools import SelfTools

logger = logging.getLogger(__name__)


class AgentRuntime:
    """Core runtime wrapping an Agno Agent with all four toolkits.

    Lifecycle:
    1. ``__init__`` stores config, settings, sub-instance tracking
    2. ``initialize()`` creates the Agno Agent with all toolkits
    3. ``set_heartbeat()`` links the HeartbeatTimer after both objects exist
    4. ``process_message()`` runs user/heartbeat input through the agent
    5. ``spawn_sub_instance()`` fires off a parallel asyncio task
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
        self._max_sub_instances = config.get("max_sub_instances", 3)

    async def initialize(self) -> None:
        """Create the Agno Agent instance with model and tools.

        Creates the AI model via the local model factory, builds
        instructions from identity + personality, and registers all
        four toolkits (Browser, Memory, Self, Communication).
        """
        logger.info("Initializing AgentRuntime for '%s'", self.config["name"])

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

        # Create toolkits
        self._self_tools = SelfTools(
            orchestrator_url=self.settings.orchestrator_url,
            agent_id=self.settings.agent_id,
            runtime=self,
            heartbeat=self._heartbeat,  # May be None at init, updated via set_heartbeat
        )

        tools = [
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
        ]

        # Create Agno Agent with tools
        self._agent = Agent(
            model=model,
            name=self.config["name"],
            description=self.config.get("identity", ""),
            instructions=instructions,
            tools=tools,
            add_history_to_context=True,
            num_history_messages=20,
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
        ``arun()`` call.
        """
        if self._agent is None:
            return

        identity = self.config.get("identity", "") or ""
        personality = self.config.get("personality", "") or ""
        parts = [p for p in (identity, personality) if p.strip()]
        self._agent.instructions = "\n".join(parts) if parts else None

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
                "I encountered an error processing your message. "
                "Please try again."
            )

    # ------------------------------------------------------------------
    # Sub-instance spawning
    # ------------------------------------------------------------------

    async def spawn_sub_instance(self, task_prompt: str) -> str:
        """Spawn a fire-and-forget sub-instance for parallel work.

        Sub-instances run through the same ``process_message()`` pipeline
        and share the same context, tools, and capabilities.

        Args:
            task_prompt: The prompt to process in the sub-instance.

        Returns:
            Status message indicating success or concurrency cap reached.
        """
        if self._active_sub_instances >= self._max_sub_instances:
            return (
                f"Cannot spawn: at maximum ({self._max_sub_instances}) "
                "concurrent sub-instances."
            )
        self._active_sub_instances += 1
        task = asyncio.create_task(self._run_sub_instance(task_prompt))
        task.add_done_callback(lambda _: self._on_sub_instance_done())
        return "Sub-instance spawned successfully."

    async def _run_sub_instance(self, prompt: str) -> str:
        """Run a sub-instance through process_message.

        Exceptions are caught and logged -- sub-instance failures must
        never crash the parent agent.
        """
        try:
            return await self.process_message(prompt)
        except Exception:
            logger.exception("Sub-instance failed")
            return ""

    def _on_sub_instance_done(self) -> None:
        """Decrement active sub-instance counter when a task completes."""
        self._active_sub_instances = max(0, self._active_sub_instances - 1)

    @property
    def is_ready(self) -> bool:
        """Return True if the Agno Agent has been initialized."""
        return self._agent is not None
