"""OHLCV candle models — daily (bhav copy) and intraday."""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import BigInteger, Date, Float, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from atos.core.database import Base


class DailyCandle(Base):
    __tablename__ = "daily_candles"
    __table_args__ = (UniqueConstraint("symbol", "date", name="uq_daily_candle"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(
        String, ForeignKey("instruments.symbol"), nullable=False
    )
    date: Mapped[date] = mapped_column(Date, nullable=False)
    open: Mapped[float | None] = mapped_column(Float)
    high: Mapped[float | None] = mapped_column(Float)
    low: Mapped[float | None] = mapped_column(Float)
    close: Mapped[float | None] = mapped_column(Float)
    volume: Mapped[int | None] = mapped_column(BigInteger)
    delivery_pct: Mapped[float | None] = mapped_column(Float)

    def __repr__(self) -> str:
        return f"<DailyCandle {self.symbol} {self.date} C={self.close}>"


class IntradayCandle(Base):
    __tablename__ = "intraday_candles"
    __table_args__ = (
        UniqueConstraint("symbol", "timeframe", "ts", name="uq_intraday_candle"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String, nullable=False)
    timeframe: Mapped[str] = mapped_column(String, nullable=False)  # 1min, 5min, 15min
    ts: Mapped[datetime] = mapped_column(nullable=False)
    open: Mapped[float | None] = mapped_column(Float)
    high: Mapped[float | None] = mapped_column(Float)
    low: Mapped[float | None] = mapped_column(Float)
    close: Mapped[float | None] = mapped_column(Float)
    volume: Mapped[int | None] = mapped_column(BigInteger)

    def __repr__(self) -> str:
        return f"<IntradayCandle {self.symbol} {self.timeframe} {self.ts}>"
