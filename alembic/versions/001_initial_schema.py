"""Initial schema - all domain tables.

Revision ID: 001
Revises:
Create Date: 2026-02-16

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create all domain tables."""

    # 1. agents (no FKs)
    op.create_table(
        "agents",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("identity", sa.Text, server_default="", nullable=False),
        sa.Column("personality", sa.Text, server_default="", nullable=False),
        sa.Column("memory", sa.Text, server_default="", nullable=False),
        sa.Column("heartbeat_prompt", sa.Text, server_default="", nullable=False),
        sa.Column("heartbeat_interval_seconds", sa.Integer, server_default="900", nullable=False),
        sa.Column("heartbeat_enabled", sa.Boolean, server_default="true", nullable=False),
        sa.Column("model_provider", sa.String(50), server_default="anthropic", nullable=False),
        sa.Column("model_name", sa.String(100), server_default="claude-sonnet-4-20250514", nullable=False),
        sa.Column("avatar_url", sa.Text, nullable=True),
        sa.Column("status", sa.String(20), server_default="created", nullable=False),
        sa.Column("pod_name", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
    )

    # 2. channels (no FKs)
    op.create_table(
        "channels",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("channel_type", sa.String(20), server_default="shared", nullable=False),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
    )

    # 3. skills (no FKs)
    op.create_table(
        "skills",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False, unique=True),
        sa.Column("description", sa.String(250), nullable=False),
        sa.Column("body", sa.Text, nullable=False),
        sa.Column("is_active", sa.Boolean, server_default="true", nullable=False),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
    )

    # 4. secrets (no FKs)
    op.create_table(
        "secrets",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("key", sa.String(255), nullable=False, unique=True),
        sa.Column("value", sa.Text, nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
    )

    # 5. channel_members (FKs to channels, agents)
    op.create_table(
        "channel_members",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("channel_id", UUID(as_uuid=False), sa.ForeignKey("channels.id"), nullable=False),
        sa.Column("agent_id", UUID(as_uuid=False), sa.ForeignKey("agents.id"), nullable=True),
        sa.Column("user_identifier", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("channel_id", "agent_id", name="uq_channel_member_channel_agent"),
    )

    # 6. messages (FKs to channels, agents)
    op.create_table(
        "messages",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("channel_id", UUID(as_uuid=False), sa.ForeignKey("channels.id"), nullable=False),
        sa.Column("sender_agent_id", UUID(as_uuid=False), sa.ForeignKey("agents.id"), nullable=True),
        sa.Column("sender_user_identifier", sa.String(255), nullable=True),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("message_type", sa.String(20), server_default="chat", nullable=False),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
    )

    # 7. projects (FK to channels)
    op.create_table(
        "projects",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("goals", sa.Text, nullable=True),
        sa.Column("specs", sa.Text, nullable=True),
        sa.Column("github_repo_url", sa.Text, nullable=True),
        sa.Column("channel_id", UUID(as_uuid=False), sa.ForeignKey("channels.id"), nullable=True),
        sa.Column("status", sa.String(20), server_default="active", nullable=False),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
    )

    # 8. project_agents (FKs to projects, agents)
    op.create_table(
        "project_agents",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("project_id", UUID(as_uuid=False), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("agent_id", UUID(as_uuid=False), sa.ForeignKey("agents.id"), nullable=False),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("project_id", "agent_id", name="uq_project_agent_project_agent"),
    )

    # 9. integrations (FKs to agents, channels)
    op.create_table(
        "integrations",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("integration_type", sa.String(50), nullable=False),
        sa.Column("config", sa.Text, nullable=False),
        sa.Column("agent_id", UUID(as_uuid=False), sa.ForeignKey("agents.id"), nullable=True),
        sa.Column("channel_id", UUID(as_uuid=False), sa.ForeignKey("channels.id"), nullable=True),
        sa.Column("is_active", sa.Boolean, server_default="true", nullable=False),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    """Drop all domain tables in reverse dependency order."""
    op.drop_table("integrations")
    op.drop_table("project_agents")
    op.drop_table("projects")
    op.drop_table("messages")
    op.drop_table("channel_members")
    op.drop_table("secrets")
    op.drop_table("skills")
    op.drop_table("channels")
    op.drop_table("agents")
