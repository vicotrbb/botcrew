"""Celery tasks for message delivery to agent containers.

Agents respond using their own CommunicationTools (send_channel_message,
mark_messages_read).  The orchestrator's role is limited to triggering
the agent -- it does NOT post responses on behalf of agents.

DM delivery uses Celery for reliable retries to external agent pods.
Channel broadcast does NOT use Celery -- it goes directly through Redis
pub/sub from NativeTransport for lower latency (<500ms requirement).
"""

import logging

import httpx

from botcrew.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)

_AGENT_EVALUATE_URL_TEMPLATE = (
    "http://agent-{agent_id}.botcrew-agents.botcrew.svc.cluster.local:8080/evaluate"
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
    """Deliver a direct message to an agent by triggering evaluation.

    Dispatches the message to the agent's /evaluate endpoint with is_dm=True.
    The agent uses its own CommunicationTools to respond in the DM channel.

    Args:
        agent_id: UUID string of the target agent.
        message: Dict with keys: content (str), sender_type ("user" or "agent"),
                 sender_id (str), message_id (str), and optionally
                 reply_channel_id (str) for @mention context.

    Returns:
        Response JSON from the agent /evaluate endpoint.

    Raises:
        celery.exceptions.MaxRetriesExceededError: After 3 failed attempts.
    """
    url = _AGENT_EVALUATE_URL_TEMPLATE.format(agent_id=agent_id)

    # Build evaluate payload -- agent handles response via its own tools
    channel_id = message.get("reply_channel_id", "")
    payload = {
        "channel_id": channel_id,
        "message_content": message["content"],
        "message_id": message.get("message_id", ""),
        "sender_user_identifier": message.get("sender_id", "unknown"),
        "is_dm": True,
    }

    try:
        with httpx.Client(timeout=120.0) as client:
            response = client.post(url, json=payload)
            response.raise_for_status()
            return response.json()
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
    """Ask an agent to evaluate and respond to a channel message.

    Dispatches to the agent's /evaluate endpoint. The agent uses its own
    CommunicationTools (send_channel_message, mark_messages_read) to
    respond and track read state. The orchestrator does NOT post on
    behalf of the agent.

    Args:
        agent_id: UUID of the agent to evaluate.
        channel_id: UUID of the channel the message was sent in.
        message_content: The message text to evaluate.
        message_id: UUID of the message for read cursor tracking.
        sender_user_identifier: Who sent the message.
        is_dm: If True, agent always responds (direct message to them).

    Returns:
        Response JSON from the agent /evaluate endpoint.
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
        with httpx.Client(timeout=120.0) as client:
            response = client.post(url, json=payload)
            response.raise_for_status()
            return response.json()
    except (httpx.HTTPError, httpx.TimeoutException) as exc:
        logger.warning(
            "Instant reply evaluation failed for agent %s: %s",
            agent_id,
            str(exc),
        )
        raise self.retry(exc=exc)
