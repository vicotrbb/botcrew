"""Communication core schema additions.

Revision ID: 003
Revises: 002
Create Date: 2026-02-17

Changes:
- Create read_cursors table (per-user/per-agent read position tracking)
- Add channels.creator_user_identifier column
- Add messages.metadata column (JSON)
- Add unique constraint uq_channel_member_channel_user on channel_members
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "003"
down_revision: str | Sequence[str] | None = "002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Apply communication core schema changes."""

    # Create read_cursors table
    op.create_table(
        "read_cursors",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("channel_id", UUID(as_uuid=False), sa.ForeignKey("channels.id"), nullable=False),
        sa.Column("agent_id", UUID(as_uuid=False), sa.ForeignKey("agents.id"), nullable=True),
        sa.Column("user_identifier", sa.String(255), nullable=True),
        sa.Column("last_read_message_id", UUID(as_uuid=False), sa.ForeignKey("messages.id"), nullable=True),
        sa.Column("last_read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("channel_id", "agent_id", name="uq_read_cursor_channel_agent"),
        sa.UniqueConstraint("channel_id", "user_identifier", name="uq_read_cursor_channel_user"),
    )

    # Add creator_user_identifier to channels
    op.add_column(
        "channels",
        sa.Column("creator_user_identifier", sa.String(255), nullable=True),
    )

    # Add metadata column to messages
    op.add_column(
        "messages",
        sa.Column("metadata", sa.JSON(), nullable=True),
    )

    # Add unique constraint for user_identifier on channel_members
    op.create_unique_constraint(
        "uq_channel_member_channel_user",
        "channel_members",
        ["channel_id", "user_identifier"],
    )


def downgrade() -> None:
    """Reverse communication core schema changes."""

    # Drop unique constraint from channel_members
    op.drop_constraint("uq_channel_member_channel_user", "channel_members", type_="unique")

    # Drop metadata column from messages
    op.drop_column("messages", "metadata")

    # Drop creator_user_identifier from channels
    op.drop_column("channels", "creator_user_identifier")

    # Drop read_cursors table
    op.drop_table("read_cursors")
