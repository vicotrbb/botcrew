"""Projects and workspaces schema additions.

Revision ID: 005
Revises: 004
Create Date: 2026-02-17

Changes:
- Add role_prompt column to project_agents table
- Create project_files table for backed-up spec/planning files
- Add index on project_files.project_id for efficient lookups
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "005"
down_revision: str | Sequence[str] | None = "004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add role_prompt to project_agents and create project_files table."""

    # 1. Add role_prompt column to project_agents
    op.add_column(
        "project_agents",
        sa.Column("role_prompt", sa.Text(), nullable=True),
    )

    # 2. Create project_files table
    op.create_table(
        "project_files",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column(
            "project_id",
            UUID(as_uuid=False),
            sa.ForeignKey("projects.id"),
            nullable=False,
        ),
        sa.Column("path", sa.String(500), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("size", sa.Integer(), nullable=False),
        sa.Column(
            "last_modified",
            sa.DateTime(timezone=True),
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
        sa.UniqueConstraint(
            "project_id", "path", name="uq_project_file_project_path"
        ),
    )

    # Index for efficient project file lookups
    op.create_index(
        "ix_project_files_project_id", "project_files", ["project_id"]
    )


def downgrade() -> None:
    """Remove project_files table and role_prompt column."""

    op.drop_index("ix_project_files_project_id", "project_files")
    op.drop_table("project_files")
    op.drop_column("project_agents", "role_prompt")
