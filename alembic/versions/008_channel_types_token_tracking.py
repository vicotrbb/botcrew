"""Add channel type values, token_usage table, and project_secrets table.

Revision ID: 008
Revises: 007
Create Date: 2026-02-20

Changes:
- Create token_usage table for per-agent LLM usage tracking
- Create project_secrets junction table for project-secret assignments
- Migrate existing project/task channels from 'shared' to 'project'/'task' types
- Add index on token_usage.agent_id for aggregation queries
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "008"
down_revision: str | Sequence[str] | None = "007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create token_usage/project_secrets tables and migrate channel types."""
    # 1. Create token_usage table
    op.create_table(
        "token_usage",
        sa.Column(
            "id",
            sa.dialects.postgresql.UUID(as_uuid=False),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        sa.Column(
            "agent_id",
            sa.dialects.postgresql.UUID(as_uuid=False),
            sa.ForeignKey("agents.id"),
            nullable=False,
        ),
        sa.Column(
            "task_id",
            sa.dialects.postgresql.UUID(as_uuid=False),
            sa.ForeignKey("tasks.id"),
            nullable=True,
        ),
        sa.Column(
            "project_id",
            sa.dialects.postgresql.UUID(as_uuid=False),
            sa.ForeignKey("projects.id"),
            nullable=True,
        ),
        sa.Column("model_provider", sa.String(50), nullable=False),
        sa.Column("model_name", sa.String(100), nullable=False),
        sa.Column("input_tokens", sa.Integer(), nullable=False),
        sa.Column("output_tokens", sa.Integer(), nullable=False),
        sa.Column("call_type", sa.String(50), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_token_usage_agent_id", "token_usage", ["agent_id"])

    # 2. Create project_secrets junction table
    op.create_table(
        "project_secrets",
        sa.Column(
            "id",
            sa.dialects.postgresql.UUID(as_uuid=False),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        sa.Column(
            "project_id",
            sa.dialects.postgresql.UUID(as_uuid=False),
            sa.ForeignKey("projects.id"),
            nullable=False,
        ),
        sa.Column(
            "secret_id",
            sa.dialects.postgresql.UUID(as_uuid=False),
            sa.ForeignKey("secrets.id"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint("project_id", "secret_id", name="uq_project_secret"),
    )

    # 3. Data migration: re-classify existing project/task channels
    op.execute(
        "UPDATE channels SET channel_type='project' "
        "WHERE id IN (SELECT channel_id FROM projects WHERE channel_id IS NOT NULL)"
    )
    op.execute(
        "UPDATE channels SET channel_type='task' "
        "WHERE id IN (SELECT channel_id FROM tasks WHERE channel_id IS NOT NULL)"
    )


def downgrade() -> None:
    """Revert token_usage, project_secrets, and channel type migration."""
    op.drop_table("token_usage")
    op.drop_table("project_secrets")
    op.execute(
        "UPDATE channels SET channel_type='shared' "
        "WHERE channel_type IN ('project', 'task')"
    )
