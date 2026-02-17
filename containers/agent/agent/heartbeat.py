"""HeartbeatTimer -- asyncio background task for periodic agent waking.

Implements the core autonomy mechanism: an asyncio background loop that
periodically wakes the agent by sending its heartbeat prompt through the
AgentRuntime.  The timer is cancellable and restartable with a new
interval or prompt, enabling self-evolution of wake behaviour.

Design follows the ReconciliationLoop pattern (asyncio.create_task +
asyncio.sleep loop) used elsewhere in botcrew.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import Any

logger = logging.getLogger(__name__)


class HeartbeatTimer:
    """Background task that periodically wakes an agent with its heartbeat prompt.

    Lifecycle:
    1. ``__init__`` stores runtime ref, interval, prompt, optional activity cb.
    2. ``start()`` launches the asyncio background loop.
    3. ``stop()`` cancels the loop.
    4. ``restart()`` stops then starts (optionally with new interval/prompt).

    The loop sleeps *first*, then processes -- this prevents an immediate fire
    on boot and avoids drift (Research pitfall #1).  A processing lock prevents
    overlapping heartbeats if processing takes longer than the interval
    (Research pitfall #4).
    """

    def __init__(
        self,
        runtime: Any,
        interval: int,
        prompt: str,
        on_activity: Callable[[str, dict[str, Any]], Awaitable[None]] | None = None,
    ) -> None:
        """Initialise the heartbeat timer.

        Args:
            runtime: AgentRuntime instance (must have ``process_message()``).
            interval: Seconds between heartbeats (300-86400).
            prompt: Heartbeat prompt text sent to the agent.
            on_activity: Optional async callback ``(event_type, details)`` for
                         activity logging.  Fire-and-forget -- failures are
                         silently caught.
        """
        self._runtime = runtime
        self._interval = interval
        self._prompt = prompt
        self._on_activity = on_activity
        self._task: asyncio.Task[None] | None = None
        self._running = False
        self._processing_lock = asyncio.Lock()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def start(self) -> None:
        """Start the heartbeat background loop (idempotent)."""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._loop())
        logger.info("Heartbeat started (interval=%ds)", self._interval)

    async def stop(self) -> None:
        """Stop the heartbeat background loop."""
        self._running = False
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        logger.info("Heartbeat stopped")

    async def restart(
        self,
        interval: int | None = None,
        prompt: str | None = None,
    ) -> None:
        """Stop and restart the heartbeat, optionally updating interval/prompt.

        Args:
            interval: New interval in seconds (or ``None`` to keep current).
            prompt: New prompt text (or ``None`` to keep current).
        """
        if interval is not None:
            self._interval = interval
        if prompt is not None:
            self._prompt = prompt
        await self.stop()
        await self.start()
        logger.info("Heartbeat restarted (interval=%ds)", self._interval)

    # ------------------------------------------------------------------
    # Read-only properties
    # ------------------------------------------------------------------

    @property
    def interval(self) -> int:
        """Current heartbeat interval in seconds."""
        return self._interval

    @property
    def prompt(self) -> str:
        """Current heartbeat prompt text."""
        return self._prompt

    # ------------------------------------------------------------------
    # Internal loop
    # ------------------------------------------------------------------

    async def _loop(self) -> None:
        """Sleep-first heartbeat loop.

        Sleeps for the configured interval, then sends the heartbeat prompt
        through the agent runtime.  If a previous heartbeat is still being
        processed when the next tick fires, the tick is skipped.
        """
        while self._running:
            # Sleep FIRST -- prevents immediate fire on boot and avoids drift
            await asyncio.sleep(self._interval)

            if not self._running:
                break

            # Skip tick if previous heartbeat is still processing
            if self._processing_lock.locked():
                logger.info(
                    "Skipping heartbeat -- still processing previous"
                )
                continue

            async with self._processing_lock:
                try:
                    response = await self._runtime.process_message(
                        self._prompt
                    )

                    # Fire-and-forget activity callback
                    if self._on_activity is not None:
                        try:
                            await self._on_activity(
                                "heartbeat_wake",
                                {
                                    "prompt": self._prompt[:200],
                                    "response_length": len(response)
                                    if response
                                    else 0,
                                },
                            )
                        except Exception:
                            pass  # Activity logging is fire-and-forget

                except Exception as exc:
                    logger.error(
                        "Heartbeat processing error: %s",
                        exc,
                        exc_info=True,
                    )
                    # Never crash the loop
