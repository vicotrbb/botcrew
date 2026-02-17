"""Celery tasks for message delivery to agent containers.

DM delivery uses Celery for reliable retries to external agent pods.
Channel broadcast does NOT use Celery -- it goes directly through Redis
pub/sub from NativeTransport for lower latency (<500ms requirement).
"""

import logging

import httpx
from celery import shared_task

logger = logging.getLogger(__name__)

_AGENT_URL_TEMPLATE = (
    "http://agent-{agent_id}.botcrew-agents.botcrew.svc.cluster.local:8080/message"
)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=5,
    retry_backoff=True,
    retry_backoff_max=60,
    acks_late=True,
)
def deliver_dm_to_agent(self, agent_id: str, message: dict) -> dict:
    """Deliver a direct message to an agent container via HTTP POST.

    Args:
        agent_id: UUID string of the target agent.
        message: Dict with keys: content (str), sender_type ("user" or "agent"),
                 sender_id (str), message_id (str).

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
        with httpx.Client(timeout=30.0) as client:
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
