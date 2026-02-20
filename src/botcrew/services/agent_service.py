"""Agent business logic service.

Orchestrates database operations and Kubernetes pod lifecycle for agents.
Provides CRUD operations, pod-status-enriched listing, and agent duplication.
"""

from __future__ import annotations

import json
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from botcrew.models.agent import Agent
from botcrew.models.integration import Integration
from botcrew.models.secret import Secret
from botcrew.schemas.pagination import PaginationMeta, decode_cursor
from botcrew.services.model_provider import PROVIDER_REGISTRY, validate_provider_configured
from botcrew.services.pod_manager import PodManager

logger = logging.getLogger(__name__)

DEFAULT_PERSONALITY = (
    "You are a Botcrew agent -- an autonomous AI crew member. You collaborate with "
    "other agents and humans, take initiative on tasks, and evolve your skills and "
    "personality through your work and interactions. You are part of an always-on "
    "workforce that genuinely works together."
)

DEFAULT_HEARTBEAT_PROMPT = (
    "Check your assigned tasks and projects for work that needs attention.\n\n"
    "Use list_my_tasks and list_my_projects to see current assignments. "
    "Read your memory to recall what you did previously and avoid re-doing completed work.\n\n"
    "For each assigned project, check for a coordination doc at "
    "/workspace/projects/{project_id}/.botcrew/coordination.md using read_file. "
    "If none exists and you have project goals, create one and draft an initial plan. "
    "If one exists, check your assigned work items and execute them via self_invoke.\n\n"
    "For each task that needs work, use self_invoke with a focused instruction "
    "describing exactly what to do. Each sub-call runs independently with full tool access.\n\n"
    "When nothing needs attention, consider improving yourself -- reflect on recent work, "
    "update your identity or personality, or refine this heartbeat prompt.\n\n"
    "Only send messages to channels when you have something meaningful to share."
)


