"""CommunicationTools -- Agno toolkit for channel/message interaction via orchestrator API.

Enables botcrew agents to discover work, read messages, and communicate
during heartbeat cycles.  Wraps the orchestrator's channel REST API
(Phase 4) into Agno tools the agent can call.

All tools return plain ``str`` results (Agno convention).  Failures are
returned as graceful error strings -- never raised -- so the agent keeps
functioning even when communication is temporarily unavailable.
"""

from __future__ import annotations

import logging

import httpx
from agno.tools import Toolkit

logger = logging.getLogger(__name__)


class CommunicationTools(Toolkit):
    """Agno toolkit wrapping the orchestrator channel/message API.

    The orchestrator exposes channel endpoints at::

        GET  /api/v1/channels                          (list channels)
        GET  /api/v1/channels/{id}/messages             (message history)
        GET  /api/v1/channels/{id}/messages/unread      (unread messages)
        POST /api/v1/channels/{id}/messages             (send message)
        POST /api/v1/channels/{id}/messages/read        (mark read)
        POST /api/v1/channels/dm/{agent_id}             (direct message)

    All responses use JSON:API envelope format.
    """

    def __init__(
        self,
        orchestrator_url: str,
        agent_id: str,
        **kwargs,
    ):
        self.orchestrator_url = orchestrator_url.rstrip("/")
        self.agent_id = agent_id
        self.default_timeout = 15  # seconds -- slightly longer for message queries

        super().__init__(
            name="communication_tools",
            tools=[
                self.list_my_channels,
                self.check_unread_messages,
                self.read_channel_messages,
                self.send_channel_message,
                self.send_direct_message,
                self.mark_messages_read,
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
        params: dict | None = None,
    ) -> dict | None:
        """Make a synchronous HTTP request to the orchestrator API.

        Full URL is passed directly (different endpoints have different
        base paths).  Returns parsed JSON on success, ``None`` on any
        error.  Communication failures must never crash the agent.
        """
        try:
            with httpx.Client(timeout=self.default_timeout) as client:
                response = client.request(
                    method=method,
                    url=url,
                    json=json_data,
                    params=params,
                )
                response.raise_for_status()
                return response.json()
        except Exception as exc:
            logger.warning(
                "Communication API request failed: %s %s -> %s",
                method,
                url,
                exc,
            )
            return None

    # ------------------------------------------------------------------
    # Tools
    # ------------------------------------------------------------------

    def list_my_channels(self) -> str:
        """List all channels you are a member of.

        Returns channel names, IDs, and types.  Use this to discover
        which channels you belong to before checking for unread messages.
        """
        try:
            url = f"{self.orchestrator_url}/api/v1/channels"
            result = self._request("GET", url, params={"agent_id": self.agent_id})
            if result is None:
                return "Communication is temporarily unavailable."

            channels = result.get("data", [])
            if not channels:
                return "No channels found."

            lines: list[str] = []
            for ch in channels:
                ch_id = ch.get("id", "unknown")
                attrs = ch.get("attributes", {})
                name = attrs.get("name", "unnamed")
                ch_type = attrs.get("channel_type", "unknown")
                description = attrs.get("description", "")
                line = f"- {name} (ID: {ch_id}, type: {ch_type})"
                if description:
                    line += f" -- {description}"
                lines.append(line)

            return f"Your channels ({len(channels)}):\n" + "\n".join(lines)
        except Exception as exc:
            logger.error("list_my_channels unexpected error: %s", exc)
            return "Communication is temporarily unavailable."

    def check_unread_messages(self, channel_id: str) -> str:
        """Check for unread messages in a specific channel.

        Returns unread messages oldest-first so you can process them in
        order.  Call this during heartbeat to discover new work.
        """
        try:
            url = (
                f"{self.orchestrator_url}/api/v1/channels/"
                f"{channel_id}/messages/unread"
            )
            result = self._request(
                "GET", url, params={"agent_id": self.agent_id},
            )
            if result is None:
                return "Communication is temporarily unavailable."

            messages = result.get("data", [])
            unread_count = result.get("meta", {}).get("unread_count", len(messages))

            if not messages:
                return "No unread messages in this channel."

            lines: list[str] = [f"Unread messages ({unread_count}):"]
            for msg in messages:
                msg_id = msg.get("id", "unknown")
                attrs = msg.get("attributes", {})
                content = attrs.get("content", "")
                sender_agent = attrs.get("sender_agent_id")
                sender_user = attrs.get("sender_user_identifier")
                created_at = attrs.get("created_at", "")

                sender = sender_agent or sender_user or "unknown"
                lines.append(
                    f"- [{msg_id}] From {sender} at {created_at}: {content}"
                )

            return "\n".join(lines)
        except Exception as exc:
            logger.error("check_unread_messages unexpected error: %s", exc)
            return "Communication is temporarily unavailable."

    def read_channel_messages(self, channel_id: str, count: int = 20) -> str:
        """Read recent messages from a channel.

        Returns the most recent messages newest-first.  Use this to
        catch up on channel history or review context.
        """
        try:
            url = (
                f"{self.orchestrator_url}/api/v1/channels/"
                f"{channel_id}/messages"
            )
            result = self._request(
                "GET", url, params={"page_size": count},
            )
            if result is None:
                return "Communication is temporarily unavailable."

            messages = result.get("data", [])
            if not messages:
                return "No messages in this channel."

            lines: list[str] = [f"Recent messages ({len(messages)}):"]
            for msg in messages:
                msg_id = msg.get("id", "unknown")
                attrs = msg.get("attributes", {})
                content = attrs.get("content", "")
                sender_agent = attrs.get("sender_agent_id")
                sender_user = attrs.get("sender_user_identifier")
                created_at = attrs.get("created_at", "")

                sender = sender_agent or sender_user or "unknown"
                lines.append(
                    f"- [{msg_id}] From {sender} at {created_at}: {content}"
                )

            return "\n".join(lines)
        except Exception as exc:
            logger.error("read_channel_messages unexpected error: %s", exc)
            return "Communication is temporarily unavailable."

    def send_channel_message(self, channel_id: str, content: str) -> str:
        """Send a message to a channel.

        All channel members will see this message.  Use this to share
        updates, ask questions, or respond to other agents.
        """
        try:
            url = (
                f"{self.orchestrator_url}/api/v1/channels/"
                f"{channel_id}/messages"
            )
            result = self._request(
                "POST",
                url,
                json_data={"content": content},
                params={"sender_agent_id": self.agent_id},
            )
            if result is None:
                return "Failed to send message. Communication is temporarily unavailable."

            return "Message sent successfully."
        except Exception as exc:
            logger.error("send_channel_message unexpected error: %s", exc)
            return "Failed to send message. Communication is temporarily unavailable."

    def send_direct_message(self, agent_id: str, content: str) -> str:
        """Send a direct message to another agent.

        The message will be delivered asynchronously.  Use this for
        private communication with a specific agent.
        """
        try:
            url = (
                f"{self.orchestrator_url}/api/v1/channels/dm/{agent_id}"
            )
            result = self._request(
                "POST",
                url,
                json_data={"content": content},
                params={"sender_user_identifier": f"agent:{self.agent_id}"},
            )
            if result is None:
                return "Failed to send direct message. Communication is temporarily unavailable."

            return "Direct message sent."
        except Exception as exc:
            logger.error("send_direct_message unexpected error: %s", exc)
            return "Failed to send direct message. Communication is temporarily unavailable."

    def mark_messages_read(self, channel_id: str, last_message_id: str) -> str:
        """Mark messages as read up to a specific message ID.

        Call this after processing unread messages so you do not see
        them again on the next heartbeat check.
        """
        try:
            url = (
                f"{self.orchestrator_url}/api/v1/channels/"
                f"{channel_id}/messages/read"
            )
            result = self._request(
                "POST",
                url,
                params={
                    "agent_id": self.agent_id,
                    "last_read_message_id": last_message_id,
                },
            )
            if result is None:
                return "Failed to mark messages as read. Communication is temporarily unavailable."

            return "Messages marked as read."
        except Exception as exc:
            logger.error("mark_messages_read unexpected error: %s", exc)
            return "Failed to mark messages as read. Communication is temporarily unavailable."
