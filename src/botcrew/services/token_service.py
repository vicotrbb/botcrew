"""Token usage tracking service layer.

Provides recording and aggregation of per-agent LLM token usage
for cost monitoring and budget enforcement.
"""

from __future__ import annotations

import logging

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from botcrew.models.token_usage import TokenUsage

logger = logging.getLogger(__name__)


class TokenService:
    """Service for recording and querying LLM token usage.

    Args:
        db: Async SQLAlchemy session for database operations.
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def record_usage(
        self,
        agent_id: str,
        input_tokens: int,
        output_tokens: int,
        model_provider: str,
        model_name: str,
        task_id: str | None = None,
        project_id: str | None = None,
        call_type: str | None = None,
    ) -> TokenUsage:
        """Record a single LLM call's token usage.

        Args:
            agent_id: UUID of the agent that made the call.
            input_tokens: Number of input/prompt tokens.
            output_tokens: Number of output/completion tokens.
            model_provider: Provider name (openai, anthropic, etc.).
            model_name: Model identifier (gpt-4, claude-3-opus, etc.).
            task_id: Optional task UUID this call was made for.
            project_id: Optional project UUID this call was made for.
            call_type: Optional call type label (heartbeat, tool_call, etc.).

        Returns:
            The created TokenUsage record.
        """
        record = TokenUsage(
            agent_id=agent_id,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            model_provider=model_provider,
            model_name=model_name,
            task_id=task_id,
            project_id=project_id,
            call_type=call_type,
        )
        self.db.add(record)
        await self.db.commit()
        await self.db.refresh(record)
        return record

    async def get_agent_token_totals(self, agent_id: str) -> dict:
        """Get aggregate token totals for an agent.

        Args:
            agent_id: UUID of the agent.

        Returns:
            Dict with total_input_tokens and total_output_tokens.
        """
        result = await self.db.execute(
            select(
                func.coalesce(func.sum(TokenUsage.input_tokens), 0).label(
                    "total_input"
                ),
                func.coalesce(func.sum(TokenUsage.output_tokens), 0).label(
                    "total_output"
                ),
            ).where(TokenUsage.agent_id == agent_id)
        )
        row = result.one()
        return {
            "total_input_tokens": int(row.total_input),
            "total_output_tokens": int(row.total_output),
        }

    async def record_batch(self, records: list[dict]) -> None:
        """Bulk insert multiple token usage records.

        Used by agent pods reporting multiple LLM calls at once.

        Args:
            records: List of dicts with same fields as record_usage.
        """
        usage_objects = [TokenUsage(**r) for r in records]
        self.db.add_all(usage_objects)
        await self.db.commit()
