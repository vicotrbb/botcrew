"""In-process WebSocket connection manager for per-channel message fan-out."""

from __future__ import annotations

import logging
from collections import defaultdict

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Track WebSocket connections per channel for local fan-out.

    Keys are channel_id -> client_id -> WebSocket instance.
    Dead connections are automatically cleaned up during send_to_channel.
    """

    def __init__(self) -> None:
        self.channels: dict[str, dict[str, WebSocket]] = defaultdict(dict)

    async def connect(
        self, websocket: WebSocket, channel_id: str, client_id: str
    ) -> None:
        """Accept a WebSocket connection and register it in a channel."""
        await websocket.accept()
        self.channels[channel_id][client_id] = websocket

    def disconnect(self, channel_id: str, client_id: str) -> None:
        """Remove a client from a channel. Cleans up empty channel dicts."""
        self.channels[channel_id].pop(client_id, None)
        if not self.channels[channel_id]:
            del self.channels[channel_id]

    async def send_to_channel(
        self, channel_id: str, message: dict, exclude: str | None = None
    ) -> None:
        """Fan out a message to all local WebSocket clients in a channel.

        Skips the client matching ``exclude`` (typically the sender).
        Any connection that raises on send is treated as dead and removed.
        """
        dead: list[str] = []
        for client_id, ws in self.channels.get(channel_id, {}).items():
            if client_id == exclude:
                continue
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(client_id)
        for client_id in dead:
            logger.debug(
                "Removing dead WebSocket connection: channel=%s client=%s",
                channel_id,
                client_id,
            )
            self.disconnect(channel_id, client_id)

    def get_channel_client_count(self, channel_id: str) -> int:
        """Return the number of connected clients in a channel."""
        return len(self.channels.get(channel_id, {}))

    def get_connected_channels(self) -> list[str]:
        """Return list of channel IDs that have at least one connected client."""
        return list(self.channels.keys())
