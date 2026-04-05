"""Screener tables (Phase 2): screener_runs, screener_results, signal_log.

Revision ID: 0002
Revises: 0001
Create Date: 2026-04-05
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "screener_runs",
        sa.Column("id", sa.BigInteger(), nullable=False, autoincrement=True),
        sa.Column("run_date", sa.Date(), nullable=False),
        sa.Column("run_type", sa.String(), nullable=True),  # MORNING, INTRADAY, SWING
        sa.Column("total_in", sa.Integer(), nullable=True),
        sa.Column("total_out", sa.Integer(), nullable=True),
        sa.Column("duration_s", sa.Float(), nullable=True),
        sa.Column("params_ver", sa.String(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "screener_results",
        sa.Column("id", sa.BigInteger(), nullable=False, autoincrement=True),
        sa.Column("run_id", sa.BigInteger(), nullable=True),
        sa.Column("symbol", sa.String(), nullable=False),
        sa.Column("composite_score", sa.Float(), nullable=True),
        sa.Column("rank", sa.Integer(), nullable=True),
        sa.Column(
            "filter_pass", postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
        sa.Column(
            "indicator_vals", postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
        sa.Column("alerted", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["run_id"], ["screener_runs.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "signal_log",
        sa.Column("id", sa.BigInteger(), nullable=False, autoincrement=True),
        sa.Column("symbol", sa.String(), nullable=False),
        sa.Column("signal_type", sa.String(), nullable=True),
        sa.Column("timeframe", sa.String(), nullable=True),
        sa.Column(
            "triggered_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "conditions", postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
        sa.Column("strength", sa.Float(), nullable=True),
        sa.Column("acted_on", sa.Boolean(), nullable=False, server_default="false"),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("signal_log")
    op.drop_table("screener_results")
    op.drop_table("screener_runs")
