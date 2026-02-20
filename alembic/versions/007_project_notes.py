"""Add notes column to projects table.

Revision ID: 007
Revises: 006
Create Date: 2026-02-20

Changes:
- Add nullable notes (Text) column to projects table for agent progress notes
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "007"
down_revision: str | Sequence[str] | None = "006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add notes column to projects table."""
    op.add_column("projects", sa.Column("notes", sa.Text(), nullable=True))


def downgrade() -> None:
    """Remove notes column from projects table."""
    op.drop_column("projects", "notes")
