"""Journal tables (Phase 5): journal_entries, post_mortems.

Revision ID: 0003
Revises: 0002
Create Date: 2026-04-05
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "journal_entries",
        sa.Column("id", sa.BigInteger(), nullable=False, autoincrement=True),
        sa.Column("trade_id", sa.String(), nullable=True),
        sa.Column("entry_date", sa.Date(), nullable=False, server_default=sa.text("CURRENT_DATE")),
        sa.Column("category", sa.String(), nullable=True),  # PRE_TRADE, POST_TRADE, MARKET_NOTE
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("tags", sa.Text(), nullable=True),  # comma-separated
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["trade_id"], ["trades.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "post_mortems",
        sa.Column("id", sa.BigInteger(), nullable=False, autoincrement=True),
        sa.Column("week_start", sa.Date(), nullable=True),
        sa.Column("week_end", sa.Date(), nullable=True),
        sa.Column("trades_reviewed", sa.Integer(), nullable=True),
        sa.Column("win_rate", sa.Float(), nullable=True),
        sa.Column("avg_rr", sa.Float(), nullable=True),
        sa.Column("ai_insights", sa.Text(), nullable=True),
        sa.Column(
            "param_suggestions",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("post_mortems")
    op.drop_table("journal_entries")
