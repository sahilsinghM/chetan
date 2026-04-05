"""Trade and TradeEvent ORM models."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, Boolean, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from atos.core.database import Base


class Trade(Base):
    __tablename__ = "trades"

    # ── Identity ──────────────────────────────────────────────
    id: Mapped[str] = mapped_column(String, primary_key=True)  # UUID
    symbol: Mapped[str] = mapped_column(String, nullable=False)
    instrument_type: Mapped[str] = mapped_column(String, nullable=False)
    direction: Mapped[str] = mapped_column(String, nullable=False)
    strategy: Mapped[str | None] = mapped_column(String)

    # ── Lifecycle ─────────────────────────────────────────────
    status: Mapped[str] = mapped_column(String, default="PLANNED")
    entry_date: Mapped[datetime | None] = mapped_column()
    entry_price: Mapped[float | None] = mapped_column(Float)
    exit_date: Mapped[datetime | None] = mapped_column()
    exit_price: Mapped[float | None] = mapped_column(Float)
    qty: Mapped[int | None] = mapped_column(Integer)
    qty_remaining: Mapped[int | None] = mapped_column(Integer)

    # ── Levels ────────────────────────────────────────────────
    sl: Mapped[float | None] = mapped_column(Float)
    t1: Mapped[float | None] = mapped_column(Float)
    t2: Mapped[float | None] = mapped_column(Float)
    trail_sl: Mapped[float | None] = mapped_column(Float)

    # ── Exit ──────────────────────────────────────────────────
    exit_reason: Mapped[str | None] = mapped_column(String)

    # ── PnL ───────────────────────────────────────────────────
    gross_pnl: Mapped[float | None] = mapped_column(Float)
    charges: Mapped[float | None] = mapped_column(Float)
    net_pnl: Mapped[float | None] = mapped_column(Float)

    # ── AI context ────────────────────────────────────────────
    ai_confidence: Mapped[float | None] = mapped_column(Float)
    ai_reasoning: Mapped[str | None] = mapped_column(Text)
    chart_snapshot: Mapped[str | None] = mapped_column(String)
    indicator_vals: Mapped[dict | None] = mapped_column(JSONB)
    rulebook_ver: Mapped[str | None] = mapped_column(String)
    tags: Mapped[str | None] = mapped_column(String)

    # ── Flags ─────────────────────────────────────────────────
    is_paper: Mapped[bool] = mapped_column(Boolean, default=True)
    dhan_order_id: Mapped[str | None] = mapped_column(String)

    # ── Timestamps ────────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        default=datetime.utcnow, onupdate=datetime.utcnow
    )

    events: Mapped[list["TradeEvent"]] = relationship(
        "TradeEvent", back_populates="trade", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Trade {self.id[:8]} {self.symbol} {self.direction} {self.status}>"


class TradeEvent(Base):
    __tablename__ = "trade_events"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    trade_id: Mapped[str] = mapped_column(
        String, ForeignKey("trades.id", ondelete="CASCADE"), nullable=False
    )
    event_type: Mapped[str] = mapped_column(String, nullable=False)
    ts: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    price: Mapped[float | None] = mapped_column(Float)
    qty: Mapped[int | None] = mapped_column(Integer)
    note: Mapped[str | None] = mapped_column(Text)
    raw_payload: Mapped[dict | None] = mapped_column(JSONB)

    trade: Mapped["Trade"] = relationship("Trade", back_populates="events")

    def __repr__(self) -> str:
        return f"<TradeEvent {self.event_type} trade={self.trade_id[:8]}>"
