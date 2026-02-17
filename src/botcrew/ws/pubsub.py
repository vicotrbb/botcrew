"""Redis pub/sub manager for WebSocket fan-out across server instances."""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Awaitable, Callable

import redis.asyncio as aioredis

logger = logging.getLogger(__name__)


class PubSubManager:
    """Manages a dedicated Redis pub/sub connection for WebSocket fan-out.

    Uses a SEPARATE Redis connection from app.state.redis because pub/sub mode
    blocks the connection for regular commands.  Messages are published to
    channel-specific topics (``ws:channel:{channel_id}``) and a background
    listener forwards incoming messages to a handler callback.
    """

    CHANNEL_PREFIX: str = "ws:channel:"

    def __init__(self, redis_url: str) -> None:
        self._redis_url = redis_url
        self._redis: aioredis.Redis | None = None
        self._pubsub: aioredis.client.PubSub | None = None
        self._listener_task: asyncio.Task | None = None
        self._handler: Callable[[str, dict], Awaitable[None]] | None = None

    async def start(
        self, handler: Callable[[str, dict], Awaitable[None]]
    ) -> None:
        """Connect to Redis, subscribe to the channel pattern, and start listening.

        Args:
            handler: Async callback invoked with ``(channel_id, data)`` for
                each incoming message.
        """
        self._handler = handler
        # CRITICAL: separate connection -- never share with app.state.redis
        self._redis = aioredis.from_url(self._redis_url, decode_responses=True)
        self._pubsub = self._redis.pubsub()
        await self._pubsub.psubscribe(f"{self.CHANNEL_PREFIX}*")
        self._listener_task = asyncio.create_task(self._listen())
        logger.info("PubSubManager started, listening on %s*", self.CHANNEL_PREFIX)

    async def stop(self) -> None:
        """Gracefully shut down the listener, unsubscribe, and close the connection."""
        if self._listener_task is not None:
            self._listener_task.cancel()
            try:
                await self._listener_task
            except asyncio.CancelledError:
                pass
        if self._pubsub is not None:
            try:
                await self._pubsub.punsubscribe()
                await self._pubsub.aclose()
            except Exception:
                logger.debug("Error closing pubsub connection", exc_info=True)
        if self._redis is not None:
            try:
                await self._redis.aclose()
            except Exception:
                logger.debug("Error closing redis connection", exc_info=True)
        logger.info("PubSubManager stopped")

    async def _listen(self) -> None:
        """Background loop: read from Redis pub/sub and forward to the handler."""
        try:
            async for message in self._pubsub.listen():
                if message["type"] == "pmessage":
                    channel_id = message["channel"].removeprefix(
                        self.CHANNEL_PREFIX
                    )
                    try:
                        data = json.loads(message["data"])
                    except (json.JSONDecodeError, TypeError):
                        logger.warning(
                            "Invalid JSON in pub/sub message on %s",
                            message["channel"],
                        )
                        continue
                    try:
                        await self._handler(channel_id, data)
                    except Exception:
                        logger.exception(
                            "Handler error for channel %s", channel_id
                        )
        except asyncio.CancelledError:
            pass
        except Exception:
            logger.exception("PubSubManager listener crashed")

    async def publish(self, channel_id: str, message: dict) -> None:
        """Publish a message to the Redis topic for a channel.

        No-op if the manager has not been started yet.
        """
        if self._redis is None:
            return
        await self._redis.publish(
            f"{self.CHANNEL_PREFIX}{channel_id}", json.dumps(message)
        )
