"""Activity logging and querying service.

Provides a fire-and-forget API for recording agent activities and a query
interface for retrieving activity history. The log_activity method never
raises -- failures are logged as warnings and return None.
"""

from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from botcrew.models.activity import Activity

logger = logging.getLogger(__name__)


class ActivityService:
    """Service for logging and querying agent activity records.

    Args:
        db: Async SQLAlchemy session for database operations.
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def log_activity(
        self,
        agent_id: str,
        event_type: str,
        summary: str = "",
        details: dict | None = None,
    ) -> Activity | None:
        """Create and persist an activity record.

        This method never raises. On any database error the exception is
        logged as a warning and ``None`` is returned so that callers can
        treat activity logging as fire-and-forget.

        Args:
            agent_id: UUID of the agent performing the activity.
            event_type: Short event classifier (max 50 chars), e.g.
                "heartbeat_wake", "self_identity_update", "message_sent".
            summary: Human-readable description of the activity.
            details: Optional structured data for the event.

        Returns:
            The created Activity record, or None if logging failed.
        """
        try:
            activity = Activity(
                agent_id=agent_id,
                event_type=event_type,
                summary=summary,
                details=details,
            )
            self.db.add(activity)
            await self.db.flush()
            return activity
        except Exception:
            logger.warning(
                "Failed to log activity for agent '%s' event_type='%s'",
                agent_id,
                event_type,
                exc_info=True,
            )
            return None

    async def list_activities(
        self,
        agent_id: str,
        limit: int = 50,
        event_type: str | None = None,
    ) -> list[Activity]:
        """Query activities for an agent, ordered by newest first.

        Args:
            agent_id: UUID of the agent whose activities to retrieve.
            limit: Maximum number of records to return (default 50).
            event_type: Optional filter to return only activities of
                this event type.

        Returns:
            List of Activity records ordered by created_at DESC.
        """
        query = (
            select(Activity)
            .where(Activity.agent_id == agent_id)
            .order_by(Activity.created_at.desc())
            .limit(limit)
        )

        if event_type is not None:
            query = query.where(Activity.event_type == event_type)

        result = await self.db.execute(query)
        return list(result.scalars().all())
