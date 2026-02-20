"""Evaluate endpoint -- instant reply relevance evaluation for agent containers.

POST /evaluate receives a channel message, fetches recent context from the
orchestrator, and makes a single LLM call to decide whether the agent should
respond. Uses an isolated session to avoid polluting conversation history.
"""

from __future__ import annotations

import logging

import httpx
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter()

# Evaluation prompt template -- single LLM call for relevance + response
_EVALUATE_PROMPT = """A user ({sender}) just sent this message in a channel:

"{message_content}"

Recent conversation context (last {context_count} messages):
{context_messages}

You are {agent_name}. {agent_identity}

{dm_or_channel_instruction}

Consider:
- Is this message relevant to your role, expertise, or assigned work?
- Have other agents already adequately addressed this in the recent context?
- Can you add unique value by responding?

If you should respond, write your response below.
If you should NOT respond (message is not relevant to you, or others have covered it), respond with exactly: [NO_RESPONSE]"""

_DM_INSTRUCTION = (
    "This is a direct message to you. Always respond helpfully -- "
    "the user is specifically talking to you."
)

_CHANNEL_INSTRUCTION = (
    "Respond only if you can add unique value based on your role and expertise. "
    "Do not respond just because you can -- respond because you should."
)


class EvaluateRequest(BaseModel):
    """Request body for the /evaluate endpoint."""

    channel_id: str
    message_content: str
    message_id: str
    sender_user_identifier: str
    is_dm: bool = False


class EvaluateResponse(BaseModel):
    """Response from the /evaluate endpoint."""

    should_respond: bool
    content: str | None = None
    agent_id: str


def _fetch_channel_context(
    orchestrator_url: str,
    channel_id: str,
    count: int = 10,
) -> str:
    """Fetch recent messages from the channel for context.

    Returns a formatted string of recent messages, or empty string on failure.
    Uses the same endpoint as CommunicationTools.read_channel_messages.
    """
    url = f"{orchestrator_url}/api/v1/channels/{channel_id}/messages"
    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(url, params={"page_size": count})
            resp.raise_for_status()
            data = resp.json().get("data", [])

        lines = []
        # Messages come newest-first, reverse for chronological order
        for item in reversed(data):
            attrs = item.get("attributes", {})
            sender = attrs.get("sender_agent_id") or attrs.get(
                "sender_user_identifier", "unknown"
            )
            content = attrs.get("content", "")
            lines.append(f"  {sender}: {content}")

        return "\n".join(lines) if lines else "(no recent messages)"
    except Exception:
        logger.warning(
            "Failed to fetch channel context for %s", channel_id, exc_info=True
        )
        return "(context unavailable)"


@router.post("/evaluate", response_model=EvaluateResponse)
async def evaluate(
    request: Request, body: EvaluateRequest
) -> EvaluateResponse | JSONResponse:
    """Evaluate whether to respond to a channel message and generate response.

    Makes a single LLM call that includes relevance evaluation and response
    generation. If the agent decides not to respond, it outputs [NO_RESPONSE].
    Uses an isolated session_id to avoid polluting main conversation history.

    Args:
        request: FastAPI request (provides app.state access).
        body: EvaluateRequest with channel, message, and DM flag.

    Returns:
        EvaluateResponse with should_respond flag and optional content.
        503 if the runtime is not initialized.
    """
    runtime = getattr(request.app.state, "runtime", None)
    if runtime is None or not runtime.is_ready:
        return JSONResponse(
            status_code=503,
            content={"detail": "Agent runtime is not ready"},
        )

    config: dict = request.app.state.config
    agent_id = config.get(
        "agent_id",
        getattr(request.app.state, "agent_id", "unknown"),
    )
    agent_name = config.get("name", "Agent")
    agent_identity = config.get("identity", "") or ""
    orchestrator_url = runtime.settings.orchestrator_url

    # Fetch recent channel context
    context_messages = _fetch_channel_context(
        orchestrator_url, body.channel_id, count=10
    )

    # Build evaluation prompt
    dm_or_channel = _DM_INSTRUCTION if body.is_dm else _CHANNEL_INSTRUCTION
    prompt = _EVALUATE_PROMPT.format(
        sender=body.sender_user_identifier,
        message_content=body.message_content,
        context_count=10,
        context_messages=context_messages,
        agent_name=agent_name,
        agent_identity=agent_identity,
        dm_or_channel_instruction=dm_or_channel,
    )

    # Use isolated evaluation -- does not pollute main conversation history
    response_text = await runtime.evaluate_message(
        prompt, session_id=f"evaluate-{body.message_id}"
    )

    # Parse response: check for [NO_RESPONSE] marker
    should_respond = "[NO_RESPONSE]" not in response_text
    return EvaluateResponse(
        should_respond=should_respond,
        content=response_text if should_respond else None,
        agent_id=agent_id,
    )
