"""Task system schema.

Revision ID: 006
Revises: 005
Create Date: 2026-02-19

Changes:
- Create tasks table
- Create task_agents junction table
- Create task_secrets junction table
- Create task_skills junction table
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "006"
down_revision: str | Sequence[str] | None = "005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create tasks, task_agents, task_secrets, and task_skills tables."""

    # 1. Create tasks table
    op.create_table(
        "tasks",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("directive", sa.Text(), nullable=False),
        sa.Column("notes", sa.Text(), server_default="", nullable=False),
        sa.Column("status", sa.String(20), server_default="open", nullable=False),
        sa.Column(
            "channel_id",
            UUID(as_uuid=False),
            sa.ForeignKey("channels.id"),
            nullable=True,
        ),
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

    # 2. Create task_agents junction table
    op.create_table(
        "task_agents",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column(
            "task_id",
            UUID(as_uuid=False),
            sa.ForeignKey("tasks.id"),
            nullable=False,
        ),
        sa.Column(
            "agent_id",
            UUID(as_uuid=False),
            sa.ForeignKey("agents.id"),
            nullable=False,
        ),
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
        sa.UniqueConstraint("task_id", "agent_id", name="uq_task_agent_task_agent"),
    )
    op.create_index("ix_task_agents_task_id", "task_agents", ["task_id"])

    # 3. Create task_secrets junction table
    op.create_table(
        "task_secrets",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column(
            "task_id",
            UUID(as_uuid=False),
            sa.ForeignKey("tasks.id"),
            nullable=False,
        ),
        sa.Column(
            "secret_id",
            UUID(as_uuid=False),
            sa.ForeignKey("secrets.id"),
            nullable=False,
        ),
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
        sa.UniqueConstraint("task_id", "secret_id", name="uq_task_secret_task_secret"),
    )
    op.create_index("ix_task_secrets_task_id", "task_secrets", ["task_id"])

    # 4. Create task_skills junction table
    op.create_table(
        "task_skills",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column(
            "task_id",
            UUID(as_uuid=False),
            sa.ForeignKey("tasks.id"),
            nullable=False,
        ),
        sa.Column(
            "skill_id",
            UUID(as_uuid=False),
            sa.ForeignKey("skills.id"),
            nullable=False,
        ),
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
        sa.UniqueConstraint("task_id", "skill_id", name="uq_task_skill_task_skill"),
    )
    op.create_index("ix_task_skills_task_id", "task_skills", ["task_id"])


def downgrade() -> None:
    """Drop task_skills, task_secrets, task_agents, and tasks tables."""

    op.drop_index("ix_task_skills_task_id", "task_skills")
    op.drop_table("task_skills")

    op.drop_index("ix_task_secrets_task_id", "task_secrets")
    op.drop_table("task_secrets")

    op.drop_index("ix_task_agents_task_id", "task_agents")
    op.drop_table("task_agents")

    op.drop_table("tasks")
