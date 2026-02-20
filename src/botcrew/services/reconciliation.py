"""Self-healing reconciliation loop for agent pod lifecycle.

Runs as an asyncio background task, periodically comparing desired state
(agents in DB) with actual state (pods in K8s). Missing or failed pods
are recreated with exponential backoff after repeated failures.
"""

from __future__ import annotations

import asyncio
import logging
import time

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from botcrew.models.agent import Agent
from botcrew.services.pod_manager import PodManager

logger = logging.getLogger(__name__)

# Backoff constants
_MAX_IMMEDIATE_RETRIES = 5
_BACKOFF_BASE_SECONDS = 10
_BACKOFF_MAX_SECONDS = 600
_PENDING_TIMEOUT_SECONDS = 180  # 3 minutes before treating Pending as error


class ReconciliationLoop:
    """Background loop that reconciles agent DB state with K8s pod state.

    Runs every ``interval`` seconds. For each agent in running/error/recovering
    status, checks whether the expected pod exists and is healthy. Missing pods
    for running agents are marked as error. Error agents are recovered by
    recreating their pod, with exponential backoff after repeated failures.

    Agents in ``creating`` or ``terminating`` status are deliberately skipped
    to avoid race conditions with the CRUD endpoints.

    Note: ``idle`` status handling is deferred to Phase 5 (Heartbeat + Agent
    Autonomy). When idle is implemented, the reconciliation loop will need to
    also handle idle agents whose pods should still be running.

    Args:
        session_factory: Async SQLAlchemy session factory for DB access.
        pod_manager: Initialized PodManager for K8s pod operations.
        interval: Seconds between reconciliation cycles (default 60).
    """

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        pod_manager: PodManager,
        interval: int = 60,
    ) -> None:
        self.session_factory = session_factory
        self.pod_manager = pod_manager
        self.interval = interval
        self._task: asyncio.Task[None] | None = None
        self._failure_counts: dict[str, int] = {}
        self._last_attempt: dict[str, float] = {}

    async def start(self) -> None:
        """Start the reconciliation background task."""
        self._task = asyncio.create_task(self._run_loop())
        logger.info("Reconciliation loop started (interval=%ds)", self.interval)

    async def stop(self) -> None:
        """Cancel and await the reconciliation background task."""
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        logger.info("Reconciliation loop stopped")

    async def _run_loop(self) -> None:
        """Run reconciliation in a loop, sleeping between cycles."""
        while True:
            try:
                await self._reconcile()
            except Exception:
                logger.exception("Reconciliation cycle failed")
            await asyncio.sleep(self.interval)

    async def _reconcile(self) -> None:
        """Compare desired state (DB) with actual state (K8s) and correct drift.

        1. Query agents in running/error/recovering status.
        2. List actual pods via K8s API.
        3. For running agents with missing pods: mark as error.
        4. For running agents with failed pods: mark as error, delete pod.
        5. For error agents with missing pods: attempt recovery with backoff.
        """
        # --- Read desired state from DB ---
        async with self.session_factory() as session:
            result = await session.execute(
                select(Agent).where(
                    Agent.status.in_(["running", "error", "recovering"])
                )
            )
            agents = result.scalars().all()

        if not agents:
            return

        # --- Read actual state from K8s ---
        actual_pods = await self.pod_manager.list_agent_pods()
        actual_pod_names = {pod.metadata.name for pod in actual_pods}
        pod_phases = {
            pod.metadata.name: pod.status.phase for pod in actual_pods
        }

        # --- Reconcile each agent ---
        for agent in agents:
            agent_id = str(agent.id)
            pod_name = agent.pod_name

            if agent.status == "running" and pod_name not in actual_pod_names:
                # Pod disappeared for a running agent -- mark as error
                await self._set_agent_status(agent_id, "error")
                logger.warning(
                    "Pod '%s' missing for running agent '%s' -- marked as error",
                    pod_name,
                    agent_id,
                )

            elif agent.status == "running" and pod_name in actual_pod_names:
                phase = pod_phases.get(pod_name)
                if phase == "Failed":
                    # Pod failed -- delete and mark as error for recovery
                    await self._set_agent_status(agent_id, "error")
                    await self.pod_manager.delete_agent_pod(pod_name)
                    logger.warning(
                        "Pod '%s' failed for agent '%s' -- deleted and marked as error",
                        pod_name,
                        agent_id,
                    )
                elif phase == "Pending":
                    # Pod stuck in Pending (likely insufficient resources).
                    # Track how long it's been pending; after threshold, delete
                    # and mark as error so recovery can retry with fresh spec.
                    pending_key = f"pending:{agent_id}"
                    first_seen = self._last_attempt.get(pending_key, 0.0)
                    now = time.monotonic()
                    if first_seen == 0.0:
                        self._last_attempt[pending_key] = now
                    elif now - first_seen > _PENDING_TIMEOUT_SECONDS:
                        await self._set_agent_status(agent_id, "error")
                        await self.pod_manager.delete_agent_pod(pod_name)
                        self._last_attempt.pop(pending_key, None)
                        logger.warning(
                            "Pod '%s' stuck Pending for >%ds for agent '%s' "
                            "-- deleted and marked as error",
                            pod_name,
                            _PENDING_TIMEOUT_SECONDS,
                            agent_id,
                        )

            elif agent.status in ("error", "recovering") and pod_name not in actual_pod_names:
                # Error/recovering agent with no pod -- attempt recovery
                await self._attempt_recovery(agent_id, agent)

    async def _attempt_recovery(self, agent_id: str, agent: Agent) -> None:
        """Try to recreate a pod for an agent in error state, with backoff.

        After ``_MAX_IMMEDIATE_RETRIES`` consecutive failures, exponential
        backoff is applied: 10s, 20s, 40s, 80s, ... capped at 600s.
        """
        failure_count = self._failure_counts.get(agent_id, 0)

        # Check backoff for agents that have failed repeatedly
        if failure_count >= _MAX_IMMEDIATE_RETRIES:
            backoff = min(
                _BACKOFF_BASE_SECONDS * (2 ** (failure_count - _MAX_IMMEDIATE_RETRIES)),
                _BACKOFF_MAX_SECONDS,
            )
            last_attempt = self._last_attempt.get(agent_id, 0.0)
            elapsed = time.monotonic() - last_attempt
            if elapsed < backoff:
                logger.debug(
                    "Skipping recovery for agent '%s' (backoff %.0fs, elapsed %.0fs)",
                    agent_id,
                    backoff,
                    elapsed,
                )
                return

        # Transition to recovering
        await self._set_agent_status(agent_id, "recovering")

        try:
            # Recreate pod -- re-read agent from DB for fresh state
            async with self.session_factory() as session:
                fresh_agent = await session.get(Agent, agent_id)
                if fresh_agent is None:
                    logger.warning("Agent '%s' disappeared during recovery", agent_id)
                    return
                pod_name = await self.pod_manager.create_agent_pod(fresh_agent)
                fresh_agent.pod_name = pod_name
                fresh_agent.status = "running"
                await session.commit()

            # Success -- reset failure tracking
            self._failure_counts.pop(agent_id, None)
            self._last_attempt.pop(agent_id, None)
            logger.info(
                "Recovered agent '%s' with new pod '%s'",
                agent_id,
                pod_name,
            )

        except Exception:
            # Recovery failed -- increment failure count and revert status
            self._failure_counts[agent_id] = failure_count + 1
            self._last_attempt[agent_id] = time.monotonic()
            await self._set_agent_status(agent_id, "error")
            logger.exception(
                "Failed to recover agent '%s' (attempt %d)",
                agent_id,
                failure_count + 1,
            )

    async def _set_agent_status(self, agent_id: str, status: str) -> None:
        """Update an agent's status in the database."""
        async with self.session_factory() as session:
            agent = await session.get(Agent, agent_id)
            if agent is not None:
                agent.status = status
                await session.commit()
