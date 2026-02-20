"""Celery tasks for message delivery to agent containers.

DM delivery uses Celery for reliable retries to external agent pods.
Channel broadcast does NOT use Celery -- it goes directly through Redis
pub/sub from NativeTransport for lower latency (<500ms requirement).
"""

import logging

import httpx

from botcrew.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)

_AGENT_URL_TEMPLATE = (
    "http://agent-{agent_id}.botcrew-agents.botcrew.svc.cluster.local:8080/message"
)

_ORCHESTRATOR_CHANNEL_MSG_TEMPLATE = (
    "http://botcrew-orchestrator:8000/api/v1/channels/{channel_id}/messages"
)

_AGENT_EVALUATE_URL_TEMPLATE = (
    "http://agent-{agent_id}.botcrew-agents.botcrew.svc.cluster.local:8080/evaluate"
)

_ORCHESTRATOR_MARK_READ_TEMPLATE = (
    "http://botcrew-orchestrator:8000/api/v1/channels/{channel_id}/messages/read"
)


@celery_app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=5,
    retry_backoff=True,
    retry_backoff_max=60,
    acks_late=True,
)
def deliver_dm_to_agent(self, agent_id: str, message: dict) -> dict:
    """Deliver a direct message to an agent container via HTTP POST.

    If the message originated from a channel @mention (reply_channel_id is
    present), the agent's response is posted back to that channel.

    Args:
        agent_id: UUID string of the target agent.
        message: Dict with keys: content (str), sender_type ("user" or "agent"),
                 sender_id (str), message_id (str), and optionally
                 reply_channel_id (str) for @mention responses.

    Returns:
        Response JSON from the agent /message endpoint.

    Raises:
        celery.exceptions.MaxRetriesExceededError: After 3 failed attempts.
    """
    url = _AGENT_URL_TEMPLATE.format(agent_id=agent_id)
    payload = {
        "content": message["content"],
        "user_id": message.get("sender_id"),
    }

    try:
        with httpx.Client(timeout=60.0) as client:
            response = client.post(url, json=payload)
            response.raise_for_status()
            result = response.json()

            # If this was a channel @mention, post the response back
            reply_channel_id = message.get("reply_channel_id")
            if reply_channel_id and result.get("content"):
                _post_reply_to_channel(
                    client, reply_channel_id, agent_id, result["content"]
                )

            return result
    except (httpx.HTTPError, httpx.TimeoutException) as exc:
        attempt = self.request.retries + 1
        logger.warning(
            "DM delivery to agent %s failed (attempt %d/%d): %s",
            agent_id,
            attempt,
            self.max_retries + 1,
            str(exc),
        )
        raise self.retry(exc=exc)


def _post_reply_to_channel(
    client: httpx.Client,
    channel_id: str,
    agent_id: str,
    content: str,
) -> None:
    """Post the agent's @mention response back to the originating channel."""
    url = _ORCHESTRATOR_CHANNEL_MSG_TEMPLATE.format(channel_id=channel_id)
    try:
        resp = client.post(
            url,
            json={
                "data": {
                    "type": "messages",
                    "attributes": {
                        "content": content,
                        "message_type": "chat",
                    },
                }
            },
            params={"sender_agent_id": agent_id},
        )
        resp.raise_for_status()
        logger.info(
            "Posted @mention reply from agent %s to channel %s",
            agent_id,
            channel_id,
        )
    except Exception:
        logger.warning(
            "Failed to post @mention reply from agent %s to channel %s",
            agent_id,
            channel_id,
            exc_info=True,
        )


def _mark_message_read(
    client: httpx.Client,
    channel_id: str,
    agent_id: str,
    message_id: str,
) -> None:
    """Advance the agent's read cursor past the evaluated message.

    This ensures heartbeat's check_unread_messages skips messages
    that were already evaluated by the instant reply pipeline.
    """
    url = _ORCHESTRATOR_MARK_READ_TEMPLATE.format(channel_id=channel_id)
    try:
        resp = client.post(
            url,
            params={
                "last_read_message_id": message_id,
                "agent_id": agent_id,
            },
        )
        resp.raise_for_status()
    except Exception:
        logger.warning(
            "Failed to mark message %s as read for agent %s in channel %s",
            message_id,
            agent_id,
            channel_id,
            exc_info=True,
        )


@celery_app.task(
    bind=True,
    max_retries=1,
    default_retry_delay=3,
    acks_late=True,
)
def evaluate_instant_reply(
    self,
    agent_id: str,
    channel_id: str,
    message_content: str,
    message_id: str,
    sender_user_identifier: str,
    is_dm: bool = False,
) -> dict:
    """Ask an agent to evaluate and optionally respond to a channel message.

    Dispatches to the agent's /evaluate endpoint. If the agent decides to
    respond, posts the reply to the channel. Always advances the read
    cursor afterward (heartbeat deference).

    Args:
        agent_id: UUID of the agent to evaluate.
        channel_id: UUID of the channel the message was sent in.
        message_content: The message text to evaluate.
        message_id: UUID of the message for read cursor tracking.
        sender_user_identifier: Who sent the message.
        is_dm: If True, agent skips relevance check and always responds.

    Returns:
        Dict with should_respond and optional content.
    """
    url = _AGENT_EVALUATE_URL_TEMPLATE.format(agent_id=agent_id)
    payload = {
        "channel_id": channel_id,
        "message_content": message_content,
        "message_id": message_id,
        "sender_user_identifier": sender_user_identifier,
        "is_dm": is_dm,
    }

    try:
        with httpx.Client(timeout=90.0) as client:
            response = client.post(url, json=payload)
            response.raise_for_status()
            result = response.json()

            # If agent decided to respond, post reply to channel
            if result.get("should_respond") and result.get("content"):
                _post_reply_to_channel(
                    client, channel_id, agent_id, result["content"]
                )

            # Always mark message as read (heartbeat deference)
            _mark_message_read(client, channel_id, agent_id, message_id)

            return result
    except (httpx.HTTPError, httpx.TimeoutException) as exc:
        logger.warning(
            "Instant reply evaluation failed for agent %s: %s",
            agent_id,
            str(exc),
        )
        raise self.retry(exc=exc)
