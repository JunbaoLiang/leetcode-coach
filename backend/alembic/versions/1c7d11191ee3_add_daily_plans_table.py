"""add daily plans table

Revision ID: 1c7d11191ee3
Revises: 5d2807379724
Create Date: 2026-07-16 15:24:17.727580

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '1c7d11191ee3'
down_revision: str | Sequence[str] | None = '5d2807379724'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add daily_plans — one frozen checklist per (user, day)."""
    op.create_table(
        "daily_plans",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("plan_date", sa.Date(), nullable=False),
        sa.Column("items", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("user_id", "plan_date", name="uq_daily_plan_user_date"),
    )
    op.create_index("ix_daily_plans_user_id", "daily_plans", ["user_id"])


def downgrade() -> None:
    """Drop daily_plans."""
    op.drop_index("ix_daily_plans_user_id", table_name="daily_plans")
    op.drop_table("daily_plans")
