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
