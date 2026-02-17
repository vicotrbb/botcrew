"""AgentRuntime -- Agno Agent wrapper for the agent container.

Wraps an Agno ``Agent`` instance with BrowserTools and MemoryTools,
providing a ``process_message()`` interface used by both the /message
and /wake endpoints.

The runtime is initialised during the FastAPI lifespan startup, after
the boot sequence has fetched configuration from the orchestrator.
"""

from __future__ import annotations

import logging
from typing import Any

from agno.agent import Agent

from agent.config import AgentSettings
from agent.model_factory import create_model
from agent.tools.browser_tools import BrowserTools
from agent.tools.memory_tools import MemoryTools

logger = logging.getLogger(__name__)


class AgentRuntime:
    """Core runtime wrapping an Agno Agent with browser and memory tools.

    Lifecycle:
    1. ``__init__`` stores config and settings (no Agent yet)
    2. ``initialize()`` creates the Agno Agent instance
    3. ``process_message()`` runs user/heartbeat input through the agent
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

    async def initialize(self) -> None:
        """Create the Agno Agent instance with model and tools.

        Creates the AI model via the local model factory, builds
        instructions from identity + personality, and registers
        BrowserTools and MemoryTools as active toolkits.
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

        # Create Agno Agent with tools
        self._agent = Agent(
            model=model,
            name=self.config["name"],
            description=self.config.get("identity", ""),
            instructions=instructions,
            tools=[
                BrowserTools(browser_url=self.settings.browser_sidecar_url),
                MemoryTools(
                    orchestrator_url=self.settings.orchestrator_url,
                    agent_id=self.settings.agent_id,
                ),
            ],
            add_history_to_context=True,
            num_history_messages=20,
            add_datetime_to_context=True,
            markdown=True,
        )

        logger.info("AgentRuntime initialized successfully")

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

    @property
    def is_ready(self) -> bool:
        """Return True if the Agno Agent has been initialized."""
        return self._agent is not None
