"""Message endpoint -- user message processing for agent containers.

POST /message accepts user input, processes it through the Agno agent
with BrowserTools and MemoryTools, and returns the agent's response.
"""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

router = APIRouter()


class MessageRequest(BaseModel):
    """Request body for the /message endpoint."""

    content: str
    user_id: str | None = None


class MessageResponse(BaseModel):
    """Response from the /message endpoint."""

    content: str
    agent_id: str


@router.post("/message", response_model=MessageResponse)
async def message(request: Request, body: MessageRequest) -> MessageResponse | JSONResponse:
    """Process a user message through the Agno agent.

    The message is passed through AgentRuntime.process_message(), which
    invokes the Agno agent with full tool access (browser + memory)
    and windowed message history (last 20 messages).

    Args:
        request: FastAPI request (provides app.state access).
        body: MessageRequest with content and optional user_id.

    Returns:
        MessageResponse with the agent's response and its ID.
        503 if the runtime is not initialized.
    """
    runtime = getattr(request.app.state, "runtime", None)
    if runtime is None or not runtime.is_ready:
        return JSONResponse(
            status_code=503,
            content={"detail": "Agent runtime is not ready"},
        )

    response = await runtime.process_message(
        body.content,
        user_id=body.user_id,
    )

    config: dict = request.app.state.config
    agent_id = config.get(
        "agent_id",
        getattr(request.app.state, "agent_id", "unknown"),
    )

    return MessageResponse(content=response, agent_id=agent_id)
