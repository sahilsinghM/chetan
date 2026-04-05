"""Initial schema: instruments, candles, trades, event_log.

Revision ID: 0001
Revises:
Create Date: 2026-04-05
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── instruments ───────────────────────────────────────────
    op.create_table(
        "instruments",
        sa.Column("symbol", sa.String(), nullable=False),
        sa.Column("isin", sa.String(), nullable=True),
        sa.Column("company_name", sa.String(), nullable=True),
        sa.Column("sector", sa.String(), nullable=True),
        sa.Column("series", sa.String(), nullable=False, server_default="EQ"),
        sa.Column("exchange", sa.String(), nullable=False, server_default="NSE"),
        sa.Column("lot_size", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("tick_size", sa.Float(), nullable=False, server_default="0.05"),
        sa.Column("is_fno", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("is_nse500", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("symbol"),
        sa.UniqueConstraint("isin", name="uq_instrument_isin"),
    )

    # ── daily_candles ─────────────────────────────────────────
    op.create_table(
        "daily_candles",
        sa.Column(
            "id", sa.BigInteger(), nullable=False, autoincrement=True
        ),
        sa.Column("symbol", sa.String(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("open", sa.Float(), nullable=True),
        sa.Column("high", sa.Float(), nullable=True),
        sa.Column("low", sa.Float(), nullable=True),
        sa.Column("close", sa.Float(), nullable=True),
        sa.Column("volume", sa.BigInteger(), nullable=True),
        sa.Column("delivery_pct", sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(["symbol"], ["instruments.symbol"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("symbol", "date", name="uq_daily_candle"),
    )
    op.create_index(
        "idx_daily_candles_symbol_date",
        "daily_candles",
        ["symbol", sa.text("date DESC")],
    )

    # ── intraday_candles ──────────────────────────────────────
    op.create_table(
        "intraday_candles",
        sa.Column("id", sa.BigInteger(), nullable=False, autoincrement=True),
        sa.Column("symbol", sa.String(), nullable=False),
        sa.Column("timeframe", sa.String(), nullable=False),
        sa.Column("ts", sa.DateTime(), nullable=False),
        sa.Column("open", sa.Float(), nullable=True),
        sa.Column("high", sa.Float(), nullable=True),
        sa.Column("low", sa.Float(), nullable=True),
        sa.Column("close", sa.Float(), nullable=True),
        sa.Column("volume", sa.BigInteger(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("symbol", "timeframe", "ts", name="uq_intraday_candle"),
    )

    # ── trades ────────────────────────────────────────────────
    op.create_table(
        "trades",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("symbol", sa.String(), nullable=False),
        sa.Column("instrument_type", sa.String(), nullable=False),
        sa.Column("direction", sa.String(), nullable=False),
        sa.Column("strategy", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=False, server_default="PLANNED"),
        sa.Column("entry_date", sa.DateTime(), nullable=True),
        sa.Column("entry_price", sa.Float(), nullable=True),
        sa.Column("exit_date", sa.DateTime(), nullable=True),
        sa.Column("exit_price", sa.Float(), nullable=True),
        sa.Column("qty", sa.Integer(), nullable=True),
        sa.Column("qty_remaining", sa.Integer(), nullable=True),
        sa.Column("sl", sa.Float(), nullable=True),
        sa.Column("t1", sa.Float(), nullable=True),
        sa.Column("t2", sa.Float(), nullable=True),
        sa.Column("trail_sl", sa.Float(), nullable=True),
        sa.Column("exit_reason", sa.String(), nullable=True),
        sa.Column("gross_pnl", sa.Float(), nullable=True),
        sa.Column("charges", sa.Float(), nullable=True),
        sa.Column("net_pnl", sa.Float(), nullable=True),
        sa.Column("ai_confidence", sa.Float(), nullable=True),
        sa.Column("ai_reasoning", sa.Text(), nullable=True),
        sa.Column("chart_snapshot", sa.String(), nullable=True),
        sa.Column(
            "indicator_vals", postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
        sa.Column("rulebook_ver", sa.String(), nullable=True),
        sa.Column("tags", sa.String(), nullable=True),
        sa.Column("is_paper", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("dhan_order_id", sa.String(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_trades_symbol", "trades", ["symbol"])
    op.create_index("idx_trades_status", "trades", ["status"])
    op.create_index(
        "idx_trades_entry_date", "trades", [sa.text("entry_date DESC")]
    )

    # ── trade_events ──────────────────────────────────────────
    op.create_table(
        "trade_events",
        sa.Column("id", sa.BigInteger(), nullable=False, autoincrement=True),
        sa.Column("trade_id", sa.String(), nullable=False),
        sa.Column("event_type", sa.String(), nullable=False),
        sa.Column(
            "ts",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("price", sa.Float(), nullable=True),
        sa.Column("qty", sa.Integer(), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column(
            "raw_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
        sa.ForeignKeyConstraint(
            ["trade_id"], ["trades.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # ── event_log ─────────────────────────────────────────────
    op.create_table(
        "event_log",
        sa.Column("id", sa.BigInteger(), nullable=False, autoincrement=True),
        sa.Column("event_type", sa.String(), nullable=False),
        sa.Column("trade_id", sa.String(), nullable=True),
        sa.Column("symbol", sa.String(), nullable=True),
        sa.Column("source", sa.String(), nullable=True),
        sa.Column(
            "payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_event_log_type", "event_log", ["event_type"])
    op.create_index(
        "idx_event_log_created_at", "event_log", [sa.text("created_at DESC")]
    )


def downgrade() -> None:
    op.drop_table("event_log")
    op.drop_table("trade_events")
    op.drop_table("trades")
    op.drop_table("intraday_candles")
    op.drop_table("daily_candles")
    op.drop_table("instruments")
