"""Agent lifecycle schema adjustments.

Revision ID: 002
Revises: 001
Create Date: 2026-02-16

Changes:
- agents.status server_default: 'created' -> 'creating' (Phase 2 state machine)
- agents.heartbeat_interval_seconds server_default: '900' -> '300' (5-min default)
- Add agents.last_active_at column (nullable timestamp)
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "002"
down_revision: str | Sequence[str] | None = "001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Apply agent lifecycle schema changes."""

    # Change status default from 'created' to 'creating'
    op.alter_column(
        "agents",
        "status",
        server_default="creating",
    )

    # Change heartbeat_interval_seconds default from 900 to 300
    op.alter_column(
        "agents",
        "heartbeat_interval_seconds",
        server_default="300",
    )

    # Add last_active_at column for tracking agent activity
    op.add_column(
        "agents",
        sa.Column("last_active_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    """Reverse agent lifecycle schema changes."""

    # Remove last_active_at column
    op.drop_column("agents", "last_active_at")

    # Restore heartbeat_interval_seconds default to 900
    op.alter_column(
        "agents",
        "heartbeat_interval_seconds",
        server_default="900",
    )

    # Restore status default to 'created'
    op.alter_column(
        "agents",
        "status",
        server_default="created",
    )
