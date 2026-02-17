"""Heartbeat and agent autonomy schema additions.

Revision ID: 004
Revises: 003
Create Date: 2026-02-17

Changes:
- Create activities table for agent activity tracking
- Add composite index on (agent_id, created_at) for chronological queries
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "004"
down_revision: str | Sequence[str] | None = "003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create activities table for agent activity logging."""

    op.create_table(
        "activities",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column(
            "agent_id",
            UUID(as_uuid=False),
            sa.ForeignKey("agents.id"),
            nullable=False,
        ),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("summary", sa.Text(), server_default="", nullable=False),
        sa.Column("details", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    # Index on agent_id for filtering by agent
    op.create_index("ix_activities_agent_id", "activities", ["agent_id"])

    # Index on event_type for filtering by event
    op.create_index("ix_activities_event_type", "activities", ["event_type"])

    # Composite index for chronological queries per agent
    op.create_index(
        "ix_activities_agent_id_created_at",
        "activities",
        ["agent_id", "created_at"],
    )


def downgrade() -> None:
    """Drop activities table."""

    op.drop_index("ix_activities_agent_id_created_at", "activities")
    op.drop_index("ix_activities_event_type", "activities")
    op.drop_index("ix_activities_agent_id", "activities")
    op.drop_table("activities")