class AgentService:
    """Agent lifecycle management with database and Kubernetes orchestration.

    Handles agent CRUD, provider validation, pod creation/deletion,
    and live status enrichment from Kubernetes pod state.

    Args:
        db: Async SQLAlchemy session for database operations.
        pod_manager: Kubernetes pod lifecycle manager.
    """

    def __init__(self, db: AsyncSession, pod_manager: PodManager) -> None:
        self.db = db
        self.pod_manager = pod_manager

    async def get_system_secrets(self) -> dict[str, str]:
        """Query system secrets and active AI provider integration keys.

        Merges from two sources:
        1. The ``secrets`` table (base key-value store)
        2. Active ``ai_provider`` integrations (purpose-built provider UI)

        Integration values override secrets table values.
        """
        # Base secrets from secrets table
        result = await self.db.execute(select(Secret))
        secrets = {s.key: s.value for s in result.scalars().all()}

        # Override/fill from active AI provider integrations
        int_result = await self.db.execute(
            select(Integration).where(
                Integration.integration_type == "ai_provider",
                Integration.is_active.is_(True),
            )
        )
        for integration in int_result.scalars().all():
            try:
                config = json.loads(integration.config)
            except (json.JSONDecodeError, TypeError):
                logger.warning(
                    "Skipping integration '%s': invalid JSON config",
                    integration.name,
                )
                continue

            provider_name = config.get("provider")
            api_key = config.get("api_key")
            if not provider_name or not api_key:
                continue

            provider_reg = PROVIDER_REGISTRY.get(provider_name)
            if not provider_reg:
                continue

            env_key = provider_reg.get("env_key")
            if env_key:
                secrets[env_key] = api_key

        return secrets

    async def create_agent(
        self,
        name: str,
        model_provider: str,
        model_name: str,
        **kwargs: object,
    ) -> Agent:
        """Create a new agent with pod orchestration.

        Validates that the model provider has configured API keys,
        creates the database record, and launches a Kubernetes pod.
        If pod creation fails, the agent is saved in 'error' status
        for the reconciliation loop to pick up.

        Args:
            name: Agent display name.
            model_provider: AI provider (openai, anthropic, ollama, glm).
            model_name: Model identifier for the provider.
            **kwargs: Optional overrides for identity, personality,
                heartbeat_interval_seconds.

        Returns:
            The created Agent instance with populated timestamps.

        Raises:
            ValueError: If the model provider is not configured.
        """
        secrets = await self.get_system_secrets()
        if not validate_provider_configured(model_provider, secrets):
            raise ValueError(
                f"Provider '{model_provider}' is not configured. "
                "Add the required API key via the secrets API."
            )

        agent = Agent(
            name=name,
            model_provider=model_provider,
            model_name=model_name,
            status="creating",
            personality=kwargs.get("personality") or DEFAULT_PERSONALITY,
            identity=str(kwargs.get("identity", "") or ""),
            heartbeat_prompt=DEFAULT_HEARTBEAT_PROMPT,
            heartbeat_interval_seconds=int(
                kwargs.get("heartbeat_interval_seconds", 300) or 300
            ),
        )
        self.db.add(agent)
        await self.db.flush()

        try:
            pod_name = await self.pod_manager.create_agent_pod(agent)
            agent.pod_name = pod_name
            agent.status = "running"
        except Exception:
            agent.status = "error"
            logger.exception("Failed to create pod for agent '%s' (%s)", name, agent.id)

        await self.db.commit()
        await self.db.refresh(agent)
        return agent

    async def list_agents(
        self,
        page_size: int = 20,
        after: str | None = None,
        status_filter: str | None = None,
        sort_by: str = "created_at",
        sort_desc: bool = False,
    ) -> tuple[list[Agent], PaginationMeta]:
        """List agents with cursor-based pagination.

        Args:
            page_size: Maximum number of agents to return.
            after: Opaque cursor for pagination (from previous response).
            status_filter: Optional status value to filter by.
            sort_by: Column to sort by ('created_at' or 'name').
            sort_desc: Whether to sort descending.

        Returns:
            Tuple of (agents list, pagination metadata).
        """
        query = select(Agent)

        if status_filter:
            query = query.where(Agent.status == status_filter)

        if after:
            cursor_created_at, cursor_id = decode_cursor(after)
            if sort_desc:
                query = query.where(
                    (Agent.created_at < cursor_created_at)
                    | (
                        (Agent.created_at == cursor_created_at)
                        & (Agent.id < cursor_id)
                    )
                )
            else:
                query = query.where(
                    (Agent.created_at > cursor_created_at)
                    | (
                        (Agent.created_at == cursor_created_at)
                        & (Agent.id > cursor_id)
                    )
                )

        if sort_by == "name":
            order_col = Agent.name.desc() if sort_desc else Agent.name.asc()
            query = query.order_by(order_col, Agent.id.asc())
        else:
            order_col = (
                Agent.created_at.desc() if sort_desc else Agent.created_at.asc()
            )
            query = query.order_by(order_col, Agent.id.asc())

        query = query.limit(page_size + 1)

        result = await self.db.execute(query)
        agents = list(result.scalars().all())

        has_next = len(agents) > page_size
        if has_next:
            agents = agents[:page_size]

        return agents, PaginationMeta(
            has_next=has_next,
            has_prev=after is not None,
        )

    async def enrich_agents_with_pod_status(
        self, agents: list[Agent]
    ) -> list[Agent]:
        """Overlay actual Kubernetes pod state onto agent status for display.

        Batch-queries all agent pods from Kubernetes and updates the in-memory
        status of each agent based on actual pod phase. Does NOT commit changes
        to the database -- the reconciliation loop (Plan 05) handles persistence.

        The 'idle' status transition is deferred to Phase 5 (Heartbeat + Agent
        Autonomy) where the heartbeat mechanism will set it.

        Args:
            agents: List of Agent instances to enrich.

        Returns:
            The same list with potentially modified .status attributes.
        """
        try:
            actual_pods = await self.pod_manager.list_agent_pods()
        except Exception:
            logger.exception("Failed to list agent pods for status enrichment")
            return agents

        pod_status_by_name: dict[str, str | None] = {
            pod.metadata.name: pod.status.phase for pod in actual_pods
        }

        for agent in agents:
            if agent.status in ("running", "error", "recovering"):
                pod_phase = pod_status_by_name.get(agent.pod_name)
                if pod_phase is None and agent.status == "running":
                    # Pod missing but DB says running -- display as error
                    agent.status = "error"
                elif pod_phase == "Failed":
                    agent.status = "error"
                # "Pending" or already "error" in DB: leave as-is
            # "creating" or "terminating": leave as-is (in-progress transitions)

        return agents

    async def get_agent(self, agent_id: str) -> Agent | None:
        """Get a single agent by ID.

        Args:
            agent_id: UUID of the agent.

        Returns:
            The Agent instance, or None if not found.
        """
        return await self.db.get(Agent, agent_id)

    async def get_agent_with_live_status(self, agent_id: str) -> Agent | None:
        """Get a single agent with live Kubernetes pod status.

        Fetches the agent from the database and enriches its status
        with the actual pod phase from Kubernetes.

        Args:
            agent_id: UUID of the agent.

        Returns:
            The Agent instance with enriched status, or None if not found.
        """
        agent = await self.db.get(Agent, agent_id)
        if agent is None:
            return None

        if agent.pod_name and agent.status in ("running", "error", "recovering"):
            try:
                pod_phase = await self.pod_manager.get_pod_status(agent.pod_name)
                if pod_phase is None and agent.status == "running":
                    agent.status = "error"
                elif pod_phase == "Failed":
                    agent.status = "error"
            except Exception:
                logger.exception(
                    "Failed to get pod status for agent '%s'", agent_id
                )

        return agent

    async def update_agent(self, agent_id: str, **kwargs: object) -> Agent:
        """Update an existing agent's fields.

        If model_provider or model_name is changing, validates that the
        new provider has configured API keys.

        Args:
            agent_id: UUID of the agent to update.
            **kwargs: Fields to update (only non-None values are applied).

        Returns:
            The updated Agent instance.

        Raises:
            ValueError: If agent not found or provider validation fails.
        """
        agent = await self.db.get(Agent, agent_id)
        if agent is None:
            raise ValueError("Agent not found")

        new_provider = kwargs.get("model_provider")
        new_model = kwargs.get("model_name")
        if new_provider or new_model:
            provider = str(new_provider) if new_provider else agent.model_provider
            secrets = await self.get_system_secrets()
            if not validate_provider_configured(provider, secrets):
                raise ValueError(
                    f"Provider '{provider}' is not configured. "
                    "Add the required API key via the secrets API."
                )

        for key, value in kwargs.items():
            if value is not None:
                setattr(agent, key, value)

        await self.db.commit()
        await self.db.refresh(agent)
        return agent

    async def delete_agent(self, agent_id: str) -> None:
        """Delete an agent and its Kubernetes pod.

        CRITICAL ordering: sets status to 'terminating' first (so
        reconciliation skips it), deletes the pod, then removes the
        DB record. Pod is always deleted BEFORE the DB record to
        prevent orphaned pods.

        Args:
            agent_id: UUID of the agent to delete.

        Raises:
            ValueError: If agent not found.
        """
        agent = await self.db.get(Agent, agent_id)
        if agent is None:
            raise ValueError("Agent not found")

        # Mark as terminating so reconciliation loop skips it
        agent.status = "terminating"
        await self.db.commit()

        # Delete pod FIRST -- never orphan a pod
        if agent.pod_name:
            try:
                await self.pod_manager.delete_agent_pod(agent.pod_name)
            except Exception:
                logger.exception(
                    "Failed to delete pod '%s' for agent '%s'",
                    agent.pod_name,
                    agent_id,
                )

        # Then delete DB record
        await self.db.delete(agent)
        await self.db.commit()

    async def duplicate_agent(self, agent_id: str) -> Agent:
        """Clone an agent's configuration with empty memory and a new pod.

        Creates a new agent with the source agent's config (name, model,
        identity, personality, heartbeat settings, avatar). Memory starts
        empty and is not cloned.

        Args:
            agent_id: UUID of the source agent to duplicate.

        Returns:
            The newly created Agent instance.

        Raises:
            ValueError: If source agent not found.
        """
        source = await self.db.get(Agent, agent_id)
        if source is None:
            raise ValueError("Agent not found")

        return await self.create_agent(
            name=f"{source.name} (copy)",
            model_provider=source.model_provider,
            model_name=source.model_name,
            identity=source.identity,
            personality=source.personality,
            heartbeat_interval_seconds=source.heartbeat_interval_seconds,
        )
