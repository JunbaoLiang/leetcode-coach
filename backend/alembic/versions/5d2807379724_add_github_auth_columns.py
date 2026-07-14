"""add github auth columns

Revision ID: 5d2807379724
Revises: 420659e8a0b7
Create Date: 2026-07-13 16:48:15.630535

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '5d2807379724'
down_revision: str | Sequence[str] | None = '420659e8a0b7'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add GitHub OAuth identity columns (M5 multi-user)."""
    op.add_column("users", sa.Column("github_id", sa.String(length=40), nullable=True))
    op.add_column("users", sa.Column("avatar_url", sa.String(length=300), nullable=True))
    op.add_column(
        "users",
        sa.Column("onboarded", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_index("ix_users_github_id", "users", ["github_id"], unique=True)
    # pre-existing local users finished onboarding before this column existed
    # (TRUE literal works on both PostgreSQL and SQLite; bare 1 breaks PostgreSQL)
    op.execute("UPDATE users SET onboarded = TRUE")


def downgrade() -> None:
    """Drop GitHub OAuth identity columns."""
    op.drop_index("ix_users_github_id", table_name="users")
    with op.batch_alter_table("users") as batch:
        batch.drop_column("onboarded")
        batch.drop_column("avatar_url")
        batch.drop_column("github_id")
