"""Evaluate endpoint -- message evaluation for agent containers.

POST /evaluate receives a channel message context and processes it through the
full agent runtime with all tools. The agent decides whether and how to respond
using its CommunicationTools (send_channel_message). Uses an isolated session
to avoid polluting main conversation history.
"""

from __future__ import annotations

import logging

import httpx
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter()

# Evaluation prompt -- agent uses its own tools to respond
_EVALUATE_PROMPT = """A user ({sender}) just sent this message in channel {channel_id}:

"{message_content}"

Recent conversation context (last {context_count} messages):
{context_messages}

{dm_or_channel_instruction}

If you decide to respond, use send_channel_message(channel_id="{channel_id}", content="your response") to post your reply.
After responding (or deciding not to), use mark_messages_read(channel_id="{channel_id}", last_message_id="{message_id}") to mark the message as read."""

_DM_INSTRUCTION = (
    "This is a DIRECT MESSAGE to you personally. The user is specifically talking "
    "to you and expects a reply. You MUST respond using send_channel_message."
)

_CHANNEL_INSTRUCTION = (
    "This is a message in one of your assigned project or task channels. "
    "You are part of this team. If the message asks a question, requests input, "
    "or invites collaboration, respond with your perspective based on your role. "
    "If the message is purely informational and needs no reply, just mark it as read."
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
    """Evaluate a channel message and let the agent respond using its tools.

    Processes the message through the full agent runtime with all tools
    (including CommunicationTools). The agent decides whether to respond
    and uses send_channel_message() to post its reply directly.

    Uses process_message() with the full runtime so the agent has access
    to all tools. The session is the agent's main session so it maintains
    conversation context.

    Args:
        request: FastAPI request (provides app.state access).
        body: EvaluateRequest with channel, message, and DM flag.

    Returns:
        EvaluateResponse with agent_id.
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
    orchestrator_url = runtime.settings.orchestrator_url

    # Fetch recent channel context
    context_messages = _fetch_channel_context(
        orchestrator_url, body.channel_id, count=10
    )

    # Build prompt -- agent will use its tools to respond
    dm_or_channel = _DM_INSTRUCTION if body.is_dm else _CHANNEL_INSTRUCTION
    prompt = _EVALUATE_PROMPT.format(
        sender=body.sender_user_identifier,
        message_content=body.message_content,
        channel_id=body.channel_id,
        message_id=body.message_id,
        context_count=10,
        context_messages=context_messages,
        dm_or_channel_instruction=dm_or_channel,
    )

    # Process through full runtime -- agent has all tools including CommunicationTools
    await runtime.process_message(prompt)

    return EvaluateResponse(agent_id=agent_id)
